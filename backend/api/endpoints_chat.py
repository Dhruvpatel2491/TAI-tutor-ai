"""
Chat API endpoints for TAI Tutor AI.

Blueprint for chat-related routes:
- POST /chats - Create a new chat session
- GET /chats - List chat sessions
- GET /chats/<chat_id> - Get a specific chat
- POST /chats/<chat_id>/messages - Add a message
- DELETE /chats/<chat_id> - Delete a chat
- POST /chats/<chat_id>/archive - Archive/unarchive a chat
- PUT /chats/<chat_id>/title - Update chat title
"""

import logging
from flask import Blueprint, request, jsonify

# Import with fallback for running as script
try:
    from config import AUTH_DISABLED
    from auth import (
        extract_bearer_token,
        verify_jwt,
        get_user_from_request,
    )
    from modules.chat import get_chat_manager
except ImportError:
    from config import AUTH_DISABLED
    from auth import (
        extract_bearer_token,
        verify_jwt,
        get_user_from_request,
    )
    from modules.chat import get_chat_manager

logger = logging.getLogger("backend.api.endpoints_chat")

chat_bp = Blueprint("chat", __name__, url_prefix="/chats")


def _get_user_id_from_request():
    """Extract user_id from request auth token or return None if auth is disabled."""
    if not AUTH_DISABLED:
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


@chat_bp.route("", methods=["POST"])
def create_chat_session():
    """Create a new chat session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    payload = request.get_json(force=True, silent=True) or {}
    title = payload.get("title")
    
    try:
        session = get_chat_manager().create_chat(user_id=user_id, title=title)
        if session:
            return jsonify(session.to_dict()), 201
        return jsonify({"error": "failed to create chat"}), 500
    except Exception as e:
        logger.exception("Failed to create chat")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("", methods=["GET"])
def list_chats():
    """List all chat sessions for the current user."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    include_archived = request.args.get("include_archived", "false").lower() in ("true", "1", "yes")
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        offset = 0
    
    try:
        chats = get_chat_manager().list_chats(
            user_id=user_id,
            include_archived=include_archived,
            limit=limit,
            offset=offset
        )
        return jsonify({"chats": chats}), 200
    except Exception as e:
        logger.exception("Failed to list chats")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<chat_id>", methods=["GET"])
def get_chat_session(chat_id: str):
    """Get a specific chat session with all messages."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    try:
        session = get_chat_manager().get_chat(user_id, chat_id)
        if session:
            return jsonify(session.to_dict()), 200
        return jsonify({"error": "chat not found"}), 404
    except Exception as e:
        logger.exception("Failed to get chat")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<chat_id>/messages", methods=["POST"])
def add_chat_message(chat_id: str):
    """Add a message to an existing chat session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    payload = request.get_json(force=True, silent=True) or {}
    role = payload.get("role")
    content = payload.get("content")
    metadata = payload.get("metadata", {})
    
    if not role or not content:
        return jsonify({"error": "missing 'role' or 'content'"}), 400
    
    if role not in ("user", "assistant"):
        return jsonify({"error": "role must be 'user' or 'assistant'"}), 400
    
    try:
        message = get_chat_manager().add_message(
            user_id=user_id,
            chat_id=chat_id,
            role=role,
            content=content,
            metadata=metadata
        )
        if message:
            return jsonify(message.to_dict()), 201
        return jsonify({"error": "chat not found or failed to add message"}), 404
    except Exception as e:
        logger.exception("Failed to add message to chat")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<chat_id>", methods=["DELETE"])
def delete_chat_session(chat_id: str):
    """Delete a chat session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    try:
        deleted = get_chat_manager().delete_chat(user_id, chat_id)
        if deleted:
            return jsonify({"status": "deleted", "chat_id": chat_id}), 200
        return jsonify({"error": "chat not found"}), 404
    except Exception as e:
        logger.exception("Failed to delete chat")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<chat_id>/archive", methods=["POST"])
def archive_chat_session(chat_id: str):
    """Archive or unarchive a chat session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    payload = request.get_json(force=True, silent=True) or {}
    archive = payload.get("archive", True)
    
    try:
        success = get_chat_manager().archive_chat(user_id, chat_id, archive)
        if success:
            status = "archived" if archive else "unarchived"
            return jsonify({"status": status, "chat_id": chat_id}), 200
        return jsonify({"error": "chat not found"}), 404
    except Exception as e:
        logger.exception("Failed to archive chat")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/<chat_id>/title", methods=["PUT"])
def update_chat_session_title(chat_id: str):
    """Update the title of a chat session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    payload = request.get_json(force=True, silent=True) or {}
    title = payload.get("title")
    
    if not title:
        return jsonify({"error": "missing 'title'"}), 400
    
    try:
        success = get_chat_manager().update_chat_title(user_id, chat_id, title)
        if success:
            return jsonify({"status": "updated", "chat_id": chat_id, "title": title}), 200
        return jsonify({"error": "chat not found"}), 404
    except Exception as e:
        logger.exception("Failed to update chat title")
        return jsonify({"error": str(e)}), 500
