# TAI-tutor-ai

TAI-tutor-ai is a local, developer-focused AI tutoring platform that uses LlamaIndex + Ollama to run LLM workloads locally. It provides multimodal document ingestion, indexing, and a simple backend API to query the index and produce tutoring-style responses (hints, adaptive plans, practice tests).

This README documents how to run the project in development, explains key architecture pieces and features, and includes troubleshooting and contribution tips.

## Quick start (dev)

1. Create and activate a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start the backend (defaults to port 5000):

```bash
python backend/server.py
```

3. Start the frontend (from the project root):

```bash
cd frontend
# if first time
npm install
npm start
```

Notes:
- The backend will attempt to load `.env` automatically using `python-dotenv` if present.
- Ollama (local service) should be running for the LLM/embedding calls to work (default: `localhost:11434`). See "Ollama" below.

## Architecture & key files

- `backend/server.py` — Flask backend exposing `/health`, `/query`, `/query_v2`, and `/rebuild` endpoints. Constants at the top (e.g., `OLLAMA_LLM`, `OLLAMA_EMBED`) control default models and timeouts.
- `backend/llm_methods.py` — indexing and ingestion logic (parsers for PDFs, PPTX, notebooks, Python code, and other formats). Contains `get_or_create_index()` and document loaders.
- `index_store/` — persisted index and metadata. Expected files include `docstore.json` and `embeddings_meta.json`.
- `trial-data/` and `data/base-data/` — source documents used to build the index in development and for a larger corpus, respectively.
- `frontend/` — React app that communicates with the backend. Key components: `components/ChatbotInterface.js`, `components/PlannerPanel.js`.

## Features

- Multimodal ingestion: parsers handle `.pdf`, `.pptx`, `.ipynb`, `.py` and plain text. Indexing supports configurable chunk size/overlap and parser selection.
- Local LLM + embedding via Ollama: uses LlamaIndex wrapper for retrieval and query flows.
- Hint vs direct answer modes: prompt templates are designed to support both hint-first tutoring and direct answers (see `backend/llm_methods.py` and prompt hooks).
- Persisted index and incremental ingestion: `embeddings_meta.json` keeps track of which files were already embedded to avoid reprocessing unchanged files.

## Environment variables (common)

- `DISABLE_AUTH` — set to `true` to run the backend in dev mode without auth checks (NOT for production).
- `DEFAULT_DEV_USER` — dev user id used when `DISABLE_AUTH=true`.
- `MAIN_PROJECT_DIR` — project root used for saved plans and user_data. Defaults to the repo root.
- `OLLAMA_LLM`, `OLLAMA_EMBED` — model names for Ollama (local). Change these if you prefer different local models.

There is an `.env.example` in the repo root. Copy it to `.env` and update values as needed.

## Ollama (local model) notes

- This project expects Ollama to run locally (default host `localhost:11434`). If Ollama is not available, the backend will fail to make LLM/embedding calls. For CI or environments without Ollama, you can mock these calls in tests or add an adapter (see `backend/llm_adapters.py` suggestion in project copilot instructions).

## Rebuilding the index

The backend exposes a rebuild flow via the `/rebuild` route or the `get_index(force_rebuild=True, build_kwargs=...)` helper in `llm_methods.py`. When rebuilding, you can pass indexing overrides (parser, chunk size, etc.). The code will only remove and recreate the index directory when `force_rebuild` is explicit.

Example rebuild request body (JSON):

```json
{
	"rebuild": true,
	"indexing": {"parser": "code", "chunk_size": 512}
}
```

## Running tests

This repo includes a small pytest suite under `backend/test_server.py` and top-level `test/` tests. Typical dev flow:

1. Start backend: `python backend/server.py` (or set `BACKEND_PORT` env)
2. In another shell (with the same virtualenv) run:

```bash
pytest -q
```

Notes about tests:
- Tests assume Ollama is running or that LLM network calls are mocked. Use request mocking (e.g., `requests-mock`) or monkeypatch to run tests without Ollama.

## Troubleshooting

- If the backend fails to start due to missing packages, ensure `pip install -r requirements.txt` completed successfully.
- If you see connection errors to Ollama, confirm the Ollama daemon is running and listening on the expected port.
- If the index seems stale, use the rebuild API with `rebuild: true` to force re-indexing.

## Contributing & extensions

- When adding parsers or model adapters, follow project conventions: small deterministic helper functions in `backend/llm_methods.py`, update `embeddings_meta.json` via `save_embedding_metadata()` after adding embeddings, and write tests near `backend/test_server.py`.
- If you want to add cloud model fallbacks (OpenAI, etc.), add an adapter module `backend/llm_adapters.py` and keep the rest of the codebase using the adapter interface.

## Suggested next docs (optional)

- `backend/README.md` — backend-specific run, config, and advanced debug steps.
- Example `.env` geared for local development with safe defaults (if you want a clearer starting point than `.env.example`).

---

If you'd like, I can also: add a `backend/README.md` with troubleshooting steps, or create an explicit `.env` tailored for your environment. Which would you prefer next?

## Authentication (developer/demo)

The backend exposes simple register/login endpoints intended for local development and demos. These endpoints persist user records under `user_data/login_register/` and return a signed JWT used by other API endpoints (e.g., `/plans`, `/saved_plans`).

- POST /auth/register — JSON body: `{ "email": "user@example.com", "password": "..." }`. Returns `201` and `{"token": "<jwt>"}` on success. Returns `409` if the user already exists.
- POST /auth/login — JSON body: `{ "email": "user@example.com", "password": "..." }`. Returns `200` and `{"token": "<jwt>"}` on success, or `401` for invalid credentials.

Notes:
- This demo auth is file-backed and should NOT be used in production. Passwords are stored with PBKDF2-SHA256 and a random salt, but you should use a proper auth provider and secure storage for real deployments.
- The frontend will call these endpoints when `REACT_APP_BACKEND_URL` is set; otherwise it falls back to the local demo auth (stored in browser localStorage).
