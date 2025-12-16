"""
Admin endpoints for TAI-tutor-ai.
Provides REST API for admin panel operations: user management, course management, system settings.
"""
import os
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

try:
    from backend.admin_auth import verify_admin_password
except ImportError:
    from admin_auth import verify_admin_password

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Paths
USER_DATA_DIR = Path(__file__).parent.parent / "user_data"
COURSE_DATA_DIR = Path(__file__).parent / "course-data"
LOGIN_REGISTER_DIR = USER_DATA_DIR / "login_register"
CHATS_DIR = USER_DATA_DIR / "chats"
ALLOWED_EXTENSIONS = {'zip', 'pdf', 'pptx', 'txt', 'md', 'py', 'ipynb'}


def _verify_admin_token(req):
    """Verify admin authentication from request."""
    auth_header = req.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False, jsonify({"error": "Missing or invalid authorization header"}), 401
    
    token = auth_header.split(' ', 1)[1]
    if not verify_admin_password(token):
        return False, jsonify({"error": "Invalid admin credentials"}), 403
    
    return True, None, None


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# AUTHENTICATION ENDPOINT
# ============================================================================

@admin_bp.route('/verify', methods=['POST'])
def verify_admin():
    """Verify admin password."""
    data = request.get_json()
    password = data.get('password', '')
    
    if verify_admin_password(password):
        return jsonify({"success": True, "token": password}), 200
    else:
        return jsonify({"success": False, "error": "Invalid password"}), 401


# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@admin_bp.route('/users', methods=['GET'])
def get_users():
    """Get list of all registered users."""
    is_valid, error_response, status_code = _verify_admin_token(request)
    if not is_valid:
        return error_response, status_code
    
    try:
        users = []
        if LOGIN_REGISTER_DIR.exists():
            for user_file in LOGIN_REGISTER_DIR.glob("*.json"):
                try:
                    with open(user_file, 'r') as f:
                        user_data = json.load(f)
                        # Count user chats
                        email = user_data.get('email', '')
                        chat_dir = CHATS_DIR / email.replace('@', '__at__').replace('.', '__dot__')
                        chat_count = len(list(chat_dir.glob("*.json"))) if chat_dir.exists() else 0
                        
                        users.append({
                            "email": user_data.get('email'),
                            "name": user_data.get('name'),
                            "created_at": user_data.get('created_at'),
                            "chat_count": chat_count
                        })
                except Exception as e:
                    print(f"Error reading user file {user_file}: {e}")
                    continue
        
        return jsonify({"users": users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/users/<email>', methods=['DELETE'])
def delete_user(email):
    """Delete a user and their associated data."""
    is_valid, error_response, status_code = _verify_admin_token(request)
    if not is_valid:
        return error_response, status_code
    
    try:
        # Sanitize email for file paths
        safe_email = email.replace('@', '__at__').replace('.', '__dot__')
        
        # Delete user registration file
        user_file = LOGIN_REGISTER_DIR / f"{safe_email}.json"
        if user_file.exists():
            user_file.unlink()
        
        # Delete user chats
        chat_dir = CHATS_DIR / safe_email
        if chat_dir.exists():
            shutil.rmtree(chat_dir)
        
        # Delete user quiz data
        quiz_dir = USER_DATA_DIR / "quiz" / email
        if quiz_dir.exists():
            shutil.rmtree(quiz_dir)
        
        # Delete user saved plans
        plans_dir = USER_DATA_DIR / "saved_plans" / email
        if plans_dir.exists():
            shutil.rmtree(plans_dir)
        
        return jsonify({"success": True, "message": f"User {email} deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# COURSE MANAGEMENT ENDPOINTS
# ============================================================================

@admin_bp.route('/courses', methods=['GET'])
def get_courses():
    """Get directory structure of course files."""
    is_valid, error_response, status_code = _verify_admin_token(request)
    if not is_valid:
        return error_response, status_code
    
    def build_tree(path):
        """Recursively build directory tree."""
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
                    tree["children"].append(build_tree(child))
            except PermissionError:
                pass
        
        return tree
    
    try:
        if not COURSE_DATA_DIR.exists():
            COURSE_DATA_DIR.mkdir(parents=True, exist_ok=True)
            return jsonify({"courses": [], "root": str(COURSE_DATA_DIR)}), 200
        
        courses = []
        for course_dir in COURSE_DATA_DIR.iterdir():
            if course_dir.is_dir():
                courses.append(build_tree(course_dir))
        
        return jsonify({"courses": courses, "root": str(COURSE_DATA_DIR)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/courses/upload', methods=['POST'])
def upload_course():
    """Upload course files (zip file) and extract to specified path."""
    is_valid, error_response, status_code = _verify_admin_token(request)
    if not is_valid:
        return error_response, status_code
    
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file part in request"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Get target path from form data
        target_path = request.form.get('path', '')
        if not target_path:
            return jsonify({"error": "Target path is required"}), 400
        
        # Secure the filename and path
        filename = secure_filename(file.filename)
        
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
            
            return jsonify({
                "success": True,
                "message": f"Zip file extracted to {target_path}",
                "path": str(target_dir.relative_to(COURSE_DATA_DIR))
            }), 200
        else:
            # For non-zip files, just save them
            file_path = target_dir / filename
            file.save(file_path)
            
            return jsonify({
                "success": True,
                "message": f"File uploaded to {target_path}",
                "path": str(file_path.relative_to(COURSE_DATA_DIR))
            }), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/courses/delete', methods=['POST'])
def delete_course():
    """Delete course files or directories."""
    is_valid, error_response, status_code = _verify_admin_token(request)
    if not is_valid:
        return error_response, status_code
    
    try:
        data = request.get_json()
        paths = data.get('paths', [])
        
        if not paths:
            return jsonify({"error": "No paths provided"}), 400
        
        deleted = []
        errors = []
        
        for path_str in paths:
            try:
                # Normalize path separators and resolve relative to COURSE_DATA_DIR
                # Don't use secure_filename on the whole path as it breaks directory structure
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
                else:
                    errors.append(f"Path not found: {path_str}")
            except Exception as e:
                errors.append(f"Error deleting {path_str}: {str(e)}")
        
        return jsonify({
            "success": True,
            "deleted": deleted,
            "errors": errors
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SYSTEM SETTINGS ENDPOINTS
# ============================================================================

@admin_bp.route('/health', methods=['GET'])
def admin_health():
    """Get system health check information."""
    is_valid, error_response, status_code = _verify_admin_token(request)
    if not is_valid:
        return error_response, status_code
    
    try:
        # Get system info
        info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "course_data_dir": str(COURSE_DATA_DIR),
            "user_data_dir": str(USER_DATA_DIR),
            "courses_count": len(list(COURSE_DATA_DIR.glob("*"))) if COURSE_DATA_DIR.exists() else 0,
            "users_count": len(list(LOGIN_REGISTER_DIR.glob("*.json"))) if LOGIN_REGISTER_DIR.exists() else 0
        }
        
        return jsonify(info), 200
    except Exception as e:
        return jsonify({"error": str(e), "status": "unhealthy"}), 500


@admin_bp.route('/rebuild', methods=['POST'])
def trigger_rebuild():
    """Trigger vector database rebuild by calling the existing rebuild endpoint."""
    is_valid, error_response, status_code = _verify_admin_token(request)
    if not is_valid:
        return error_response, status_code
    
    try:
        # Import the get_index function from server to trigger rebuild
        # The server.py already has a /rebuild endpoint that handles this
        try:
            from backend.server import get_index
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from server import get_index
        
        # Trigger rebuild in a background thread to avoid blocking
        import threading
        
        def _rebuild_task():
            try:
                get_index(force_rebuild=True)
            except Exception as e:
                print(f"Background rebuild failed: {e}")
        
        rebuild_thread = threading.Thread(target=_rebuild_task, daemon=True)
        rebuild_thread.start()
        
        return jsonify({
            "success": True,
            "message": "Vector database rebuild started in background. This may take several minutes."
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
