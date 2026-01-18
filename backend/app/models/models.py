"""
SQLAlchemy models for PhotoVault.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Index,
    Integer, String, Text, JSON, Table, UniqueConstraint, LargeBinary
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pgvector.sqlalchemy import Vector

from app.db.session import Base
from app.core.config import settings


# Association tables
album_media = Table(
    "album_media",
    Base.metadata,
    Column("album_id", UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True),
    Column("media_id", UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("added_at", DateTime, default=datetime.utcnow),
    Column("order", Integer, default=0),
)

media_tags = Table(
    "media_tags",
    Base.metadata,
    Column("media_id", UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("confidence", Float, default=1.0),
    Column("source", String(50), default="manual"),  # manual, clip, yolo
)


class User(Base):
    """User model with authentication and profile data."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    role = Column(String(50), default="user")  # admin, user
    
    # NAS mapping
    nas_path = Column(String(512))
    storage_quota_gb = Column(Integer, default=100)
    storage_used_bytes = Column(Integer, default=0)
    
    # Settings
    settings = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    media = relationship("Media", back_populates="owner", cascade="all, delete-orphan")
    albums = relationship("Album", back_populates="owner", cascade="all, delete-orphan")
    people = relationship("Person", back_populates="owner", cascade="all, delete-orphan")
    smart_albums = relationship("SmartAlbum", back_populates="owner", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


class Media(Base):
    """Media item (photo or video) model."""
    __tablename__ = "media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # File info
    filename = Column(String(512), nullable=False)
    original_path = Column(String(1024), nullable=False)
    relative_path = Column(String(1024))
    file_hash = Column(String(64), index=True)  # SHA-256 for duplicate detection
    file_size = Column(Integer)
    mime_type = Column(String(100))
    media_type = Column(String(20))  # photo, video
    
    # Dimensions
    width = Column(Integer)
    height = Column(Integer)
    duration = Column(Float)  # For videos, in seconds
    
    # Thumbnails
    thumbnail_small = Column(String(512))
    thumbnail_medium = Column(String(512))
    thumbnail_large = Column(String(512))
    
    # EXIF/Metadata
    taken_at = Column(DateTime, index=True)
    camera_make = Column(String(100))
    camera_model = Column(String(100))
    lens_model = Column(String(100))
    focal_length = Column(Float)
    aperture = Column(Float)
    iso = Column(Integer)
    shutter_speed = Column(String(50))
    
    # Location
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)
    location_name = Column(String(255))
    country = Column(String(100))
    city = Column(String(100))
    
    # AI Processing
    clip_embedding = Column(Vector(settings.VECTOR_DIMENSION))
    clip_processed = Column(Boolean, default=False)
    face_processed = Column(Boolean, default=False)
    yolo_processed = Column(Boolean, default=False)
    
    # YOLO detections stored as JSON
    yolo_detections = Column(JSON)
    
    # Status
    is_favorite = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at = Column(DateTime)
    
    # Relationships
    owner = relationship("User", back_populates="media")
    albums = relationship("Album", secondary=album_media, back_populates="media")
    tags = relationship("Tag", secondary=media_tags, back_populates="media")
    faces = relationship("Face", back_populates="media", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_media_owner_taken", "owner_id", "taken_at"),
        Index("ix_media_owner_created", "owner_id", "created_at"),
        Index("ix_media_hash", "file_hash"),
        Index("ix_media_location", "latitude", "longitude"),
        UniqueConstraint("owner_id", "original_path", name="uq_media_owner_path"),
    )


class Album(Base):
    """Album model for organizing media."""
    __tablename__ = "albums"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    cover_media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"))
    
    # Settings
    is_shared = Column(Boolean, default=False)
    share_token = Column(String(64), unique=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="albums")
    media = relationship("Media", secondary=album_media, back_populates="albums")
    cover_media = relationship("Media", foreign_keys=[cover_media_id])
    
    __table_args__ = (
        Index("ix_albums_owner", "owner_id"),
        UniqueConstraint("owner_id", "name", name="uq_album_owner_name"),
    )


class SmartAlbum(Base):
    """Smart album with saved search queries."""
    __tablename__ = "smart_albums"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    query = Column(Text, nullable=False)  # Natural language query
    filters = Column(JSON)  # Structured filters
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="smart_albums")


class Tag(Base):
    """Tag model for categorizing media."""
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50))  # object, scene, activity, etc.
    
    # CLIP embedding for semantic search
    clip_embedding = Column(Vector(settings.VECTOR_DIMENSION))
    
    # Relationships
    media = relationship("Media", secondary=media_tags, back_populates="tags")


class Person(Base):
    """Person model for face recognition grouping."""
    __tablename__ = "people"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255))
    is_named = Column(Boolean, default=False)
    
    # Representative face embedding (average of all faces)
    face_embedding = Column(Vector(128))  # dlib face encoding is 128-dimensional
    
    # Cover face
    cover_face_id = Column(UUID(as_uuid=True), ForeignKey("faces.id", ondelete="SET NULL"))
    
    # Stats
    face_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="people")
    faces = relationship("Face", back_populates="person", foreign_keys="Face.person_id")
    
    __table_args__ = (
        Index("ix_people_owner", "owner_id"),
    )


class Face(Base):
    """Face detection model."""
    __tablename__ = "faces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id", ondelete="SET NULL"))
    
    # Bounding box (normalized 0-1)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    
    # Face encoding
    encoding = Column(Vector(128))  # dlib 128-dimensional encoding
    
    # Quality metrics
    confidence = Column(Float)
    blur_score = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    media = relationship("Media", back_populates="faces")
    person = relationship("Person", back_populates="faces", foreign_keys=[person_id])
    
    __table_args__ = (
        Index("ix_faces_media", "media_id"),
        Index("ix_faces_person", "person_id"),
    )


class ProcessingJob(Base):
    """Background processing job tracking."""
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    
    job_type = Column(String(50), nullable=False)  # scan, index, face, clip, yolo
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    
    # Progress
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Details
    params = Column(JSON)
    result = Column(JSON)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    __table_args__ = (
        Index("ix_jobs_user_status", "user_id", "status"),
    )


class EmailVerification(Base):
    """Email verification tokens."""
    __tablename__ = "email_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(512), nullable=False, unique=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Audit log for tracking user actions."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(UUID(as_uuid=True))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_audit_user_action", "user_id", "action"),
        Index("ix_audit_created", "created_at"),
    )
