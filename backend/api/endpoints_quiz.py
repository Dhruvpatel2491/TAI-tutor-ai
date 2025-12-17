"""
Quiz API endpoints for TAI Tutor AI.

Blueprint for quiz-related routes:
- POST /quiz/generate - Generate a new quiz
- GET /quiz/list - List all quizzes
- GET /quiz/<quiz_id> - Get a specific quiz
- POST /quiz/<quiz_id>/answer - Submit an answer
- POST /quiz/<quiz_id>/complete - Mark quiz as completed
- DELETE /quiz/<quiz_id> - Delete a quiz
"""

import logging
from flask import Blueprint, request, jsonify

# Import with fallback for running as script
try:
    from config import AUTH_DISABLED
    from auth import extract_bearer_token, verify_jwt
    from modules.quiz import (
        generate_quiz,
        list_quizzes,
        load_quiz,
        submit_quiz_answer,
        complete_quiz,
        delete_quiz,
    )
except ImportError:
    from config import AUTH_DISABLED
    from auth import extract_bearer_token, verify_jwt
    from modules.quiz import (
        generate_quiz,
        list_quizzes,
        load_quiz,
        submit_quiz_answer,
        complete_quiz,
        delete_quiz,
    )

logger = logging.getLogger("backend.api.endpoints_quiz")

quiz_bp = Blueprint("quiz", __name__, url_prefix="/quiz")


def _get_user_id_from_request():
    """Extract user_id from request auth token."""
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
        return user_id, None


def _serialize_quiz(quiz):
    """Convert quiz object to JSON-serializable dict."""
    result = quiz.model_dump()
    if result.get("date_taken"):
        result["date_taken"] = (
            result["date_taken"].isoformat()
            if hasattr(result["date_taken"], "isoformat")
            else str(result["date_taken"])
        )
    if result.get("date_completed"):
        result["date_completed"] = (
            result["date_completed"].isoformat()
            if hasattr(result["date_completed"], "isoformat")
            else str(result["date_completed"])
        )
    return result


@quiz_bp.route("/generate", methods=["POST"])
def quiz_generate():
    """Generate a new quiz based on topic."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400
    
    payload = request.get_json(force=True, silent=True) or {}
    topic = payload.get("topic")
    if not topic:
        return jsonify({"error": "missing 'topic' in request body"}), 400
    
    try:
        quiz = generate_quiz(
            user_id=user_id,
            topic=topic,
            plan_text=payload.get("plan_text"),
            plan_reference=payload.get("plan_reference"),
            num_questions=int(payload.get("num_questions", 5)),
            question_types=payload.get("question_types"),
            difficulty=payload.get("difficulty", "medium"),
            model=payload.get("model"),
            temperature=float(payload.get("temperature", 0.3)),
            max_tokens=int(payload.get("max_tokens", 2048))
        )
        return jsonify(_serialize_quiz(quiz)), 201
    except Exception as e:
        logger.exception("Quiz generation failed")
        return jsonify({"error": str(e)}), 500


@quiz_bp.route("/list", methods=["GET"])
def quiz_list():
    """List all quizzes for the authenticated user."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "missing user_id query parameter"}), 400
    
    try:
        quizzes = list_quizzes(user_id)
        result = [_serialize_quiz(q) for q in quizzes]
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Failed to list quizzes")
        return jsonify({"error": str(e)}), 500


@quiz_bp.route("/<quiz_id>", methods=["GET"])
def quiz_get(quiz_id: str):
    """Get a specific quiz by ID."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "missing user_id query parameter"}), 400
    
    try:
        quiz = load_quiz(user_id, quiz_id)
        if not quiz:
            return jsonify({"error": "quiz not found"}), 404
        return jsonify(_serialize_quiz(quiz)), 200
    except Exception as e:
        logger.exception("Failed to get quiz")
        return jsonify({"error": str(e)}), 500


@quiz_bp.route("/<quiz_id>/answer", methods=["POST"])
def quiz_answer(quiz_id: str):
    """Submit an answer for a quiz question."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400
    
    payload = request.get_json(force=True, silent=True) or {}
    question_id = payload.get("question_id")
    user_answer = payload.get("user_answer")
    
    if not question_id or user_answer is None:
        return jsonify({"error": "missing question_id or user_answer"}), 400
    
    try:
        result = submit_quiz_answer(
            user_id=user_id,
            quiz_id=quiz_id,
            question_id=question_id,
            user_answer=user_answer,
            time_taken_seconds=payload.get("time_taken_seconds")
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to submit quiz answer")
        return jsonify({"error": str(e)}), 500


@quiz_bp.route("/<quiz_id>/complete", methods=["POST"])
def quiz_complete(quiz_id: str):
    """Mark a quiz as completed."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "missing user_id"}), 400
    
    try:
        quiz = complete_quiz(user_id, quiz_id)
        return jsonify(_serialize_quiz(quiz)), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception("Failed to complete quiz")
        return jsonify({"error": str(e)}), 500


@quiz_bp.route("/<quiz_id>", methods=["DELETE"])
def quiz_delete(quiz_id: str):
    """Delete a quiz by ID."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "missing user_id query parameter"}), 400
    
    try:
        deleted = delete_quiz(user_id, quiz_id)
        if deleted:
            return jsonify({"status": "deleted", "quiz_id": quiz_id}), 200
        else:
            return jsonify({"error": "quiz not found"}), 404
    except Exception as e:
        logger.exception("Failed to delete quiz")
        return jsonify({"error": str(e)}), 500
