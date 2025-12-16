"""
Admin module for TAI Tutor AI.

This module provides administrative functions for:
- User management
- Course management
- System health monitoring
- Configuration management
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Import with fallback for running as script
try:
    from config import (
        USER_DATA_DIR,
        DATA_DIR,
        INDEX_DIR,
        MAIN_PROJECT_DIR,
    )
except ImportError:
    from config import (
        USER_DATA_DIR,
        DATA_DIR,
        INDEX_DIR,
        MAIN_PROJECT_DIR,
    )

logger = logging.getLogger("backend.admin.admin")


# =============================================================================
# User Management
# =============================================================================

def list_users() -> List[Dict[str, Any]]:
    """
    List all registered users.
    
    Returns:
        List of user info dictionaries
    """
    users = []
    login_dir = Path(USER_DATA_DIR) / "login_register"
    
    if not login_dir.exists():
        return users
    
    for user_file in login_dir.glob("*.json"):
        try:
            with open(user_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Extract email from filename or data
            email = data.get("email") or user_file.stem.replace("__at__", "@").replace("__dot__", ".")
            
            users.append({
                "email": email,
                "name": data.get("name", "N/A"),
                "created_at": data.get("created_at"),
                "last_login": data.get("last_login"),
            })
        except Exception as e:
            logger.warning(f"Failed to read user file {user_file}: {e}")
            continue
    
    return sorted(users, key=lambda u: u.get("email", "").lower())


def get_user_details(email: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific user.
    
    Args:
        email: User's email address
    
    Returns:
        User details dictionary or None if not found
    """
    safe_email = email.replace("@", "__at__").replace(".", "__dot__")
    user_file = Path(USER_DATA_DIR) / "login_register" / f"{safe_email}.json"
    
    if not user_file.exists():
        return None
    
    try:
        with open(user_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Count user's chats
        chat_dir = Path(USER_DATA_DIR) / "chats" / safe_email
        chat_count = len(list(chat_dir.glob("*.json"))) if chat_dir.exists() else 0
        
        # Count user's quizzes
        quiz_dir = Path(USER_DATA_DIR) / "quiz" / email
        quiz_count = len(list(quiz_dir.glob("*.json"))) if quiz_dir.exists() else 0
        
        # Count user's plans
        plan_dir = Path(USER_DATA_DIR) / "saved_plans" / email
        plan_count = len(list(plan_dir.glob("*.json"))) if plan_dir.exists() else 0
        
        return {
            "email": email,
            "name": data.get("name", "N/A"),
            "created_at": data.get("created_at"),
            "last_login": data.get("last_login"),
            "chat_count": chat_count,
            "quiz_count": quiz_count,
            "plan_count": plan_count,
        }
    except Exception as e:
        logger.error(f"Failed to get user details for {email}: {e}")
        return None


def delete_user(email: str) -> bool:
    """
    Delete a user and their data.
    
    Args:
        email: User's email address
    
    Returns:
        True if deletion was successful
    """
    safe_email = email.replace("@", "__at__").replace(".", "__dot__")
    
    deleted = False
    
    # Delete user credentials file
    user_file = Path(USER_DATA_DIR) / "login_register" / f"{safe_email}.json"
    if user_file.exists():
        try:
            user_file.unlink()
            deleted = True
            logger.info(f"Deleted user credentials for {email}")
        except Exception as e:
            logger.error(f"Failed to delete user credentials: {e}")
    
    # Delete user's chat history
    chat_dir = Path(USER_DATA_DIR) / "chats" / safe_email
    if chat_dir.exists():
        try:
            import shutil
            shutil.rmtree(chat_dir)
            logger.info(f"Deleted chat history for {email}")
        except Exception as e:
            logger.error(f"Failed to delete chat history: {e}")
    
    return deleted


# =============================================================================
# Course Management
# =============================================================================

def list_courses() -> List[Dict[str, Any]]:
    """
    List all course data directories.
    
    Returns:
        List of course info dictionaries
    """
    courses = []
    course_dir = Path(DATA_DIR)
    
    if not course_dir.exists():
        return courses
    
    for item in course_dir.iterdir():
        if item.is_dir():
            # Count files in course directory
            file_count = sum(1 for _ in item.rglob("*") if _.is_file())
            
            # Get modification time
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
            except Exception:
                mtime = None
            
            courses.append({
                "name": item.name,
                "path": str(item),
                "file_count": file_count,
                "modified_at": mtime.isoformat() if mtime else None,
            })
    
    return sorted(courses, key=lambda c: c.get("name", "").lower())


def get_course_files(course_name: str) -> List[Dict[str, Any]]:
    """
    Get list of files in a course directory.
    
    Args:
        course_name: Name of the course directory
    
    Returns:
        List of file info dictionaries
    """
    course_dir = Path(DATA_DIR) / course_name
    
    if not course_dir.exists():
        return []
    
    files = []
    for item in course_dir.rglob("*"):
        if item.is_file():
            try:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(course_dir)),
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "type": item.suffix.lower().strip(".") or "unknown",
                })
            except Exception as e:
                logger.warning(f"Failed to get file info for {item}: {e}")
                continue
    
    return sorted(files, key=lambda f: f.get("path", ""))


# =============================================================================
# System Health
# =============================================================================

def get_system_health() -> Dict[str, Any]:
    """
    Get system health status.
    
    Returns:
        Dictionary with system health information
    """
    health = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {},
    }
    
    # Check index directory
    index_path = Path(INDEX_DIR)
    index_exists = index_path.exists() and (index_path / "docstore.json").exists()
    health["components"]["index"] = {
        "status": "ok" if index_exists else "missing",
        "path": str(index_path),
        "exists": index_exists,
    }
    
    # Check data directory
    data_path = Path(DATA_DIR)
    data_exists = data_path.exists()
    file_count = sum(1 for _ in data_path.rglob("*") if _.is_file()) if data_exists else 0
    health["components"]["data"] = {
        "status": "ok" if data_exists else "missing",
        "path": str(data_path),
        "exists": data_exists,
        "file_count": file_count,
    }
    
    # Check user data directory
    user_data_path = Path(USER_DATA_DIR)
    user_data_exists = user_data_path.exists()
    health["components"]["user_data"] = {
        "status": "ok" if user_data_exists else "missing",
        "path": str(user_data_path),
        "exists": user_data_exists,
    }
    
    # Overall status
    if not all(c.get("status") == "ok" for c in health["components"].values()):
        health["status"] = "degraded"
    
    return health


def get_storage_stats() -> Dict[str, Any]:
    """
    Get storage statistics.
    
    Returns:
        Dictionary with storage statistics
    """
    stats = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "directories": {},
    }
    
    def get_dir_size(path: Path) -> int:
        """Calculate total size of directory."""
        total = 0
        if path.exists():
            for item in path.rglob("*"):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except Exception:
                        pass
        return total
    
    # Index directory
    index_path = Path(INDEX_DIR)
    stats["directories"]["index"] = {
        "path": str(index_path),
        "size_bytes": get_dir_size(index_path),
        "file_count": sum(1 for _ in index_path.rglob("*") if _.is_file()) if index_path.exists() else 0,
    }
    
    # Data directory
    data_path = Path(DATA_DIR)
    stats["directories"]["data"] = {
        "path": str(data_path),
        "size_bytes": get_dir_size(data_path),
        "file_count": sum(1 for _ in data_path.rglob("*") if _.is_file()) if data_path.exists() else 0,
    }
    
    # User data directory
    user_data_path = Path(USER_DATA_DIR)
    stats["directories"]["user_data"] = {
        "path": str(user_data_path),
        "size_bytes": get_dir_size(user_data_path),
        "file_count": sum(1 for _ in user_data_path.rglob("*") if _.is_file()) if user_data_path.exists() else 0,
    }
    
    return stats
