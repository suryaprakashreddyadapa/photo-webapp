"""
Media management routes.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import os
import aiofiles

from app.db.session import get_db
from app.models.models import User, Media, Tag, media_tags
from app.schemas.schemas import (
    MediaResponse, MediaUpdate, MediaBulkAction, PaginatedResponse
)
from app.api.deps import get_current_user
from app.core.config import settings


router = APIRouter(prefix="/media", tags=["Media"])


def media_to_response(media: Media, tags: List[str] = None, faces_count: int = 0) -> MediaResponse:
    """Convert Media model to response schema."""
    return MediaResponse(
        id=media.id,
        filename=media.filename,
        original_path=media.original_path,
        relative_path=media.relative_path,
        file_size=media.file_size,
        mime_type=media.mime_type,
        media_type=media.media_type,
        width=media.width,
        height=media.height,
        duration=media.duration,
        thumbnail_small=media.thumbnail_small,
        thumbnail_medium=media.thumbnail_medium,
        thumbnail_large=media.thumbnail_large,
        taken_at=media.taken_at,
        camera_make=media.camera_make,
        camera_model=media.camera_model,
        latitude=media.latitude,
        longitude=media.longitude,
        location_name=media.location_name,
        is_favorite=media.is_favorite,
        is_hidden=media.is_hidden,
        created_at=media.created_at,
        tags=tags or [],
        faces_count=faces_count
    )


@router.get("/", response_model=PaginatedResponse)
async def list_media(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    media_type: Optional[str] = None,
    sort_by: str = Query("taken_at", regex="^(taken_at|created_at|filename)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    favorites_only: bool = False,
    hidden: bool = False,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's media with pagination and filters."""
    query = select(Media).where(
        Media.owner_id == current_user.id,
        Media.is_deleted == False
    )
    
    if media_type:
        query = query.where(Media.media_type == media_type)
    
    if favorites_only:
        query = query.where(Media.is_favorite == True)
    
    if not hidden:
        query = query.where(Media.is_hidden == False)
    
    if year:
        query = query.where(func.extract('year', Media.taken_at) == year)
    
    if month:
        query = query.where(func.extract('month', Media.taken_at) == month)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = getattr(Media, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    media_items = result.scalars().all()
    
    # Get tags and face counts for each media
    items = []
    for media in media_items:
        # Get tags
        tags_result = await db.execute(
            select(Tag.name).join(media_tags).where(media_tags.c.media_id == media.id)
        )
        tags = [row[0] for row in tags_result]
        
        # Get face count
        from app.models.models import Face
        face_count_result = await db.execute(
            select(func.count(Face.id)).where(Face.media_id == media.id)
        )
        faces_count = face_count_result.scalar() or 0
        
        items.append(media_to_response(media, tags, faces_count))
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=items
    )


@router.get("/timeline")
async def get_timeline(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media grouped by date for timeline view."""
    result = await db.execute(
        select(
            func.date(Media.taken_at).label('date'),
            func.count(Media.id).label('count')
        ).where(
            Media.owner_id == current_user.id,
            Media.is_deleted == False,
            Media.is_hidden == False,
            Media.taken_at.isnot(None)
        ).group_by('date').order_by(func.date(Media.taken_at).desc())
    )
    
    timeline = [
        {"date": str(row.date), "count": row.count}
        for row in result
    ]
    
    return timeline


@router.get("/map")
async def get_map_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media with location data for map view."""
    result = await db.execute(
        select(Media).where(
            Media.owner_id == current_user.id,
            Media.is_deleted == False,
            Media.is_hidden == False,
            Media.latitude.isnot(None),
            Media.longitude.isnot(None)
        ).limit(10000)  # Limit for performance
    )
    
    media_items = result.scalars().all()
    
    return [
        {
            "id": str(media.id),
            "latitude": media.latitude,
            "longitude": media.longitude,
            "thumbnail": media.thumbnail_small,
            "taken_at": media.taken_at.isoformat() if media.taken_at else None
        }
        for media in media_items
    ]


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media by ID."""
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == current_user.id
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Get tags
    tags_result = await db.execute(
        select(Tag.name).join(media_tags).where(media_tags.c.media_id == media.id)
    )
    tags = [row[0] for row in tags_result]
    
    # Get face count
    from app.models.models import Face
    face_count_result = await db.execute(
        select(func.count(Face.id)).where(Face.media_id == media.id)
    )
    faces_count = face_count_result.scalar() or 0
    
    return media_to_response(media, tags, faces_count)


@router.put("/{media_id}", response_model=MediaResponse)
async def update_media(
    media_id: UUID,
    media_data: MediaUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update media metadata."""
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == current_user.id
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    if media_data.is_favorite is not None:
        media.is_favorite = media_data.is_favorite
    
    if media_data.is_hidden is not None:
        media.is_hidden = media_data.is_hidden
    
    await db.commit()
    await db.refresh(media)
    
    return media_to_response(media)


@router.delete("/{media_id}")
async def delete_media(
    media_id: UUID,
    permanent: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete media (soft delete by default)."""
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == current_user.id
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    if permanent:
        await db.delete(media)
    else:
        media.is_deleted = True
        media.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Media deleted successfully"}


@router.post("/bulk")
async def bulk_action(
    action_data: MediaBulkAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform bulk actions on media."""
    result = await db.execute(
        select(Media).where(
            Media.id.in_(action_data.media_ids),
            Media.owner_id == current_user.id
        )
    )
    media_items = result.scalars().all()
    
    if not media_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No media found"
        )
    
    for media in media_items:
        if action_data.action == "favorite":
            media.is_favorite = True
        elif action_data.action == "unfavorite":
            media.is_favorite = False
        elif action_data.action == "hide":
            media.is_hidden = True
        elif action_data.action == "unhide":
            media.is_hidden = False
        elif action_data.action == "delete":
            media.is_deleted = True
            media.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"Bulk action '{action_data.action}' completed", "count": len(media_items)}


@router.get("/{media_id}/file")
async def get_media_file(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the original media file."""
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == current_user.id
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    file_path = media.original_path
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    return FileResponse(
        file_path,
        media_type=media.mime_type,
        filename=media.filename
    )


@router.get("/{media_id}/thumbnail/{size}")
async def get_thumbnail(
    media_id: UUID,
    size: str = Query(..., regex="^(small|medium|large)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media thumbnail."""
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == current_user.id
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    thumbnail_path = None
    if size == "small":
        thumbnail_path = media.thumbnail_small
    elif size == "medium":
        thumbnail_path = media.thumbnail_medium
    elif size == "large":
        thumbnail_path = media.thumbnail_large
    
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not found"
        )
    
    return FileResponse(thumbnail_path, media_type="image/jpeg")


@router.get("/{media_id}/faces")
async def get_media_faces(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get faces detected in media."""
    from app.models.models import Face, Person
    
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == current_user.id
        )
    )
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    faces_result = await db.execute(
        select(Face, Person.name).outerjoin(Person).where(Face.media_id == media_id)
    )
    
    faces = []
    for face, person_name in faces_result:
        faces.append({
            "id": str(face.id),
            "person_id": str(face.person_id) if face.person_id else None,
            "person_name": person_name,
            "x": face.x,
            "y": face.y,
            "width": face.width,
            "height": face.height,
            "confidence": face.confidence
        })
    
    return faces


@router.get("/trash/")
async def list_trash(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List deleted media (trash)."""
    query = select(Media).where(
        Media.owner_id == current_user.id,
        Media.is_deleted == True
    ).order_by(Media.deleted_at.desc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    media_items = result.scalars().all()
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=[media_to_response(media) for media in media_items]
    )


@router.post("/trash/restore")
async def restore_from_trash(
    media_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore media from trash."""
    result = await db.execute(
        select(Media).where(
            Media.id.in_(media_ids),
            Media.owner_id == current_user.id,
            Media.is_deleted == True
        )
    )
    media_items = result.scalars().all()
    
    for media in media_items:
        media.is_deleted = False
        media.deleted_at = None
    
    await db.commit()
    
    return {"message": f"Restored {len(media_items)} items"}


@router.delete("/trash/empty")
async def empty_trash(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete all items in trash."""
    result = await db.execute(
        select(Media).where(
            Media.owner_id == current_user.id,
            Media.is_deleted == True
        )
    )
    media_items = result.scalars().all()
    
    count = len(media_items)
    for media in media_items:
        await db.delete(media)
    
    await db.commit()
    
    return {"message": f"Permanently deleted {count} items"}
