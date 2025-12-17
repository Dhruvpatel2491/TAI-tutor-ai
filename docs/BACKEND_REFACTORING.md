# Backend Refactoring Summary

## Overview

The backend has been restructured from a flat file layout to a modular architecture for better maintainability, readability, and scalability. This document explains the new layout, migration notes, and concrete setup/run instructions for developers.

## New Directory Structure

```md
backend/
├── __init__.py                    # Package init
├── config.py                      # Centralized configuration (NEW)
├── server_new.py                  # New Flask server entry point (NEW)
├── .env.example                   # Environment variable template (NEW)
│
├── modules/                       # Core business logic (NEW)
│   ├── __init__.py
│   ├── users.py                   # User authentication & management
│   ├── chat.py                    # Chat session management
│   ├── planner.py                 # Learning plan generation
│   ├── quiz.py                    # Quiz generation & evaluation
│   ├── codequest.py               # CodeQuest challenges & sessions
│   └── courses.py                 # Course file management
│
├── api/                           # Flask blueprints (NEW)
│   ├── __init__.py
│   ├── endpoints_users.py         # User & auth endpoints
│   ├── endpoints_chat.py          # Chat CRUD endpoints
│   ├── endpoints_planner.py       # Plan CRUD endpoints
│   ├── endpoints_quiz.py          # Quiz endpoints
│   └── endpoints_codequest.py     # CodeQuest endpoints
│
├── admin/                         # Admin panel (NEW)
│   ├── __init__.py
│   ├── admin.py                   # Admin helper functions
│   ├── admin_auth.py              # Admin authentication
│   ├── endpoints_auth.py          # Auth blueprint (/auth/*)
│   └── endpoints_admin.py         # Admin blueprint (/admin/*)
│
├── rag/                           # RAG/Vector store (NEW)
│   ├── __init__.py
│   └── vector_store_generator.py  # Document parsing, embedding, indexing
│
├── prompts/                       # Prompt templates (NEW)
│   ├── __init__.py
│   ├── chat_prompts.py            # Chat response prompts
│   ├── quiz_prompts.py            # Quiz generation prompts
│   ├── codequest_prompts.py       # CodeQuest prompts
│   └── planner_prompts.py         # Planning prompts
│
└── [OLD FILES - can be removed after migration]
    ├── server.py                  # Original server (DEPRECATED)
    ├── auth.py                    # -> modules/users.py
    ├── admin_auth.py              # -> admin/admin_auth.py
    ├── chat_manager.py            # -> modules/chat.py
    ├── planner.py                 # -> modules/planner.py
    ├── quiz.py                    # -> modules/quiz.py
    ├── codequest_manager.py       # -> modules/codequest.py
    ├── codequest_challenges.py    # -> prompts/codequest_prompts.py
    ├── llm_codequest.py           # Still used by modules/codequest.py
    ├── prompts.py                 # -> prompts/chat_prompts.py
    ├── vector_store_gen.py        # -> rag/vector_store_generator.py
    └── endpoints_admin.py         # -> admin/endpoints_admin.py
```

## Key Changes

### 1. Centralized Configuration (`config.py`)

All environment variables and configuration settings are now in one place:

- Directory paths (INDEX_DIR, DATA_DIR, etc.)
- Server settings (port, debug mode)
- Authentication settings (JWT config, auth disabled flag)
- LLM settings (Ollama model, temperature, etc.)
- Cache settings (enabled, max size, TTL)

### 2. Modular Architecture

- **modules/**: Contains pure business logic without Flask dependencies
- **api/**: Contains Flask blueprints that import from modules/
- **admin/**: Contains admin-specific logic and endpoints
- **prompts/**: Contains all prompt templates for LLM interactions
- **rag/**: Contains vector store and document processing logic

### 3. Blueprint Pattern

All API endpoints are now organized into Flask blueprints:

- `users_bp`: `/` prefix (auth status, user info)
- `chat_bp`: `/chats` prefix
- `planner_bp`: `/plans`, `/saved_plans` prefix
- `quiz_bp`: `/quiz` prefix
- `codequest_bp`: `/codequest` prefix
- `auth_bp`: `/auth` prefix
- `admin_bp`: `/admin` prefix

### 4. Core Endpoints in server_new.py / server_v2.py

The main server entrypoint exposes diagnostic and RAG endpoints. In this repo the active entrypoint is `backend/server_v2.py`. Equivalent endpoints (or similar) implemented by the server include:

- `GET /health` — health check and optional index validation
- `POST /rebuild` — force an index rebuild (accepts indexing overrides)
- `POST /query`, `POST /query_v2`, `POST /query_v3` — RAG query endpoints; `v2`/`v3` accept model/behavior overrides
- `GET /cache/stats` — response cache statistics
- `POST /cache/clear` — clear response cache
- `GET /_debug/env` — debug-only environment dump (dev only)

Note: prefer `server_v2.py` when starting the app during development. If a `server.py` exists in your branch it may be an older entrypoint; check for `server_v2.py` first.

## Migration & Developer Setup

1. **Update imports in your code** to use the new paths. Example:

```python
# Old
from auth import verify_jwt

# New
from modules.users import verify_jwt
```

1. **Set environment variables**. Copy the example and edit for your environment:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env to configure OLLAMA_* model names, MAIN_PROJECT_DIR, DISABLE_AUTH, etc.
```

1. **Create / activate a Python virtualenv and install deps**:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

1. **Start the backend (development)**

Prefer the `server_v2.py` entrypoint in this repo. From the repository root:

```bash
# from repo root
python backend/server_v2.py

# If your branch still has the older `server.py`, check it before use.
```

1. **Rebuilding the index**

Use the `/rebuild` endpoint (POST) or call the helper in `rag/vector_store_generator.py` with `force_rebuild=True`. Example request body to overwrite indexing config:

```json
{ "rebuild": true, "indexing": { "parser": "code", "chunk_size": 512 } }
```

1. **After verification (optional cleanup)**

Only remove legacy files once the new layout is verified and you have a working test run. A safe checklist:

1. Confirm `server_v2.py` starts and endpoints respond
1. Run the test suite (`pytest` in `backend_test/`)
1. Then remove deprecated files if desired (e.g., `server.py`, `auth.py`, `chat_manager.py`, `vector_store_gen.py`) — keep backups or a git branch.

## API Endpoint Summary

| Endpoint | Method | Description | Blueprint |
|----------|--------|-------------|-----------|
| `/health` | GET | Health check | server |
| `/rebuild` | POST | Rebuild index | server |
| `/query` | POST | Basic RAG query | server |
| `/query_v2` | POST | Query with model selection | server |
| `/query_v3` | POST | Enhanced query | server |
| `/cache/stats` | GET | Cache statistics | server |
| `/cache/clear` | POST | Clear cache | server |
| `/auth/register` | POST | Register user | auth_bp |
| `/auth/login` | POST | Login user | auth_bp |
| `/auth/status` | GET | Auth configuration | users_bp |
| `/auth/user` | GET | Current user info | users_bp |
| `/auth/user/stats` | GET | User statistics | users_bp |
| `/chats` | GET/POST | List/Create chats | chat_bp |
| `/chats/<id>` | GET/DELETE | Get/Delete chat | chat_bp |
| `/chats/<id>/messages` | POST | Add message | chat_bp |
| `/chats/<id>/archive` | POST | Archive chat | chat_bp |
| `/chats/<id>/title` | PUT | Update title | chat_bp |
| `/plans` | GET/POST | List/Create plans | planner_bp |
| `/plans/<id>` | GET | Get plan | planner_bp |
| `/saved_plans` | GET/POST | List/Save plans | planner_bp |
| `/saved_plans/update` | POST | Update saved plan | planner_bp |
| `/saved_plans/delete` | POST | Delete saved plan | planner_bp |
| `/quiz/generate` | POST | Generate quiz | quiz_bp |
| `/quiz/list` | GET | List quizzes | quiz_bp |
| `/quiz/<id>` | GET/DELETE | Get/Delete quiz | quiz_bp |
| `/quiz/<id>/answer` | POST | Submit answer | quiz_bp |
| `/quiz/<id>/complete` | POST | Complete quiz | quiz_bp |
| `/codequest/tracks` | GET | List tracks | codequest_bp |
| `/codequest/challenges` | GET | List challenges | codequest_bp |
| `/codequest/sessions` | GET/POST | List/Create sessions | codequest_bp |
| `/codequest/sessions/<id>` | GET | Get session | codequest_bp |
| `/codequest/sessions/<id>/submit` | POST | Submit solution | codequest_bp |
| `/codequest/sessions/<id>/finish` | POST | Finish session | codequest_bp |
| `/codequest/sessions/<id>/exit` | POST | Exit session | codequest_bp |
| `/codequest/sessions/<id>/navigate` | POST | Navigate session | codequest_bp |
| `/codequest/sessions/<id>/draft` | POST | Save draft | codequest_bp |
| `/admin/*` | Various | Admin endpoints | admin_bp |

## Testing & Validation

Quick validation steps for developers:

- Start the backend:

```bash
python backend/server_v2.py
```

- Run unit and integration tests:

```bash
cd backend_test
pytest -q
```

Notes:

- Tests may assume Ollama is available locally. If Ollama is not available set `MOCK_LLM_ECHO=1` in your environment to enable mock LLM responses.
- If tests fail due to environment differences (missing models, different ports), review `backend/.env.example` and `backend/config.py` for configuration.

## Where to look first (developer hotspots)

- `backend/server_v2.py` — New server entrypoint and endpoint wiring
- `backend/config.py` — Centralized configuration
- `backend/modules/` — Business logic (chat, users, planner, codequest, quiz)
- `backend/api/` — Flask blueprints and request handling
- `backend/rag/vector_store_generator.py` — Indexing, parsers, and ingestion

If you need a more detailed migration checklist for a release branch, create a short-lived branch and test the full flow (start server, rebuild index, run frontend against it).
