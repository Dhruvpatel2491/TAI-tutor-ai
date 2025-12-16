# TAI-tutor-ai — Documentation Index

This `docs/` folder contains developer-focused docs for the TAI-tutor-ai project. Use this landing page as a quick reference for running the frontend and backend, and for a concise list of features.

## Quick links

- `BACKEND_REFACTORING.md` — backend structure, migration notes, and developer setup
- `CHAT_HISTORY.md` — chat history design, API examples, frontend integration

## Quick start — Backend (developer)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

1. Configure environment variables:

```bash
cp backend/.env.example backend/.env
# edit backend/.env to set OLLAMA_* model names, MAIN_PROJECT_DIR, DISABLE_AUTH, etc.
```

1. Start the backend (development):

```bash
python backend/server_v2.py
```

Notes:

- `backend/server_v2.py` is the primary development entrypoint in this repo. If you see a `server.py` in another branch, prefer `server_v2.py` here.
- Ollama (local LLM) is expected at `localhost:11434`. If you don't have Ollama for local testing, set `MOCK_LLM_ECHO=1` in your environment to use mock responses.

## Quick start — Frontend (developer)

1. From repo root, enter the frontend folder and install node deps:

```bash
cd frontend
npm install
```

1. Start the development server (hot reload):

```bash
npm start
```

1. Configure backend URL if needed in `frontend/src/config.js` (defaults to `http://localhost:5000`).

Notes:

- `package.json` uses `react-scripts` and a `start` script that sets `CHOKIDAR_USEPOLLING` for stable file watching in some environments.

## Features (consolidated)

- Local RAG (retrieval-augmented generation) using LlamaIndex + Ollama embeddings/LMs
- Multimodal ingestion: `.pdf`, `.pptx`, `.ipynb`, `.py` and plain text parsers
- Persisted vector index in `backend/vector_index_store/` with incremental/update-aware ingestion
- Chat sessions persisted per-user under `user_data/chats/<user>/` with CRUD + archive
- Hint vs Direct Answer modes via prompt templates
- CodeQuest: interactive coding challenges and per-user sessions (no server-side code execution)
- Quiz generation and evaluation endpoints
- Planner (learning plan) generation and saved plans
- Admin endpoints and a small admin auth layer
- Dev-friendly mock mode for LLM (`MOCK_LLM_ECHO=1`) for tests/CI

## Tests

Run backend tests from repo root:

```bash
cd backend_test
pytest -q
```

If tests rely on Ollama and you don't have it, set `MOCK_LLM_ECHO=1` to avoid external LLM calls.

## Where to find things

- Backend entrypoints and config: `backend/` (see `server_v2.py`, `config.py`)
- Backend business logic: `backend/modules/`
- API blueprints: `backend/api/`
- Vector/index logic: `backend/rag/`
- Frontend: `frontend/` (React app)
- Persisted state: `user_data/` and `backend/vector_index_store/`

If you'd like, I can also generate a short `backend/README.md` or expand any of the sections above into a step-by-step troubleshooting guide.
