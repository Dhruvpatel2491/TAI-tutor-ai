"""
Index Manager for TAI Tutor AI.

This module handles all vector index management including:
- Lazy loading and caching of VectorStoreIndex
- Thread-safe index access with locking
- Force rebuild functionality
- Rebuild lock file management for cooldown periods
- Model initialization for embeddings and LLM

The index manager is responsible for:
1. Loading existing index from storage
2. Creating new index from documents when needed
3. Incremental updates when new files are detected
4. Persisting rebuild state across server restarts
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Import configuration with fallback for running as script
try:
    from config import (
        INDEX_DIR,
        DATA_DIR,
        EMBEDDINGS_DIR,
        OLLAMA_LLM,
        OLLAMA_EMBED,
        DEFAULT_TEMPERATURE,
        DEFAULT_MAX_TOKENS,
        DEFAULT_TIMEOUT,
        REBUILD_COOLDOWN_SECONDS,
        REBUILD_LOCK_FILE,
    )
except ImportError:
    from config import (
        INDEX_DIR,
        DATA_DIR,
        EMBEDDINGS_DIR,
        OLLAMA_LLM,
        OLLAMA_EMBED,
        DEFAULT_TEMPERATURE,
        DEFAULT_MAX_TOKENS,
        DEFAULT_TIMEOUT,
        REBUILD_COOLDOWN_SECONDS,
        REBUILD_LOCK_FILE,
    )

logger = logging.getLogger("backend.rag.index_manager")


# =============================================================================
# LlamaIndex Imports (Optional)
# =============================================================================

try:
    from llama_index.llms.ollama import Ollama
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.core.settings import Settings
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    logger.warning("LlamaIndex not available. Index functionality limited.")


# =============================================================================
# Thread-Safe Index State
# =============================================================================

_index_lock = threading.Lock()
_index_obj = None
_query_engine = None

_rebuild_lock = threading.Lock()
_rebuild_in_progress = False

# Module-level reference to get_or_create_index (populated lazily)
_get_or_create_index_fn = None


# =============================================================================
# Rebuild Lock File Management
# =============================================================================

def read_persisted_rebuild_lock() -> Dict[str, Any]:
    """
    Read the persisted rebuild lock file.
    
    Returns:
        Dictionary with rebuild state (last_started, last_completed timestamps)
    """
    try:
        if REBUILD_LOCK_FILE.exists():
            with open(REBUILD_LOCK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logger.debug("Could not read persisted rebuild lock file")
    return {}


def write_persisted_rebuild_lock(data: Dict[str, Any]) -> None:
    """
    Write the rebuild lock file atomically.
    
    Args:
        data: Dictionary with rebuild state to persist
    """
    try:
        os.makedirs(REBUILD_LOCK_FILE.parent, exist_ok=True)
        tmp = str(REBUILD_LOCK_FILE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, str(REBUILD_LOCK_FILE))
    except Exception:
        logger.warning("Could not write persisted rebuild lock file")


def is_rebuild_in_cooldown() -> Tuple[bool, int]:
    """
    Check if rebuild is blocked due to cooldown period.
    
    Returns:
        Tuple of (is_blocked, seconds_remaining)
    """
    persisted = read_persisted_rebuild_lock() or {}
    last_started = persisted.get("last_started")
    now_ts = time.time()
    
    if last_started:
        try:
            last_ts = float(last_started)
        except Exception:
            last_ts = 0
        elapsed = now_ts - last_ts
        if elapsed < REBUILD_COOLDOWN_SECONDS:
            return True, int(REBUILD_COOLDOWN_SECONDS - elapsed)
    
    return False, 0


# =============================================================================
# Model Initialization
# =============================================================================

def read_embedding_model_from_folder(embeddings_dir: str, fallback: str = "") -> str:
    """
    Read embedding model name from embeddings folder configuration.
    
    Checks for model.txt or config.json in the embeddings directory.
    
    Args:
        embeddings_dir: Path to embeddings configuration directory
        fallback: Fallback model name if not found
        
    Returns:
        Model name string
    """
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
    return fallback or OLLAMA_EMBED


def init_models() -> None:
    """
    Initialize LlamaIndex Settings for embedding and LLM models.
    
    This function is idempotent - safe to call multiple times.
    
    Raises:
        RuntimeError: If LlamaIndex is not available
        Exception: If model initialization fails
    """
    if not LLAMA_INDEX_AVAILABLE:
        raise RuntimeError("LlamaIndex not available for model initialization")
    
    try:
        # Prefer embedding model from config folder, then env var, then default
        embed_model_name = read_embedding_model_from_folder(
            EMBEDDINGS_DIR, 
            fallback=OLLAMA_EMBED
        )
        Settings.embed_model = OllamaEmbedding(
            model_name=embed_model_name,
            max_tokens=DEFAULT_MAX_TOKENS,
            request_timeout=DEFAULT_TIMEOUT
        )
        Settings.llm = Ollama(
            model=OLLAMA_LLM,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
            request_timeout=DEFAULT_TIMEOUT
        )
        logger.info(f"Initialized Ollama LLM='{OLLAMA_LLM}' embed='{embed_model_name}'")
    except Exception as e:
        logger.error(f"Could not initialize Ollama models: {e}")
        raise


# =============================================================================
# Index Management
# =============================================================================

def get_index(
    force_rebuild: bool = False, 
    build_kwargs: Optional[Dict[str, Any]] = None
) -> Tuple[Any, Any]:
    """
    Thread-safe lazy loader for VectorStoreIndex and its query engine.
    
    Lazily imports the heavy index builder to allow dev server to start
    even if LLM/index dependencies are missing.
    
    Args:
        force_rebuild: Force complete rebuild of the index
        build_kwargs: Build-time parameters (chunk_size, chunk_overlap, etc.)
        
    Returns:
        Tuple of (index_obj, query_engine) or (None, None) on failure
        
    Raises:
        Exception: If index creation/loading fails
    """
    global _index_obj, _query_engine, _get_or_create_index_fn
    
    with _index_lock:
        if _index_obj is None or force_rebuild:
            logger.info(f"Loading/creating index (force_rebuild={force_rebuild}) build_kwargs={build_kwargs}")
            
            # Lazy import of the index builder
            if _get_or_create_index_fn is None:
                try:
                    from rag.vector_store_generator import get_or_create_index
                    _get_or_create_index_fn = get_or_create_index
                except ImportError:
                    try:
                        from rag.vector_store_generator import get_or_create_index
                        _get_or_create_index_fn = get_or_create_index
                    except ImportError:
                        try:
                            from vector_store_generator import get_or_create_index
                            _get_or_create_index_fn = get_or_create_index
                        except Exception as e:
                            logger.warning(f"LLM/index libraries not available: {e}")
                            raise

            # Initialize models
            init_models()
            
            # Create or load index
            try:
                if build_kwargs and force_rebuild:
                    try:
                        _index_obj = _get_or_create_index_fn(
                            index_dir=INDEX_DIR,
                            data_dir=DATA_DIR,
                            force_rebuild=force_rebuild,
                            indexing=build_kwargs
                        )
                    except TypeError:
                        logger.warning("get_or_create_index does not accept build kwargs; retrying without them")
                        _index_obj = _get_or_create_index_fn(
                            index_dir=INDEX_DIR,
                            data_dir=DATA_DIR,
                            force_rebuild=force_rebuild
                        )
                else:
                    _index_obj = _get_or_create_index_fn(
                        index_dir=INDEX_DIR,
                        data_dir=DATA_DIR,
                        force_rebuild=force_rebuild
                    )
            except Exception as e:
                logger.exception(f"Failed to create/load index: {e}")
                raise

            # Create query engine
            try:
                _query_engine = _index_obj.as_query_engine(llm=Settings.llm)
            except Exception as e:
                logger.warning(f"Could not create query engine from index: {e}")
                _query_engine = None
                
        return _index_obj, _query_engine


def trigger_async_rebuild() -> str:
    """
    Trigger an asynchronous index rebuild if not already in progress.
    
    Respects cooldown period and prevents concurrent rebuilds.
    
    Returns:
        Status string: 'rebuild_started', 'rebuild_already_in_progress', 
                      or 'rebuild_cooldown'
    """
    global _rebuild_in_progress
    
    with _rebuild_lock:
        # Check cooldown
        cooldown_blocked, seconds_left = is_rebuild_in_cooldown()
        if cooldown_blocked:
            logger.info(f"Rebuild suppressed due to cooldown (seconds_left={seconds_left})")
            return "rebuild_cooldown"
        
        # Check if already in progress
        if _rebuild_in_progress:
            logger.info("Async rebuild already in progress; not starting a new one")
            return "rebuild_already_in_progress"
        
        # Claim the rebuild slot
        try:
            persisted = read_persisted_rebuild_lock() or {}
            persisted["last_started"] = str(time.time())
            write_persisted_rebuild_lock(persisted)
        except Exception:
            logger.debug("Failed to persist rebuild start time")
        
        _rebuild_in_progress = True

    def _async_rebuild():
        global _rebuild_in_progress
        try:
            get_index(force_rebuild=True)
            logger.info("Async rebuild completed successfully")
            
            # Record completion time
            try:
                persisted = read_persisted_rebuild_lock() or {}
                persisted["last_completed"] = str(time.time())
                write_persisted_rebuild_lock(persisted)
            except Exception:
                logger.debug("Failed to persist rebuild completion time")
        except Exception:
            logger.exception("Async rebuild failed")
        finally:
            with _rebuild_lock:
                _rebuild_in_progress = False

    thread = threading.Thread(target=_async_rebuild, daemon=True)
    thread.start()
    return "rebuild_started"


def trigger_sync_rebuild() -> bool:
    """
    Trigger a synchronous (blocking) index rebuild.
    
    Returns:
        True if rebuild succeeded, False otherwise
    """
    try:
        get_index(force_rebuild=True)
        logger.info("Sync rebuild completed successfully")
        return True
    except Exception:
        logger.exception("Sync rebuild failed")
        return False


def is_rebuild_in_progress() -> bool:
    """Check if an async rebuild is currently in progress."""
    return _rebuild_in_progress


def get_index_status() -> Dict[str, Any]:
    """
    Get current index status for health checks.
    
    Returns:
        Dictionary with index_exists, meta_entries, current_files counts,
        and any detected issues
    """
    # Import with fallback
    try:
        from rag.vector_store_generator import load_embedding_metadata
    except ImportError:
        try:
            from rag.vector_store_generator import load_embedding_metadata
        except ImportError:
            from vector_store_generator import load_embedding_metadata
    
    index_file = Path(INDEX_DIR) / "docstore.json"
    index_exists = index_file.exists()
    
    # Load embedding metadata
    embeddings_meta = set()
    try:
        embeddings_meta = load_embedding_metadata(INDEX_DIR)
        if not isinstance(embeddings_meta, (set, list)):
            embeddings_meta = set(embeddings_meta or [])
        else:
            embeddings_meta = set(embeddings_meta)
    except Exception as e:
        logger.warning(f"Could not read embedding metadata: {e}")
    
    # Collect current data files
    current_files = set()
    try:
        for root, _, files in os.walk(DATA_DIR):
            for fname in files:
                current_files.add(os.path.abspath(os.path.join(root, fname)))
    except Exception as e:
        logger.warning(f"Could not enumerate data files in {DATA_DIR}: {e}")
    
    # Determine mismatches
    missing_on_disk = [p for p in embeddings_meta if not os.path.exists(p)]
    new_files = list(current_files - embeddings_meta) if embeddings_meta else list(current_files)
    
    # Determine if rebuild needed
    needs_rebuild = False
    reasons = []
    if not index_exists:
        needs_rebuild = True
        reasons.append("missing_index")
    if missing_on_disk:
        needs_rebuild = True
        reasons.append("meta_points_to_missing_files")
    if new_files:
        needs_rebuild = True
        reasons.append("new_data_files")
    
    return {
        "index_exists": index_exists,
        "meta_entries": len(embeddings_meta),
        "current_files": len(current_files),
        "missing_meta_files": len(missing_on_disk),
        "new_files": len(new_files),
        "needs_rebuild": needs_rebuild,
        "reasons": reasons,
    }


# =============================================================================
# Utility Functions for Testing
# =============================================================================

def set_get_or_create_index_fn(fn) -> None:
    """
    Allow tests to monkeypatch the get_or_create_index function.
    
    Args:
        fn: Function to use instead of the default get_or_create_index
    """
    global _get_or_create_index_fn
    _get_or_create_index_fn = fn


def reset_index_state() -> None:
    """
    Reset all index state for testing purposes.
    
    Clears cached index, query engine, and rebuild state.
    """
    global _index_obj, _query_engine, _rebuild_in_progress, _get_or_create_index_fn
    
    with _index_lock:
        _index_obj = None
        _query_engine = None
    
    with _rebuild_lock:
        _rebuild_in_progress = False
    
    _get_or_create_index_fn = None
