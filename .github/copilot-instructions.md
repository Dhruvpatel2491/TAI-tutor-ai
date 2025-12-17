<!-- Copilot instructions for TAI-tutor-ai (concise, actionable) -->
# TAI-tutor-ai — Copilot instructions

Purpose: give an AI coding agent the minimal, targeted knowledge to be productive here.

Big picture
- Backend: Flask app at [backend/server.py](../backend/server.py). Key APIs: `/health`, `/query`, `/query_v2`, `/rebuild`. It composes LlamaIndex for retrieval + Ollama local LLMs for responses.
- Indexing: [backend/vector_store_gen.py](../backend/vector_store_gen.py) creates a persisted vector index in `vector_index_store/` (files: `docstore.json`, `embeddings_meta.json`, `index_store.json`). Parsers for PDFs, PPTX, notebooks and code live in this file.
- Frontend: React app in `frontend/` calls the backend. UI components live under `frontend/src/components`; calls/logic in `frontend/src/services` and pages under `frontend/src/pages`.

State & persistence hotspots
- Chat sessions: JSON files in `user_data/chats/<user>/` — managed by [backend/chat_manager.py](../backend/chat_manager.py). This module is authoritative for chat CRUD and uses atomic write patterns (temp file + replace).
- Vector index: `vector_index_store/` is the single source of truth for persisted embeddings/index artifacts.
- CodeQuest: challenge/session data persisted under `user_data/codequest/`; back-end logic in [backend/codequest_manager.py](../backend/codequest_manager.py) and LLM helpers in [backend/llm_codequest.py](../backend/llm_codequest.py). Note: CodeQuest does NOT execute user code server-side.

Quick run & test
- Start backend (dev): from repo root: `cd backend && python server.py` (use `BACKEND_PORT` env var to override).
- Frontend (dev): `cd frontend && npm install && npm start` (base URL config: `frontend/src/config.js`).
- Tests: backend tests in `backend_test/`. Run them after starting the backend: `pytest backend_test/`.

Edit hotspots & where to change behavior
- LLM/embedding defaults and model selection: edit constants in [backend/server.py](../backend/server.py) (e.g., `OLLAMA_LLM`, `OLLAMA_EMBED`). Prefer env var overrides.
- Indexing/parsing behavior: modify `get_or_create_index()` and the `indexing` config in [backend/vector_store_gen.py](../backend/vector_store_gen.py) (`parser`, `chunk_size`, `chunk_overlap`).
- Chat persistence: modify [backend/chat_manager.py](../backend/chat_manager.py). Preserve atomic write semantics when changing serialization.
- Prompts: centralized in [backend/prompts.py](../backend/prompts.py). Add templates here and call them from `server.py`.

Conventions & project-specific patterns
- Two response modes: "hint" (scaffolded) vs "direct answer" — prompts and handlers reflect this split.
- Parsers should be deterministic and keep I/O local to [backend/vector_store_gen.py](../backend/vector_store_gen.py).
- Avoid adding ad-hoc tree-sitter language binaries; follow the vendor build flow for `build/my-languages.so`.
- CodeQuest intentionally avoids running user code; do not add execution or test-case leakage to the backend.

Integrations to be aware of
- Ollama local service (default): expected at `localhost:11434`. If adding cloud LLM fallbacks, isolate them behind an adapter (suggested [backend/llm_adapters.py](../backend/llm_adapters.py)).
- Key Python deps are in `requirements.txt` (e.g., `llama-index`, `ollama`, `PyMuPDF`, `python-pptx`, `tree_sitter`, `nbformat`). Use a virtualenv.

Where to look first (priority)
- [backend/server.py](../backend/server.py) — API wiring, model constants, and query engine invocation.
- [backend/vector_store_gen.py](../backend/vector_store_gen.py) — ingestion and parser implementations.
- `vector_index_store/` — inspect persisted index artifacts after a rebuild.
- [backend/chat_manager.py](../backend/chat_manager.py) — chat session lifecycle and file layout.
- `frontend/src/services` and `frontend/src/components` — client calls and chat UI patterns.

Examples (useful request payloads)
- Rebuild index: {"question":"List classes","rebuild":true,"indexing":{"parser":"code","chunk_size":512}}
- Query with model override: {"question":"Summarize","model":"llama3-chatqa:latest","temperature":0.1}

If anything is unclear or you'd like this expanded into contributor onboarding steps, tell me which area to expand first (backend run/debug, index rebuilds, or CodeQuest flow).

