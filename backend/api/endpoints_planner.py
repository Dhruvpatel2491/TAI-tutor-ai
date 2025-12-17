"""
Planner API endpoints for TAI Tutor AI.

Blueprint for learning plan routes:
- POST /plans - Create a new learning plan
- GET /plans - List plans for user
- GET /plans/<plan_id> - Get a specific plan
- POST /saved_plans - Save a plan to disk
- GET /saved_plans - List saved plans
- POST /saved_plans/update - Update a saved plan
- POST /saved_plans/delete - Delete a saved plan
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

# Import with fallback for running as script
try:
    from config import AUTH_DISABLED, MAIN_PROJECT_DIR
    from auth import extract_bearer_token, verify_jwt
    from modules.planner import default_planner, generate_plan
except ImportError:
    from config import AUTH_DISABLED, MAIN_PROJECT_DIR
    from auth import extract_bearer_token, verify_jwt
    from modules.planner import default_planner, generate_plan

logger = logging.getLogger("backend.api.endpoints_planner")

planner_bp = Blueprint("planner", __name__)


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


@planner_bp.route("/plans", methods=["POST"])
def create_plan():
    """Create a new learning plan."""
    user_id, error_response = _get_user_id_from_request()
    if error_response:
        return error_response
    
    payload = request.get_json(force=True, silent=True) or {}
    requirement = payload.get("requirement") or payload.get("requirements") or ""
    
    if not user_id or not isinstance(requirement, str):
        return jsonify({"error": "invalid payload, require 'requirement' string"}), 400

    use_mock = bool(payload.get("mock") or payload.get("use_mock") or os.environ.get("MOCK_LLM_ECHO"))

    plan_text = ""
    if not use_mock:
        try:
            edit_plan_id = payload.get("edit_plan_id")
            edit_instructions = payload.get("edit_instructions")
            original_plan = payload.get("original_plan_text")
            
            if not original_plan and edit_plan_id:
                prev = default_planner.get_plan(edit_plan_id)
                if prev:
                    original_plan = getattr(prev, "plan_text", None)

            plan_text = generate_plan(
                user_id=user_id,
                requirement=requirement,
                original_plan=original_plan,
                edit_instructions=edit_instructions,
                model=payload.get("plan_model"),
                temperature=float(payload.get("plan_temperature", 0.15)),
                max_tokens=int(payload.get("plan_max_tokens", 1024))
            )
        except Exception:
            logger.exception("Plan generation failed; storing empty plan_text")

    created = default_planner.create_plan(user_id=user_id, plan_text=plan_text)
    try:
        out = created.model_dump()
    except Exception:
        out = getattr(created, "__dict__", {})
    return jsonify(out), 201


@planner_bp.route("/plans", methods=["GET"])
def list_plans():
    """List all plans for user."""
    if not AUTH_DISABLED:
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        if not token:
            return jsonify({"error": "missing Authorization Bearer token"}), 401
        claims = verify_jwt(token)
        if not claims:
            return jsonify({"error": "invalid or expired token"}), 401
        user_id = claims.get("sub")
        q_user = request.args.get("user_id")
        if q_user and q_user != user_id:
            return jsonify({"error": "forbidden: query user_id does not match token subject"}), 403
    else:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "missing user_id query parameter"}), 400

    plans = default_planner.list_plans_for_user(user_id)
    out = []
    for p in plans:
        try:
            out.append(p.model_dump())
        except Exception:
            out.append(getattr(p, "__dict__", {}))
    return jsonify(out), 200


@planner_bp.route("/plans/<plan_id>", methods=["GET"])
def get_plan(plan_id: str):
    """Get a specific plan by ID."""
    p = default_planner.get_plan(plan_id)
    if not p:
        return jsonify({"error": "not found"}), 404
    
    if not AUTH_DISABLED:
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        if not token:
            return jsonify({"error": "missing Authorization Bearer token"}), 401
        claims = verify_jwt(token)
        if not claims:
            return jsonify({"error": "invalid or expired token"}), 401
        user_id = claims.get("sub")
        if p.user_id != user_id:
            return jsonify({"error": "forbidden"}), 403

    try:
        payload = p.model_dump()
    except Exception:
        payload = getattr(p, "__dict__", {})
    return jsonify(payload), 200


@planner_bp.route("/saved_plans", methods=["POST"])
def save_plan():
    """Persist a generated plan to the filesystem."""
    payload = request.get_json(force=True, silent=True) or {}
    plan_name = payload.get("plan_name")
    plan_text = payload.get("plan_text") or ""
    
    if not plan_name:
        return jsonify({"error": "missing plan_name"}), 400

    if not AUTH_DISABLED:
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        if not token:
            return jsonify({"error": "missing Authorization Bearer token"}), 401
        claims = verify_jwt(token)
        if not claims:
            return jsonify({"error": "invalid or expired token"}), 401
        user_id = claims.get("sub")
    else:
        user_id = payload.get("user_id")
        if not user_id:
            return jsonify({"error": "missing user_id"}), 400

    try:
        save_dir = Path(MAIN_PROJECT_DIR) / "user_data" / "saved_plans" / str(user_id)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{str(plan_name)}.json"
        created_at = datetime.now(timezone.utc).isoformat()
        data = {"name": plan_name, "user_id": user_id, "plan_text": plan_text, "created_at": created_at}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return jsonify({"status": "saved", "path": str(file_path)}), 201
    except Exception as e:
        logger.exception("Failed to save plan to disk")
        return jsonify({"error": str(e)}), 500


@planner_bp.route("/saved_plans", methods=["GET"])
def list_saved_plans():
    """List saved plans for a user."""
    if not AUTH_DISABLED:
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        if not token:
            return jsonify({"error": "missing Authorization Bearer token"}), 401
        claims = verify_jwt(token)
        if not claims:
            return jsonify({"error": "invalid or expired token"}), 401
        user_id = claims.get("sub")
    else:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "missing user_id query parameter"}), 400

    results = []
    try:
        base_user_saved_plans = Path(MAIN_PROJECT_DIR) / "user_data" / "saved_plans"
        exact = base_user_saved_plans / str(user_id)
        
        if exact.exists() and exact.is_dir():
            for p in sorted(exact.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(p, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                except Exception:
                    data = {}
                
                stat = p.stat()
                created = data.get('created_at') if isinstance(data, dict) else None
                if not created:
                    created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                
                name = data.get('name') if isinstance(data, dict) else p.stem
                plan_text = data.get('plan_text') if isinstance(data, dict) else ""
                owner_id = data.get('user_id') if isinstance(data, dict) else ""
                
                results.append({
                    'name': name,
                    'owner': owner_id,
                    'path': str(p.resolve()),
                    'created_at': created,
                    'plan_text': plan_text
                })
    except Exception as e:
        logger.exception('Failed to list saved plans')
        return jsonify({"error": str(e)}), 500

    return jsonify(results), 200


@planner_bp.route("/saved_plans/update", methods=["POST"])
def update_saved_plan():
    """Regenerate and update an existing saved plan file."""
    payload = request.get_json(force=True, silent=True) or {}
    file_path = payload.get("path")
    plan_name = payload.get("plan_name")
    new_requirement = payload.get("new_requirement") or payload.get("requirement") or ""
    original_text = payload.get("original_plan_text")
    edit_instructions = payload.get("edit_instructions")

    if not AUTH_DISABLED:
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        if not token:
            return jsonify({"error": "missing Authorization Bearer token"}), 401
        claims = verify_jwt(token)
        if not claims:
            return jsonify({"error": "invalid or expired token"}), 401
        user_id = claims.get("sub")
    else:
        user_id = payload.get("user_id")
        if not user_id:
            return jsonify({"error": "missing user_id"}), 400

    if not file_path:
        if not plan_name:
            return jsonify({"error": "missing path or plan_name"}), 400
        save_dir = Path(MAIN_PROJECT_DIR) / "user_data" / "saved_plans" / str(user_id)
        candidate = save_dir / f"{plan_name}.json"
        if not candidate.exists():
            return jsonify({"error": f"plan file not found: {candidate}"}), 404
        file_path = str(candidate)

    try:
        p = Path(file_path)
        if not p.exists():
            return jsonify({"error": "file not found"}), 404
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        logger.exception("Failed to read saved plan file")
        return jsonify({"error": str(e)}), 500

    if not original_text:
        original_text = data.get("plan_text") if isinstance(data, dict) else None

    if not new_requirement:
        return jsonify({"error": "missing new_requirement"}), 400

    try:
        new_plan_text = generate_plan(
            user_id=user_id,
            requirement=new_requirement,
            original_plan=original_text,
            edit_instructions=edit_instructions,
            model=payload.get("plan_model"),
            temperature=float(payload.get("plan_temperature", 0.15)),
            max_tokens=int(payload.get("plan_max_tokens", 1024))
        )
    except Exception:
        logger.exception("Plan regeneration failed")
        return jsonify({"error": "regeneration failed"}), 500

    try:
        if isinstance(data, dict):
            data["plan_text"] = new_plan_text
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            data = {
                "name": plan_name or p.stem,
                "user_id": user_id,
                "plan_text": new_plan_text,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        with p.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except Exception as e:
        logger.exception("Failed to write updated plan file")
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "updated", "path": str(p), "plan_text": new_plan_text}), 200


@planner_bp.route("/saved_plans/delete", methods=["POST"])
def delete_saved_plan():
    """Delete a saved plan file."""
    payload = request.get_json(force=True, silent=True) or {}
    file_path = payload.get("path")
    plan_name = payload.get("plan_name")

    if not AUTH_DISABLED:
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        if not token:
            return jsonify({"error": "missing Authorization Bearer token"}), 401
        claims = verify_jwt(token)
        if not claims:
            return jsonify({"error": "invalid or expired token"}), 401
        user_id = claims.get("sub")
    else:
        user_id = payload.get("user_id")
        if not user_id:
            return jsonify({"error": "missing user_id"}), 400

    if not file_path:
        if not plan_name:
            return jsonify({"error": "missing path or plan_name"}), 400
        save_dir = Path(MAIN_PROJECT_DIR) / "user_data" / "saved_plans" / str(user_id)
        candidate = save_dir / f"{plan_name}.json"
        if not candidate.exists():
            return jsonify({"error": f"plan file not found: {candidate}"}), 404
        file_path = str(candidate)

    try:
        p = Path(file_path)
        if not p.exists():
            return jsonify({"error": "file not found"}), 404
        p.unlink()
        return jsonify({"status": "deleted", "path": str(p)}), 200
    except Exception as e:
        logger.exception("Failed to delete saved plan file")
        return jsonify({"error": str(e)}), 500
