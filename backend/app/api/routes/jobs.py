"""
Job management routes for users.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.models import User, ProcessingJob
from app.schemas.schemas import JobResponse, JobCreate
from app.api.deps import get_current_user


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/", response_model=List[JobResponse])
async def list_user_jobs(
    status_filter: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List current user's processing jobs."""
    query = select(ProcessingJob).where(ProcessingJob.user_id == current_user.id)
    
    if status_filter:
        query = query.where(ProcessingJob.status == status_filter)
    
    query = query.order_by(ProcessingJob.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return [
        JobResponse(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            total_items=job.total_items,
            processed_items=job.processed_items,
            failed_items=job.failed_items,
            progress=job.processed_items / job.total_items * 100 if job.total_items > 0 else 0,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )
        for job in jobs
    ]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job details."""
    result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id,
            ProcessingJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=job.total_items,
        processed_items=job.processed_items,
        failed_items=job.failed_items,
        progress=job.processed_items / job.total_items * 100 if job.total_items > 0 else 0,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at
    )


@router.post("/scan", response_model=JobResponse)
async def trigger_scan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger a scan of user's NAS folder."""
    from app.workers.tasks import scan_and_index_media
    
    if not current_user.nas_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No NAS path configured for user"
        )
    
    # Check for existing running scan
    existing = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.user_id == current_user.id,
            ProcessingJob.job_type == "scan",
            ProcessingJob.status.in_(["pending", "running"])
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A scan is already in progress"
        )
    
    # Create job record
    job = ProcessingJob(
        user_id=current_user.id,
        job_type="scan",
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Queue the task
    scan_and_index_media.delay(str(job.id), str(current_user.id))
    
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=0,
        processed_items=0,
        failed_items=0,
        progress=0,
        created_at=job.created_at
    )


@router.post("/process-faces", response_model=JobResponse)
async def trigger_face_processing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger face recognition processing."""
    from app.workers.tasks import process_ai_features
    
    # Check user settings
    user_settings = current_user.settings or {}
    if not user_settings.get("face_recognition_enabled", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Face recognition is disabled in settings"
        )
    
    # Create job record
    job = ProcessingJob(
        user_id=current_user.id,
        job_type="face_recognition",
        status="pending",
        params={"process_type": "face"}
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Queue the task
    process_ai_features.delay(str(job.id), str(current_user.id), "face")
    
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=0,
        processed_items=0,
        failed_items=0,
        progress=0,
        created_at=job.created_at
    )


@router.post("/process-clip", response_model=JobResponse)
async def trigger_clip_processing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger CLIP embedding generation."""
    from app.workers.tasks import process_ai_features
    
    # Check user settings
    user_settings = current_user.settings or {}
    if not user_settings.get("clip_enabled", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CLIP processing is disabled in settings"
        )
    
    # Create job record
    job = ProcessingJob(
        user_id=current_user.id,
        job_type="clip_embedding",
        status="pending",
        params={"process_type": "clip"}
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Queue the task
    process_ai_features.delay(str(job.id), str(current_user.id), "clip")
    
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=0,
        processed_items=0,
        failed_items=0,
        progress=0,
        created_at=job.created_at
    )


@router.post("/process-yolo", response_model=JobResponse)
async def trigger_yolo_processing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger YOLO object detection."""
    from app.workers.tasks import process_ai_features
    
    # Check user settings
    user_settings = current_user.settings or {}
    if not user_settings.get("yolo_enabled", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YOLO processing is disabled in settings"
        )
    
    # Create job record
    job = ProcessingJob(
        user_id=current_user.id,
        job_type="yolo_detection",
        status="pending",
        params={"process_type": "yolo"}
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Queue the task
    process_ai_features.delay(str(job.id), str(current_user.id), "yolo")
    
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=0,
        processed_items=0,
        failed_items=0,
        progress=0,
        created_at=job.created_at
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running job."""
    result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id,
            ProcessingJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job cannot be cancelled"
        )
    
    job.status = "cancelled"
    await db.commit()
    
    return {"message": "Job cancelled"}
