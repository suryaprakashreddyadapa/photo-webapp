"""
People and face recognition routes.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.models import User, Person, Face, Media
from app.schemas.schemas import PersonResponse, PersonUpdate, PersonMerge, FaceResponse, FaceAssign, PaginatedResponse
from app.api.deps import get_current_user


router = APIRouter(prefix="/people", tags=["People"])


@router.get("/", response_model=List[PersonResponse])
async def list_people(
    named_only: bool = False,
    min_faces: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all detected people."""
    query = select(Person).where(
        Person.owner_id == current_user.id,
        Person.face_count >= min_faces
    )
    
    if named_only:
        query = query.where(Person.is_named == True)
    
    query = query.order_by(Person.face_count.desc())
    
    result = await db.execute(query)
    people = result.scalars().all()
    
    response = []
    for person in people:
        # Get cover face thumbnail
        cover_thumbnail = None
        if person.cover_face_id:
            face_result = await db.execute(
                select(Face, Media).join(Media).where(Face.id == person.cover_face_id)
            )
            row = face_result.first()
            if row:
                face, media = row
                cover_thumbnail = media.thumbnail_small
        
        response.append(PersonResponse(
            id=person.id,
            name=person.name,
            is_named=person.is_named,
            face_count=person.face_count,
            cover_face_thumbnail=cover_thumbnail,
            created_at=person.created_at
        ))
    
    return response


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get person by ID."""
    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            Person.owner_id == current_user.id
        )
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    return PersonResponse(
        id=person.id,
        name=person.name,
        is_named=person.is_named,
        face_count=person.face_count,
        created_at=person.created_at
    )


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: UUID,
    person_data: PersonUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update person name."""
    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            Person.owner_id == current_user.id
        )
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    person.name = person_data.name
    person.is_named = True
    
    await db.commit()
    await db.refresh(person)
    
    return PersonResponse(
        id=person.id,
        name=person.name,
        is_named=person.is_named,
        face_count=person.face_count,
        created_at=person.created_at
    )


@router.delete("/{person_id}")
async def delete_person(
    person_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete person (faces become unassigned)."""
    result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            Person.owner_id == current_user.id
        )
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    # Unassign all faces
    await db.execute(
        Face.__table__.update().where(Face.person_id == person_id).values(person_id=None)
    )
    
    await db.delete(person)
    await db.commit()
    
    return {"message": "Person deleted"}


@router.get("/{person_id}/media", response_model=PaginatedResponse)
async def get_person_media(
    person_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get media containing this person."""
    # Verify person ownership
    person_result = await db.execute(
        select(Person).where(
            Person.id == person_id,
            Person.owner_id == current_user.id
        )
    )
    if not person_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    # Count total
    count_result = await db.execute(
        select(func.count(func.distinct(Face.media_id))).where(Face.person_id == person_id)
    )
    total = count_result.scalar() or 0
    
    # Get media
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Media).join(Face).where(
            Face.person_id == person_id
        ).distinct().order_by(Media.taken_at.desc()).offset(offset).limit(page_size)
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


@router.post("/merge")
async def merge_people(
    merge_data: PersonMerge,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Merge multiple people into one."""
    # Verify target person
    target_result = await db.execute(
        select(Person).where(
            Person.id == merge_data.target_person_id,
            Person.owner_id == current_user.id
        )
    )
    target_person = target_result.scalar_one_or_none()
    
    if not target_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target person not found"
        )
    
    # Verify source people
    source_result = await db.execute(
        select(Person).where(
            Person.id.in_(merge_data.source_person_ids),
            Person.owner_id == current_user.id
        )
    )
    source_people = source_result.scalars().all()
    
    if len(source_people) != len(merge_data.source_person_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some source people not found"
        )
    
    # Move all faces to target person
    total_faces = 0
    for source_person in source_people:
        if source_person.id == target_person.id:
            continue
        
        # Update faces
        await db.execute(
            Face.__table__.update().where(
                Face.person_id == source_person.id
            ).values(person_id=target_person.id)
        )
        
        total_faces += source_person.face_count
        
        # Delete source person
        await db.delete(source_person)
    
    # Update target person face count
    target_person.face_count += total_faces
    
    await db.commit()
    
    return {"message": f"Merged {len(source_people)} people into {target_person.name or 'unnamed person'}"}


# ============== Face Routes ==============

@router.get("/faces/unassigned", response_model=List[FaceResponse])
async def list_unassigned_faces(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List faces not assigned to any person."""
    result = await db.execute(
        select(Face, Media).join(Media).where(
            Media.owner_id == current_user.id,
            Face.person_id.is_(None)
        ).limit(limit)
    )
    
    faces = []
    for face, media in result:
        faces.append(FaceResponse(
            id=face.id,
            media_id=face.media_id,
            person_id=None,
            x=face.x,
            y=face.y,
            width=face.width,
            height=face.height,
            confidence=face.confidence,
            thumbnail=media.thumbnail_small
        ))
    
    return faces


@router.put("/faces/{face_id}/assign")
async def assign_face(
    face_id: UUID,
    data: FaceAssign,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign a face to a person."""
    # Get face and verify ownership through media
    result = await db.execute(
        select(Face, Media).join(Media).where(
            Face.id == face_id,
            Media.owner_id == current_user.id
        )
    )
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face not found"
        )
    
    face, media = row
    
    # Verify person ownership
    person_result = await db.execute(
        select(Person).where(
            Person.id == data.person_id,
            Person.owner_id == current_user.id
        )
    )
    person = person_result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    # Update old person's face count if face was assigned
    if face.person_id:
        old_person_result = await db.execute(
            select(Person).where(Person.id == face.person_id)
        )
        old_person = old_person_result.scalar_one_or_none()
        if old_person:
            old_person.face_count = max(0, old_person.face_count - 1)
    
    # Assign face to new person
    face.person_id = person.id
    person.face_count += 1
    
    await db.commit()
    
    return {"message": "Face assigned successfully"}


@router.put("/faces/{face_id}/unassign")
async def unassign_face(
    face_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unassign a face from its person."""
    # Get face and verify ownership through media
    result = await db.execute(
        select(Face, Media).join(Media).where(
            Face.id == face_id,
            Media.owner_id == current_user.id
        )
    )
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face not found"
        )
    
    face, media = row
    
    if face.person_id:
        # Update person's face count
        person_result = await db.execute(
            select(Person).where(Person.id == face.person_id)
        )
        person = person_result.scalar_one_or_none()
        if person:
            person.face_count = max(0, person.face_count - 1)
        
        face.person_id = None
        await db.commit()
    
    return {"message": "Face unassigned"}


@router.post("/faces/{face_id}/create-person", response_model=PersonResponse)
async def create_person_from_face(
    face_id: UUID,
    name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new person from a face."""
    # Get face and verify ownership through media
    result = await db.execute(
        select(Face, Media).join(Media).where(
            Face.id == face_id,
            Media.owner_id == current_user.id
        )
    )
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face not found"
        )
    
    face, media = row
    
    # Create new person
    person = Person(
        owner_id=current_user.id,
        name=name,
        is_named=bool(name),
        face_embedding=face.encoding,
        cover_face_id=face.id,
        face_count=1
    )
    
    db.add(person)
    await db.flush()
    
    # Update old person's face count if face was assigned
    if face.person_id:
        old_person_result = await db.execute(
            select(Person).where(Person.id == face.person_id)
        )
        old_person = old_person_result.scalar_one_or_none()
        if old_person:
            old_person.face_count = max(0, old_person.face_count - 1)
    
    # Assign face to new person
    face.person_id = person.id
    
    await db.commit()
    await db.refresh(person)
    
    return PersonResponse(
        id=person.id,
        name=person.name,
        is_named=person.is_named,
        face_count=person.face_count,
        created_at=person.created_at
    )
