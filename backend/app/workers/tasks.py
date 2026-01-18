"""
Celery tasks for background processing.
"""
import os
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from celery import Celery
import structlog

from app.core.config import settings


logger = structlog.get_logger()

# Create Celery app
celery_app = Celery(
    "photovault",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


def get_sync_db_session():
    """Get a synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Convert async URL to sync
    sync_url = settings.DATABASE_URL.replace('+asyncpg', '')
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(bind=True, name="scan_and_index_media")
def scan_and_index_media(self, job_id: str, user_id: Optional[str] = None):
    """Scan NAS folder and index new media files."""
    from app.models.models import ProcessingJob, User, Media
    from app.services.media.processor import scan_directory, process_media_file, generate_all_thumbnails
    from app.services.nas.smb_client import get_user_nas_path, is_nas_accessible
    
    db = get_sync_db_session()
    
    try:
        # Get job
        job = db.query(ProcessingJob).filter(ProcessingJob.id == UUID(job_id)).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Check NAS accessibility
        if not is_nas_accessible():
            job.status = "failed"
            job.error_message = "NAS is not accessible"
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        # Get users to process
        if user_id:
            users = [db.query(User).filter(User.id == UUID(user_id)).first()]
        else:
            users = db.query(User).filter(User.is_active == True, User.nas_path.isnot(None)).all()
        
        total_files = 0
        processed_files = 0
        failed_files = 0
        
        for user in users:
            if not user or not user.nas_path:
                continue
            
            user_path = get_user_nas_path(user.nas_path)
            
            if not os.path.exists(user_path):
                logger.warning(f"User path does not exist: {user_path}")
                continue
            
            # Scan for media files
            media_files = scan_directory(user_path)
            total_files += len(media_files)
            
            job.total_items = total_files
            db.commit()
            
            for file_path in media_files:
                try:
                    # Check if already indexed
                    existing = db.query(Media).filter(
                        Media.owner_id == user.id,
                        Media.original_path == file_path
                    ).first()
                    
                    if existing:
                        processed_files += 1
                        continue
                    
                    # Process file
                    metadata = process_media_file(file_path)
                    
                    # Check for duplicates by hash
                    duplicate = db.query(Media).filter(
                        Media.owner_id == user.id,
                        Media.file_hash == metadata['file_hash']
                    ).first()
                    
                    if duplicate:
                        logger.info(f"Duplicate found: {file_path}")
                        processed_files += 1
                        continue
                    
                    # Create media record
                    media = Media(
                        owner_id=user.id,
                        filename=metadata['filename'],
                        original_path=file_path,
                        relative_path=os.path.relpath(file_path, user_path),
                        file_hash=metadata['file_hash'],
                        file_size=metadata['file_size'],
                        mime_type=metadata['mime_type'],
                        media_type=metadata['media_type'],
                        width=metadata.get('width'),
                        height=metadata.get('height'),
                        duration=metadata.get('duration'),
                        taken_at=metadata.get('taken_at'),
                        camera_make=metadata.get('camera_make'),
                        camera_model=metadata.get('camera_model'),
                        lens_model=metadata.get('lens_model'),
                        focal_length=metadata.get('focal_length'),
                        aperture=metadata.get('aperture'),
                        iso=metadata.get('iso'),
                        shutter_speed=metadata.get('shutter_speed'),
                        latitude=metadata.get('latitude'),
                        longitude=metadata.get('longitude'),
                        altitude=metadata.get('altitude'),
                        indexed_at=datetime.utcnow()
                    )
                    
                    db.add(media)
                    db.flush()
                    
                    # Generate thumbnails
                    thumbnails = generate_all_thumbnails(
                        file_path,
                        str(media.id),
                        metadata['media_type']
                    )
                    
                    media.thumbnail_small = thumbnails.get('thumbnail_small')
                    media.thumbnail_medium = thumbnails.get('thumbnail_medium')
                    media.thumbnail_large = thumbnails.get('thumbnail_large')
                    
                    db.commit()
                    processed_files += 1
                    
                    # Update job progress
                    job.processed_items = processed_files
                    db.commit()
                    
                    # Update task state
                    self.update_state(
                        state='PROGRESS',
                        meta={'processed': processed_files, 'total': total_files}
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    failed_files += 1
                    db.rollback()
        
        # Complete job
        job.status = "completed"
        job.processed_items = processed_files
        job.failed_items = failed_files
        job.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Scan completed: {processed_files} processed, {failed_files} failed")
        
    except Exception as e:
        logger.error(f"Scan job failed: {e}")
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@celery_app.task(bind=True, name="process_ai_features")
def process_ai_features(self, job_id: str, user_id: Optional[str], process_type: str):
    """Process AI features for media (face, clip, yolo, or all)."""
    from app.models.models import ProcessingJob, Media, Face, Person, Tag, media_tags
    
    db = get_sync_db_session()
    
    try:
        # Get job
        job = db.query(ProcessingJob).filter(ProcessingJob.id == UUID(job_id)).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Build query for unprocessed media
        query = db.query(Media).filter(Media.is_deleted == False)
        
        if user_id:
            query = query.filter(Media.owner_id == UUID(user_id))
        
        if process_type == "face":
            query = query.filter(Media.face_processed == False, Media.media_type == "photo")
        elif process_type == "clip":
            query = query.filter(Media.clip_processed == False)
        elif process_type == "yolo":
            query = query.filter(Media.yolo_processed == False, Media.media_type == "photo")
        else:  # all
            query = query.filter(
                (Media.face_processed == False) |
                (Media.clip_processed == False) |
                (Media.yolo_processed == False)
            )
        
        media_items = query.all()
        total = len(media_items)
        
        job.total_items = total
        db.commit()
        
        processed = 0
        failed = 0
        
        for media in media_items:
            try:
                file_path = media.original_path
                
                if not os.path.exists(file_path):
                    logger.warning(f"File not found: {file_path}")
                    failed += 1
                    continue
                
                # Process CLIP
                if process_type in ("clip", "all") and not media.clip_processed:
                    from app.services.ai.clip_service import get_image_embedding, auto_tag_image
                    
                    embedding = get_image_embedding(file_path)
                    if embedding is not None:
                        media.clip_embedding = embedding.tolist()
                        
                        # Auto-tag with CLIP
                        tags = auto_tag_image(file_path)
                        for tag_name, confidence in tags:
                            # Get or create tag
                            tag = db.query(Tag).filter(Tag.name == tag_name).first()
                            if not tag:
                                tag = Tag(name=tag_name, category="clip")
                                db.add(tag)
                                db.flush()
                            
                            # Add tag to media
                            db.execute(
                                media_tags.insert().values(
                                    media_id=media.id,
                                    tag_id=tag.id,
                                    confidence=confidence,
                                    source="clip"
                                ).prefix_with("INSERT IGNORE")
                            )
                    
                    media.clip_processed = True
                
                # Process Face Recognition
                if process_type in ("face", "all") and not media.face_processed and media.media_type == "photo":
                    from app.services.ai.face_service import detect_faces, find_matching_person
                    
                    detected_faces = detect_faces(file_path)
                    
                    # Get existing person encodings for this user
                    persons = db.query(Person).filter(
                        Person.owner_id == media.owner_id,
                        Person.face_embedding.isnot(None)
                    ).all()
                    
                    known_encodings = {
                        str(p.id): p.face_embedding
                        for p in persons
                    }
                    
                    for detected_face in detected_faces:
                        # Try to match to existing person
                        match = find_matching_person(
                            detected_face.encoding,
                            known_encodings
                        )
                        
                        person_id = None
                        if match:
                            person_id = UUID(match[0])
                            # Update person face count
                            person = db.query(Person).filter(Person.id == person_id).first()
                            if person:
                                person.face_count += 1
                        
                        # Create face record
                        face = Face(
                            media_id=media.id,
                            person_id=person_id,
                            x=detected_face.x,
                            y=detected_face.y,
                            width=detected_face.width,
                            height=detected_face.height,
                            encoding=detected_face.encoding.tolist(),
                            confidence=detected_face.confidence
                        )
                        db.add(face)
                    
                    media.face_processed = True
                
                # Process YOLO
                if process_type in ("yolo", "all") and not media.yolo_processed and media.media_type == "photo":
                    from app.services.ai.yolo_service import detect_objects, get_unique_tags, get_scene_tags
                    
                    detections = detect_objects(file_path)
                    
                    if detections:
                        # Store detections as JSON
                        media.yolo_detections = [
                            {
                                "class": d.class_name,
                                "confidence": d.confidence,
                                "bbox": [d.x, d.y, d.width, d.height]
                            }
                            for d in detections
                        ]
                        
                        # Add object tags
                        object_tags = get_unique_tags(detections)
                        scene_tags = get_scene_tags(detections)
                        
                        all_tags = [(t, c) for t, c in object_tags] + [(t, 0.8) for t in scene_tags]
                        
                        for tag_name, confidence in all_tags:
                            tag = db.query(Tag).filter(Tag.name == tag_name).first()
                            if not tag:
                                tag = Tag(name=tag_name, category="yolo")
                                db.add(tag)
                                db.flush()
                            
                            # Check if tag already exists for this media
                            existing = db.execute(
                                media_tags.select().where(
                                    media_tags.c.media_id == media.id,
                                    media_tags.c.tag_id == tag.id
                                )
                            ).first()
                            
                            if not existing:
                                db.execute(
                                    media_tags.insert().values(
                                        media_id=media.id,
                                        tag_id=tag.id,
                                        confidence=confidence,
                                        source="yolo"
                                    )
                                )
                    
                    media.yolo_processed = True
                
                db.commit()
                processed += 1
                
                # Update job progress
                job.processed_items = processed
                db.commit()
                
                self.update_state(
                    state='PROGRESS',
                    meta={'processed': processed, 'total': total}
                )
                
            except Exception as e:
                logger.error(f"Error processing media {media.id}: {e}")
                failed += 1
                db.rollback()
        
        # Complete job
        job.status = "completed"
        job.processed_items = processed
        job.failed_items = failed
        job.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"AI processing completed: {processed} processed, {failed} failed")
        
    except Exception as e:
        logger.error(f"AI processing job failed: {e}")
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@celery_app.task(name="cluster_faces")
def cluster_faces_task(user_id: str):
    """Cluster unassigned faces into person groups."""
    from app.models.models import Face, Person, Media
    from app.services.ai.face_service import cluster_faces, compute_average_encoding
    import numpy as np
    
    db = get_sync_db_session()
    
    try:
        # Get unassigned faces for user
        faces = db.query(Face).join(Media).filter(
            Media.owner_id == UUID(user_id),
            Face.person_id.is_(None),
            Face.encoding.isnot(None)
        ).all()
        
        if not faces:
            logger.info("No unassigned faces to cluster")
            return
        
        # Get face encodings
        encodings = [np.array(f.encoding) for f in faces]
        
        # Cluster faces
        clusters = cluster_faces(encodings)
        
        logger.info(f"Found {len(clusters)} face clusters")
        
        # Create persons for clusters with multiple faces
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            
            # Get cluster face encodings
            cluster_encodings = [encodings[i] for i in cluster]
            avg_encoding = compute_average_encoding(cluster_encodings)
            
            # Create new person
            person = Person(
                owner_id=UUID(user_id),
                face_embedding=avg_encoding.tolist(),
                face_count=len(cluster)
            )
            db.add(person)
            db.flush()
            
            # Assign faces to person
            for face_idx in cluster:
                faces[face_idx].person_id = person.id
            
            # Set cover face (best quality)
            person.cover_face_id = faces[cluster[0]].id
        
        db.commit()
        logger.info(f"Created {len([c for c in clusters if len(c) >= 2])} person groups")
        
    except Exception as e:
        logger.error(f"Face clustering failed: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="generate_thumbnails")
def generate_thumbnails_task(media_id: str):
    """Generate thumbnails for a single media item."""
    from app.models.models import Media
    from app.services.media.processor import generate_all_thumbnails
    
    db = get_sync_db_session()
    
    try:
        media = db.query(Media).filter(Media.id == UUID(media_id)).first()
        
        if not media:
            logger.error(f"Media {media_id} not found")
            return
        
        if not os.path.exists(media.original_path):
            logger.error(f"File not found: {media.original_path}")
            return
        
        thumbnails = generate_all_thumbnails(
            media.original_path,
            str(media.id),
            media.media_type
        )
        
        media.thumbnail_small = thumbnails.get('thumbnail_small')
        media.thumbnail_medium = thumbnails.get('thumbnail_medium')
        media.thumbnail_large = thumbnails.get('thumbnail_large')
        
        db.commit()
        logger.info(f"Generated thumbnails for media {media_id}")
        
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="cleanup_deleted_media")
def cleanup_deleted_media():
    """Permanently delete media that has been in trash for 30 days."""
    from app.models.models import Media
    from datetime import timedelta
    
    db = get_sync_db_session()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        old_deleted = db.query(Media).filter(
            Media.is_deleted == True,
            Media.deleted_at < cutoff_date
        ).all()
        
        count = len(old_deleted)
        
        for media in old_deleted:
            # Delete thumbnails
            for thumb_path in [media.thumbnail_small, media.thumbnail_medium, media.thumbnail_large]:
                if thumb_path and os.path.exists(thumb_path):
                    try:
                        os.remove(thumb_path)
                    except:
                        pass
            
            db.delete(media)
        
        db.commit()
        logger.info(f"Cleaned up {count} permanently deleted media items")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()


# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-deleted-media': {
        'task': 'cleanup_deleted_media',
        'schedule': 86400.0,  # Daily
    },
}
