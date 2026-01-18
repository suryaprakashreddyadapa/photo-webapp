"""
User management routes.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.db.session import get_db
from app.models.models import User, Media
from app.schemas.schemas import (
    UserResponse, UserUpdate, UserAdminUpdate, UserSettings, UserStats
)
from app.api.deps import get_current_user, get_current_admin_user
from app.core.security import get_password_hash


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    
    if user_data.settings is not None:
        current_user.settings = {**current_user.settings, **user_data.settings}
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/me/settings", response_model=UserSettings)
async def get_user_settings(
    current_user: User = Depends(get_current_user)
):
    """Get current user settings."""
    default_settings = UserSettings()
    user_settings = current_user.settings or {}
    
    return UserSettings(**{**default_settings.model_dump(), **user_settings})


@router.put("/me/settings", response_model=UserSettings)
async def update_user_settings(
    settings: UserSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user settings."""
    current_user.settings = settings.model_dump()
    await db.commit()
    
    return settings


@router.get("/me/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user statistics."""
    # Count photos
    photo_count = await db.execute(
        select(func.count(Media.id)).where(
            Media.owner_id == current_user.id,
            Media.media_type == "photo",
            Media.is_deleted == False
        )
    )
    total_photos = photo_count.scalar() or 0
    
    # Count videos
    video_count = await db.execute(
        select(func.count(Media.id)).where(
            Media.owner_id == current_user.id,
            Media.media_type == "video",
            Media.is_deleted == False
        )
    )
    total_videos = video_count.scalar() or 0
    
    # Count albums
    from app.models.models import Album
    album_count = await db.execute(
        select(func.count(Album.id)).where(Album.owner_id == current_user.id)
    )
    total_albums = album_count.scalar() or 0
    
    # Count people
    from app.models.models import Person
    people_count = await db.execute(
        select(func.count(Person.id)).where(Person.owner_id == current_user.id)
    )
    total_people = people_count.scalar() or 0
    
    # Photos by year
    photos_by_year_result = await db.execute(
        select(
            func.extract('year', Media.taken_at).label('year'),
            func.count(Media.id).label('count')
        ).where(
            Media.owner_id == current_user.id,
            Media.is_deleted == False,
            Media.taken_at.isnot(None)
        ).group_by('year').order_by('year')
    )
    photos_by_year = {int(row.year): row.count for row in photos_by_year_result if row.year}
    
    # Photos by month (last 12 months)
    photos_by_month_result = await db.execute(
        select(
            func.to_char(Media.taken_at, 'YYYY-MM').label('month'),
            func.count(Media.id).label('count')
        ).where(
            Media.owner_id == current_user.id,
            Media.is_deleted == False,
            Media.taken_at.isnot(None)
        ).group_by('month').order_by('month')
    )
    photos_by_month = {row.month: row.count for row in photos_by_month_result if row.month}
    
    return UserStats(
        total_photos=total_photos,
        total_videos=total_videos,
        total_albums=total_albums,
        total_people=total_people,
        storage_used_bytes=current_user.storage_used_bytes,
        storage_quota_bytes=current_user.storage_quota_gb * 1024 * 1024 * 1024,
        photos_by_year=photos_by_year,
        photos_by_month=photos_by_month
    )


@router.put("/me/password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user password."""
    from app.core.security import verify_password
    
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    current_user.hashed_password = get_password_hash(new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


# ============== Admin Routes ==============

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = None,  # pending, active, inactive
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)."""
    query = select(User)
    
    if search:
        query = query.where(
            or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    if status_filter == "pending":
        query = query.where(User.is_approved == False, User.is_verified == True)
    elif status_filter == "active":
        query = query.where(User.is_active == True, User.is_approved == True)
    elif status_filter == "inactive":
        query = query.where(User.is_active == False)
    
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return users


@router.get("/pending", response_model=List[UserResponse])
async def list_pending_users(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List users pending approval (admin only)."""
    result = await db.execute(
        select(User).where(
            User.is_verified == True,
            User.is_approved == False
        ).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserAdminUpdate,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    if user_data.is_approved is not None:
        user.is_approved = user_data.is_approved
    
    if user_data.role is not None:
        user.role = user_data.role
    
    if user_data.nas_path is not None:
        user.nas_path = user_data.nas_path
    
    if user_data.storage_quota_gb is not None:
        user.storage_quota_gb = user_data.storage_quota_gb
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/{user_id}/approve", response_model=UserResponse)
async def approve_user(
    user_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve a pending user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_approved = True
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/{user_id}/reject")
async def reject_user(
    user_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject a pending user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User rejected and deleted"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (admin only)."""
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}
