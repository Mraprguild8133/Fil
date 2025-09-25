import os
import io
import logging
from config import Config

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self):
        self.storage_dir = Config.STORAGE_DIR
    
    def is_file_allowed(self, file_name):
        """Check if file extension is allowed"""
        try:
            ext = os.path.splitext(file_name)[1].lower()
            for category, extensions in Config.ALLOWED_EXTENSIONS.items():
                if ext in extensions:
                    return True, category
            return False, 'unknown'
        except Exception as e:
            logger.error(f"Error checking file allowance: {e}")
            return False, 'unknown'
    
    def format_file_size(self, size_bytes):
        """Convert bytes to human readable format"""
        try:
            if size_bytes == 0:
                return "0B"
            size_names = ["B", "KB", "MB", "GB"]
            i = 0
            while size_bytes >= 1024 and i < len(size_names)-1:
                size_bytes /= 1024.0
                i += 1
            return f"{size_bytes:.2f} {size_names[i]}"
        except Exception as e:
            logger.error(f"Error formatting file size: {e}")
            return "Unknown"
