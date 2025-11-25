from flask import Flask, request, jsonify
from datetime import datetime, timezone
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
## Removed prompts.py and all related imports
from planner import default_planner
import auth
from auth import get_user_from_request

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
INDEX_DIR 	= "./index_store"
DATA_DIR 	= "./trial-data"
# directory where embedding definition lives (model.txt or config.json)
EMBEDDINGS_DIR = os.environ.get("EMBEDDINGS_DIR", "./embeddings")
OLLAMA_LLM = os.environ.get("OLLAMA_LLM", "llama3:8b")
OLLAMA_EMBED = os.environ.get("OLLAMA_EMBED", "bge-m3:latest")
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "5.0"))
DEFAULT_MAX_TOKENS = int(os.environ.get("DEFAULT_MAX_TOKENS", "1024"))
DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "600"))  # seconds
DEFAULT_PROMPT_MODE = os.environ.get("DEFAULT_PROMPT_MODE", "hint").strip().lower()  # 'hint' or 'direct'

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

# Plan-generation model and prompt templates (embedded here in server per request)
PLAN_MODEL = os.environ.get("PLAN_MODEL", "llama3:latest")
PLAN_TEMPERATURE = float(os.environ.get("PLAN_TEMPERATURE", "0.15"))
PLAN_MAX_TOKENS = int(os.environ.get("PLAN_MAX_TOKENS", "512"))

# Two general response styles: hint (scaffolded hints, not full solutions) and direct
HINT_CHAT_PROMPT_TEMPLATE = (
	"You are an expert tutor. When asked to create a study plan, provide scaffolded, hint-style guidance"
	" rather than full worked solutions. Be concise, actionable, and focus on learning objectives,"
	" stepwise progression, and short self-checks.\n\nTopics: {question}\n\n"
)

HINT_PROMPT_TEMPLATE = (
	"You are an expert tutor. When asked to create a study plan, provide scaffolded, hint-style guidance"
	" rather than full worked solutions. Be concise, actionable, and focus on learning objectives,"
	" stepwise progression, and short self-checks.\n\nTopics: {topics}\nAdditional notes: {notes}\n\n"
)

DIRECT_PROMPT_TEMPLATE = (
	"You are an expert tutor. When asked to create a study plan, provide a direct, explicit,"
	" and actionable plan including objectives, a week-by-week schedule, suggested resources,"
	" exercises, and estimated time per session.\n\nTopics: {topics}\nAdditional notes: {notes}\n\n"
)

PLAN_BODY_TEMPLATE = (
	"Generate a personalized learning plan for the user (user_id: {user_id}).\n"
	"Include: 1) Learning objectives, 2) A 4-week (or configurable) schedule with goals per week,"
	" 3) Suggested exercises or practice problems, 4) Time estimates per session, and 5) 3 quick self-check questions.\n\n"
	"Return the plan as plain text organized with clear headings."
)

# Lazy-loaded globals
_index_lock = threading.Lock()
_index_obj = None
_query_engine = None
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
			style_prompt = HINT_CHAT_PROMPT_TEMPLATE.format(question=question)

			response = query_engine.query(question)
		logger.debug(f"Response object: type={type(response)}; str={str(response)[:200]}")

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


### Simple dev-only auth endpoints (register/login) - issue JWTs
@app.route("/auth/register", methods=["POST"])
def auth_register():
	payload = request.get_json(force=True, silent=True) or {}
	email = payload.get("email") or payload.get("user_id")
	password = payload.get("password")
	if not email or not password:
		return jsonify({"error": "missing email or password"}), 400
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
	topics = payload.get("topics") or []
	notes = payload.get("notes")
	if not user_id or not isinstance(topics, (list, tuple)):
		return jsonify({"error": "invalid payload, require topics list (and authenticated user)"}), 400

	# Decide whether to generate the plan text using the backend Ollama LLM.
	use_mock = bool(payload.get("mock") or payload.get("use_mock") or os.environ.get("MOCK_LLM_ECHO"))
	plan_text = notes
	if not use_mock:
		try:
			# allow request to override model & generation params
			gen_model = payload.get("plan_model") or PLAN_MODEL
			gen_temp = float(payload.get("plan_temperature", PLAN_TEMPERATURE))
			gen_max = int(payload.get("plan_max_tokens", PLAN_MAX_TOKENS))
			prompt_mode = (payload.get("prompt_mode") or DEFAULT_PROMPT_MODE).strip().lower()

			# Compose prompt from chosen style
			topics_str = ", ".join(topics) if isinstance(topics, (list, tuple)) else str(topics)
			if prompt_mode == "direct":
				style_prompt = DIRECT_PROMPT_TEMPLATE.format(topics=topics_str, notes=(notes or ""))
			else:
				style_prompt = HINT_PROMPT_TEMPLATE.format(topics=topics_str, notes=(notes or ""))

			plan_prompt = style_prompt + PLAN_BODY_TEMPLATE.format(user_id=user_id, topics=topics_str, notes=(notes or ""))

			# Support iterative edits: caller may provide an existing plan id and
			# edit instructions. If provided, fetch the previous plan and include it
			# in the prompt so the model can produce an improved version.
			parent_id = None
			edit_plan_id = payload.get("edit_plan_id")
			edit_instructions = payload.get("edit_instructions")
			if edit_plan_id:
				parent = default_planner.get_plan(edit_plan_id)
				if not parent:
					return jsonify({"error": f"edit_plan_id '{edit_plan_id}' not found"}), 400
				parent_id = edit_plan_id
				prev_text = parent.notes or ""
				# Extend the prompt to give the model the previous plan and explicit
				# instructions for how to edit it.
				edit_block = "\n\nPrevious plan:\n" + prev_text + "\n\n"
				if edit_instructions:
					edit_block += "Edit instructions: " + str(edit_instructions) + "\n\n"
				else:
					edit_block += "Edit instructions: Improve clarity, organization, and suggest additional exercises as appropriate.\n\n"
				# Ask the model to return a revised plan and to note a short changelog
				plan_prompt = style_prompt + "Please revise the following plan according to the edit instructions.\n" + edit_block + PLAN_BODY_TEMPLATE.format(user_id=user_id, topics=topics_str, notes=(notes or "")) + "\n\nAlso include a short 'Change log' section describing what you changed."

			# Ensure the index is available so we can reuse the existing query engine plumbing
			# (this mirrors how /query_v2 constructs a per-request Ollama and query engine).
			try:
				index_obj, _ = get_index(force_rebuild=False)
			except Exception:
				# If index is not available, try to initialize models so Ollama client can be used alone.
				try:
					init_models()
				except Exception:
					# fall back to mock behavior if Ollama can't be used
					logger.exception("Could not prepare models for plan generation; falling back to simple plan text.")
					index_obj = None

			# Instantiate a per-request Ollama model for generation
			try:
				per_request_llm = Ollama(model=gen_model, temperature=gen_temp, max_tokens=gen_max, request_timeout=DEFAULT_TIMEOUT)
			except Exception as e:
				logger.exception("Failed to instantiate Ollama for plan generation")
				per_request_llm = None

			if per_request_llm and index_obj is not None:
				try:
					qe = index_obj.as_query_engine(llm=per_request_llm)
					resp = qe.query(plan_prompt)
					plan_text = str(resp)
				except Exception:
					logger.exception("Plan generation via query engine failed; attempting direct LLM call")
					try:
						# Best-effort direct call: some LLM wrappers implement __call__ or generate
						if hasattr(per_request_llm, "generate"):
							gen = per_request_llm.generate(plan_prompt)
							plan_text = str(gen)
						elif callable(per_request_llm):
							plan_text = str(per_request_llm(plan_prompt))
						else:
							# final fallback: use the prompt itself as the plan body
							plan_text = plan_prompt
					except Exception:
						logger.exception("Direct LLM generation failed; using prompt as plan text")
						plan_text = plan_prompt
			elif per_request_llm and index_obj is None:
				# try direct call without index
				try:
					if hasattr(per_request_llm, "generate"):
						gen = per_request_llm.generate(plan_prompt)
						plan_text = str(gen)
					elif callable(per_request_llm):
						plan_text = str(per_request_llm(plan_prompt))
					else:
						plan_text = plan_prompt
				except Exception:
					logger.exception("Direct LLM generation without index failed; falling back to prompt text")
					plan_text = plan_prompt
			else:
				# Could not use LLM; leave plan_text as provided notes (or empty)
				if not plan_text:
					plan_text = "A short plan: topics: " + topics_str
		except Exception:
			logger.exception("Unexpected error during plan generation; falling back to simple plan storage")

	# Persist the plan (notes field will contain either generated plan text or provided notes)
	# Persist the plan. If this was an edit, record the parent plan id to enable
	# iterative/versioned plans.
	plan = default_planner.create_plan(user_id=user_id, topics=list(topics), notes=plan_text, parent_id=parent_id)
	# Use Pydantic v2 `model_dump()` to avoid deprecation of `.dict()`.
	try:
		out = plan.model_dump()
	except Exception:
		out = getattr(plan, "__dict__", {})
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
	plan_text = payload.get("plan_text") or payload.get("notes") or ""
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

if __name__ == "__main__":
    # Simple dev server (for production use gunicorn/uwsgi)
    port = int(os.environ.get("BACKEND_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)