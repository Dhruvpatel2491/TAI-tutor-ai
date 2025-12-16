"""
Configuration module for TAI Tutor AI Backend.

This module centralizes all environment variables and configuration settings.
It loads values from environment variables with sensible defaults.
"""

import os
import logging
from pathlib import Path
from typing import Optional

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    
    # Look for .env in backend directory first, then project root
    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent
    
    # Check both locations
    for env_path in [backend_dir / '.env', project_root / '.env']:
        if env_path.exists():
            load_dotenv(dotenv_path=str(env_path))
            break
except ImportError:
    pass  # python-dotenv not installed, skip loading .env file

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backend.config")


# =============================================================================
# Directory Paths
# =============================================================================

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
MAIN_PROJECT_DIR = os.environ.get("MAIN_PROJECT_DIR", str(PROJECT_ROOT))

# Data directories
INDEX_DIR = os.environ.get("INDEX_DIR", "./vector_index_store")
DATA_DIR = os.environ.get("DATA_DIR", "./course-data")
EMBEDDINGS_DIR = os.environ.get("EMBEDDINGS_DIR", "./embeddings")
USER_DATA_DIR = Path(MAIN_PROJECT_DIR) / "user_data"

# Chat storage
CHAT_STORE_DIR = os.environ.get(
    "CHAT_STORE_DIR",
    str(USER_DATA_DIR / "chats")
)

# CodeQuest storage
CODEQUEST_STORE_DIR = os.environ.get(
    "CODEQUEST_STORE_DIR",
    str(USER_DATA_DIR / "codequest")
)

# Quiz storage
QUIZ_STORE_DIR = str(USER_DATA_DIR / "quiz")

# Saved plans directory
SAVED_PLANS_DIR = str(USER_DATA_DIR / "saved_plans")

# Admin credentials path
ADMIN_CREDS_PATH = USER_DATA_DIR / "admin" / "credentials.json"
ADMIN_CREDENTIALS_FILE = str(ADMIN_CREDS_PATH)

# Admin defaults (simple password-based authentication)
# Set ADMIN_PASSWORD environment variable to override default
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


# =============================================================================
# Server Configuration
# =============================================================================

BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "5000"))
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "true").lower() in ("true", "1", "yes", "on")


# =============================================================================
# Authentication Configuration
# =============================================================================

def is_auth_disabled() -> bool:
    """Return True only when DISABLE_AUTH is explicitly set to a truthy value."""
    val = os.environ.get("DISABLE_AUTH", "")
    try:
        return str(val).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return False


AUTH_DISABLED = is_auth_disabled()
DEFAULT_DEV_USER = os.environ.get("DEFAULT_DEV_USER", "dev")

# JWT Configuration
JWT_SECRET = os.environ.get("BACKEND_JWT_SECRET", "tai")
JWT_ALGORITHM = os.environ.get("BACKEND_JWT_ALGORITHM", "HS256")
JWT_EXP_SECONDS = int(os.environ.get("BACKEND_JWT_EXP", "3600"))


# =============================================================================
# LLM Configuration (Ollama)
# =============================================================================

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM = os.environ.get("OLLAMA_LLM", "llama3:8b")
OLLAMA_EMBED = os.environ.get("OLLAMA_EMBED", "bge-m3:latest")

# Generation defaults
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.5"))
DEFAULT_MAX_TOKENS = int(os.environ.get("DEFAULT_MAX_TOKENS", "1024"))
DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "600"))
DEFAULT_PROMPT_MODE = os.environ.get("DEFAULT_PROMPT_MODE", "direct").strip().lower()


# =============================================================================
# Planner Configuration
# =============================================================================

PLAN_MODEL = os.environ.get("PLAN_MODEL", "gpt-oss:latest")
PLAN_TEMPERATURE = float(os.environ.get("PLAN_TEMPERATURE", "0.15"))
PLAN_MAX_TOKENS = int(os.environ.get("PLAN_MAX_TOKENS", "1024"))
PLANNER_STORE = os.environ.get("PLANNER_STORE")


# =============================================================================
# Quiz Configuration
# =============================================================================

QUIZ_MODEL = os.environ.get("QUIZ_MODEL", OLLAMA_LLM)
QUIZ_TEMPERATURE = float(os.environ.get("QUIZ_TEMPERATURE", "0.3"))
QUIZ_MAX_TOKENS = int(os.environ.get("QUIZ_MAX_TOKENS", "2048"))


# =============================================================================
# CodeQuest Configuration
# =============================================================================

CODEQUEST_GENERATOR_MODEL = os.environ.get("CODEQUEST_GENERATOR_MODEL", "codellama:34b")
CODEQUEST_SUBMIT_MODEL = os.environ.get("CODEQUEST_SUBMIT_MODEL", "gpt-oss:20b")
CODEQUEST_LLM_ENABLED = os.environ.get("CODEQUEST_LLM_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on"
)


# =============================================================================
# Cache Configuration
# =============================================================================

CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() in ("true", "1", "yes", "on")
CACHE_MAX_SIZE = int(os.environ.get("CACHE_MAX_SIZE", "100"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))


# =============================================================================
# Index Rebuild Configuration
# =============================================================================

REBUILD_COOLDOWN_SECONDS = int(os.environ.get("REBUILD_COOLDOWN_SECONDS", str(1 * 60)))
EXPECTED_PERSIST_FILES = ["docstore.json"]
EMBEDDING_META_FILENAME = "embeddings_meta.json"

# Rebuild lock file path (used to persist rebuild state across restarts)
REBUILD_LOCK_FILE = Path(INDEX_DIR) / ".rebuild_lock.json"


# =============================================================================
# Helper Functions
# =============================================================================

def get_index_dir() -> str:
    """Get absolute path to index directory."""
    return os.path.abspath(INDEX_DIR)


def get_data_dir() -> str:
    """Get absolute path to data directory."""
    return os.path.abspath(DATA_DIR)


def read_embedding_model_from_folder(embeddings_dir: Optional[str] = None, fallback: str = "qwen3-embedding:8b") -> str:
    """Read embedding model name from embeddings folder configuration."""
    import json
    
    embeddings_dir = embeddings_dir or EMBEDDINGS_DIR
    
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


def log_config():
    """Log current configuration (for debugging)."""
    logger.info("=== Backend Configuration ===")
    logger.info(f"BACKEND_PORT: {BACKEND_PORT}")
    logger.info(f"AUTH_DISABLED: {AUTH_DISABLED}")
    logger.info(f"OLLAMA_LLM: {OLLAMA_LLM}")
    logger.info(f"OLLAMA_EMBED: {OLLAMA_EMBED}")
    logger.info(f"INDEX_DIR: {INDEX_DIR}")
    logger.info(f"DATA_DIR: {DATA_DIR}")
    logger.info(f"CACHE_ENABLED: {CACHE_ENABLED}")
    logger.info("=============================")
