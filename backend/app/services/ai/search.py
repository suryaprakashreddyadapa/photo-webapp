"""
Semantic search service for natural language photo queries.
"""
import re
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import structlog

from app.models.models import Media, Tag, media_tags, Person, Face
from app.schemas.schemas import SearchResponse, MediaResponse
from app.services.ai.clip_service import get_text_embedding
from app.core.config import settings


logger = structlog.get_logger()


def parse_natural_language_query(query: str) -> Dict[str, Any]:
    """Parse a natural language query to determine intent and extract parameters."""
    query_lower = query.lower().strip()
    
    # Command patterns
    create_album_pattern = r"create\s+(?:album|folder)\s+['\"]?(.+?)['\"]?$"
    delete_album_pattern = r"delete\s+(?:album|folder)\s+['\"]?(.+?)['\"]?$"
    save_search_pattern = r"save\s+(?:this\s+)?(?:search|query)\s+(?:as\s+)?['\"]?(.+?)['\"]?$"
    
    # Check for create album command
    match = re.search(create_album_pattern, query_lower)
    if match:
        return {
            "type": "create_album",
            "album_name": match.group(1).strip()
        }
    
    # Check for delete album command
    match = re.search(delete_album_pattern, query_lower)
    if match:
        return {
            "type": "delete_album",
            "album_name": match.group(1).strip()
        }
    
    # Check for save search command
    match = re.search(save_search_pattern, query_lower)
    if match:
        return {
            "type": "save_search",
            "album_name": match.group(1).strip(),
            "query": query_lower
        }
    
    # Check for stats/info queries
    stats_patterns = [
        r"how many (photos|pictures|images|videos)",
        r"(stats|statistics|info|information)",
        r"storage (used|usage)"
    ]
    for pattern in stats_patterns:
        if re.search(pattern, query_lower):
            return {"type": "stats"}
    
    # Check for help
    if query_lower in ["help", "?", "what can you do"]:
        return {"type": "help"}
    
    # Extract filters from query
    filters = {}
    search_query = query_lower
    
    # Date patterns
    date_patterns = [
        (r"from\s+(\d{4})", "year_from"),
        (r"in\s+(\d{4})", "year"),
        (r"last\s+(week|month|year)", "relative_time"),
        (r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{4})?", "month"),
        (r"(summer|winter|spring|fall|autumn)\s*(\d{4})?", "season"),
    ]
    
    for pattern, filter_type in date_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if filter_type == "year":
                filters["year"] = int(match.group(1))
            elif filter_type == "year_from":
                filters["year_from"] = int(match.group(1))
            elif filter_type == "relative_time":
                period = match.group(1)
                now = datetime.utcnow()
                if period == "week":
                    filters["date_from"] = (now - timedelta(days=7)).isoformat()
                elif period == "month":
                    filters["date_from"] = (now - timedelta(days=30)).isoformat()
                elif period == "year":
                    filters["date_from"] = (now - timedelta(days=365)).isoformat()
            elif filter_type == "month":
                month_names = {
                    "january": 1, "february": 2, "march": 3, "april": 4,
                    "may": 5, "june": 6, "july": 7, "august": 8,
                    "september": 9, "october": 10, "november": 11, "december": 12
                }
                filters["month"] = month_names.get(match.group(1))
                if match.group(2):
                    filters["year"] = int(match.group(2))
            elif filter_type == "season":
                season_months = {
                    "spring": [3, 4, 5],
                    "summer": [6, 7, 8],
                    "fall": [9, 10, 11],
                    "autumn": [9, 10, 11],
                    "winter": [12, 1, 2]
                }
                filters["months"] = season_months.get(match.group(1))
                if match.group(2):
                    filters["year"] = int(match.group(2))
            
            # Remove matched pattern from search query
            search_query = re.sub(pattern, "", search_query).strip()
    
    # Location patterns
    location_patterns = [
        r"(?:in|at|from)\s+([a-zA-Z\s]+?)(?:\s+in\s+\d{4}|\s*$)",
        r"(?:photos?|pictures?|images?)\s+(?:of|from)\s+([a-zA-Z\s]+)"
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, query_lower)
        if match:
            location = match.group(1).strip()
            # Filter out common words that aren't locations
            non_locations = {"the", "my", "our", "their", "this", "that", "last", "next"}
            if location not in non_locations:
                filters["location"] = location
                search_query = re.sub(pattern, "", search_query).strip()
                break
    
    # Person patterns
    person_patterns = [
        r"(?:photos?|pictures?)\s+(?:of|with)\s+([a-zA-Z]+)",
        r"show\s+(?:me\s+)?([a-zA-Z]+)(?:'s)?\s+(?:photos?|pictures?)",
    ]
    
    for pattern in person_patterns:
        match = re.search(pattern, query_lower)
        if match:
            person_name = match.group(1).strip()
            if person_name not in {"my", "the", "all", "some", "any"}:
                filters["person"] = person_name
                break
    
    # Media type
    if "video" in query_lower or "videos" in query_lower:
        filters["media_type"] = "video"
    elif "photo" in query_lower or "picture" in query_lower or "image" in query_lower:
        filters["media_type"] = "photo"
    
    # Favorites
    if "favorite" in query_lower or "starred" in query_lower:
        filters["favorites_only"] = True
    
    # Clean up search query
    cleanup_words = ["show", "me", "find", "search", "for", "photos", "pictures", 
                     "images", "of", "with", "the", "my", "all"]
    for word in cleanup_words:
        search_query = re.sub(rf"\b{word}\b", "", search_query)
    search_query = " ".join(search_query.split())  # Normalize whitespace
    
    return {
        "type": "search",
        "query": search_query if search_query else query,
        "filters": filters if filters else None
    }


async def semantic_search(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "relevance",
    sort_order: str = "desc"
) -> SearchResponse:
    """Perform semantic search on media using CLIP embeddings."""
    
    # Get text embedding for the query
    query_embedding = get_text_embedding(query)
    
    # Build base query
    base_query = select(Media).where(
        Media.owner_id == user_id,
        Media.is_deleted == False,
        Media.is_hidden == False
    )
    
    # Apply filters
    if filters:
        if filters.get("media_type"):
            base_query = base_query.where(Media.media_type == filters["media_type"])
        
        if filters.get("year"):
            base_query = base_query.where(func.extract('year', Media.taken_at) == filters["year"])
        
        if filters.get("year_from"):
            base_query = base_query.where(func.extract('year', Media.taken_at) >= filters["year_from"])
        
        if filters.get("month"):
            base_query = base_query.where(func.extract('month', Media.taken_at) == filters["month"])
        
        if filters.get("months"):
            base_query = base_query.where(func.extract('month', Media.taken_at).in_(filters["months"]))
        
        if filters.get("date_from"):
            date_from = datetime.fromisoformat(filters["date_from"])
            base_query = base_query.where(Media.taken_at >= date_from)
        
        if filters.get("date_to"):
            date_to = datetime.fromisoformat(filters["date_to"])
            base_query = base_query.where(Media.taken_at <= date_to)
        
        if filters.get("location"):
            location = filters["location"]
            base_query = base_query.where(
                or_(
                    Media.location_name.ilike(f"%{location}%"),
                    Media.city.ilike(f"%{location}%"),
                    Media.country.ilike(f"%{location}%")
                )
            )
        
        if filters.get("favorites_only"):
            base_query = base_query.where(Media.is_favorite == True)
        
        if filters.get("person"):
            # Search by person name
            person_name = filters["person"]
            person_subquery = (
                select(Face.media_id)
                .join(Person)
                .where(
                    Person.owner_id == user_id,
                    Person.name.ilike(f"%{person_name}%")
                )
            )
            base_query = base_query.where(Media.id.in_(person_subquery))
    
    # If we have a valid embedding, use vector similarity search
    if query_embedding is not None and sort_by == "relevance":
        # Filter to only media with embeddings
        base_query = base_query.where(Media.clip_embedding.isnot(None))
        
        # Order by similarity
        base_query = base_query.order_by(
            Media.clip_embedding.cosine_distance(query_embedding.tolist())
        )
    else:
        # Fallback to date-based sorting
        if sort_by == "taken_at" or sort_by == "relevance":
            sort_column = Media.taken_at
        elif sort_by == "created_at":
            sort_column = Media.created_at
        else:
            sort_column = Media.taken_at
        
        if sort_order == "desc":
            base_query = base_query.order_by(sort_column.desc().nullslast())
        else:
            base_query = base_query.order_by(sort_column.asc().nullsfirst())
    
    # Count total results
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(base_query)
    media_items = result.scalars().all()
    
    # Convert to response format
    from app.api.routes.media import media_to_response
    
    results = []
    for media in media_items:
        # Get tags
        tags_result = await db.execute(
            select(Tag.name).join(media_tags).where(media_tags.c.media_id == media.id)
        )
        tags = [row[0] for row in tags_result]
        
        # Get face count
        face_count_result = await db.execute(
            select(func.count(Face.id)).where(Face.media_id == media.id)
        )
        faces_count = face_count_result.scalar() or 0
        
        results.append(media_to_response(media, tags, faces_count))
    
    # Generate suggestions
    suggestions = []
    if total == 0:
        suggestions = [
            "Try a broader search term",
            "Check if your photos have been indexed",
            "Remove some filters"
        ]
    
    return SearchResponse(
        query=query,
        total=total,
        page=page,
        page_size=page_size,
        results=results,
        suggestions=suggestions
    )


async def search_by_tags(
    db: AsyncSession,
    user_id: UUID,
    tags: List[str],
    match_all: bool = False,
    page: int = 1,
    page_size: int = 50
) -> SearchResponse:
    """Search media by tags."""
    
    # Get tag IDs
    tag_result = await db.execute(
        select(Tag.id).where(Tag.name.in_(tags))
    )
    tag_ids = [row[0] for row in tag_result]
    
    if not tag_ids:
        return SearchResponse(
            query=", ".join(tags),
            total=0,
            page=page,
            page_size=page_size,
            results=[],
            suggestions=["No matching tags found"]
        )
    
    if match_all:
        # Media must have all specified tags
        subquery = (
            select(media_tags.c.media_id)
            .where(media_tags.c.tag_id.in_(tag_ids))
            .group_by(media_tags.c.media_id)
            .having(func.count(func.distinct(media_tags.c.tag_id)) == len(tag_ids))
        )
    else:
        # Media can have any of the specified tags
        subquery = (
            select(media_tags.c.media_id)
            .where(media_tags.c.tag_id.in_(tag_ids))
            .distinct()
        )
    
    base_query = select(Media).where(
        Media.owner_id == user_id,
        Media.is_deleted == False,
        Media.id.in_(subquery)
    ).order_by(Media.taken_at.desc())
    
    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)
    
    result = await db.execute(base_query)
    media_items = result.scalars().all()
    
    from app.api.routes.media import media_to_response
    
    return SearchResponse(
        query=", ".join(tags),
        total=total,
        page=page,
        page_size=page_size,
        results=[media_to_response(media) for media in media_items],
        suggestions=[]
    )
