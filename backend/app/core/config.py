"""
Application configuration using Pydantic Settings.
"""
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "PhotoVault"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production-use-strong-secret-key"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://photovault:photovault@db:5432/photovault"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    
    # JWT
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@photovault.local"
    SMTP_FROM_NAME: str = "PhotoVault"
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    
    # NAS/SMB
    NAS_HOST: str = "192.168.1.100"
    NAS_PORT: int = 445
    NAS_USERNAME: str = ""
    NAS_PASSWORD: str = ""
    NAS_SHARE_NAME: str = "photos"
    NAS_MOUNT_PATH: str = "/mnt/nas"
    
    # Storage
    LOCAL_STORAGE_PATH: str = "/app/data"
    THUMBNAIL_PATH: str = "/app/data/thumbnails"
    CACHE_PATH: str = "/app/data/cache"
    
    # AI Features
    AI_ENABLED: bool = True
    FACE_RECOGNITION_ENABLED: bool = True
    CLIP_ENABLED: bool = True
    YOLO_ENABLED: bool = True
    
    # AI Models
    CLIP_MODEL: str = "ViT-B-32"
    CLIP_PRETRAINED: str = "openai"
    YOLO_MODEL: str = "yolov8n.pt"
    FACE_RECOGNITION_MODEL: str = "hog"  # or "cnn" for GPU
    FACE_RECOGNITION_TOLERANCE: float = 0.6
    
    # Processing
    BATCH_SIZE: int = 32
    MAX_CONCURRENT_JOBS: int = 4
    THUMBNAIL_SIZES: List[int] = [150, 300, 600, 1200]
    
    # Vector Search
    VECTOR_DIMENSION: int = 512
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Admin
    ADMIN_EMAIL: str = "admin@photovault.local"
    ADMIN_PASSWORD: str = "admin123"
    REQUIRE_ADMIN_APPROVAL: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("THUMBNAIL_SIZES", mode="before")
    @classmethod
    def parse_thumbnail_sizes(cls, v):
        if isinstance(v, str):
            return [int(s.strip()) for s in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
