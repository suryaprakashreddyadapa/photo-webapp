"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============== Auth Schemas ==============

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)


class EmailVerify(BaseModel):
    """Schema for email verification."""
    token: str


# ============== User Schemas ==============

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    is_active: bool
    is_verified: bool
    is_approved: bool
    role: str
    nas_path: Optional[str] = None
    storage_quota_gb: int
    storage_used_bytes: int
    settings: Dict[str, Any] = {}
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for user update."""
    full_name: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class UserAdminUpdate(BaseModel):
    """Schema for admin user update."""
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    role: Optional[str] = None
    nas_path: Optional[str] = None
    storage_quota_gb: Optional[int] = None


# ============== Media Schemas ==============

class MediaBase(BaseModel):
    """Base media schema."""
    filename: str
    media_type: str


class MediaResponse(BaseModel):
    """Schema for media response."""
    id: UUID
    filename: str
    original_path: str
    relative_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    media_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    thumbnail_small: Optional[str] = None
    thumbnail_medium: Optional[str] = None
    thumbnail_large: Optional[str] = None
    taken_at: Optional[datetime] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    is_favorite: bool = False
    is_hidden: bool = False
    created_at: datetime
    tags: List[str] = []
    faces_count: int = 0
    
    class Config:
        from_attributes = True


class MediaUpdate(BaseModel):
    """Schema for media update."""
    is_favorite: Optional[bool] = None
    is_hidden: Optional[bool] = None


class MediaBulkAction(BaseModel):
    """Schema for bulk media actions."""
    media_ids: List[UUID]
    action: str  # favorite, unfavorite, hide, unhide, delete


# ============== Album Schemas ==============

class AlbumCreate(BaseModel):
    """Schema for album creation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class AlbumResponse(BaseModel):
    """Schema for album response."""
    id: UUID
    name: str
    description: Optional[str] = None
    cover_media_id: Optional[UUID] = None
    cover_thumbnail: Optional[str] = None
    media_count: int = 0
    is_shared: bool = False
    share_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlbumUpdate(BaseModel):
    """Schema for album update."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cover_media_id: Optional[UUID] = None


class AlbumAddMedia(BaseModel):
    """Schema for adding media to album."""
    media_ids: List[UUID]


# ============== Smart Album Schemas ==============

class SmartAlbumCreate(BaseModel):
    """Schema for smart album creation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    query: str
    filters: Optional[Dict[str, Any]] = None


class SmartAlbumResponse(BaseModel):
    """Schema for smart album response."""
    id: UUID
    name: str
    description: Optional[str] = None
    query: str
    filters: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============== Person/Face Schemas ==============

class PersonResponse(BaseModel):
    """Schema for person response."""
    id: UUID
    name: Optional[str] = None
    is_named: bool = False
    face_count: int = 0
    cover_face_thumbnail: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PersonUpdate(BaseModel):
    """Schema for person update."""
    name: str = Field(..., min_length=1, max_length=255)


class PersonMerge(BaseModel):
    """Schema for merging persons."""
    source_person_ids: List[UUID]
    target_person_id: UUID


class FaceResponse(BaseModel):
    """Schema for face response."""
    id: UUID
    media_id: UUID
    person_id: Optional[UUID] = None
    x: float
    y: float
    width: float
    height: float
    confidence: Optional[float] = None
    thumbnail: Optional[str] = None
    
    class Config:
        from_attributes = True


class FaceAssign(BaseModel):
    """Schema for assigning face to person."""
    person_id: UUID


# ============== Tag Schemas ==============

class TagResponse(BaseModel):
    """Schema for tag response."""
    id: UUID
    name: str
    category: Optional[str] = None
    media_count: int = 0
    
    class Config:
        from_attributes = True


# ============== Search Schemas ==============

class SearchQuery(BaseModel):
    """Schema for search query."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    page: int = 1
    page_size: int = 50
    sort_by: str = "taken_at"
    sort_order: str = "desc"


class SearchResponse(BaseModel):
    """Schema for search response."""
    query: str
    total: int
    page: int
    page_size: int
    results: List[MediaResponse]
    suggestions: List[str] = []


# ============== AI Assistant Schemas ==============

class AskQuery(BaseModel):
    """Schema for AI assistant query."""
    query: str
    context: Optional[Dict[str, Any]] = None


class AskResponse(BaseModel):
    """Schema for AI assistant response."""
    query: str
    response: str
    action: Optional[str] = None  # search, create_album, delete_album, etc.
    action_result: Optional[Dict[str, Any]] = None
    media: Optional[List[MediaResponse]] = None


# ============== Job Schemas ==============

class JobResponse(BaseModel):
    """Schema for job response."""
    id: UUID
    job_type: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    progress: float
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    """Schema for job creation."""
    job_type: str
    params: Optional[Dict[str, Any]] = None


# ============== Settings Schemas ==============

class UserSettings(BaseModel):
    """Schema for user settings."""
    nas_paths: List[str] = []
    face_recognition_enabled: bool = True
    clip_enabled: bool = True
    yolo_enabled: bool = True
    auto_index: bool = True
    index_interval_hours: int = 24
    thumbnail_quality: int = 85
    video_thumbnail_count: int = 3
    dark_mode: bool = True
    grid_size: str = "medium"  # small, medium, large
    sort_by: str = "taken_at"
    sort_order: str = "desc"


class SystemSettings(BaseModel):
    """Schema for system settings (admin only)."""
    require_admin_approval: bool = True
    max_upload_size_mb: int = 100
    allowed_extensions: List[str] = ["jpg", "jpeg", "png", "gif", "webp", "heic", "raw", "mp4", "mov", "avi"]
    ai_batch_size: int = 32
    max_concurrent_jobs: int = 4


# ============== Stats Schemas ==============

class UserStats(BaseModel):
    """Schema for user statistics."""
    total_photos: int
    total_videos: int
    total_albums: int
    total_people: int
    storage_used_bytes: int
    storage_quota_bytes: int
    photos_by_year: Dict[int, int]
    photos_by_month: Dict[str, int]


class SystemStats(BaseModel):
    """Schema for system statistics (admin only)."""
    total_users: int
    active_users: int
    pending_users: int
    total_media: int
    total_storage_bytes: int
    jobs_pending: int
    jobs_running: int


# ============== Pagination ==============

class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    total: int
    page: int
    page_size: int
    pages: int
    items: List[Any]
