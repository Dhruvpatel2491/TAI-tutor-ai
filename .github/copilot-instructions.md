<!-- Copilot instructions for TAI-tutor-ai (concise, actionable) -->
# TAI-tutor-ai — Copilot instructions

This file gives targeted, repo-specific guidance so an AI coding agent can be productive quickly.

- Big picture
  - Backend: Flask app at `backend/server.py`. Key endpoints: `/health`, `/query`, `/query_v2`, `/rebuild`.
    The server wires LlamaIndex (index/query) + local Ollama LLMs for responses.
  - Indexing/ingestion: `backend/vector_store_gen.py` builds and persists the vector index in `vector_index_store/` (`docstore.json`, `embeddings_meta.json`, `vector_index_store.json`). Parsers for `.pdf`, `.pptx`, `.ipynb`, `.py` live here; tree-sitter support exists for code parsing.
  - Frontend: React app in `frontend/` calls the backend HTTP APIs. UI components live under `frontend/src/components` and services under `frontend/src/services`.

- Quick run & test (concrete)
  - Backend (dev): from repo root: `cd backend && python server.py` (port can be overridden with env var `BACKEND_PORT`).
  - Frontend: `cd frontend && npm install && npm start` (uses `frontend/src/config.js` for base URL overrides).
  - Tests: backend tests are under `backend_test/` and can be run after starting the backend: `pytest backend_test/`.

- Edit contracts & hotspots (where to change behavior)
  - LLM / embedding defaults: edit constants in `backend/server.py` (e.g., `OLLAMA_LLM`, `OLLAMA_EMBED`, `DEFAULT_*`). Prefer env var overrides.
  - Index build: change parsing/chunking in `backend/vector_store_gen.py` (see `get_or_create_index()` and `indexing` dict parameters: `parser`, `chunk_size`, `chunk_overlap`).
  - Embedding metadata: persist updates using `save_embedding_metadata()`; the index store files in `vector_index_store/` are authoritative for persisted state.

- Conventions & patterns to follow
  - Parsers: keep I/O deterministic and local to `vector_store_gen.py`; add small helper functions (e.g., `extract_text_from_pdf`) in the same file.
  - Prompts: the repo prefers two modes — a "hint" (scaffolded) mode and a "direct answer" mode. There is a `backend/prompts.py` entrypoint to centralize templates; wire new prompts there and invoke from `server.py`.
  - Tree-sitter: adding languages requires building `build/my-languages.so` via the vendor workflow — avoid ad-hoc language additions.

- Integrations & dependencies
  - Local Ollama (default): expected at localhost:11434. If implementing cloud fallbacks, add an adapter (suggested `backend/llm_adapters.py`) and update unit tests.
  - Heavy deps in `requirements.txt`: `llama-index`, `ollama`, `PyMuPDF`, `python-pptx`, `tree_sitter`, `nbformat`. Use a virtualenv or pinned environment.

- Concrete examples
  - Rebuild request body example: {"question":"List classes","rebuild":true,"indexing":{"parser":"code","chunk_size":512}}
  - Query with model override example: {"question":"Summarize","model":"llama3-chatqa:latest","temperature":0.1}

- Where to look first (priority)
  - `backend/server.py` — API wiring, model constants, query engine calls.
  - `backend/vector_store_gen.py` — ingestion, parsers, index creation.
  - `vector_index_store/` — persisted index artifacts to inspect after a rebuild.
  - `frontend/src/services/botService.js` and `frontend/src/components/ChatbotInterface.js` — show how the frontend calls the backend and shapes requests.

