"""
User Management API Endpoints.

This module provides endpoints for:
- User registration
- User login
- User profile/stats retrieval
- Authentication status
"""

import os
import json
import logging
from pathlib import Path

from flask import Blueprint, request, jsonify

# Import with fallback for running as script
try:
    from config import MAIN_PROJECT_DIR, is_auth_disabled
    from auth import (
        register_user,
        verify_user,
        create_jwt_for_user,
        verify_jwt,
        extract_bearer_token,
        get_user_profile,
        get_user_from_request,
    )
    from modules.chat import get_chat_manager
except ImportError:
    from config import MAIN_PROJECT_DIR, is_auth_disabled
    from auth import (
        register_user,
        verify_user,
        create_jwt_for_user,
        verify_jwt,
        extract_bearer_token,
        get_user_profile,
        get_user_from_request,
    )
    from modules.chat import get_chat_manager

logger = logging.getLogger("backend.api.users")

users_bp = Blueprint("users", __name__)


def _get_user_id_from_request():
    """Extract user_id from request auth token or return None if auth is disabled."""
    if not is_auth_disabled():
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        if not token:
            return None, (jsonify({"error": "missing Authorization Bearer token"}), 401)
        claims = verify_jwt(token)
        if not claims:
            return None, (jsonify({"error": "invalid or expired token"}), 401)
        return claims.get("sub"), None
    else:
        payload = request.get_json(force=True, silent=True) or {}
        user_id = payload.get("user_id") or request.args.get("user_id")
        if not user_id:
            user_info = get_user_from_request(request)
            user_id = user_info.get("user_id") or user_info.get("default_dev_user")
        return user_id, None


# --------------------------------------------------------------------------
# Registration Endpoint
# --------------------------------------------------------------------------

@users_bp.route("/auth/register", methods=["POST"])
def auth_register():
    """
    Register a new user.
    
    POST /auth/register
    JSON body: {
        "email": "user@example.com",
        "password": "secret",
        "name": "User Name"
    }
    """
    payload = request.get_json(force=True, silent=True) or {}
    email = payload.get("email") or payload.get("user_id")
    password = payload.get("password")
    name = payload.get("name", "N/A")
    
    if not email:
        return jsonify({"error": "missing email or user_id"}), 400
    
    if not password:
        # Dev/test flow: return a token without creating a persisted account
        token = create_jwt_for_user(email)
        return jsonify({"token": token}), 200
    
    try:
        register_user(email, password, name)
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        logger.exception("Failed to register user")
        return jsonify({"error": str(e)}), 500

    token = create_jwt_for_user(email)
    return jsonify({"token": token}), 201


# --------------------------------------------------------------------------
# Login Endpoint
# --------------------------------------------------------------------------

@users_bp.route("/auth/login", methods=["POST"])
def auth_login():
    """
    Authenticate a user and return a JWT.
    
    POST /auth/login
    JSON body: {
        "email": "user@example.com",
        "password": "secret"
    }
    """
    payload = request.get_json(force=True, silent=True) or {}
    email = payload.get("email") or payload.get("user_id")
    password = payload.get("password")
    
    if not email or not password:
        return jsonify({"error": "missing email or password"}), 400
    
    ok = verify_user(email, password)
    if not ok:
        return jsonify({"error": "invalid credentials"}), 401
    
    token = create_jwt_for_user(email)
    return jsonify({"token": token}), 200


# --------------------------------------------------------------------------
# User Stats Endpoint
# --------------------------------------------------------------------------

@users_bp.route("/auth/user/stats", methods=["GET"])
def get_user_stats():
    """
    Get user statistics including chats, plans, quizzes, and CodeQuest scores.
    
    GET /auth/user/stats
    Headers: Authorization: Bearer <token>
    """
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    
    try:
        # Get user profile
        user_profile = get_user_profile(user_id)
        name = user_profile.get("name", "N/A") if user_profile else "N/A"
        
        # Count chats
        chat_mgr = get_chat_manager()
        chats_count = len(chat_mgr.list_chats(user_id))
        
        # Count plans
        plans_count = 0
        base_user_saved_plans = Path(MAIN_PROJECT_DIR) / "user_data" / "saved_plans" / str(user_id)
        if base_user_saved_plans.exists() and base_user_saved_plans.is_dir():
            for p in base_user_saved_plans.iterdir():
                if p.is_file() and p.suffix == ".json":
                    plans_count += 1

        # Calculate quiz score
        quiz_score = 0
        quiz_dir = Path(MAIN_PROJECT_DIR) / "user_data" / "quiz" / user_id
        if quiz_dir.exists():
            overall_score = 0
            quiz_count = 0
            for quiz_file in quiz_dir.glob("*.json"):
                try:
                    with open(quiz_file, 'r') as f:
                        quiz_data = json.load(f)
                        overall_score += quiz_data.get("score", 0)
                        quiz_count += 1
                except Exception:
                    logger.debug(f"Error reading quiz file {quiz_file}")
            quiz_score = round(overall_score / quiz_count, 1) if quiz_count > 0 else 0

        # Calculate CodeQuest score
        codequest_score = 0
        total_que = 0
        sessions_dir = (
            Path(MAIN_PROJECT_DIR) / "user_data" / "codequest" / "sessions" 
            / str(user_id).replace("@", "__at__").replace(".", "__dot__")
        )
        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    if session_data.get("status") is not None:
                        results = session_data.get("results") or {}
                        if isinstance(results, dict):
                            for r in results.values():
                                try:
                                    if bool(r.get("passed")):
                                        codequest_score += 1
                                    total_que += 1
                                except Exception:
                                    continue
                except Exception:
                    logger.debug(f"Error reading session file {session_file}")
            
            codequest_score = round(codequest_score / total_que * 100, 1) if total_que > 0 else 0

        return jsonify({
            "name": name,
            "email": user_id,
            "chats_count": chats_count,
            "plans_count": plans_count,
            "quiz_score": quiz_score,
            "codequest_score": codequest_score
        }), 200
        
    except Exception as e:
        logger.exception("Failed to get user stats")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------
# Auth Status Endpoint
# --------------------------------------------------------------------------

@users_bp.route("/auth/status", methods=["GET"])
def auth_status():
    """
    Return whether auth is disabled (for frontend to adapt UX).
    
    Response: {"auth_disabled": bool, "default_dev_user": str or null}
    """
    try:
        disabled = is_auth_disabled()
        default_user = os.environ.get("DEFAULT_DEV_USER")
        return jsonify({"auth_disabled": disabled, "default_dev_user": default_user}), 200
    except Exception:
        return jsonify({"auth_disabled": False, "default_dev_user": None}), 200


@users_bp.route("/auth/user", methods=["GET"])
def auth_user():
    """
    Return information about the current user.
    
    When auth is enabled, requires Authorization: Bearer <token>.
    When auth is disabled, returns user_id from query param or default dev user.
    """
    try:
        disabled = is_auth_disabled()
        default_user = os.environ.get("DEFAULT_DEV_USER")
        
        if not disabled:
            auth_header = request.headers.get("Authorization")
            token = extract_bearer_token(auth_header)
            if not token:
                return jsonify({"error": "missing Authorization Bearer token"}), 401
            claims = verify_jwt(token)
            if not claims:
                return jsonify({"error": "invalid or expired token"}), 401
            return jsonify({
                "auth_disabled": False,
                "user_id": claims.get("sub"),
                "claims": claims
            }), 200
        
        user_id = request.args.get("user_id") or default_user or "dev"
        return jsonify({
            "auth_disabled": True,
            "user_id": user_id,
            "default_dev_user": default_user
        }), 200
        
    except Exception:
        logger.exception("Failed to determine auth user")
        return jsonify({"error": "internal server error"}), 500
