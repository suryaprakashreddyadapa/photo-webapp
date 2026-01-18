"""
Album management routes.
"""
from typing import List, Optional
from uuid import UUID
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.models import User, Album, Media, album_media, SmartAlbum
from app.schemas.schemas import (
    AlbumCreate, AlbumResponse, AlbumUpdate, AlbumAddMedia,
    SmartAlbumCreate, SmartAlbumResponse, MediaResponse, PaginatedResponse
)
from app.api.deps import get_current_user


router = APIRouter(prefix="/albums", tags=["Albums"])


def album_to_response(album: Album, media_count: int = 0, cover_thumbnail: str = None) -> AlbumResponse:
    """Convert Album model to response schema."""
    return AlbumResponse(
        id=album.id,
        name=album.name,
        description=album.description,
        cover_media_id=album.cover_media_id,
        cover_thumbnail=cover_thumbnail,
        media_count=media_count,
        is_shared=album.is_shared,
        share_token=album.share_token if album.is_shared else None,
        created_at=album.created_at,
        updated_at=album.updated_at
    )


@router.get("/", response_model=List[AlbumResponse])
async def list_albums(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's albums."""
    result = await db.execute(
        select(Album).where(Album.owner_id == current_user.id).order_by(Album.updated_at.desc())
    )
    albums = result.scalars().all()
    
    response = []
    for album in albums:
        # Get media count
        count_result = await db.execute(
            select(func.count()).select_from(album_media).where(album_media.c.album_id == album.id)
        )
        media_count = count_result.scalar() or 0
        
        # Get cover thumbnail
        cover_thumbnail = None
        if album.cover_media_id:
            cover_result = await db.execute(
                select(Media.thumbnail_medium).where(Media.id == album.cover_media_id)
            )
            cover_thumbnail = cover_result.scalar()
        elif media_count > 0:
            # Use first media as cover
            first_media = await db.execute(
                select(Media.thumbnail_medium).join(album_media).where(
                    album_media.c.album_id == album.id
                ).order_by(album_media.c.added_at.desc()).limit(1)
            )
            cover_thumbnail = first_media.scalar()
        
        response.append(album_to_response(album, media_count, cover_thumbnail))
    
    return response


@router.post("/", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    album_data: AlbumCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new album."""
    # Check for duplicate name
    existing = await db.execute(
        select(Album).where(
            Album.owner_id == current_user.id,
            Album.name == album_data.name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Album with this name already exists"
        )
    
    album = Album(
        owner_id=current_user.id,
        name=album_data.name,
        description=album_data.description
    )
    
    db.add(album)
    await db.commit()
    await db.refresh(album)
    
    return album_to_response(album)


@router.get("/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get album by ID."""
    result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Get media count
    count_result = await db.execute(
        select(func.count()).select_from(album_media).where(album_media.c.album_id == album.id)
    )
    media_count = count_result.scalar() or 0
    
    # Get cover thumbnail
    cover_thumbnail = None
    if album.cover_media_id:
        cover_result = await db.execute(
            select(Media.thumbnail_medium).where(Media.id == album.cover_media_id)
        )
        cover_thumbnail = cover_result.scalar()
    
    return album_to_response(album, media_count, cover_thumbnail)


@router.put("/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: UUID,
    album_data: AlbumUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update album."""
    result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    if album_data.name is not None:
        # Check for duplicate name
        existing = await db.execute(
            select(Album).where(
                Album.owner_id == current_user.id,
                Album.name == album_data.name,
                Album.id != album_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Album with this name already exists"
            )
        album.name = album_data.name
    
    if album_data.description is not None:
        album.description = album_data.description
    
    if album_data.cover_media_id is not None:
        album.cover_media_id = album_data.cover_media_id
    
    await db.commit()
    await db.refresh(album)
    
    return album_to_response(album)


@router.delete("/{album_id}")
async def delete_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete album (media is not deleted)."""
    result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    await db.delete(album)
    await db.commit()
    
    return {"message": "Album deleted successfully"}


@router.get("/{album_id}/media", response_model=PaginatedResponse)
async def get_album_media(
    album_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media in album."""
    # Verify album ownership
    album_result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    if not album_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(album_media).where(album_media.c.album_id == album_id)
    )
    total = count_result.scalar() or 0
    
    # Get media
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Media).join(album_media).where(
            album_media.c.album_id == album_id
        ).order_by(album_media.c.order, album_media.c.added_at.desc()).offset(offset).limit(page_size)
    )
    media_items = result.scalars().all()
    
    from app.api.routes.media import media_to_response
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        items=[media_to_response(media) for media in media_items]
    )


@router.post("/{album_id}/media")
async def add_media_to_album(
    album_id: UUID,
    data: AlbumAddMedia,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add media to album."""
    # Verify album ownership
    album_result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    album = album_result.scalar_one_or_none()
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Verify media ownership
    media_result = await db.execute(
        select(Media).where(
            Media.id.in_(data.media_ids),
            Media.owner_id == current_user.id
        )
    )
    media_items = media_result.scalars().all()
    
    if len(media_items) != len(data.media_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some media items not found"
        )
    
    # Add media to album
    added_count = 0
    for media in media_items:
        # Check if already in album
        existing = await db.execute(
            select(album_media).where(
                album_media.c.album_id == album_id,
                album_media.c.media_id == media.id
            )
        )
        if not existing.first():
            await db.execute(
                album_media.insert().values(album_id=album_id, media_id=media.id)
            )
            added_count += 1
    
    await db.commit()
    
    return {"message": f"Added {added_count} items to album"}


@router.delete("/{album_id}/media")
async def remove_media_from_album(
    album_id: UUID,
    media_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove media from album."""
    # Verify album ownership
    album_result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    if not album_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    # Remove media from album
    await db.execute(
        album_media.delete().where(
            album_media.c.album_id == album_id,
            album_media.c.media_id.in_(media_ids)
        )
    )
    
    await db.commit()
    
    return {"message": "Media removed from album"}


@router.post("/{album_id}/share")
async def share_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable sharing for album."""
    result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    if not album.share_token:
        album.share_token = secrets.token_urlsafe(32)
    
    album.is_shared = True
    await db.commit()
    
    return {"share_token": album.share_token}


@router.delete("/{album_id}/share")
async def unshare_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable sharing for album."""
    result = await db.execute(
        select(Album).where(
            Album.id == album_id,
            Album.owner_id == current_user.id
        )
    )
    album = result.scalar_one_or_none()
    
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found"
        )
    
    album.is_shared = False
    await db.commit()
    
    return {"message": "Album sharing disabled"}


# ============== Smart Albums ==============

@router.get("/smart/", response_model=List[SmartAlbumResponse])
async def list_smart_albums(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's smart albums."""
    result = await db.execute(
        select(SmartAlbum).where(SmartAlbum.owner_id == current_user.id).order_by(SmartAlbum.created_at.desc())
    )
    smart_albums = result.scalars().all()
    
    return smart_albums


@router.post("/smart/", response_model=SmartAlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_smart_album(
    album_data: SmartAlbumCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a smart album (saved search query)."""
    smart_album = SmartAlbum(
        owner_id=current_user.id,
        name=album_data.name,
        description=album_data.description,
        query=album_data.query,
        filters=album_data.filters
    )
    
    db.add(smart_album)
    await db.commit()
    await db.refresh(smart_album)
    
    return smart_album


@router.get("/smart/{album_id}", response_model=SmartAlbumResponse)
async def get_smart_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get smart album by ID."""
    result = await db.execute(
        select(SmartAlbum).where(
            SmartAlbum.id == album_id,
            SmartAlbum.owner_id == current_user.id
        )
    )
    smart_album = result.scalar_one_or_none()
    
    if not smart_album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Smart album not found"
        )
    
    return smart_album


@router.delete("/smart/{album_id}")
async def delete_smart_album(
    album_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete smart album."""
    result = await db.execute(
        select(SmartAlbum).where(
            SmartAlbum.id == album_id,
            SmartAlbum.owner_id == current_user.id
        )
    )
    smart_album = result.scalar_one_or_none()
    
    if not smart_album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Smart album not found"
        )
    
    await db.delete(smart_album)
    await db.commit()
    
    return {"message": "Smart album deleted"}


@router.get("/smart/{album_id}/media", response_model=PaginatedResponse)
async def get_smart_album_media(
    album_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media matching smart album query."""
    result = await db.execute(
        select(SmartAlbum).where(
            SmartAlbum.id == album_id,
            SmartAlbum.owner_id == current_user.id
        )
    )
    smart_album = result.scalar_one_or_none()
    
    if not smart_album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Smart album not found"
        )
    
    # Execute the search query
    from app.services.ai.search import semantic_search
    
    search_results = await semantic_search(
        db=db,
        user_id=current_user.id,
        query=smart_album.query,
        filters=smart_album.filters,
        page=page,
        page_size=page_size
    )
    
    return search_results
