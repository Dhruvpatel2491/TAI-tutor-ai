"""
Admin API endpoints for TAI Tutor AI.

Blueprint for administrative operations:
- User management
- Course management
- System health
- Admin authentication
"""

import os
import logging
from flask import Blueprint, request, jsonify

# Import with fallback for running as script
try:
    from config import AUTH_DISABLED
    from admin.admin_auth import verify_user_and_admin, verify_admin_password
    from admin.admin import (
        list_users,
        get_user_details,
        delete_user,
        list_courses,
        get_course_files,
        get_system_health,
        get_storage_stats,
    )
    from modules.courses import (
        list_courses,
        upload_course_file,
        delete_course_file,
    )
except ImportError:
    pass

logger = logging.getLogger("backend.admin.endpoints_admin")

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _verify_admin_auth() -> tuple:
    """
    Verify admin authentication from request.
    
    Expects:
        - Authorization header with Bearer token (for user authentication)
        - X-Admin-Password header with admin password
    
    Returns:
        Tuple of (is_authenticated: bool, error_response: tuple or None)
    """
    # Check if admin auth is required
    if AUTH_DISABLED:
        # In dev mode, allow access without admin auth
        return True, None
    
    auth_header = request.headers.get("Authorization")
    admin_password = request.headers.get("X-Admin-Password")
    
    if not auth_header:
        return False, (jsonify({"error": "missing Authorization header"}), 401)
    
    if not admin_password:
        return False, (jsonify({"error": "missing X-Admin-Password header"}), 401)
    
    # Verify both user token and admin password
    is_valid, claims = verify_user_and_admin(auth_header, admin_password)
    
    if not is_valid:
        return False, (jsonify({"error": "invalid credentials"}), 401)
    
    return True, None


@admin_bp.route("/health", methods=["GET"])
def admin_health():
    """Get system health status."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        health = get_system_health()
        return jsonify(health), 200
    except Exception as e:
        logger.exception("Failed to get system health")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/storage", methods=["GET"])
def admin_storage():
    """Get storage statistics."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        stats = get_storage_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.exception("Failed to get storage stats")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# User Management
# =============================================================================

@admin_bp.route("/users", methods=["GET"])
def admin_list_users():
    """List all registered users."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        users = list_users()
        return jsonify({"users": users}), 200
    except Exception as e:
        logger.exception("Failed to list users")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/users/<email>", methods=["GET"])
def admin_get_user(email: str):
    """Get details for a specific user."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        user = get_user_details(email)
        if user is None:
            return jsonify({"error": "user not found"}), 404
        return jsonify(user), 200
    except Exception as e:
        logger.exception("Failed to get user details")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/users/<email>", methods=["DELETE"])
def admin_delete_user(email: str):
    """Delete a user."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        deleted = delete_user(email)
        if deleted:
            return jsonify({"status": "deleted", "email": email}), 200
        return jsonify({"error": "user not found or deletion failed"}), 404
    except Exception as e:
        logger.exception("Failed to delete user")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Course Management
# =============================================================================

@admin_bp.route("/courses", methods=["GET"])
def admin_list_courses():
    """List all course directories."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        courses = list_courses()
        return jsonify({"courses": courses}), 200
    except Exception as e:
        logger.exception("Failed to list courses")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/courses/<course_name>", methods=["GET"])
def admin_get_course(course_name: str):
    """Get files in a course directory."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        files = get_course_files(course_name)
        return jsonify({"course": course_name, "files": files}), 200
    except Exception as e:
        logger.exception("Failed to get course files")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/courses/<course_name>/tree", methods=["GET"])
def admin_get_course_tree(course_name: str):
    """Get directory tree for a course."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    try:
        tree = list_courses(course_name)
        return jsonify({"course": course_name, "tree": tree}), 200
    except Exception as e:
        logger.exception("Failed to get course tree")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/courses/<course_name>/upload", methods=["POST"])
def admin_upload_course_file(course_name: str):
    """Upload a file to a course directory."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400
    
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400
    
    subpath = request.form.get("subpath", "")
    
    try:
        result = upload_course_file(course_name, file, subpath)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to upload course file")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/courses/<course_name>/delete", methods=["POST"])
def admin_delete_course_file(course_name: str):
    """Delete a file from a course directory."""
    is_auth, error = _verify_admin_auth()
    if not is_auth:
        return error
    
    payload = request.get_json(force=True, silent=True) or {}
    filepath = payload.get("path")
    
    if not filepath:
        return jsonify({"error": "missing path"}), 400
    
    try:
        deleted = delete_course_file(course_name, filepath)
        if deleted:
            return jsonify({"status": "deleted", "path": filepath}), 200
        return jsonify({"error": "file not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to delete course file")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Admin Verification
# =============================================================================

@admin_bp.route("/verify", methods=["POST"])
def admin_verify():
    """
    Verify admin access.
    
    Expects:
        - Authorization header with Bearer token
        - JSON body with 'password' field containing admin password
    
    Returns:
        200 if both user token and admin password are valid
        401 if authentication fails
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "missing Authorization header"}), 401
        
        payload = request.get_json(force=True, silent=True) or {}
        admin_password = payload.get("password")
        
        if not admin_password:
            return jsonify({"error": "missing admin password"}), 400
        
        # Verify both user token and admin password
        is_valid, claims = verify_user_and_admin(auth_header, admin_password)
        
        if not is_valid:
            return jsonify({"error": "invalid credentials"}), 401
        
        return jsonify({
            "status": "verified",
            "user_id": claims.get("sub") if claims else None
        }), 200
        
    except Exception as e:
        logger.exception("Failed to verify admin access")
        return jsonify({"error": str(e)}), 500
