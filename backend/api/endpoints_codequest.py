"""
CodeQuest API endpoints for TAI Tutor AI.

Blueprint for CodeQuest routes:
- GET /codequest/tracks - List available tracks
- GET /codequest/challenges - List challenges for a track
- POST /codequest/sessions - Create a new session
- GET /codequest/sessions - List user's sessions
- GET /codequest/sessions/<session_id> - Get session details
- POST /codequest/sessions/<session_id>/submit - Submit a solution
- POST /codequest/sessions/<session_id>/finish - Finish session
- POST /codequest/sessions/<session_id>/exit - Exit session
- POST /codequest/sessions/<session_id>/navigate - Navigate session
- POST /codequest/sessions/<session_id>/draft - Save draft code
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
    from modules.codequest import get_codequest_manager
except ImportError:
    from config import AUTH_DISABLED
    from auth import (
        extract_bearer_token,
        verify_jwt,
        get_user_from_request,
    )
    from modules.codequest import get_codequest_manager

logger = logging.getLogger("backend.api.endpoints_codequest")

codequest_bp = Blueprint("codequest", __name__, url_prefix="/codequest")


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
        if not user_id:
            user_info = get_user_from_request(request)
            user_id = user_info.get("user_id") or user_info.get("default_dev_user")
        return user_id, None


@codequest_bp.route("/tracks", methods=["GET"])
def list_tracks():
    """List available CodeQuest tracks (programming languages/frameworks)."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    try:
        tracks = get_codequest_manager().list_tracks()
        return jsonify({"tracks": tracks}), 200
    except Exception as e:
        logger.exception("Failed to list CodeQuest tracks")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/challenges", methods=["GET"])
def list_challenges():
    """List challenges for a given track."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    track = (request.args.get("track") or "").strip()
    if not track:
        return jsonify({"error": "missing 'track' query param"}), 400
    
    try:
        challenges = get_codequest_manager().list_challenges(track)
        return jsonify({"track": track, "challenges": challenges}), 200
    except Exception as e:
        logger.exception("Failed to list CodeQuest challenges")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions", methods=["POST"])
def create_session():
    """Start a new CodeQuest session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    payload = request.get_json(force=True, silent=True) or {}
    track = (payload.get("track") or "").strip()
    if not track:
        return jsonify({"error": "missing 'track'"}), 400
    
    try:
        session = get_codequest_manager().create_session(
            user_id=user_id,
            track=track,
            description=payload.get("description"),
            plan_reference=payload.get("plan_reference") or payload.get("plan_reference_path") or payload.get("planReference"),
            plan_text=payload.get("plan_text") or payload.get("planText"),
            difficulty=payload.get("difficulty"),
            concepts=payload.get("concepts") if isinstance(payload.get("concepts"), list) else None,
            num_challenges=int(payload.get("num_challenges")) if str(payload.get("num_challenges") or "").isdigit() else None,
            use_llm_generator=bool(payload.get("use_llm_generator")),
        )
        mgr = get_codequest_manager()
        current = mgr.get_current_challenge_public(session)
        challenges = mgr.get_challenges_public(session)
        return jsonify({
            "session": session,
            "current_challenge": current,
            "challenges": challenges
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to create CodeQuest session")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """List the user's previous CodeQuest sessions."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    try:
        mgr = get_codequest_manager()
        sessions = mgr.list_sessions(user_id)
        
        # Compute stats
        total = len(sessions)
        completed = sum(1 for s in sessions if s.get("status") == "completed")
        active = sum(1 for s in sessions if s.get("status") == "active")
        attempts = sum(int(s.get("attempt_count", 0) or 0) for s in sessions)
        question_stats = mgr.compute_user_question_stats(user_id)
        
        stats = {
            "total_sessions": total,
            "completed_sessions": completed,
            "active_sessions": active,
            "total_attempts": attempts,
            "completion_rate": (completed / total) if total else 0.0,
            "question_stats": question_stats,
        }
        return jsonify({"sessions": sessions, "stats": stats}), 200
    except Exception as e:
        logger.exception("Failed to list CodeQuest sessions")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Get a CodeQuest session (including current challenge)."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    try:
        mgr = get_codequest_manager()
        session = mgr.get_session(user_id, session_id)
        if not session:
            return jsonify({"error": "session not found"}), 404
        
        current = mgr.get_current_challenge_public(session)
        challenges = mgr.get_challenges_public(session)
        view_mode = bool(session.get("status") != "active")
        solutions = mgr.get_solution_map(user_id, session, include_all=view_mode)
        
        return jsonify({
            "session": session,
            "current_challenge": current,
            "challenges": challenges,
            "solutions": solutions,
            "view_mode": view_mode,
        }), 200
    except Exception as e:
        logger.exception("Failed to get CodeQuest session")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions/<session_id>/submit", methods=["POST"])
def submit_solution(session_id: str):
    """Submit a solution for the current challenge and receive feedback."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400

    payload = request.get_json(force=True, silent=True) or {}
    challenge_id = payload.get("challenge_id")
    code = payload.get("code")
    
    if not challenge_id or not isinstance(code, str):
        return jsonify({"error": "missing 'challenge_id' or 'code'"}), 400
    
    try:
        result = get_codequest_manager().submit_solution(
            user_id=user_id,
            session_id=session_id,
            challenge_id=challenge_id,
            code=code,
        )
        return jsonify(result), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to submit CodeQuest solution")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions/<session_id>/finish", methods=["POST"])
def finish_session(session_id: str):
    """Finish a CodeQuest session by submitting all remaining challenges."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    try:
        mgr = get_codequest_manager()
        stats = mgr.finish_session(user_id=user_id, session_id=session_id)
        session = mgr.get_session(user_id, session_id)
        current = mgr.get_current_challenge_public(session) if session else None
        challenges = mgr.get_challenges_public(session) if session else []
        solutions = mgr.get_solution_map(user_id, session, include_all=True) if session else {}
        
        return jsonify({
            "stats": stats,
            "session": session,
            "current_challenge": current,
            "challenges": challenges,
            "solutions": solutions,
            "view_mode": True,
        }), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to finish CodeQuest session")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions/<session_id>/exit", methods=["POST"])
def exit_session(session_id: str):
    """Exit a CodeQuest session and mark it completed/incomplete."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400
    
    try:
        mgr = get_codequest_manager()
        session = mgr.exit_session(user_id=user_id, session_id=session_id)
        session = mgr.get_session(user_id, session_id) or session
        current = mgr.get_current_challenge_public(session) if session else None
        challenges = mgr.get_challenges_public(session) if session else []
        view_mode = bool(session.get("status") != "active") if session else True
        solutions = mgr.get_solution_map(user_id, session, include_all=True) if session else {}
        
        return jsonify({
            "session": session,
            "current_challenge": current,
            "challenges": challenges,
            "solutions": solutions,
            "view_mode": view_mode,
        }), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to exit CodeQuest session")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions/<session_id>/navigate", methods=["POST"])
def navigate_session(session_id: str):
    """Navigate within a CodeQuest session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400

    payload = request.get_json(force=True, silent=True) or {}
    index = payload.get("index")
    direction = payload.get("direction")
    challenge_id = payload.get("challenge_id")
    
    try:
        idx = int(index) if isinstance(index, int) or (isinstance(index, str) and index.isdigit()) else None
        mgr = get_codequest_manager()
        session = mgr.navigate_session(
            user_id=user_id,
            session_id=session_id,
            index=idx,
            direction=direction,
            challenge_id=challenge_id,
        )
        current = mgr.get_current_challenge_public(session)
        challenges = mgr.get_challenges_public(session)
        return jsonify({
            "session": session,
            "current_challenge": current,
            "challenges": challenges
        }), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to navigate CodeQuest session")
        return jsonify({"error": str(e)}), 500


@codequest_bp.route("/sessions/<session_id>/draft", methods=["POST"])
def save_draft(session_id: str):
    """Persist a per-challenge code draft for a session."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    if not user_id:
        return jsonify({"error": "could not determine user_id"}), 400

    payload = request.get_json(force=True, silent=True) or {}
    challenge_id = payload.get("challenge_id")
    code = payload.get("code")
    
    if not challenge_id or not isinstance(code, str):
        return jsonify({"error": "missing 'challenge_id' or 'code'"}), 400
    
    try:
        out = get_codequest_manager().save_draft(
            user_id=user_id,
            session_id=session_id,
            challenge_id=str(challenge_id),
            code=code,
        )
        return jsonify(out), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Failed to save CodeQuest draft")
        return jsonify({"error": str(e)}), 500
