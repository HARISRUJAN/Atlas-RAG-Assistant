"""File validation utilities."""

import os
from werkzeug.datastructures import FileStorage
from backend.config import Config


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def validate_file(file: FileStorage) -> tuple[bool, str]:
    """
    Validate uploaded file.
    
    Args:
        file: Uploaded file object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
    
    if file.filename == '':
        return False, "No file selected"
    
    if not allowed_file(file.filename):
        return False, f"File type not allowed. Allowed types: {', '.join(Config.ALLOWED_EXTENSIONS)}"
    
    # Check file size (if we can)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > Config.MAX_FILE_SIZE_BYTES:
        return False, f"File too large. Maximum size: {Config.MAX_FILE_SIZE_MB}MB"
    
    return True, ""

