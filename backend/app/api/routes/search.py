"""
Search and AI assistant routes.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.db.session import get_db
from app.models.models import User, Media, Tag, media_tags, Person, Face, Album
from app.schemas.schemas import (
    SearchQuery, SearchResponse, AskQuery, AskResponse, MediaResponse,
    AlbumCreate, SmartAlbumCreate
)
from app.api.deps import get_current_user
from app.services.ai.search import semantic_search, parse_natural_language_query
from app.services.ai.clip_service import get_text_embedding


router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/", response_model=SearchResponse)
async def search_media(
    query_data: SearchQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search media using natural language or filters."""
    results = await semantic_search(
        db=db,
        user_id=current_user.id,
        query=query_data.query,
        filters=query_data.filters,
        page=query_data.page,
        page_size=query_data.page_size,
        sort_by=query_data.sort_by,
        sort_order=query_data.sort_order
    )
    
    return results


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get search suggestions based on partial query."""
    suggestions = []
    
    # Search tags
    tag_result = await db.execute(
        select(Tag.name).where(Tag.name.ilike(f"%{q}%")).limit(5)
    )
    suggestions.extend([f"tag:{row[0]}" for row in tag_result])
    
    # Search people
    person_result = await db.execute(
        select(Person.name).where(
            Person.owner_id == current_user.id,
            Person.name.ilike(f"%{q}%"),
            Person.is_named == True
        ).limit(5)
    )
    suggestions.extend([f"person:{row[0]}" for row in person_result if row[0]])
    
    # Search locations
    location_result = await db.execute(
        select(func.distinct(Media.location_name)).where(
            Media.owner_id == current_user.id,
            Media.location_name.ilike(f"%{q}%")
        ).limit(5)
    )
    suggestions.extend([f"location:{row[0]}" for row in location_result if row[0]])
    
    # Search albums
    album_result = await db.execute(
        select(Album.name).where(
            Album.owner_id == current_user.id,
            Album.name.ilike(f"%{q}%")
        ).limit(5)
    )
    suggestions.extend([f"album:{row[0]}" for row in album_result])
    
    # Add natural language suggestions
    nl_suggestions = [
        "photos from last summer",
        "pictures with dogs",
        "sunset photos",
        "family photos",
        "beach vacation",
        "birthday party",
        "snow photos",
        "food pictures"
    ]
    
    matching_nl = [s for s in nl_suggestions if q.lower() in s.lower()][:3]
    suggestions.extend(matching_nl)
    
    return {"suggestions": suggestions[:15]}


@router.get("/tags")
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all tags with media counts."""
    result = await db.execute(
        select(Tag.name, Tag.category, func.count(media_tags.c.media_id).label('count'))
        .join(media_tags)
        .join(Media)
        .where(Media.owner_id == current_user.id)
        .group_by(Tag.id)
        .order_by(func.count(media_tags.c.media_id).desc())
    )
    
    tags = [
        {"name": row.name, "category": row.category, "count": row.count}
        for row in result
    ]
    
    return tags


@router.get("/by-tag/{tag_name}")
async def search_by_tag(
    tag_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search media by tag."""
    # Get tag
    tag_result = await db.execute(
        select(Tag).where(Tag.name == tag_name)
    )
    tag = tag_result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(media_tags).join(Media).where(
            media_tags.c.tag_id == tag.id,
            Media.owner_id == current_user.id,
            Media.is_deleted == False
        )
    )
    total = count_result.scalar() or 0
    
    # Get media
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Media).join(media_tags).where(
            media_tags.c.tag_id == tag.id,
            Media.owner_id == current_user.id,
            Media.is_deleted == False
        ).order_by(Media.taken_at.desc()).offset(offset).limit(page_size)
    )
    media_items = result.scalars().all()
    
    from app.api.routes.media import media_to_response
    
    return {
        "tag": tag_name,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [media_to_response(media) for media in media_items]
    }


@router.get("/by-date/{date}")
async def search_by_date(
    date: str,  # YYYY-MM-DD format
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search media by date."""
    from datetime import datetime
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    result = await db.execute(
        select(Media).where(
            Media.owner_id == current_user.id,
            Media.is_deleted == False,
            func.date(Media.taken_at) == target_date
        ).order_by(Media.taken_at.asc())
    )
    media_items = result.scalars().all()
    
    from app.api.routes.media import media_to_response
    
    return {
        "date": date,
        "count": len(media_items),
        "items": [media_to_response(media) for media in media_items]
    }


@router.get("/by-location")
async def search_by_location(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, ge=0.1, le=1000),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search media by location (within radius)."""
    # Simple distance calculation using Haversine approximation
    # For production, consider using PostGIS
    
    # Approximate degrees per km at equator
    lat_range = radius_km / 111.0
    lng_range = radius_km / (111.0 * abs(lat) if lat != 0 else 111.0)
    
    result = await db.execute(
        select(Media).where(
            Media.owner_id == current_user.id,
            Media.is_deleted == False,
            Media.latitude.between(lat - lat_range, lat + lat_range),
            Media.longitude.between(lng - lng_range, lng + lng_range)
        ).order_by(Media.taken_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    media_items = result.scalars().all()
    
    from app.api.routes.media import media_to_response
    
    return {
        "location": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "count": len(media_items),
        "items": [media_to_response(media) for media in media_items]
    }


# ============== AI Assistant (Ask Tab) ==============

@router.post("/ask", response_model=AskResponse)
async def ask_assistant(
    query_data: AskQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Natural language AI assistant for photo management."""
    query = query_data.query.strip().lower()
    
    # Parse the query to determine intent
    intent = parse_natural_language_query(query)
    
    response_text = ""
    action = None
    action_result = None
    media_results = None
    
    # Handle different intents
    if intent["type"] == "search":
        # Perform semantic search
        search_results = await semantic_search(
            db=db,
            user_id=current_user.id,
            query=intent["query"],
            filters=intent.get("filters"),
            page=1,
            page_size=50
        )
        
        response_text = f"Found {search_results.total} photos matching '{intent['query']}'"
        action = "search"
        media_results = search_results.results
        
    elif intent["type"] == "create_album":
        # Create a new album
        album_name = intent.get("album_name", "New Album")
        
        # Check for existing album
        existing = await db.execute(
            select(Album).where(
                Album.owner_id == current_user.id,
                Album.name == album_name
            )
        )
        if existing.scalar_one_or_none():
            response_text = f"Album '{album_name}' already exists."
            action = "error"
        else:
            album = Album(
                owner_id=current_user.id,
                name=album_name
            )
            db.add(album)
            await db.commit()
            await db.refresh(album)
            
            response_text = f"Created album '{album_name}'"
            action = "create_album"
            action_result = {"album_id": str(album.id), "album_name": album_name}
    
    elif intent["type"] == "delete_album":
        # Delete an album
        album_name = intent.get("album_name")
        
        result = await db.execute(
            select(Album).where(
                Album.owner_id == current_user.id,
                Album.name.ilike(f"%{album_name}%")
            )
        )
        album = result.scalar_one_or_none()
        
        if album:
            await db.delete(album)
            await db.commit()
            response_text = f"Deleted album '{album.name}'"
            action = "delete_album"
            action_result = {"album_name": album.name}
        else:
            response_text = f"Album '{album_name}' not found"
            action = "error"
    
    elif intent["type"] == "save_search":
        # Save search as smart album
        from app.models.models import SmartAlbum
        
        smart_album = SmartAlbum(
            owner_id=current_user.id,
            name=intent.get("album_name", intent["query"]),
            query=intent["query"],
            filters=intent.get("filters")
        )
        db.add(smart_album)
        await db.commit()
        await db.refresh(smart_album)
        
        response_text = f"Saved search as smart album '{smart_album.name}'"
        action = "save_search"
        action_result = {"smart_album_id": str(smart_album.id)}
    
    elif intent["type"] == "stats":
        # Get statistics
        from app.api.routes.users import get_user_stats
        stats = await get_user_stats(current_user, db)
        
        response_text = f"You have {stats.total_photos} photos and {stats.total_videos} videos in {stats.total_albums} albums."
        action = "stats"
        action_result = stats.model_dump()
    
    elif intent["type"] == "help":
        response_text = """I can help you with:
- **Search**: "Show me sunset photos", "Find pictures from Paris"
- **Albums**: "Create album Summer 2024", "Delete album Old Photos"
- **Smart Albums**: "Save this search as Beach Vacation"
- **Stats**: "How many photos do I have?"
- **People**: "Show photos of John"

Just ask naturally and I'll do my best to help!"""
        action = "help"
    
    else:
        # Default to search
        search_results = await semantic_search(
            db=db,
            user_id=current_user.id,
            query=query,
            page=1,
            page_size=50
        )
        
        if search_results.total > 0:
            response_text = f"Found {search_results.total} photos that might match your query"
            action = "search"
            media_results = search_results.results
        else:
            response_text = "I'm not sure what you're looking for. Try asking about photos, albums, or people."
            action = "unknown"
    
    return AskResponse(
        query=query_data.query,
        response=response_text,
        action=action,
        action_result=action_result,
        media=media_results
    )


@router.get("/similar/{media_id}")
async def find_similar_media(
    media_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Find visually similar media using CLIP embeddings."""
    # Get the source media
    result = await db.execute(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == current_user.id
        )
    )
    source_media = result.scalar_one_or_none()
    
    if not source_media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    if source_media.clip_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Media has not been processed by CLIP yet"
        )
    
    # Find similar media using vector similarity
    from pgvector.sqlalchemy import Vector
    
    result = await db.execute(
        select(Media)
        .where(
            Media.owner_id == current_user.id,
            Media.id != media_id,
            Media.is_deleted == False,
            Media.clip_embedding.isnot(None)
        )
        .order_by(Media.clip_embedding.cosine_distance(source_media.clip_embedding))
        .limit(limit)
    )
    similar_media = result.scalars().all()
    
    from app.api.routes.media import media_to_response
    
    return {
        "source_id": str(media_id),
        "similar": [media_to_response(media) for media in similar_media]
    }
