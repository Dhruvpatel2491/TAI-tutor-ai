<!-- .github/copilot-instructions.md: guidance for AI coding agents working on this repo -->
# TAI-tutor-ai — Copilot instructions (brief)

This file gives targeted, actionable guidance to AI coding agents editing this repository. Stick to the project conventions below and reference the listed files when making changes.

1) Big picture (what you must know)
- Backend is a Flask service in `backend/server.py` that wraps LlamaIndex + Ollama. It exposes `/health`, `/query`, `/query_v2`, and `/rebuild`.
- Indexing and ingestion logic lives in `backend/vector_store_gen.py` (multimodal parsers for .pdf/.pptx/.ipynb/.py and tree-sitter code handling).
- Persisted index and metadata are under `index_store/`. The code expects `docstore.json` and maintains `embeddings_meta.json` to track already-embedded files.
- Source documents live in `trial-data/` (dev) and `data/base-data/` (larger corpus).

Project goals & alignment
- Objective: this project is a personalized AI tutoring platform that guides students with hints, adaptive plans, practice tests, and multimodal support (text, code, audio, video, images). All changes should aim to preserve or advance this objective.
- When implementing features, map them to existing files: content ingestion & parsing -> `backend/vector_store_gen.py`; indexing/retrieval -> `index_store/` and `backend/server.py` query endpoints; frontend UX -> `frontend/` components.
- Do not replace the local Ollama/LlamaIndex approach without a clear migration plan; instead, add adapters (e.g., wrappers that allow switching between Ollama and cloud models like OpenAI) and document them.

2) Runtime & dev commands (how developers run things)
- Start backend dev server (non-prod):
  - cd into `backend` and run `python server.py` (defaults to port 5000; uses env var `BACKEND_PORT`).
  - For production, use Gunicorn (listed in `requirements.txt`).
- Frontend: `cd frontend && npm install && npm start` (frontend README documents Ollama assumptions).
- Ollama must be running locally (default `localhost:11434`) for LLM calls to succeed. Model names are configured in `server.py` constants `OLLAMA_LLM` and `OLLAMA_EMBED`.

3) Design priorities for feature work
- Tutoring-first responses: prefer guidance/hints over direct answers. When modifying query handlers or prompt templates, ensure any answer-generation path supports a "hint mode" and a strict "direct answer" mode. Look for where prompts are passed into `as_query_engine` and add template hooks.
- Multimodal ingestion: `vector_store_gen.py` already parses PDFs, PPTX, notebooks, and code. Add audio (Whisper) and image (OpenCV / image captioning) preprocessors that emit text/metadata documents for the index. Keep extractors deterministic and testable.
- Adaptive plans & practice tests: implement plan-generation as a separate service layer (e.g., `backend/planner.py`) that consumes user history (not currently present) and the index. Store plans and feedback in a DB (see Integration notes below).
- Safe interactions & guardrails: prefer schema validation with Pydantic (already a dependency) for request bodies and consider integrating a moderation pipeline. If using third-party guardrails (NeMo), add it behind a clear feature flag and document it.

3) Key edit-contracts and where to change behavior
- To change default LLM/embedding models or timeouts, edit constants at the top of `backend/server.py` (OLLAMA_LLM, OLLAMA_EMBED, DEFAULT_*). Prefer adding env var hooks if committing to config.
- Index construction and parser behavior: modify `get_or_create_index()` in `backend/vector_store_gen.py`. Parser selection happens via the `indexing` dict (keys: `parser`, `chunk_size`, `chunk_overlap`, `separator`, `include_metadata`). Example: the tests POST `{"rebuild":true, "indexing":{"parser":"code","chunk_size":512}}`.
- Per-request retrieval overrides are passed in the request JSON `retrieval` object and attempted against `index_obj.as_query_engine(..., **retrieval)` in `server.py`. Be defensive: code already falls back if `as_query_engine` rejects kwargs.

4) Implementation pointers & concrete examples
- Add audio support: write a new helper `extract_audio_transcript(path)` in `vector_store_gen.py` that calls Whisper, returns text and metadata, and is added to `load_multimodal_documents()`.
- Add image support: add `extract_image_caption(path)` (OpenCV + optional vision model) and include captions as Document(text=caption, metadata={...}).
- Prompt templates: centralize prompt templates in `backend/prompts.py` and reference them from `server.py` when building `as_query_engine` kwargs. Provide a "hint" template and a "direct" template.
- User auth & feedback storage: there is no auth or DB yet. If implementing, add `backend/auth.py` and `backend/db.py` and prefer JWT-based flows for API calls. For feedback, add a lightweight Mongo/Postgres integration and store feedback records with fields: user_id, timestamp, question, answer, rating, notes.
- Tests: extend `backend/test_server.py` with mocks for Ollama (use `requests-mock` or monkeypatch) so CI can run without a local Ollama instance.

4) Important project conventions and patterns (do exactly this)
- When adding or modifying parsers, follow existing pattern: short, deterministic helper functions in `vector_store_gen.py` (e.g., `extract_text_from_pdf`, `extract_code_with_ast`). Keep I/O side-effects minimal and log clearly.
- Index persistence: the repo expects `index_store/` to contain `docstore.json`. Use `save_embedding_metadata()` to update `embeddings_meta.json` after adding embeddings.
- Respect the rebuild flow: `server.get_index(force_rebuild=True, build_kwargs=...)` will remove and recreate the directory. Avoid silent destructive changes—log and only remove when `force_rebuild` is explicit.

5) Integration & external dependencies to be mindful of (project-aligned)
- Ollama (local service) — required in current setup. For cloud model fallbacks (OpenAI, PaLM), introduce an adapter module `backend/llm_adapters.py` with a consistent interface used by `server.py` and tests.
- NeMo Guardrails / moderation: integrate behind a feature flag; prefer Pydantic + keyword filters until a guardrails provider is available for CI.- Add audio support: write a new helper `extract_audio_transcript(path)` in `vector_store_gen.py` that calls Whisper, returns text and metadata, and is added to `load_multimodal_documents()`.


5) Tests & verification
- There is a small pytest suite `backend/test_server.py` which assumes the backend is already running on port 5000. Typical dev test flow:
  1. Start backend: `python backend/server.py` (or set BACKEND_PORT env)
  2. In another shell run: `pytest backend/test_server.py`.
- Tests exercise `/query`, `/query_v2`, and `/rebuild` (including rebuild with `indexing` override).

6) Integration & external dependencies to be mindful of
- Ollama (local service) — required. Model names must match installed models. Frontend also talks to local Ollama in its README; backend uses Ollama via llama-index + the `ollama` client.
- Tree-sitter: `vector_store_gen.py` builds `build/my-languages.so` from vendor grammars if missing. This can be slow and requires the vendor grammar checkouts (see code). If adding languages, add vendor repos accordingly.
- Heavy dependencies listed in `requirements.txt` (llama-index and related ollama packages, PyMuPDF, python-pptx, tree_sitter, nbformat). Pin versions rather than broad ranges when changing.

6) When to propose architecture changes
- Small features (new extractors, prompt templates, a planner module): implement as new files/modules and wire them into `server.py` and `vector_store_gen.py` with tests.

7) Small examples you can use/emit in PRs
- Rebuild index (code example request body):
  {
    "question": "List classes",
    "rebuild": true,
    "indexing": {"parser": "code", "chunk_size": 512}
  }
- Query v2 with model override:
  {"question": "Summarize", "model": "llama3-chatqa:latest", "temperature": 0.1}

8) When editing, prefer low-risk incremental changes
- Add unit tests or small integration tests in `backend/` near `test_server.py`. Tests should assume Ollama is running or mock network calls.
- When changing index persistence or embedding logic, update `embeddings_meta.json` flow and add a test that exercises adding a new file to `trial-data/`.

Final note
- Keep the tutoring objective front-and-center: prefer hinting, scaffolding, and multimodal enrichment over rote answers. If you add a feature that changes UX or data retention, call it out in the PR description and include tests or a migration plan.

If you'd like, I can now (pick one):
- add a small `backend/prompts.py` and migrate one prompt into it (hint + direct templates), or

Please tell me which next step you prefer or any section you'd like expanded.

If anything above is unclear or you'd like me to include more examples (sample request/response pairs or a short data-flow ASCII diagram), tell me which section to expand and I will iterate.
