from flask import Flask, request, jsonify
import threading
import os
import logging
import json
import importlib.util
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.api")

# Configuration via env vars with sensible defaults
INDEX_DIR = os.environ.get("INDEX_DIR", ".embeddings/index_store")
DATA_DIR = os.environ.get("DATA_DIR", "../test/data/CSC15")
# directory where embedding definition lives (model.txt or config.json)
EMBEDDINGS_DIR = os.environ.get("EMBEDDINGS_DIR", "./embeddings")
OLLAMA_LLM = os.environ.get("OLLAMA_LLM", "llama3-chatqa")
OLLAMA_EMBED = os.environ.get("OLLAMA_EMBED", "qwen3-embedding:8b")
DEFAULT_TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "5.0"))
DEFAULT_MAX_TOKENS = int(os.environ.get("OLLAMA_MAX_TOKENS", "1024"))

# Lazy-loaded globals
_index_lock = threading.Lock()
_index_obj = None
_query_engine = None

# Import Ollama/Settings directly
try:
    from llama_index.llms.ollama import Ollama  # noqa: E402
    from llama_index.embeddings.ollama import OllamaEmbedding  # noqa: E402
    from llama_index.core.settings import Settings  # noqa: E402
except Exception as e:
    logger.error(f"Failed to import Ollama or LlamaIndex classes: {e}")
    raise

# Dynamically load local test/test.py to avoid colliding with stdlib 'test' package.
def _load_local_test_module():
    # compute path: project_root/test/test.py relative to this file
    cur = Path(__file__).resolve()
    candidate = (cur.parent.parent / "test" / "test.py").resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Local test.py not found at expected path: {candidate}")
    spec = importlib.util.spec_from_file_location("project_test", str(candidate))
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        raise ImportError(f"Could not load spec for {candidate}")
    loader.exec_module(module)
    return module

try:
    _local_test = _load_local_test_module()
    get_or_create_index = getattr(_local_test, "get_or_create_index")
except Exception as e:
    logger.error(f"Failed to load local test module: {e}")
    raise

# helper to read embedding model name from embeddings folder
def _read_embedding_model_from_folder(embeddings_dir: str, fallback: str = "qwen3-embedding:8b") -> str:
    try:
        p_txt = os.path.join(embeddings_dir, "model.txt")
        if os.path.exists(p_txt):
            with open(p_txt, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        p_json = os.path.join(embeddings_dir, "config.json")
        if os.path.exists(p_json):
            with open(p_json, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict) and "model" in cfg and cfg["model"]:
                return str(cfg["model"])
    except Exception:
        logger.debug("Could not read embedding model from folder; using fallback.")
    return fallback

def init_models():
    """Initialize Settings for embedding and llm models (idempotent)."""
    try:
        # prefer embedding model specified in embeddings folder, then env var, then default
        embed_model_name = _read_embedding_model_from_folder(EMBEDDINGS_DIR, fallback=os.environ.get("OLLAMA_EMBED", OLLAMA_EMBED))
        Settings.embed_model = OllamaEmbedding(model_name=embed_model_name, max_tokens=DEFAULT_MAX_TOKENS)
        Settings.llm = Ollama(model=OLLAMA_LLM, temperature=DEFAULT_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS)
        logger.info(f"Initialized Ollama LLM='{OLLAMA_LLM}' embed='{embed_model_name}'")
    except Exception as e:
        logger.error(f"Could not initialize Ollama models: {e}")
        raise

def get_index(force_rebuild: bool = False, build_kwargs: dict | None = None):
	"""Thread-safe lazy loader for the VectorStoreIndex and its query engine.
	If build_kwargs is provided and force_rebuild is true, we attempt to pass them
	through to get_or_create_index(**build_kwargs). If that call signature is not
	supported, we fallback to the original call."""
	global _index_obj, _query_engine
	with _index_lock:
		if _index_obj is None or force_rebuild:
			logger.info(f"Loading/creating index (force_rebuild={force_rebuild}) build_kwargs={build_kwargs}")
			init_models()
			try:
				if build_kwargs and force_rebuild:
					# try to pass kwargs to get_or_create_index, but be tolerant
					try:
						_index_obj = get_or_create_index(index_dir=INDEX_DIR, data_dir=DATA_DIR, force_rebuild=force_rebuild, **build_kwargs)
					except TypeError:
						# signature probably doesn't accept the extra args; retry without them
						logger.warning("get_or_create_index does not accept build kwargs; retrying without them")
						_index_obj = get_or_create_index(index_dir=INDEX_DIR, data_dir=DATA_DIR, force_rebuild=force_rebuild)
				else:
					_index_obj = get_or_create_index(index_dir=INDEX_DIR, data_dir=DATA_DIR, force_rebuild=force_rebuild)
			except Exception as e:
				logger.exception(f"Failed to create/load index: {e}")
				raise

			# create a fresh query engine attached to the index (default/global LLM)
			try:
				_query_engine = _index_obj.as_query_engine(llm=Settings.llm)
			except Exception as e:
				logger.warning(f"Could not create query engine from index: {e}")
				_query_engine = None
		return _index_obj, _query_engine

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/query", methods=["POST"])
def query():
	"""
	POST /query
	JSON body: {"question": "...", "rebuild": false, "indexing": {...}, "retrieval": {...}}
	- indexing: optional dict of build-time params (chunk_size, chunk_overlap, ranker, reranker, etc.)
	            applied only when rebuild=True (passed to get_or_create_index if supported).
	- retrieval: optional dict passed to index_obj.as_query_engine(..., **retrieval). Example keys:
	             similarity_top_k, rerank_top_k, text_qa_template (or "prompt"), streaming, ...
	"""
	payload = request.get_json(force=True, silent=True) or {}
	question = payload.get("question") or payload.get("q") or ""
	if not question:
		return jsonify({"error": "missing 'question' in body"}), 400

	rebuild = bool(payload.get("rebuild", False))
	indexing = payload.get("indexing") or {}
	if indexing is None or not isinstance(indexing, dict):
		indexing = {}
	retrieval = payload.get("retrieval") or {}
	if retrieval is None or not isinstance(retrieval, dict):
		retrieval = {}

	try:
		# Pass build-time params only when forcing a rebuild; otherwise ignore them in get_index
		index_obj, qe = get_index(force_rebuild=rebuild, build_kwargs=(indexing if rebuild else None))
		if index_obj is None:
			return jsonify({"error": "index not available"}), 500

		# If retrieval params given, try to create a per-request query engine using them (safe attempt)
		qe_to_use = qe
		if retrieval:
			r_kwargs = retrieval.copy()
			# allow "prompt" alias for text_qa_template
			if "prompt" in r_kwargs and "text_qa_template" not in r_kwargs:
				r_kwargs["text_qa_template"] = r_kwargs.pop("prompt")
			try:
				qe_temp = index_obj.as_query_engine(llm=Settings.llm, **r_kwargs)
				qe_to_use = qe_temp
			except TypeError:
				logger.warning("as_query_engine() may not accept provided retrieval kwargs; using default query engine")
			except Exception:
				logger.exception("Failed to create per-request query engine with retrieval parameters; using default")

		# Run the query (synchronous)
		logger.info(f"Received query; rebuild={rebuild} retrieval={bool(retrieval)}")
		response = qe_to_use.query(question)
		answer_text = str(response)
		return jsonify({"answer": answer_text}), 200
	except Exception as e:
		logger.exception("Query failed")
		return jsonify({"error": str(e)}), 500

# New endpoint: version 2 allows specifying "model" (LLM) in the request body.
@app.route("/query_v2", methods=["POST"])
def query_v2():
	"""
	POST /query_v2
	JSON body: {
	  "question": "...",
	  "model": "llama3-chatqa",            # optional - if absent, falls back to configured default
	  "temperature": 0.0,                  # optional override
	  "max_tokens": 1024,                  # optional override
	  "rebuild": false,                    # optional
	  "indexing": {...},                   # optional build-time params for rebuild
	  "retrieval": {...}                   # optional retrieval params passed to as_query_engine
	}
	"""
	payload = request.get_json(force=True, silent=True) or {}
	question = payload.get("question") or payload.get("q") or ""
	if not question:
		return jsonify({"error": "missing 'question' in body"}), 400

	requested_model = payload.get("model") or os.environ.get("OLLAMA_LLM", OLLAMA_LLM)
	try:
		temp = float(payload.get("temperature", DEFAULT_TEMPERATURE))
	except Exception:
		temp = DEFAULT_TEMPERATURE
	try:
		max_toks = int(payload.get("max_tokens", DEFAULT_MAX_TOKENS))
	except Exception:
		max_toks = DEFAULT_MAX_TOKENS

	rebuild = bool(payload.get("rebuild", False))
	indexing = payload.get("indexing") or {}
	if indexing is None or not isinstance(indexing, dict):
		indexing = {}
	retrieval = payload.get("retrieval") or {}
	if retrieval is None or not isinstance(retrieval, dict):
		retrieval = {}

	try:
		# get index (apply build-time params only if force_rebuild requested)
		index_obj, _ = get_index(force_rebuild=rebuild, build_kwargs=(indexing if rebuild else None))
		if index_obj is None:
			return jsonify({"error": "index not available"}), 500

		# instantiate per-request Ollama model
		try:
			per_request_llm = Ollama(model=requested_model, temperature=temp, max_tokens=max_toks)
		except Exception as e:
			logger.exception("Failed to instantiate per-request Ollama model")
			return jsonify({"error": f"failed to instantiate model '{requested_model}': {e}"}), 500

		# create a temporary query engine using this LLM and optional retrieval params
		try:
			r_kwargs = retrieval.copy()
			if "prompt" in r_kwargs and "text_qa_template" not in r_kwargs:
				r_kwargs["text_qa_template"] = r_kwargs.pop("prompt")
			query_engine = index_obj.as_query_engine(llm=per_request_llm, **r_kwargs) if r_kwargs else index_obj.as_query_engine(llm=per_request_llm)
		except TypeError:
			logger.warning("as_query_engine() may not accept provided retrieval kwargs; creating query engine without them")
			try:
				query_engine = index_obj.as_query_engine(llm=per_request_llm)
			except Exception as e:
				logger.exception("Failed to create query engine with per-request model")
				return jsonify({"error": f"failed to create query engine: {e}"}), 500
		except Exception as e:
			logger.exception("Failed to create query engine with per-request model")
			return jsonify({"error": f"failed to create query engine: {e}"}), 500

		# run the query
		logger.info(f"Received v2 query; model={requested_model}, rebuild={rebuild}, retrieval={bool(retrieval)}")
		response = query_engine.query(question)
		answer_text = str(response)
		return jsonify({"answer": answer_text}), 200

	except Exception as e:
		logger.exception("Query v2 failed")
		return jsonify({"error": str(e)}), 500

@app.route("/rebuild", methods=["POST"])
def rebuild():
    """
    Trigger force rebuild of the index.
    Optional JSON body: {"wait": true} if you want this call to block until rebuild finishes.
    """
    payload = request.get_json(force=True, silent=True) or {}
    wait = bool(payload.get("wait", True))

    def _rebuild_task():
        try:
            get_index(force_rebuild=True)
            logger.info("Index rebuild completed.")
        except Exception:
            logger.exception("Index rebuild failed")

    if wait:
        # blocking rebuild
        try:
            _rebuild_task()
            return jsonify({"status": "rebuilt"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # async rebuild
        t = threading.Thread(target=_rebuild_task, daemon=True)
        t.start()
        return jsonify({"status": "rebuild_started"}), 202

if __name__ == "__main__":
    # Simple dev server (for production use gunicorn/uwsgi)
    port = int(os.environ.get("BACKEND_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)