from flask import Flask, request, jsonify
from datetime import datetime, timezone
import time
import threading
import os
import logging
import json
import importlib.util
from pathlib import Path
# Load environment variables from project's .env (if present). We prefer a .env
# file located at the repository root (parent of the backend folder). This uses
# python-dotenv when available but continues gracefully if the package or file
# is missing.
try:
	from dotenv import load_dotenv
	env_path = Path(__file__).resolve().parent.parent / '.env'
	if env_path.exists():
		load_dotenv(dotenv_path=str(env_path))
		logging.getLogger('backend.api').info(f'Loaded .env from {env_path}')
except Exception:
	logging.getLogger('backend.api').debug('python-dotenv not available or .env not found; skipping load')
# Lazy import note: avoid importing heavy LLM/index modules at top-level so the
# dev server can start even if optional dependencies are missing. We'll import
# `get_or_create_index` inside `get_index` when needed.
# Local module imports (no `backend.` prefix) so running `python server.py`
# from the backend folder works as expected.
# Import prompts module for ChatPrompter class
try:
	from backend.prompts import ChatPrompter
except Exception:
	from prompts import ChatPrompter

# Import planner with a fallback so running as a module or script works
try:
	# When imported as `backend` package
	from backend.planner import default_planner
except Exception:
	# When running `python server.py` from the backend folder the top-level
	# module name is `planner.py`, so fall back to that import path.
	from planner import default_planner
try:
	# package import when running as `backend` package
	from backend import auth
	from backend.auth import get_user_from_request
except Exception:
	# fallback when running as a script from the backend folder
	import auth
	from auth import get_user_from_request

# Import quiz module
try:
	from backend import quiz as quiz_module
except Exception:
	import quiz as quiz_module

# Compatibility wrapper: some versions of llama-index expect a Prompt-like object
# with a `partial_format(**kwargs)` method. Our prompt helpers return plain strings.
# Wrap strings in a small adapter so older/newer llama-index internals that call
# `.partial_format()` won't fail.
class _PromptAdapter:
	def __init__(self, template: str):
		self.template = template

	def partial_format(self, **kwargs):
		"""
		Always return a real BasePromptTemplate instance for llama-index compatibility.
		If llama-index is not installed, raise an error so the developer can fix the environment.
		"""
		try:
			from llama_index.prompts.base import BasePromptTemplate  # type: ignore
		except Exception:
			raise RuntimeError("llama_index.prompts.base.BasePromptTemplate is required for prompt adaptation. Please ensure llama-index is installed and up to date.")

		try:
			formatted = self.template.format(**kwargs)
		except Exception:
			formatted = self.template

		class _WrappedPrompt(BasePromptTemplate):
			def __init__(self, template_text: str, input_vars: list):
				self.template = template_text
				self.input_variables = input_vars
				self.kwargs = kwargs
				self.template_vars = kwargs

			def partial_format(self, **pkwargs):
				try:
					return self.template.format(**pkwargs)
				except Exception:
					return self.template

			def __str__(self) -> str:
				return str(self.template)

		return _WrappedPrompt(formatted, list(kwargs.keys()) if isinstance(kwargs, dict) else [])

	def __contains__(self, item: str) -> bool:
		"""Allow substring checks (e.g., `HINT_TEMPLATE in adapter`) used in tests."""
		try:
			return item in self.template
		except Exception:
			return False

	def __str__(self) -> str:
		return str(self.template)

from flask_cors import CORS
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.api")

# Configuration via env vars with sensible defaults
INDEX_DIR 	= "./vector_index_store"
DATA_DIR 	= "./trial-data"
# directory where embedding definition lives (model.txt or config.json)
EMBEDDINGS_DIR = os.environ.get("EMBEDDINGS_DIR", "./embeddings")
OLLAMA_LLM = os.environ.get("OLLAMA_LLM", "llama3:8b")
OLLAMA_EMBED = os.environ.get("OLLAMA_EMBED", "bge-m3:latest")
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.5"))
DEFAULT_MAX_TOKENS = int(os.environ.get("DEFAULT_MAX_TOKENS", "1024"))
DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "600"))  # seconds
DEFAULT_PROMPT_MODE = os.environ.get("DEFAULT_PROMPT_MODE", "direct").strip().lower()  # 'hint' or 'direct'

# Main project directory (allows saving/reading files relative to a configurable root)
MAIN_PROJECT_DIR = os.environ.get("MAIN_PROJECT_DIR", os.getcwd())


def is_auth_disabled() -> bool:
	"""Return True only when DISABLE_AUTH is explicitly set to a truthy value.

	Treat common string values like '1', 'true', 'yes', 'on' (case-insensitive) as True.
	This avoids treating the string 'false' (which is non-empty) as True when using
	bool(os.environ.get(...)).
	"""
	val = os.environ.get("DISABLE_AUTH", "")
	try:
		return str(val).strip().lower() in ("1", "true", "yes", "on")
	except Exception:
		return False

try:
	from backend.planner import default_planner, generate_plan
except Exception:
	from planner import default_planner, generate_plan
PLAN_MODEL = os.environ.get("PLAN_MODEL", "gpt-oss:latest")
PLAN_TEMPERATURE = float(os.environ.get("PLAN_TEMPERATURE", "0.15"))
PLAN_MAX_TOKENS = int(os.environ.get("PLAN_MAX_TOKENS", "1024"))

# Response caching configuration
CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() in ("true", "1", "yes", "on")
CACHE_MAX_SIZE = int(os.environ.get("CACHE_MAX_SIZE", "100"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))  # 1 hour default

# Simple LRU cache for responses
from collections import OrderedDict
import hashlib

class ResponseCache:
	"""Simple thread-safe LRU cache with TTL for caching LLM responses."""
	
	def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
		self.max_size = max_size
		self.ttl_seconds = ttl_seconds
		self._cache: OrderedDict = OrderedDict()
		self._lock = threading.Lock()
	
	def _make_key(self, question: str, style: str, response_type: str, length: str, model: str) -> str:
		"""Generate a cache key from query parameters."""
		key_string = f"{question}|{style}|{response_type}|{length}|{model}"
		return hashlib.sha256(key_string.encode()).hexdigest()
	
	def get(self, question: str, style: str, response_type: str, length: str, model: str) -> str | None:
		"""Get cached response if available and not expired."""
		if not CACHE_ENABLED:
			return None
		key = self._make_key(question, style, response_type, length, model)
		with self._lock:
			if key in self._cache:
				entry = self._cache[key]
				if time.time() - entry["timestamp"] < self.ttl_seconds:
					# Move to end (most recently used)
					self._cache.move_to_end(key)
					logger.debug(f"Cache hit for query key: {key[:16]}...")
					return entry["response"]
				else:
					# Expired, remove it
					del self._cache[key]
					logger.debug(f"Cache expired for key: {key[:16]}...")
		return None
	
	def set(self, question: str, style: str, response_type: str, length: str, model: str, response: str) -> None:
		"""Store a response in the cache."""
		if not CACHE_ENABLED:
			return
		key = self._make_key(question, style, response_type, length, model)
		with self._lock:
			if key in self._cache:
				del self._cache[key]
			self._cache[key] = {"response": response, "timestamp": time.time()}
			# Evict oldest if over capacity
			while len(self._cache) > self.max_size:
				oldest_key = next(iter(self._cache))
				del self._cache[oldest_key]
				logger.debug(f"Cache evicted oldest entry")
	
	def clear(self) -> None:
		"""Clear all cached responses."""
		with self._lock:
			self._cache.clear()
			logger.info("Response cache cleared")
	
	def stats(self) -> dict:
		"""Get cache statistics."""
		with self._lock:
			return {
				"size": len(self._cache),
				"max_size": self.max_size,
				"ttl_seconds": self.ttl_seconds,
				"enabled": CACHE_ENABLED
			}

# Global cache instance
_response_cache = ResponseCache(max_size=CACHE_MAX_SIZE, ttl_seconds=CACHE_TTL_SECONDS)

# Lazy-loaded globals
_index_lock = threading.Lock()
_index_obj = None
_query_engine = None
# guard to prevent concurrent async rebuilds started from health checks
_rebuild_lock = threading.Lock()
_rebuild_in_progress = False
REBUILD_COOLDOWN_SECONDS = int(os.environ.get("REBUILD_COOLDOWN_SECONDS", str(1 * 60)))  # default 10 minutes
REBUILD_LOCK_FILE = Path(INDEX_DIR) / ".rebuild_lock.json"

def _read_persisted_rebuild_lock():
	try:
		if REBUILD_LOCK_FILE.exists():
			with open(REBUILD_LOCK_FILE, "r", encoding="utf-8") as f:
				return json.load(f)
	except Exception:
		logger.debug("Could not read persisted rebuild lock file")
	return {}

def _write_persisted_rebuild_lock(data: dict):
	try:
		os.makedirs(REBUILD_LOCK_FILE.parent, exist_ok=True)
		tmp = str(REBUILD_LOCK_FILE) + ".tmp"
		with open(tmp, "w", encoding="utf-8") as f:
			json.dump(data, f)
		os.replace(tmp, str(REBUILD_LOCK_FILE))
	except Exception:
		logger.warning("Could not write persisted rebuild lock file")
# module-level reference to the vector_store_gen.get_or_create_index function (populated lazily)
get_or_create_index = None

# Simple in-memory user registry for dev-only register/login endpoints
USERS: dict = {}

# Import Ollama/Settings directly
try:
    from llama_index.llms.ollama import Ollama  # noqa: E402
    from llama_index.embeddings.ollama import OllamaEmbedding  # noqa: E402
    from llama_index.core.settings import Settings  # noqa: E402
except Exception as e:
    logger.error(f"Failed to import Ollama or LlamaIndex classes: {e}")
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
        embed_model_name = _read_embedding_model_from_folder(EMBEDDINGS_DIR, fallback= OLLAMA_EMBED)
        Settings.embed_model = OllamaEmbedding(model_name=embed_model_name, max_tokens=DEFAULT_MAX_TOKENS, request_timeout=DEFAULT_TIMEOUT)
        Settings.llm = Ollama(model=OLLAMA_LLM, temperature=DEFAULT_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS, request_timeout=DEFAULT_TIMEOUT)
        logger.info(f"Initialized Ollama LLM='{OLLAMA_LLM}' embed='{embed_model_name}'")
    except Exception as e:
        logger.error(f"Could not initialize Ollama models: {e}")
        raise

def get_index(force_rebuild: bool = False, build_kwargs: dict | None = None):
	"""Thread-safe lazy loader for the VectorStoreIndex and its query engine.
	We import the heavy `get_or_create_index` lazily here so the dev server can
	start for auth/planner flows even if LLM/index dependencies are missing.
	"""
	global _index_obj, _query_engine
	# expose get_or_create_index at module level so tests can monkeypatch it
	global get_or_create_index
	with _index_lock:
		if _index_obj is None or force_rebuild:
			logger.info(f"Loading/creating index (force_rebuild={force_rebuild}) build_kwargs={build_kwargs}")
			# Lazy import of the index builder which depends on llama-index/ollama.
			# Allow tests to monkeypatch `server.get_or_create_index` by checking
			# the module-level name first; only import from vector_store_gen if it's
			# not already provided.
			if get_or_create_index is None:
				try:
					from vector_store_gen import get_or_create_index as _goci
					# bind the imported function to the module-level name
					get_or_create_index = _goci
				except Exception as e:
					logger.warning(f"LLM/index libraries not available: {e}")
					# Re-raise so callers that actually need the index see a clear error
					raise

			# initialize model settings (this may raise if Ollama isn't available)
			init_models()
			try:
				if build_kwargs and force_rebuild:
					# Pass indexing dict as 'indexing' kwarg for parser selection
					try:
						_index_obj = get_or_create_index(index_dir=INDEX_DIR, data_dir=DATA_DIR, force_rebuild=force_rebuild, indexing=build_kwargs)
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
				try:
					_query_engine = _index_obj.as_query_engine(llm=Settings.llm)
				except TypeError:
					logger.info("as_query_engine() does not accept text_qa_template; creating query engine without template")
					_query_engine = _index_obj.as_query_engine(llm=Settings.llm)
			except Exception as e:
				logger.warning(f"Could not create query engine from index: {e}")
				_query_engine = None
		return _index_obj, _query_engine

@app.route("/health", methods=["GET"])
def health():
	"""
	Health endpoint with a lightweight check for index/embeddings presence.
	If the persisted index or embeddings appear missing, start an asynchronous
	rebuild of the index (non-blocking) and return an informative status so
	the frontend can surface that a rebuild is in progress.
	"""
	try:
		index_file = Path(INDEX_DIR) / "docstore.json"
		index_exists = index_file.exists()

		# Check embedding metadata (if present) and compare with actual data files
		embeddings_meta = set()
		try:
			# import helper from vector_store_gen if available
			try:
				from vector_store_gen import load_embedding_metadata
			except Exception:
				load_embedding_metadata = None

			if load_embedding_metadata:
				embeddings_meta = load_embedding_metadata(INDEX_DIR)
				if not isinstance(embeddings_meta, (set, list)):
					embeddings_meta = set(embeddings_meta or [])
				else:
					embeddings_meta = set(embeddings_meta)
		except Exception as e:
			logger.warning(f"Could not read embedding metadata: {e}")
			embeddings_meta = set()

		# collect current data files under DATA_DIR
		current_files = set()
		try:
			for root, _, files in os.walk(DATA_DIR):
				for fname in files:
					current_files.add(os.path.abspath(os.path.join(root, fname)))
		except Exception as e:
			logger.warning(f"Could not enumerate data files in {DATA_DIR}: {e}")

		# determine mismatches
		missing_on_disk = [p for p in embeddings_meta if not os.path.exists(p)]
		new_files = list(current_files - embeddings_meta) if embeddings_meta else list(current_files)

		needs_rebuild = False
		reason = []
		if not index_exists:
			needs_rebuild = True
			reason.append("missing_index")
		if missing_on_disk:
			needs_rebuild = True
			reason.append("meta_points_to_missing_files")
		if new_files:
			needs_rebuild = True
			reason.append("new_data_files")

		if needs_rebuild:
			logger.info(f"Health check: rebuild needed (reasons={reason}) index_exists={index_exists} meta_count={len(embeddings_meta)} current_files={len(current_files)}")

			# guard to ensure only one async rebuild is started and respect persisted cooldown
			global _rebuild_in_progress
			started = False
			cooldown_blocked = False
			cooldown_seconds_left = 0
			with _rebuild_lock:
				# check persisted lock to avoid frequent rebuilds across restarts
				persisted = _read_persisted_rebuild_lock() or {}
				last_started = persisted.get("last_started")
				now_ts = time.time()
				if last_started:
					try:
						last_ts = float(last_started)
					except Exception:
						last_ts = 0
					elapsed = now_ts - last_ts
					if elapsed < REBUILD_COOLDOWN_SECONDS:
						cooldown_blocked = True
						cooldown_seconds_left = int(REBUILD_COOLDOWN_SECONDS - elapsed)
				# also check in-memory flag
				if not cooldown_blocked and not _rebuild_in_progress:
					# update persisted last_started immediately to claim the slot
					try:
						persisted["last_started"] = str(now_ts)
						_write_persisted_rebuild_lock(persisted)
					except Exception:
						logger.debug("Failed to persist rebuild start time")
					_rebuild_in_progress = True
					started = True

			if cooldown_blocked:
				logger.info(f"Rebuild suppressed due to cooldown (seconds_left={cooldown_seconds_left})")
				rebuild_status = "rebuild_cooldown"
			elif started:
				def _async_rebuild():
					global _rebuild_in_progress
					try:
						# attempt to force a rebuild (this will call into vector_store_gen)
						get_index(force_rebuild=True)
						logger.info("Async rebuild completed successfully")
						# record completion time
						try:
							persisted = _read_persisted_rebuild_lock() or {}
							persisted["last_completed"] = str(time.time())
							_write_persisted_rebuild_lock(persisted)
						except Exception:
							logger.debug("Failed to persist rebuild completion time")
					except Exception:
						logger.exception("Async rebuild failed")
					finally:
						with _rebuild_lock:
							_rebuild_in_progress = False

				t = threading.Thread(target=_async_rebuild, daemon=True)
				t.start()
				rebuild_status = "rebuild_started"
			else:
				logger.info("Async rebuild already in progress; not starting a new one")
				rebuild_status = "rebuild_already_in_progress"

			return jsonify({
				"status": rebuild_status,
				"index_exists": index_exists,
				"meta_entries": len(embeddings_meta),
				"current_files": len(current_files),
				"missing_meta_files": len(missing_on_disk),
				"new_files": len(new_files),
				"reasons": reason,
			}), 200

		# all good
		return jsonify({
			"status": "ok",
			"index_exists": index_exists,
			"meta_entries": len(embeddings_meta),
			"current_files": len(current_files),
		}), 200
	except Exception as e:
		logger.exception("Health check failed")
		return jsonify({"status": "error", "error": str(e)}), 500

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
			# Remove all prompt/template logic
			try:
				qe_temp = index_obj.as_query_engine(llm=Settings.llm, **r_kwargs)
				qe_to_use = qe_temp
			except TypeError:
				logger.warning("as_query_engine() may not accept provided retrieval kwargs; using default query engine")
			except Exception:
				logger.exception("Failed to create per-request query engine with retrieval parameters; using default")

		# Run the query (synchronous)
		logger.info(f"Received query; rebuild={rebuild} retrieval={bool(retrieval)}")
		# Debug: log the retrieval kwargs and any derived template
		try:
			logger.debug(f"Retrieval kwargs: {r_kwargs}")
		except Exception:
			logger.debug("No retrieval kwargs available for logging")

		# Allow a mock path to verify pipeline without calling Ollama. This can be
		# triggered either via env var MOCK_LLM_ECHO or per-request payload flag
		# "mock": true (useful for testing without restarting the server).
		use_mock = bool(payload.get("mock") or payload.get("use_mock") or os.environ.get("MOCK_LLM_ECHO"))
		if use_mock:
			class _MockResponse:
				def __init__(self, q):
					self._q = q
				def __str__(self):
					return f"MOCK_ECHO: {self._q}"
				@property
				def source_nodes(self):
					return []
			logger.info("Using MOCK_LLM_ECHO response")
			response = _MockResponse(question)
		else:
			response = qe_to_use.query(question)

		# Debug: inspect response object for useful attributes
		try:
			logger.debug(f"Response object type: {type(response)}")
			attrs = dir(response)
			logger.debug(f"Response dir() sample: {attrs[:20]}")
			# Common properties across llama-index responses
			for attr in ("source_nodes", "source_documents", "docs", "nodes"):
				val = getattr(response, attr, None)
				if val is not None:
					try:
						logger.debug(f"Response.{attr} length: {len(val)}")
						if len(val) > 0:
							# attempt to log a short snippet
							first = val[0]
							snippet = str(getattr(first, 'text', first))[:400]
							logger.debug(f"Response.{attr}[0] snippet: {snippet}")
					except Exception:
						logger.debug(f"Could not inspect {attr} on response")
		except Exception:
			logger.debug("Failed to introspect response object")

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

	requested_model = payload.get("model") or  OLLAMA_LLM
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
			per_request_llm = Ollama(model=requested_model, temperature=temp, max_tokens=max_toks, request_timeout=300)
		except Exception as e:
			logger.exception("Failed to instantiate per-request Ollama model")
			return jsonify({"error": f"failed to instantiate model '{requested_model}': {e}"}), 500

		# create a temporary query engine using this LLM and optional retrieval params
		try:
			r_kwargs = retrieval.copy()
			# Remove all prompt/template logic
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
		# Debug: log retrieval kwargs and derived template
		try:
			logger.debug(f"Per-request retrget_or_create_indexieval kwargs: {r_kwargs}")
		except Exception:
			logger.debug("No per-request retrieval kwargs to log")

		# allow quick mock path for testing (env var or per-request flag)
		use_mock = bool(payload.get("mock") or payload.get("use_mock") or os.environ.get("MOCK_LLM_ECHO"))
		if use_mock:
			class _MockResponseV2:
				def __init__(self, q):
					self._q = q
				def __str__(self):
					return f"MOCK_ECHO_V2: {self._q}"
			response = _MockResponseV2(question)
		else:
			# Use the query engine directly for retrieval-style queries
			response = query_engine.query(question)
		logger.debug(f"Response object: type={type(response)}; str={str(response)[:200]}")

		answer_text = str(response)
		return jsonify({"answer": answer_text}), 200

	except Exception as e:
		logger.exception("Query v2 failed")
		return jsonify({"error": str(e)}), 500


# Enhanced query endpoint with full prompt customization and conversation history
@app.route("/query_v3", methods=["POST"])
def query_v3():
	"""
	POST /query_v3
	Enhanced query endpoint with support for:
	- Response style (formal, casual, technical)
	- Response type (direct, hinting, socratic)
	- Response length (short, medium, long)
	- Conversation history for context-awareness
	- Response caching for faster replies
	
	JSON body: {
		"question": "...",
		"model": "llama3-chatqa",            # optional - defaults to configured LLM
		"temperature": 0.0,                  # optional override
		"max_tokens": 1024,                  # optional override
		"style": "formal",                   # optional: formal, casual, technical
		"response_type": "direct",           # optional: direct, hinting, socratic
		"length": "medium",                  # optional: short, medium, long
		"conversation_history": [...],       # optional: list of {role, content} dicts
		"use_cache": true,                   # optional: whether to use response caching
		"rebuild": false,                    # optional
		"indexing": {...},                   # optional build-time params for rebuild
		"retrieval": {...}                   # optional retrieval params
	}
	
	Response: {
		"answer": "...",
		"cached": false,                     # whether response was from cache
		"style": "formal",                   # actual style used
		"response_type": "direct",           # actual type used
		"length": "medium"                   # actual length used
	}
	"""
	payload = request.get_json(force=True, silent=True) or {}
	question = payload.get("question") or payload.get("q") or ""
	if not question:
		return jsonify({"error": "missing 'question' in body"}), 400

	# Extract model and generation parameters
	requested_model = payload.get("model") or OLLAMA_LLM
	try:
		temp = float(payload.get("temperature", DEFAULT_TEMPERATURE))
	except Exception:
		temp = DEFAULT_TEMPERATURE
	try:
		max_toks = int(payload.get("max_tokens", DEFAULT_MAX_TOKENS))
	except Exception:
		max_toks = DEFAULT_MAX_TOKENS

	# Extract prompt customization parameters
	style = (payload.get("style") or "formal").lower()
	response_type = (payload.get("response_type") or payload.get("type") or "direct").lower()
	length = (payload.get("length") or "medium").lower()
	
	# Validate parameters
	if style not in ["formal", "casual", "technical"]:
		style = "formal"
	if response_type not in ["direct", "hinting", "socratic"]:
		response_type = "direct"
	if length not in ["short", "medium", "long"]:
		length = "medium"

	# Extract conversation history
	conversation_history = payload.get("conversation_history") or []
	if not isinstance(conversation_history, list):
		conversation_history = []

	# Check cache first (unless explicitly disabled)
	use_cache = payload.get("use_cache", True)
	cached_response = None
	if use_cache and not conversation_history:  # Don't cache contextual queries
		cached_response = _response_cache.get(question, style, response_type, length, requested_model)
		if cached_response:
			logger.info(f"Returning cached response for query")
			return jsonify({
				"answer": cached_response,
				"cached": True,
				"style": style,
				"response_type": response_type,
				"length": length
			}), 200

	rebuild = bool(payload.get("rebuild", False))
	indexing = payload.get("indexing") or {}
	if not isinstance(indexing, dict):
		indexing = {}
	retrieval = payload.get("retrieval") or {}
	if not isinstance(retrieval, dict):
		retrieval = {}

	try:
		# Get index
		index_obj, _ = get_index(force_rebuild=rebuild, build_kwargs=(indexing if rebuild else None))
		if index_obj is None:
			return jsonify({"error": "index not available"}), 500

		# Instantiate per-request Ollama model
		try:
			per_request_llm = Ollama(
				model=requested_model,
				temperature=temp,
				max_tokens=max_toks,
				request_timeout=300
			)
		except Exception as e:
			logger.exception("Failed to instantiate per-request Ollama model")
			return jsonify({"error": f"failed to instantiate model '{requested_model}': {e}"}), 500

		# Build the enhanced prompt using ChatPrompter
		prompter = ChatPrompter.from_history_list(
			history=conversation_history,
			style=style,
			response_type=response_type,
			length=length
		)
		
		# Generate the full prompt with context
		enhanced_question = prompter.build_full_prompt(question)
		logger.debug(f"Enhanced prompt length: {len(enhanced_question)} chars")

		# Create query engine
		try:
			r_kwargs = retrieval.copy()
			query_engine = index_obj.as_query_engine(llm=per_request_llm, **r_kwargs) if r_kwargs else index_obj.as_query_engine(llm=per_request_llm)
		except TypeError:
			logger.warning("as_query_engine() may not accept provided retrieval kwargs; creating without them")
			try:
				query_engine = index_obj.as_query_engine(llm=per_request_llm)
			except Exception as e:
				logger.exception("Failed to create query engine")
				return jsonify({"error": f"failed to create query engine: {e}"}), 500
		except Exception as e:
			logger.exception("Failed to create query engine")
			return jsonify({"error": f"failed to create query engine: {e}"}), 500

		# Log query details
		logger.info(f"Query v3: model={requested_model}, style={style}, type={response_type}, length={length}, history_len={len(conversation_history)}")

		# Allow mock path for testing
		use_mock = bool(payload.get("mock") or payload.get("use_mock") or os.environ.get("MOCK_LLM_ECHO"))
		if use_mock:
			class _MockResponseV3:
				def __init__(self, q, s, t, l):
					self._q = q
					self._style = s
					self._type = t
					self._length = l
				def __str__(self):
					return f"MOCK_ECHO_V3: style={self._style}, type={self._type}, length={self._length} | {self._q[:100]}"
			response = _MockResponseV3(question, style, response_type, length)
		else:
			# Use enhanced question with full prompt context
			response = query_engine.query(enhanced_question)

		answer_text = str(response)
		
		# Cache the response (only for non-contextual queries)
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


@app.route("/cache/stats", methods=["GET"])
def cache_stats():
	"""Get cache statistics."""
	return jsonify(_response_cache.stats()), 200


@app.route("/cache/clear", methods=["POST"])
def cache_clear():
	"""Clear the response cache."""
	_response_cache.clear()
	return jsonify({"status": "cache_cleared"}), 200


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


### Simple dev-only auth endpoints (register/login) - issue JWTs
@app.route("/auth/register", methods=["POST"])
def auth_register():
	payload = request.get_json(force=True, silent=True) or {}
	email = payload.get("email") or payload.get("user_id")
	password = payload.get("password")
	# For developer convenience (tests/dev), allow a simple register flow when
	# only a user_id is provided and no password. In that case, issue a JWT
	# directly without persisting a password. This keeps the endpoint usable
	# in lightweight dev/test scenarios.
	if not email:
		return jsonify({"error": "missing email or user_id"}), 400
	if not password:
		# dev/test flow: return a token without creating a persisted account
		token = auth.create_jwt_for_user(email)
		return jsonify({"token": token}), 200
	try:
		# register persists to disk via backend/auth.register_user
		auth.register_user(email, password)
	except ValueError as e:
		# user exists or invalid input
		return jsonify({"error": str(e)}), 409
	except Exception as e:
		logger.exception("Failed to register user")
		return jsonify({"error": str(e)}), 500

	token = auth.create_jwt_for_user(email)
	return jsonify({"token": token}), 201


@app.route("/auth/login", methods=["POST"])
def auth_login():
	payload = request.get_json(force=True, silent=True) or {}
	email = payload.get("email") or payload.get("user_id")
	password = payload.get("password")
	if not email or not password:
		return jsonify({"error": "missing email or password"}), 400
	# verify password against on-disk store
	ok = auth.verify_user(email, password)
	if not ok:
		return jsonify({"error": "invalid credentials"}), 401
	token = auth.create_jwt_for_user(email)
	return jsonify({"token": token}), 200


### Planner API (simple, no-auth endpoints for prototyping)
@app.route("/plans", methods=["POST"])  # create
def create_plan():
	# Auth required unless disabled via env var
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		payload = request.get_json(force=True, silent=True) or {}
		user_id = payload.get("user_id")

	payload = request.get_json(force=True, silent=True) or {}
	# Expect a single 'requirement' string from the frontend (not a topics list)
	requirement = payload.get("requirement") or payload.get("requirements") or ""
	if not user_id or not isinstance(requirement, str):
		return jsonify({"error": "invalid payload, require 'requirement' string (and authenticated user)"}), 400

	# Support mock path for tests/dev
	use_mock = bool(payload.get("mock") or payload.get("use_mock") or os.environ.get("MOCK_LLM_ECHO"))

	plan_text = ""
	if not use_mock:
		try:
			gen_model = payload.get("plan_model") or PLAN_MODEL
			gen_temp = float(payload.get("plan_temperature", PLAN_TEMPERATURE))
			gen_max = int(payload.get("plan_max_tokens", PLAN_MAX_TOKENS))
			edit_plan_id = payload.get("edit_plan_id")
			edit_instructions = payload.get("edit_instructions")
			original_plan = None
			# callers may optionally pass original_plan_text for iterative edits
			if payload.get("original_plan_text"):
				original_plan = payload.get("original_plan_text")
			elif edit_plan_id:
				# if caller provided an existing planner-managed plan id, include it for iterative generation
				prev = default_planner.get_plan(edit_plan_id)
				if prev:
					original_plan = getattr(prev, "plan_text", None)

			plan_text = generate_plan(user_id=user_id, requirement=requirement, original_plan=original_plan, edit_instructions=edit_instructions, model=gen_model, temperature=gen_temp, max_tokens=gen_max)
		except Exception:
			logger.exception("Plan generation failed; storing empty plan_text")

	# Persist the plan into planner store
	created = default_planner.create_plan(user_id=user_id, plan_text=plan_text)
	try:
		out = created.model_dump()
	except Exception:
		out = getattr(created, "__dict__", {})
	return jsonify(out), 201


@app.route("/plans", methods=["GET"])  # list by user
def list_plans():
	# Auth required unless disabled via env var
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
		# If caller passed user_id query param, ensure it matches token subject
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


@app.route("/plans/<plan_id>", methods=["GET"])
def get_plan(plan_id: str):
	p = default_planner.get_plan(plan_id)
	if not p:
		return jsonify({"error": "not found"}), 404
	# Auth required unless disabled via env var
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
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


@app.route("/saved_plans", methods=["POST"])
def save_plan():
	"""
	Persist a generated plan to the filesystem under ./saved_plans/{user_id}/{plan_name}.json
	JSON body: {"plan_name": "...", "plan_text": "...", "user_id": "..."}
	If DISABLE_AUTH is not set, requires Authorization bearer token and will use the token subject.
	"""
	payload = request.get_json(force=True, silent=True) or {}
	plan_name = payload.get("plan_name")
	plan_text = payload.get("plan_text") or ""
	if not plan_name:
		return jsonify({"error": "missing plan_name"}), 400

	# determine user_id via auth unless disabled
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		user_id = payload.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id (server running with DISABLE_AUTH=true)"}), 400

	# sanitize filename
	try:
		# import re
		# safe = re.sub(r'[^A-Za-z0-9._-]', '_', plan_name)[:200]
		# Save under MAIN_PROJECT_DIR for configurable project root
		save_dir = Path(MAIN_PROJECT_DIR) / "user_data" / "saved_plans" / str(user_id)
		save_dir.mkdir(parents=True, exist_ok=True)
		file_path = save_dir / f"{str(plan_name)}.json"
		# include explicit created_at timestamp in UTC so listing endpoint can surface it
		created_at = datetime.now(timezone.utc).isoformat()
		payload = {"name": plan_name, "user_id": user_id, "plan_text": plan_text, "created_at": created_at}
		with open(file_path, "w", encoding="utf-8") as f:
			json.dump(payload, f, indent=2)
		return jsonify({"status": "saved", "path": str(file_path)}), 201
	except Exception as e:
		logger.exception("Failed to save plan to disk")
		return jsonify({"error": str(e)}), 500


@app.route("/saved_plans/update", methods=["POST"])
def update_saved_plan():
	"""Regenerate and update an existing saved plan file.

	Expected JSON body: { "path": "/abs/path/to/file.json", "new_requirement": "...", "original_plan_text": "...", "edit_instructions": "..." }
	If `path` is not provided, `plan_name` and user identification (auth or user_id) can be used.
	Returns updated plan metadata on success.
	"""
	payload = request.get_json(force=True, silent=True) or {}
	file_path = payload.get("path")
	plan_name = payload.get("plan_name")
	# Accept either 'new_requirement' or a single 'requirement' field
	new_requirement = payload.get("new_requirement") or payload.get("requirement") or ""
	original_text = payload.get("original_plan_text")
	edit_instructions = payload.get("edit_instructions")

	# determine user id via auth unless disabled
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		user_id = payload.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id (server running with DISABLE_AUTH=true)"}), 400

	# Resolve file path if only plan_name provided
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

	# If original_text wasn't provided, prefer the file's plan_text
	if not original_text:
		original_text = data.get("plan_text") if isinstance(data, dict) else None

	if not new_requirement:
		return jsonify({"error": "missing new_requirement"}), 400

	# Generate new plan text
	try:
		gen_model = payload.get("plan_model") or PLAN_MODEL
		gen_temp = float(payload.get("plan_temperature", PLAN_TEMPERATURE))
		gen_max = int(payload.get("plan_max_tokens", PLAN_MAX_TOKENS))
		new_plan_text = generate_plan(user_id=user_id, requirement=new_requirement, original_plan=original_text, edit_instructions=edit_instructions, model=gen_model, temperature=gen_temp, max_tokens=gen_max)
	except Exception:
		logger.exception("Plan regeneration failed")
		return jsonify({"error": "regeneration failed"}), 500

	# Update file content and write back
	try:
		# Prefer to preserve other metadata keys
		if isinstance(data, dict):
			data["plan_text"] = new_plan_text
			data["updated_at"] = datetime.now(timezone.utc).isoformat()
		else:
			data = {"name": plan_name or p.stem, "user_id": user_id, "plan_text": new_plan_text, "updated_at": datetime.now(timezone.utc).isoformat()}
		with p.open("w", encoding="utf-8") as fh:
			json.dump(data, fh, indent=2)
	except Exception as e:
		logger.exception("Failed to write updated plan file")
		return jsonify({"error": str(e)}), 500

	# Return updated metadata
	return jsonify({"status": "updated", "path": str(p), "plan_text": new_plan_text}), 200


@app.route("/saved_plans/delete", methods=["POST"])
def delete_saved_plan():
	"""Delete a saved plan file.

	Expected JSON body: { "path": "/abs/path/to/file.json" } or { "plan_name": "name" }
	Auth behavior mirrors other saved_plans endpoints.
	"""
	payload = request.get_json(force=True, silent=True) or {}
	file_path = payload.get("path")
	plan_name = payload.get("plan_name")

	# determine user id via auth unless disabled
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		user_id = payload.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id (server running with DISABLE_AUTH=true)"}), 400

	# Resolve file path if only plan_name provided
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

@app.route("/saved_plans", methods=["GET"])
def list_saved_plans():
	"""
	List saved plans for a user. Looks in ./user_data/saved_plan/{user_id}/ and ./saved_plans/{user_id}/
	Returns JSON list of {name, path, created_at, filename}
	"""
	print("DISABLE_AUTH:", os.environ.get("DISABLE_AUTH"))
	# determine user_id via auth unless disabled
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")

	else:
		user_id = request.args.get("user_id")
		print("User ID (DISABLE_AUTH):", user_id)	
		if not user_id:
			return jsonify({"error": "missing user_id query parameter (server running with DISABLE_AUTH=true)"}), 400

	results = []
	try:
		candidates = []
		# Look under configurable MAIN_PROJECT_DIR to support different repo roots
		base_user_saved_plans = Path(MAIN_PROJECT_DIR) / "user_data" / "saved_plans"
		for base in [base_user_saved_plans]:
			if not (base.exists() and base.is_dir()):
				continue
			# Prefer an exact match directory (e.g., .../saved_plans/{user_id}/)
			exact = base / str(user_id)
			if exact.exists() and exact.is_dir():
				for p in exact.rglob('*.json'):
					candidates.append(p)
				continue
			# Fallback: try plural/singular and approximate matches where the
			# directory name contains the provided user_id (handles emails vs short ids)
			for child in base.iterdir():
				try:
					if child.is_dir() and (str(user_id) in child.name):
						for p in child.rglob('*.json'):
							candidates.append(p)
				except Exception:
					# skip entries we cannot stat/read
					continue

		# deduplicate by absolute path
		seen = set()
		for p in sorted(candidates, key=lambda x: x.stat().st_mtime, reverse=True):
			ap = str(p.resolve())
			if ap in seen:
				continue
			seen.add(ap)
			try:
				with open(p, 'r', encoding='utf-8') as fh:
					data = json.load(fh)
			except Exception:
				data = {}
			stat = p.stat()
			created = None
			# prefer explicit metadata in file
			if isinstance(data, dict) and data.get('created_at'):
				created = data.get('created_at')
			else:
				created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

			name = (data.get('name') if isinstance(data, dict) and data.get('name') else p.stem)
			plan_text = data.get('plan_text') if isinstance(data, dict) else ""
			owner_id = data.get('user_id') if isinstance(data, dict) else ""
			results.append({
				'name': name,
				'owner': owner_id,
				'path': ap,
				'created_at': created,
				'plan_text': plan_text
			})
	except Exception as e:
		logger.exception('Failed to list saved plans')
		return jsonify({"error": str(e)}), 500

	return jsonify(results), 200


@app.route("/auth/status", methods=["GET"])
def auth_status():
	"""Return whether auth is disabled (for frontend to adapt UX).
	Response: {"auth_disabled": bool, "default_dev_user": str or null}
	"""
	try:
		disabled = is_auth_disabled()
		default_user = os.environ.get("DEFAULT_DEV_USER")
		return jsonify({"auth_disabled": disabled, "default_dev_user": default_user}), 200
	except Exception:
		return jsonify({"auth_disabled": False, "default_dev_user": None}), 200

@app.route("/auth/user", methods=["GET"])
def auth_user():
	"""
	Return information about the current user.
	When auth is enabled (DISABLE_AUTH not set), requires Authorization: Bearer <token>
	and returns the token subject plus claims.
	When auth is disabled, returns user_id from query param (if provided) or the
	DEFAULT_DEV_USER / 'dev' fallback so callers can discover the effective user id.
	"""
	try:
		disabled = is_auth_disabled()
		default_user = os.environ.get("DEFAULT_DEV_USER")
		# Auth enabled: require and verify bearer token
		if not disabled:
			auth_header = request.headers.get("Authorization")
			token = auth.extract_bearer_token(auth_header)
			if not token:
				return jsonify({"error": "missing Authorization Bearer token"}), 401
			claims = auth.verify_jwt(token)
			if not claims:
				return jsonify({"error": "invalid or expired token"}), 401
			return jsonify({"auth_disabled": False, "user_id": claims.get("sub"), "claims": claims}), 200
		# Auth disabled: allow query param or default dev user
		user_id = request.args.get("user_id") or default_user or "dev"
		return jsonify({"auth_disabled": True, "user_id": user_id, "default_dev_user": default_user}), 200
	except Exception:
		logger.exception("Failed to determine auth user")
		return jsonify({"error": "internal server error"}), 500

import os
from flask import jsonify, request, current_app

# Temporary debug endpoint — enable only in dev by setting BACKEND_DEBUG=1
@app.route('/_debug/env')
def debug_env():
	# Always return environment variables and their values
	env = {k: v for k, v in os.environ.items()}
	return jsonify(env)


# ============================================================================
# Quiz API Endpoints
# ============================================================================

@app.route("/quiz/generate", methods=["POST"])
def generate_quiz():
	"""
	Generate a new quiz based on topic and optionally a learning plan.
	
	JSON body: {
		"topic": "Python Basics",           # Required: quiz topic/title
		"plan_text": "...",                 # Optional: learning plan text for context
		"plan_reference": "plan-123",       # Optional: reference to a learning plan ID
		"num_questions": 5,                 # Optional: number of questions (default 5)
		"question_types": ["multiple_choice", "true_false", "short_answer"],  # Optional
		"difficulty": "medium",             # Optional: easy, medium, hard
		"model": "llama3:8b"                # Optional: Ollama model to use
	}
	
	Returns the generated quiz with questions.
	"""
	# Auth required unless disabled
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		payload = request.get_json(force=True, silent=True) or {}
		user_id = payload.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id (server running with DISABLE_AUTH=true)"}), 400
	
	payload = request.get_json(force=True, silent=True) or {}
	topic = payload.get("topic")
	if not topic:
		return jsonify({"error": "missing 'topic' in request body"}), 400
	
	try:
		quiz = quiz_module.generate_quiz(
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
		
		# Convert to dict for JSON response
		result = quiz.model_dump()
		# Convert datetime objects to ISO strings
		if result.get("date_taken"):
			result["date_taken"] = result["date_taken"].isoformat() if hasattr(result["date_taken"], "isoformat") else str(result["date_taken"])
		if result.get("date_completed"):
			result["date_completed"] = result["date_completed"].isoformat() if hasattr(result["date_completed"], "isoformat") else str(result["date_completed"])
		
		return jsonify(result), 201
		
	except Exception as e:
		logger.exception("Quiz generation failed")
		return jsonify({"error": str(e)}), 500


@app.route("/quiz/list", methods=["GET"])
def list_quizzes():
	"""
	List all quizzes for the authenticated user.
	
	Returns list of quiz metadata (id, title, score, status, dates).
	"""
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		user_id = request.args.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id query parameter"}), 400
	
	try:
		quizzes = quiz_module.list_quizzes(user_id)
		result = []
		for q in quizzes:
			item = q.model_dump()
			if item.get("date_taken"):
				item["date_taken"] = item["date_taken"].isoformat() if hasattr(item["date_taken"], "isoformat") else str(item["date_taken"])
			if item.get("date_completed"):
				item["date_completed"] = item["date_completed"].isoformat() if hasattr(item["date_completed"], "isoformat") else str(item["date_completed"])
			result.append(item)
		return jsonify(result), 200
	except Exception as e:
		logger.exception("Failed to list quizzes")
		return jsonify({"error": str(e)}), 500


@app.route("/quiz/<quiz_id>", methods=["GET"])
def get_quiz(quiz_id: str):
	"""
	Get a specific quiz by ID.
	
	Returns the full quiz with questions (and user responses if any).
	"""
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		user_id = request.args.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id query parameter"}), 400
	
	try:
		quiz = quiz_module.load_quiz(user_id, quiz_id)
		if not quiz:
			return jsonify({"error": "quiz not found"}), 404
		
		result = quiz.model_dump()
		if result.get("date_taken"):
			result["date_taken"] = result["date_taken"].isoformat() if hasattr(result["date_taken"], "isoformat") else str(result["date_taken"])
		if result.get("date_completed"):
			result["date_completed"] = result["date_completed"].isoformat() if hasattr(result["date_completed"], "isoformat") else str(result["date_completed"])
		
		return jsonify(result), 200
	except Exception as e:
		logger.exception("Failed to get quiz")
		return jsonify({"error": str(e)}), 500


@app.route("/quiz/<quiz_id>/answer", methods=["POST"])
def submit_quiz_answer(quiz_id: str):
	"""
	Submit an answer for a quiz question.
	
	JSON body: {
		"question_id": "q1",
		"user_answer": "A. The correct option",
		"time_taken_seconds": 30.5  # Optional
	}
	
	Returns whether the answer is correct, the correct answer, explanation, and updated score.
	"""
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		payload = request.get_json(force=True, silent=True) or {}
		user_id = payload.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id"}), 400
	
	payload = request.get_json(force=True, silent=True) or {}
	question_id = payload.get("question_id")
	user_answer = payload.get("user_answer")
	
	if not question_id or user_answer is None:
		return jsonify({"error": "missing question_id or user_answer"}), 400
	
	try:
		result = quiz_module.submit_quiz_answer(
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


@app.route("/quiz/<quiz_id>/complete", methods=["POST"])
def complete_quiz(quiz_id: str):
	"""
	Mark a quiz as completed.
	
	Returns the final quiz result with score.
	"""
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		payload = request.get_json(force=True, silent=True) or {}
		user_id = payload.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id"}), 400
	
	try:
		quiz = quiz_module.complete_quiz(user_id, quiz_id)
		result = quiz.model_dump()
		if result.get("date_taken"):
			result["date_taken"] = result["date_taken"].isoformat() if hasattr(result["date_taken"], "isoformat") else str(result["date_taken"])
		if result.get("date_completed"):
			result["date_completed"] = result["date_completed"].isoformat() if hasattr(result["date_completed"], "isoformat") else str(result["date_completed"])
		return jsonify(result), 200
	except ValueError as e:
		return jsonify({"error": str(e)}), 404
	except Exception as e:
		logger.exception("Failed to complete quiz")
		return jsonify({"error": str(e)}), 500


@app.route("/quiz/<quiz_id>", methods=["DELETE"])
def delete_quiz(quiz_id: str):
	"""
	Delete a quiz by ID.
	"""
	if not is_auth_disabled():
		auth_header = request.headers.get("Authorization")
		token = auth.extract_bearer_token(auth_header)
		if not token:
			return jsonify({"error": "missing Authorization Bearer token"}), 401
		claims = auth.verify_jwt(token)
		if not claims:
			return jsonify({"error": "invalid or expired token"}), 401
		user_id = claims.get("sub")
	else:
		user_id = request.args.get("user_id")
		if not user_id:
			return jsonify({"error": "missing user_id query parameter"}), 400
	
	try:
		deleted = quiz_module.delete_quiz(user_id, quiz_id)
		if deleted:
			return jsonify({"status": "deleted", "quiz_id": quiz_id}), 200
		else:
			return jsonify({"error": "quiz not found"}), 404
	except Exception as e:
		logger.exception("Failed to delete quiz")
		return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Simple dev server (for production use gunicorn/uwsgi)
    port = int(os.environ.get("BACKEND_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)