"""
Admin Secrets API - Hidden field in settings to view database passwords
Only accessible by admin users with additional verification
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import hashlib

from app.api.deps import get_current_admin_user
from app.models.models import User
from app.core.config import settings

router = APIRouter()


class SecretAccessRequest(BaseModel):
    """Request to access secrets - requires admin password confirmation"""
    admin_password: str
    reason: str  # Audit trail


class SecretsResponse(BaseModel):
    """Response containing system secrets"""
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str
    redis_url: str
    secret_key_hash: str  # Only show hash of JWT secret
    accessed_at: datetime
    accessed_by: str


class SecretAccessLog(BaseModel):
    """Audit log entry for secret access"""
    user_id: int
    user_email: str
    accessed_at: datetime
    reason: str
    ip_address: Optional[str]


# In-memory audit log (in production, store in database)
secret_access_logs: list[SecretAccessLog] = []


@router.post("/secrets/verify", response_model=SecretsResponse)
async def get_system_secrets(
    request: SecretAccessRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get system secrets including database passwords.
    
    This endpoint is only accessible by admin users and requires
    password re-verification for security.
    
    All access is logged for audit purposes.
    """
    from app.core.security import verify_password
    
    # Verify admin password again for security
    if not verify_password(request.admin_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password"
        )
    
    # Log the access
    log_entry = SecretAccessLog(
        user_id=current_user.id,
        user_email=current_user.email,
        accessed_at=datetime.utcnow(),
        reason=request.reason,
        ip_address=None
    )
    secret_access_logs.append(log_entry)
    
    # Parse database URL
    db_url = settings.DATABASE_URL
    try:
        db_parts = db_url.replace("postgresql://", "").split("@")
        user_pass = db_parts[0].split(":")
        host_port_db = db_parts[1].split("/")
        host_port = host_port_db[0].split(":")
        
        db_user = user_pass[0]
        db_password = user_pass[1] if len(user_pass) > 1 else ""
        db_host = host_port[0]
        db_port = int(host_port[1]) if len(host_port) > 1 else 5432
        db_name = host_port_db[1] if len(host_port_db) > 1 else "photovault"
    except Exception:
        db_user = "unknown"
        db_password = "parse_error"
        db_host = "unknown"
        db_port = 5432
        db_name = "unknown"
    
    secret_key_hash = hashlib.sha256(
        settings.SECRET_KEY.encode()
    ).hexdigest()[:16] + "..."
    
    return SecretsResponse(
        database_host=db_host,
        database_port=db_port,
        database_name=db_name,
        database_user=db_user,
        database_password=db_password,
        redis_url=settings.REDIS_URL,
        secret_key_hash=secret_key_hash,
        accessed_at=datetime.utcnow(),
        accessed_by=current_user.email
    )


@router.get("/secrets/access-logs")
async def get_secret_access_logs(
    current_user: User = Depends(get_current_admin_user)
):
    """Get audit logs of who accessed system secrets."""
    return {
        "logs": [log.dict() for log in secret_access_logs[-100:]],
        "total_accesses": len(secret_access_logs)
    }


@router.get("/secrets/available")
async def check_secrets_available(
    current_user: User = Depends(get_current_admin_user)
):
    """Check if secrets viewing is available (admin only)."""
    return {
        "available": True,
        "requires_password_verification": True,
        "audit_logging_enabled": True,
        "last_accessed": secret_access_logs[-1].accessed_at if secret_access_logs else None
    }
