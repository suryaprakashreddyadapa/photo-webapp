"""Celery application configuration."""
import os
from celery import Celery
from celery.schedules import crontab

# Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "photovault",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit 55 minutes
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time for AI tasks
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to free memory
    
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    
    # Task routing
    task_routes={
        "app.workers.tasks.process_face_recognition": {"queue": "ai"},
        "app.workers.tasks.process_clip_embedding": {"queue": "ai"},
        "app.workers.tasks.process_yolo_detection": {"queue": "ai"},
        "app.workers.tasks.scan_nas_folder": {"queue": "default"},
        "app.workers.tasks.process_media_file": {"queue": "default"},
        "app.workers.tasks.generate_thumbnails": {"queue": "default"},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Scan NAS folders every hour
        "scan-nas-hourly": {
            "task": "app.workers.tasks.scheduled_nas_scan",
            "schedule": crontab(minute=0),  # Every hour at minute 0
        },
        # Clean up old jobs daily
        "cleanup-jobs-daily": {
            "task": "app.workers.tasks.cleanup_old_jobs",
            "schedule": crontab(hour=3, minute=0),  # 3 AM daily
        },
        # Process pending AI tasks
        "process-pending-ai": {
            "task": "app.workers.tasks.process_pending_ai_tasks",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
        },
        # Empty trash (permanently delete old items)
        "empty-old-trash": {
            "task": "app.workers.tasks.empty_old_trash",
            "schedule": crontab(hour=4, minute=0),  # 4 AM daily
        },
    },
)

# Task priority queues
celery_app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "ai": {
        "exchange": "ai",
        "routing_key": "ai",
    },
    "priority": {
        "exchange": "priority",
        "routing_key": "priority",
    },
}
