"""
TAI Tutor AI - Backend Server

Main Flask application entry point.
This file initializes the Flask app, configures CORS, registers blueprints,
and provides the core health, rebuild, and query endpoints.

All other endpoints are organized in their respective blueprint modules
under the `api/` directory.
"""

import os
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import configuration - with fallback for running as script
try:
    from config import (
        INDEX_DIR,
        DATA_DIR,
        BACKEND_PORT,
        OLLAMA_LLM,
        DEFAULT_TEMPERATURE,
        DEFAULT_MAX_TOKENS,
    )
except ImportError:
    pass
# Import RAG components - use new modular structure
try:
    from rag.index_manager import (
        get_index,
        get_index_status,
        trigger_async_rebuild,
        trigger_sync_rebuild,
    )
    from rag.retrieval_chat import (
        get_cache,
        validate_style,
        validate_response_type,
        validate_length,
        should_use_mock,
        MockResponse,
        MockResponseV2,
        MockResponseV3,
    )
except ImportError:
    pass

# Import prompts
try:
    from prompts.chat_prompts import ChatPrompter
except ImportError:
    pass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.api")

# Initialize Flask app
app = Flask(__name__)
CORS(app)


# --------------------------------------------------------------------------
# Global Cache Instance
# --------------------------------------------------------------------------

_response_cache = get_cache()


# --------------------------------------------------------------------------
# Blueprint Registration
# --------------------------------------------------------------------------

# Admin blueprints
try:
    from admin.endpoints_admin import admin_bp
    from admin.endpoints_auth import auth_bp as admin_auth_bp
except ImportError:
    from admin.endpoints_admin import admin_bp
    from admin.endpoints_auth import auth_bp as admin_auth_bp

# API blueprints
try:
    from api.endpoints_users import users_bp
    from api.endpoints_chat import chat_bp
    from api.endpoints_planner import planner_bp
    from api.endpoints_quiz import quiz_bp
    from api.endpoints_codequest import codequest_bp
except ImportError:
    from api.endpoints_users import users_bp
    from api.endpoints_chat import chat_bp
    from api.endpoints_planner import planner_bp
    from api.endpoints_quiz import quiz_bp
    from api.endpoints_codequest import codequest_bp

# Register all blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(planner_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(codequest_bp)


# --------------------------------------------------------------------------
# Health Endpoint
# --------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """
    Health endpoint with lightweight check for index/embeddings presence.
    
    Uses index_manager for status checks and triggering async rebuilds.
    """
    try:
        # Get index status from index_manager
        status = get_index_status()
        
        if status["needs_rebuild"]:
            logger.info(f"Health check: rebuild needed (reasons={status['reasons']})")
            
            # Trigger async rebuild through index_manager
            rebuild_status = trigger_async_rebuild()
            
            return jsonify({
                "status": rebuild_status,
                "index_exists": status["index_exists"],
                "meta_entries": status["meta_entries"],
                "current_files": status["current_files"],
                "missing_meta_files": status["missing_meta_files"],
                "new_files": status["new_files"],
                "reasons": status["reasons"],
            }), 200

        return jsonify({
            "status": "ok",
            "index_exists": status["index_exists"],
            "meta_entries": status["meta_entries"],
            "current_files": status["current_files"],
        }), 200
        
    except Exception as e:
        logger.exception("Health check failed")
        return jsonify({"status": "error", "error": str(e)}), 500


# --------------------------------------------------------------------------
# Query Endpoints
# --------------------------------------------------------------------------

@app.route("/query", methods=["POST"])
def query():
    """
    POST /query
    Basic query endpoint using the vector index.
    """
    payload = request.get_json(force=True, silent=True) or {}
    question = payload.get("question") or payload.get("q") or ""
    if not question:
        return jsonify({"error": "missing 'question' in body"}), 400

    rebuild = bool(payload.get("rebuild", False))
    indexing = payload.get("indexing") or {}
    retrieval = payload.get("retrieval") or {}

    try:
        from llama_index.core.settings import Settings
        
        index_obj, qe = get_index(force_rebuild=rebuild, build_kwargs=(indexing if rebuild else None))
        if index_obj is None:
            return jsonify({"error": "index not available"}), 500

        qe_to_use = qe
        if retrieval:
            try:
                qe_to_use = index_obj.as_query_engine(llm=Settings.llm, **retrieval)
            except Exception:
                logger.warning("Could not create per-request query engine; using default")

        use_mock = should_use_mock(payload)
        if use_mock:
            response = MockResponse(question)
        else:
            response = qe_to_use.query(question)

        return jsonify({"answer": str(response)}), 200
        
    except Exception as e:
        logger.exception("Query failed")
        return jsonify({"error": str(e)}), 500


@app.route("/query_v2", methods=["POST"])
def query_v2():
    """
    POST /query_v2
    Query endpoint with model selection support.
    """
    payload = request.get_json(force=True, silent=True) or {}
    question = payload.get("question") or payload.get("q") or ""
    if not question:
        return jsonify({"error": "missing 'question' in body"}), 400

    requested_model = payload.get("model") or OLLAMA_LLM
    temp = float(payload.get("temperature", DEFAULT_TEMPERATURE))
    max_toks = int(payload.get("max_tokens", DEFAULT_MAX_TOKENS))
    rebuild = bool(payload.get("rebuild", False))
    indexing = payload.get("indexing") or {}
    retrieval = payload.get("retrieval") or {}

    try:
        from llama_index.llms.ollama import Ollama
        
        index_obj, _ = get_index(force_rebuild=rebuild, build_kwargs=(indexing if rebuild else None))
        if index_obj is None:
            return jsonify({"error": "index not available"}), 500

        per_request_llm = Ollama(model=requested_model, temperature=temp, max_tokens=max_toks, request_timeout=300)
        
        try:
            query_engine = index_obj.as_query_engine(llm=per_request_llm, **retrieval) if retrieval else index_obj.as_query_engine(llm=per_request_llm)
        except TypeError:
            query_engine = index_obj.as_query_engine(llm=per_request_llm)

        use_mock = should_use_mock(payload)
        if use_mock:
            response = MockResponseV2(question)
        else:
            response = query_engine.query(question)

        return jsonify({"answer": str(response)}), 200

    except Exception as e:
        logger.exception("Query v2 failed")
        return jsonify({"error": str(e)}), 500


@app.route("/query_v3", methods=["POST"])
def query_v3():
    """
    POST /query_v3
    Enhanced query with prompt customization, history, and caching.
    """
    payload = request.get_json(force=True, silent=True) or {}
    question = payload.get("question") or payload.get("q") or ""
    if not question:
        return jsonify({"error": "missing 'question' in body"}), 400

    requested_model = payload.get("model") or OLLAMA_LLM
    temp = float(payload.get("temperature", DEFAULT_TEMPERATURE))
    max_toks = int(payload.get("max_tokens", DEFAULT_MAX_TOKENS))

    # Use validation helpers from retrieval_chat
    style = validate_style(payload.get("style"))
    response_type = validate_response_type(payload.get("response_type") or payload.get("type"))
    length = validate_length(payload.get("length"))

    conversation_history = payload.get("conversation_history") or []
    if not isinstance(conversation_history, list):
        conversation_history = []

    use_cache = payload.get("use_cache", True)
    if use_cache and not conversation_history:
        cached_response = _response_cache.get(question, style, response_type, length, requested_model)
        if cached_response:
            return jsonify({
                "answer": cached_response,
                "cached": True,
                "style": style,
                "response_type": response_type,
                "length": length
            }), 200

    rebuild = bool(payload.get("rebuild", False))
    indexing = payload.get("indexing") or {}
    retrieval = payload.get("retrieval") or {}

    try:
        from llama_index.llms.ollama import Ollama
        
        index_obj, _ = get_index(force_rebuild=rebuild, build_kwargs=(indexing if rebuild else None))
        if index_obj is None:
            return jsonify({"error": "index not available"}), 500

        per_request_llm = Ollama(model=requested_model, temperature=temp, max_tokens=max_toks, request_timeout=300)

        prompter = ChatPrompter.from_history_list(
            history=conversation_history,
            style=style,
            response_type=response_type,
            length=length
        )
        enhanced_question = prompter.build_full_prompt(question)

        try:
            query_engine = index_obj.as_query_engine(llm=per_request_llm, **retrieval) if retrieval else index_obj.as_query_engine(llm=per_request_llm)
        except TypeError:
            query_engine = index_obj.as_query_engine(llm=per_request_llm)

        use_mock = should_use_mock(payload)
        if use_mock:
            response = MockResponseV3(question, style, response_type, length)
        else:
            response = query_engine.query(enhanced_question)

        answer_text = str(response)
        
        if use_cache and not conversation_history:
            _response_cache.set(question, style, response_type, length, requested_model, answer_text)

        return jsonify({
            "answer": answer_text,
            "cached": False,
            "style": style,
            "response_type": response_type,
            "length": length
        }), 200

    except Exception as e:
        logger.exception("Query v3 failed")
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------------
# Cache Endpoints
# --------------------------------------------------------------------------

@app.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Get cache statistics."""
    return jsonify(_response_cache.stats()), 200


@app.route("/cache/clear", methods=["POST"])
def cache_clear():
    """Clear the response cache."""
    _response_cache.clear()
    return jsonify({"status": "cache_cleared"}), 200


# --------------------------------------------------------------------------
# Rebuild Endpoint
# --------------------------------------------------------------------------

@app.route("/rebuild", methods=["POST"])
def rebuild():
    """
    Trigger force rebuild of the index.
    
    JSON body: {"wait": true} for blocking rebuild, {"wait": false} for async.
    """
    payload = request.get_json(force=True, silent=True) or {}
    wait = bool(payload.get("wait", True))

    if wait:
        # Synchronous (blocking) rebuild
        success = trigger_sync_rebuild()
        if success:
            return jsonify({"status": "rebuilt"}), 200
        else:
            return jsonify({"error": "rebuild failed"}), 500
    else:
        # Asynchronous rebuild
        status = trigger_async_rebuild()
        return jsonify({"status": status}), 202


# --------------------------------------------------------------------------
# Debug Endpoint (dev only)
# --------------------------------------------------------------------------

@app.route('/_debug/env')
def debug_env():
    """Temporary debug endpoint - returns environment variables."""
    env = {k: v for k, v in os.environ.items()}
    return jsonify(env)


# --------------------------------------------------------------------------
# Main Entry Point
# --------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", BACKEND_PORT))
    app.run(host="0.0.0.0", port=port, debug=True)
