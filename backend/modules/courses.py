"""
Courses module for TAI Tutor AI.

This module handles course file management and directory operations.
"""

import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import with fallback for running as script
try:
    from config import DATA_DIR, BACKEND_DIR
except ImportError:
    from config import DATA_DIR, BACKEND_DIR

logger = logging.getLogger("backend.modules.courses")

# Course data directory
COURSE_DATA_DIR = BACKEND_DIR / "course-data"

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {'zip', 'pdf', 'pptx', 'txt', 'md', 'py', 'ipynb'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_course_data_dir() -> Path:
    """Get the course data directory path."""
    return COURSE_DATA_DIR


def ensure_course_dir_exists() -> Path:
    """Ensure course data directory exists."""
    COURSE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return COURSE_DATA_DIR


def build_directory_tree(path: Path) -> Dict[str, Any]:
    """
    Recursively build directory tree structure.
    
    Args:
        path: Path to directory or file
    
    Returns:
        Dict with directory tree structure
    """
    tree = {
        "name": path.name,
        "path": str(path.relative_to(COURSE_DATA_DIR)),
        "type": "directory" if path.is_dir() else "file",
        "size": path.stat().st_size if path.is_file() else 0
    }
    
    if path.is_dir():
        tree["children"] = []
        try:
            for child in sorted(path.iterdir()):
                tree["children"].append(build_directory_tree(child))
        except PermissionError:
            pass
    
    return tree


def list_courses() -> List[Dict[str, Any]]:
    """
    List all courses in the course data directory.
    
    Returns:
        List of course directory trees
    """
    ensure_course_dir_exists()
    
    courses = []
    for course_dir in COURSE_DATA_DIR.iterdir():
        if course_dir.is_dir():
            courses.append(build_directory_tree(course_dir))
    
    return courses


def upload_course_file(
    file,
    target_path: str,
    filename: str
) -> Dict[str, Any]:
    """
    Upload a course file to the specified path.
    
    Args:
        file: File object to upload
        target_path: Target directory path
        filename: Secure filename
    
    Returns:
        Dict with upload result
    """
    from werkzeug.utils import secure_filename
    
    # Create full target directory path
    target_dir = COURSE_DATA_DIR / secure_filename(target_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle zip files - extract them
    if filename.lower().endswith('.zip'):
        # Save zip temporarily
        temp_zip = target_dir / filename
        file.save(temp_zip)
        
        # Extract zip
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        # Remove temporary zip file
        temp_zip.unlink()
        
        return {
            "success": True,
            "message": f"Zip file extracted to {target_path}",
            "path": str(target_dir.relative_to(COURSE_DATA_DIR))
        }
    else:
        # For non-zip files, just save them
        file_path = target_dir / filename
        file.save(file_path)
        
        return {
            "success": True,
            "message": f"File uploaded to {target_path}",
            "path": str(file_path.relative_to(COURSE_DATA_DIR))
        }


def delete_course_paths(paths: List[str]) -> Dict[str, Any]:
    """
    Delete course files or directories.
    
    Args:
        paths: List of paths to delete
    
    Returns:
        Dict with deleted paths and errors
    """
    deleted = []
    errors = []
    
    for path_str in paths:
        try:
            # Normalize path separators
            normalized_path = path_str.replace('\\', '/')
            
            # Prevent directory traversal attacks
            if '..' in normalized_path or normalized_path.startswith('/'):
                errors.append(f"Invalid path: {path_str}")
                continue
            
            full_path = (COURSE_DATA_DIR / normalized_path).resolve()
            
            # Ensure path is within course data directory
            if not str(full_path).startswith(str(COURSE_DATA_DIR.resolve())):
                errors.append(f"Path outside course directory: {path_str}")
                continue
            
            if full_path.exists():
                if full_path.is_dir():
                    shutil.rmtree(full_path)
                else:
                    full_path.unlink()
                deleted.append(path_str)
                logger.info(f"Deleted course path: {path_str}")
            else:
                errors.append(f"Path not found: {path_str}")
        except Exception as e:
            errors.append(f"Error deleting {path_str}: {str(e)}")
    
    return {
        "success": True,
        "deleted": deleted,
        "errors": errors
    }


def get_course_stats() -> Dict[str, int]:
    """
    Get course statistics.
    
    Returns:
        Dict with course counts
    """
    ensure_course_dir_exists()
    
    return {
        "courses_count": len(list(COURSE_DATA_DIR.glob("*")))
    }
