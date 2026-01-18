"""
Admin routes for system management.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.models import User, Media, ProcessingJob, AuditLog
from app.schemas.schemas import (
    UserResponse, UserAdminUpdate, SystemSettings, SystemStats, JobResponse
)
from app.api.deps import get_current_admin_user
from app.core.config import settings


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system-wide statistics."""
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # Active users
    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True, User.is_approved == True)
    )
    active_users = active_users_result.scalar() or 0
    
    # Pending users
    pending_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_verified == True, User.is_approved == False)
    )
    pending_users = pending_users_result.scalar() or 0
    
    # Total media
    total_media_result = await db.execute(
        select(func.count(Media.id)).where(Media.is_deleted == False)
    )
    total_media = total_media_result.scalar() or 0
    
    # Total storage
    total_storage_result = await db.execute(
        select(func.sum(Media.file_size)).where(Media.is_deleted == False)
    )
    total_storage = total_storage_result.scalar() or 0
    
    # Pending jobs
    pending_jobs_result = await db.execute(
        select(func.count(ProcessingJob.id)).where(ProcessingJob.status == "pending")
    )
    jobs_pending = pending_jobs_result.scalar() or 0
    
    # Running jobs
    running_jobs_result = await db.execute(
        select(func.count(ProcessingJob.id)).where(ProcessingJob.status == "running")
    )
    jobs_running = running_jobs_result.scalar() or 0
    
    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        pending_users=pending_users,
        total_media=total_media,
        total_storage_bytes=total_storage,
        jobs_pending=jobs_pending,
        jobs_running=jobs_running
    )


@router.get("/settings", response_model=SystemSettings)
async def get_system_settings(
    admin_user: User = Depends(get_current_admin_user)
):
    """Get system settings."""
    return SystemSettings(
        require_admin_approval=settings.REQUIRE_ADMIN_APPROVAL,
        max_upload_size_mb=100,
        allowed_extensions=["jpg", "jpeg", "png", "gif", "webp", "heic", "raw", "mp4", "mov", "avi"],
        ai_batch_size=settings.BATCH_SIZE,
        max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS
    )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[str] = None,
    job_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all processing jobs."""
    query = select(ProcessingJob)
    
    if status_filter:
        query = query.where(ProcessingJob.status == status_filter)
    
    if job_type:
        query = query.where(ProcessingJob.job_type == job_type)
    
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


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job details."""
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
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


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a running job."""
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
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
    
    # TODO: Actually cancel the Celery task
    
    return {"message": "Job cancelled"}


@router.post("/reindex")
async def trigger_reindex(
    user_id: Optional[UUID] = None,
    background_tasks: BackgroundTasks = None,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger a full reindex of media."""
    from app.workers.tasks import scan_and_index_media
    
    # Create job record
    job = ProcessingJob(
        user_id=user_id,
        job_type="reindex",
        status="pending"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Queue the task
    scan_and_index_media.delay(str(job.id), str(user_id) if user_id else None)
    
    return {"message": "Reindex job queued", "job_id": str(job.id)}


@router.post("/process-ai")
async def trigger_ai_processing(
    user_id: Optional[UUID] = None,
    process_type: str = Query(..., regex="^(face|clip|yolo|all)$"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger AI processing for media."""
    from app.workers.tasks import process_ai_features
    
    # Create job record
    job = ProcessingJob(
        user_id=user_id,
        job_type=f"ai_{process_type}",
        status="pending",
        params={"process_type": process_type}
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Queue the task
    process_ai_features.delay(str(job.id), str(user_id) if user_id else None, process_type)
    
    return {"message": f"AI processing job ({process_type}) queued", "job_id": str(job.id)}


@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs."""
    query = select(AuditLog)
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    
    if action:
        query = query.where(AuditLog.action == action)
    
    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]


@router.get("/health")
async def health_check(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """System health check."""
    import redis
    from app.core.config import settings
    
    health = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "nas": "unknown"
    }
    
    # Check database
    try:
        await db.execute(select(1))
        health["database"] = "healthy"
    except Exception as e:
        health["database"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health["redis"] = "healthy"
    except Exception as e:
        health["redis"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    # Check NAS mount
    import os
    if os.path.exists(settings.NAS_MOUNT_PATH):
        health["nas"] = "mounted"
    else:
        health["nas"] = "not mounted"
        health["status"] = "degraded"
    
    return health
