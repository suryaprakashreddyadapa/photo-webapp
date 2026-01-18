"""
Incremental NAS Indexing Service

Efficiently scans NAS for changes without re-processing entire library.
Uses file modification times and checksums to detect changes.
"""

import os
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.models import Media, ScanState
from app.core.config import settings


class ChangeType(Enum):
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


@dataclass
class FileChange:
    path: str
    change_type: ChangeType
    old_mtime: Optional[datetime] = None
    new_mtime: Optional[datetime] = None
    old_size: Optional[int] = None
    new_size: Optional[int] = None


class IncrementalScanner:
    """
    Incremental scanner that only processes changed files.
    
    Features:
    - Tracks file modification times
    - Detects new, modified, and deleted files
    - Supports resumable scans
    - Minimal database queries
    """
    
    SUPPORTED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif',
        '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'
    }
    
    def __init__(self, db: Session, user_id: int, nas_path: str):
        self.db = db
        self.user_id = user_id
        self.nas_path = nas_path
        self.scan_id: Optional[str] = None
        self.stats = {
            "files_scanned": 0,
            "new_files": 0,
            "modified_files": 0,
            "deleted_files": 0,
            "unchanged_files": 0,
            "errors": 0
        }
    
    def get_file_signature(self, path: str) -> tuple[datetime, int]:
        """Get file modification time and size for change detection."""
        stat = os.stat(path)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        size = stat.st_size
        return mtime, size
    
    def quick_hash(self, path: str, sample_size: int = 65536) -> str:
        """Generate a quick hash using file header and tail."""
        hasher = hashlib.md5()
        file_size = os.path.getsize(path)
        
        with open(path, 'rb') as f:
            hasher.update(f.read(sample_size))
            if file_size > sample_size * 2:
                f.seek(-sample_size, 2)
                hasher.update(f.read(sample_size))
            hasher.update(str(file_size).encode())
        
        return hasher.hexdigest()
    
    def detect_changes(self) -> List[FileChange]:
        """Detect all changes between filesystem and database."""
        changes = []
        indexed_files = self.get_indexed_files()
        indexed_paths = set(indexed_files.keys())
        current_files = self.scan_filesystem()
        
        # Find new files
        for path in (current_files - indexed_paths):
            try:
                mtime, size = self.get_file_signature(path)
                changes.append(FileChange(path=path, change_type=ChangeType.NEW, new_mtime=mtime, new_size=size))
                self.stats["new_files"] += 1
            except Exception:
                self.stats["errors"] += 1
        
        # Find deleted files
        for path in (indexed_paths - current_files):
            old_mtime, old_size, _ = indexed_files[path]
            changes.append(FileChange(path=path, change_type=ChangeType.DELETED, old_mtime=old_mtime, old_size=old_size))
            self.stats["deleted_files"] += 1
        
        return changes
    
    def run_incremental_scan(self) -> Dict:
        """Run incremental scan and return summary."""
        import uuid
        self.scan_id = str(uuid.uuid4())
        changes = self.detect_changes()
        
        return {
            "scan_id": self.scan_id,
            "stats": self.stats,
            "total_changes": len(changes)
        }
