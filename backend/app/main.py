"""
PhotoVault - Self-hosted Photo Management System
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog
import os

from app.core.config import settings
from app.db.session import init_db, close_db
from app.api.routes import auth, users, media, albums, people, search, admin, jobs


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting PhotoVault application")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Create required directories
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.THUMBNAIL_PATH, exist_ok=True)
    os.makedirs(settings.CACHE_PATH, exist_ok=True)
    
    # Create default admin user if not exists
    await create_default_admin()
    
    yield
    
    # Shutdown
    logger.info("Shutting down PhotoVault application")
    await close_db()


async def create_default_admin():
    """Create default admin user if not exists."""
    from sqlalchemy import select
    from app.db.session import async_session_maker
    from app.models.models import User
    from app.core.security import get_password_hash
    
    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                full_name="Administrator",
                is_active=True,
                is_verified=True,
                is_approved=True,
                role="admin"
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Created default admin user: {settings.ADMIN_EMAIL}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Self-hosted photo management system with AI features",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(albums.router, prefix="/api")
app.include_router(people.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


# Mount static files for thumbnails (if serving directly)
if os.path.exists(settings.THUMBNAIL_PATH):
    app.mount(
        "/thumbnails",
        StaticFiles(directory=settings.THUMBNAIL_PATH),
        name="thumbnails"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS if not settings.DEBUG else 1
    )
