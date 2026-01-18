"""
SMB client for Synology NAS integration.
"""
import os
from pathlib import Path
from typing import List, Optional, Generator
import structlog
from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.open import Open, CreateDisposition, FileAttributes, ShareAccess, ImpersonationLevel
from smbprotocol.file_info import FileInformationClass
import uuid

from app.core.config import settings


logger = structlog.get_logger()


class SMBClient:
    """SMB client for connecting to Synology NAS."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        share_name: str = None
    ):
        self.host = host or settings.NAS_HOST
        self.port = port or settings.NAS_PORT
        self.username = username or settings.NAS_USERNAME
        self.password = password or settings.NAS_PASSWORD
        self.share_name = share_name or settings.NAS_SHARE_NAME
        
        self.connection = None
        self.session = None
        self.tree = None
    
    def connect(self) -> bool:
        """Establish connection to SMB share."""
        try:
            # Create connection
            self.connection = Connection(uuid.uuid4(), self.host, self.port)
            self.connection.connect()
            
            # Create session
            self.session = Session(self.connection, self.username, self.password)
            self.session.connect()
            
            # Connect to share
            share_path = f"\\\\{self.host}\\{self.share_name}"
            self.tree = TreeConnect(self.session, share_path)
            self.tree.connect()
            
            logger.info(f"Connected to SMB share: {share_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SMB share: {e}")
            return False
    
    def disconnect(self):
        """Close SMB connection."""
        try:
            if self.tree:
                self.tree.disconnect()
            if self.session:
                self.session.disconnect()
            if self.connection:
                self.connection.disconnect()
            logger.info("Disconnected from SMB share")
        except Exception as e:
            logger.warning(f"Error during SMB disconnect: {e}")
    
    def list_directory(self, path: str = "") -> List[dict]:
        """List contents of a directory."""
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            # Open directory
            dir_open = Open(self.tree, path)
            dir_open.create(
                ImpersonationLevel.Impersonation,
                ShareAccess.FILE_SHARE_READ,
                CreateDisposition.FILE_OPEN,
                FileAttributes.FILE_ATTRIBUTE_DIRECTORY
            )
            
            # Query directory contents
            entries = []
            query_info = dir_open.query_directory("*", FileInformationClass.FILE_DIRECTORY_INFORMATION)
            
            for entry in query_info:
                name = entry['file_name'].get_value().decode('utf-16-le')
                if name in ('.', '..'):
                    continue
                
                entries.append({
                    'name': name,
                    'is_directory': bool(entry['file_attributes'].get_value() & FileAttributes.FILE_ATTRIBUTE_DIRECTORY),
                    'size': entry['end_of_file'].get_value(),
                    'created': entry['creation_time'].get_value(),
                    'modified': entry['last_write_time'].get_value()
                })
            
            dir_open.close()
            return entries
            
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            return []
    
    def read_file(self, path: str) -> Optional[bytes]:
        """Read a file from the SMB share."""
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            file_open = Open(self.tree, path)
            file_open.create(
                ImpersonationLevel.Impersonation,
                ShareAccess.FILE_SHARE_READ,
                CreateDisposition.FILE_OPEN,
                FileAttributes.FILE_ATTRIBUTE_NORMAL
            )
            
            # Read file content
            content = file_open.read(0, file_open.end_of_file)
            file_open.close()
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return None
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists on the SMB share."""
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            file_open = Open(self.tree, path)
            file_open.create(
                ImpersonationLevel.Impersonation,
                ShareAccess.FILE_SHARE_READ,
                CreateDisposition.FILE_OPEN,
                FileAttributes.FILE_ATTRIBUTE_NORMAL
            )
            file_open.close()
            return True
        except:
            return False
    
    def walk(self, path: str = "") -> Generator[tuple, None, None]:
        """Walk through directory tree (like os.walk)."""
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            entries = self.list_directory(path)
            
            dirs = []
            files = []
            
            for entry in entries:
                if entry['is_directory']:
                    dirs.append(entry['name'])
                else:
                    files.append(entry['name'])
            
            yield (path, dirs, files)
            
            for dir_name in dirs:
                subpath = f"{path}\\{dir_name}" if path else dir_name
                yield from self.walk(subpath)
                
        except Exception as e:
            logger.error(f"Error walking directory {path}: {e}")


def mount_nas_share(
    mount_point: str = None,
    host: str = None,
    share_name: str = None,
    username: str = None,
    password: str = None
) -> bool:
    """Mount NAS share using system mount command (Linux)."""
    mount_point = mount_point or settings.NAS_MOUNT_PATH
    host = host or settings.NAS_HOST
    share_name = share_name or settings.NAS_SHARE_NAME
    username = username or settings.NAS_USERNAME
    password = password or settings.NAS_PASSWORD
    
    try:
        # Create mount point if it doesn't exist
        os.makedirs(mount_point, exist_ok=True)
        
        # Check if already mounted
        if os.path.ismount(mount_point):
            logger.info(f"NAS share already mounted at {mount_point}")
            return True
        
        # Mount using CIFS
        mount_cmd = f"mount -t cifs //{host}/{share_name} {mount_point} -o username={username},password={password},vers=3.0"
        
        import subprocess
        result = subprocess.run(
            mount_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully mounted NAS share at {mount_point}")
            return True
        else:
            logger.error(f"Failed to mount NAS share: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error mounting NAS share: {e}")
        return False


def unmount_nas_share(mount_point: str = None) -> bool:
    """Unmount NAS share."""
    mount_point = mount_point or settings.NAS_MOUNT_PATH
    
    try:
        if not os.path.ismount(mount_point):
            logger.info(f"NAS share not mounted at {mount_point}")
            return True
        
        import subprocess
        result = subprocess.run(
            f"umount {mount_point}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully unmounted NAS share from {mount_point}")
            return True
        else:
            logger.error(f"Failed to unmount NAS share: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error unmounting NAS share: {e}")
        return False


def get_user_nas_path(user_nas_path: str) -> str:
    """Get the full path to a user's NAS folder."""
    if user_nas_path.startswith('/'):
        # Absolute path within mount
        return os.path.join(settings.NAS_MOUNT_PATH, user_nas_path.lstrip('/'))
    else:
        # Relative path
        return os.path.join(settings.NAS_MOUNT_PATH, user_nas_path)


def is_nas_accessible() -> bool:
    """Check if NAS mount is accessible."""
    mount_path = settings.NAS_MOUNT_PATH
    
    if not os.path.exists(mount_path):
        return False
    
    if not os.path.ismount(mount_path):
        return False
    
    try:
        os.listdir(mount_path)
        return True
    except:
        return False
