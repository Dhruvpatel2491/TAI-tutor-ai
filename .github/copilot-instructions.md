<!-- Condensed copilot instructions for TAI-tutor-ai -->
# TAI-tutor-ai — Copilot instructions (concise)

This short guide highlights the essential knowledge AI coding agents need to be productive in this repo.

1) Big picture
- Backend: Flask app at `backend/server.py` — exposes `/health`, `/query`, `/query_v2`, `/rebuild`. It orchestrates LlamaIndex + Ollama for retrieval + LLM answers.
- Ingestion & index: `backend/vector_store_gen.py` builds the index (parsers for `.pdf`, `.pptx`, `.ipynb`, `.py` and tree-sitter code support). Index files live in `index_store/` (`docstore.json`, `embeddings_meta.json`).
- Frontend: `frontend/` React app communicates with backend; local Ollama is assumed for some flows.

2) Run & test (quick commands)
- Start backend (dev): `cd backend && python server.py` (port via `BACKEND_PORT`).
- Start frontend: `cd frontend && npm install && npm start`.
- Tests: start backend, then `pytest backend/test_server.py` to exercise `/query`, `/query_v2`, and `/rebuild` flows.

3) Key edit contracts / hotspots
- Change LLM/embedding defaults in `backend/server.py` (constants `OLLAMA_LLM`, `OLLAMA_EMBED`, `DEFAULT_*`). Prefer env vars for overrides.
- Modify index behavior in `get_or_create_index()` inside `backend/vector_store_gen.py`. Parser options are passed via the `indexing` dict (e.g., `parser`, `chunk_size`, `chunk_overlap`).
- Index persistence: update `embeddings_meta.json` using `save_embedding_metadata()` when adding embeddings. `server.get_index(force_rebuild=True, build_kwargs=...)` triggers destructive rebuilds only when explicit.

4) Conventions & patterns (follow exactly)
- Parsers: add short deterministic helpers inside `vector_store_gen.py` (e.g., `extract_text_from_pdf`, `extract_code_with_ast`). Keep I/O minimal and deterministic.
- Prompting: prefer a "hint mode" (scaffolded guidance) and a "direct answer" mode. Centralize templates (suggested new file: `backend/prompts.py`) and wire into `server.py` when calling `as_query_engine`.
- Tree-sitter: `vector_store_gen.py` may build `build/my-languages.so` from vendor grammars — this step can be slow; only add grammars via the vendor workflow.

5) Integrations & dependencies to be mindful of
- Ollama (local) — required for default LLM calls (localhost:11434). If adding cloud fallbacks, implement a `backend/llm_adapters.py` adapter interface and update tests.
- Heavy packages in `requirements.txt`: `llama-index`, `ollama` client, `PyMuPDF`, `python-pptx`, `tree_sitter`, `nbformat`.

6) Small example requests
- Rebuild index (POST body example):
  `{"question":"List classes","rebuild":true,"indexing":{"parser":"code","chunk_size":512}}`
- Query with model override:
  `{"question":"Summarize","model":"llama3-chatqa:latest","temperature":0.1}`

7) Safe, low-risk changes
- Prefer incremental changes: add small modules (e.g., `backend/prompts.py`, `backend/llm_adapters.py`), wire them into `server.py`, and add unit tests under `backend/`.
- When modifying index persistence or embeddings, include a test that adds a file to `trial-data/` and verifies `embeddings_meta.json` updates.

8) Where to look first (files to open)
- `backend/server.py` — API entrypoints, model constants, query engine wiring.
- `backend/vector_store_gen.py` — ingestion/parsers, `get_or_create_index()`.
- `index_store/` — persisted index artifacts (`docstore.json`, `embeddings_meta.json`).
- `frontend/` — React UI and services that call the backend.

If you'd like, I can now: add `backend/prompts.py` and migrate one prompt (hint + direct), or produce a short data-flow diagram. Which would you prefer? Please review and tell me any missing specifics to include.
