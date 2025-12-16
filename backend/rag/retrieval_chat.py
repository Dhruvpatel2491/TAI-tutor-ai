"""
Retrieval Chat for TAI Tutor AI.

This module handles all RAG-based query functionality including:
- Response caching with LRU eviction and TTL
- Query execution with different prompt styles
- Multiple query endpoint implementations (v1, v2, v3)
- Integration with ChatPrompter for response customization

The retrieval_chat module is responsible for:
1. Caching LLM responses for performance
2. Creating query engines with custom parameters
3. Executing queries against the vector index
4. Applying prompt customization (style, type, length)
"""

import hashlib
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

# Import configuration with fallback for running as script
try:
    from config import (
        OLLAMA_LLM,
        DEFAULT_TEMPERATURE,
        DEFAULT_MAX_TOKENS,
        CACHE_ENABLED,
        CACHE_MAX_SIZE,
        CACHE_TTL_SECONDS,
    )
except ImportError:
    from config import (
        OLLAMA_LLM,
        DEFAULT_TEMPERATURE,
        DEFAULT_MAX_TOKENS,
        CACHE_ENABLED,
        CACHE_MAX_SIZE,
        CACHE_TTL_SECONDS,
    )

logger = logging.getLogger("backend.rag.retrieval_chat")


# =============================================================================
# LlamaIndex Imports (Optional)
# =============================================================================

try:
    from llama_index.llms.ollama import Ollama
    from llama_index.core.settings import Settings
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    logger.warning("LlamaIndex not available. Query functionality limited.")


# =============================================================================
# Response Cache
# =============================================================================

class ResponseCache:
    """
    Thread-safe LRU cache with TTL for caching LLM responses.
    
    This cache helps reduce latency and API costs by storing
    responses to frequently asked questions.
    
    Attributes:
        max_size: Maximum number of entries in cache
        ttl_seconds: Time-to-live for cache entries in seconds
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize the response cache.
        
        Args:
            max_size: Maximum number of cached responses
            ttl_seconds: Time-to-live for cache entries
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
    
    def _make_key(
        self, 
        question: str, 
        style: str, 
        response_type: str, 
        length: str, 
        model: str
    ) -> str:
        """
        Generate a cache key from query parameters.
        
        Args:
            question: The user's question
            style: Response style (formal, casual, technical)
            response_type: Response type (direct, hinting, socratic)
            length: Response length (short, medium, long)
            model: LLM model name
            
        Returns:
            SHA256 hash of combined parameters
        """
        key_string = f"{question}|{style}|{response_type}|{length}|{model}"
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(
        self, 
        question: str, 
        style: str, 
        response_type: str, 
        length: str, 
        model: str
    ) -> Optional[str]:
        """
        Get cached response if available and not expired.
        
        Args:
            question: The user's question
            style: Response style
            response_type: Response type
            length: Response length
            model: LLM model name
            
        Returns:
            Cached response string or None if not found/expired
        """
        if not CACHE_ENABLED:
            return None
            
        key = self._make_key(question, style, response_type, length, model)
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.ttl_seconds:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    logger.debug(f"Cache hit for query key: {key[:16]}...")
                    return entry["response"]
                else:
                    # Expired, remove it
                    del self._cache[key]
                    logger.debug(f"Cache expired for key: {key[:16]}...")
        return None
    
    def set(
        self, 
        question: str, 
        style: str, 
        response_type: str, 
        length: str, 
        model: str, 
        response: str
    ) -> None:
        """
        Store a response in the cache.
        
        Args:
            question: The user's question
            style: Response style
            response_type: Response type
            length: Response length
            model: LLM model name
            response: The response to cache
        """
        if not CACHE_ENABLED:
            return
            
        key = self._make_key(question, style, response_type, length, model)
        
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = {
                "response": response,
                "timestamp": time.time()
            }
            
            # Evict oldest if over capacity
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug("Cache evicted oldest entry")
    
    def clear(self) -> None:
        """Clear all cached responses."""
        with self._lock:
            self._cache.clear()
            logger.info("Response cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with size, max_size, ttl_seconds, enabled status
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "enabled": CACHE_ENABLED
            }


# Global cache instance
_response_cache = ResponseCache(
    max_size=CACHE_MAX_SIZE, 
    ttl_seconds=CACHE_TTL_SECONDS
)


def get_cache() -> ResponseCache:
    """Get the global response cache instance."""
    return _response_cache


# =============================================================================
# Mock Response Classes (for testing)
# =============================================================================

class MockResponse:
    """Mock response for testing without LLM calls."""
    
    def __init__(self, question: str):
        self._question = question
    
    def __str__(self) -> str:
        return f"MOCK_ECHO: {self._question}"
    
    @property
    def source_nodes(self) -> List:
        return []


class MockResponseV2:
    """Mock response for v2 queries."""
    
    def __init__(self, question: str):
        self._question = question
    
    def __str__(self) -> str:
        return f"MOCK_ECHO_V2: {self._question}"


class MockResponseV3:
    """Mock response for v3 queries with style parameters."""
    
    def __init__(self, question: str, style: str, response_type: str, length: str):
        self._question = question
        self._style = style
        self._type = response_type
        self._length = length
    
    def __str__(self) -> str:
        return (
            f"MOCK_ECHO_V3: style={self._style}, type={self._type}, "
            f"length={self._length} | {self._question[:100]}"
        )


# =============================================================================
# Query Execution
# =============================================================================

def create_query_engine(
    index_obj: Any,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    retrieval_kwargs: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Create a query engine from an index with optional customization.
    
    Args:
        index_obj: VectorStoreIndex instance
        model: LLM model name (defaults to OLLAMA_LLM)
        temperature: Temperature for generation
        max_tokens: Maximum tokens for response
        retrieval_kwargs: Additional kwargs for as_query_engine
        
    Returns:
        Query engine instance
        
    Raises:
        Exception: If query engine creation fails
    """
    if not LLAMA_INDEX_AVAILABLE:
        raise RuntimeError("LlamaIndex not available for query engine creation")
    
    # Determine LLM to use
    if model and model != OLLAMA_LLM:
        # Create per-request LLM
        llm = Ollama(
            model=model,
            temperature=temperature or DEFAULT_TEMPERATURE,
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
            request_timeout=300
        )
    else:
        # Use global settings LLM
        llm = Settings.llm
    
    # Create query engine with optional retrieval kwargs
    r_kwargs = retrieval_kwargs or {}
    
    try:
        if r_kwargs:
            query_engine = index_obj.as_query_engine(llm=llm, **r_kwargs)
        else:
            query_engine = index_obj.as_query_engine(llm=llm)
    except TypeError:
        logger.warning("as_query_engine() may not accept provided retrieval kwargs; creating without them")
        query_engine = index_obj.as_query_engine(llm=llm)
    
    return query_engine


def execute_query(
    query_engine: Any,
    question: str,
    use_mock: bool = False
) -> Tuple[str, Any]:
    """
    Execute a query and return the response.
    
    Args:
        query_engine: Query engine instance
        question: The question to ask
        use_mock: If True, return mock response without LLM call
        
    Returns:
        Tuple of (answer_text, response_object)
    """
    if use_mock:
        response = MockResponse(question)
        logger.info("Using MOCK_LLM_ECHO response")
    else:
        response = query_engine.query(question)
        _log_response_debug(response)
    
    answer_text = str(response)
    return answer_text, response


def execute_query_v2(
    query_engine: Any,
    question: str,
    use_mock: bool = False
) -> Tuple[str, Any]:
    """
    Execute a v2 query with model customization support.
    
    Args:
        query_engine: Query engine instance
        question: The question to ask
        use_mock: If True, return mock response without LLM call
        
    Returns:
        Tuple of (answer_text, response_object)
    """
    if use_mock:
        response = MockResponseV2(question)
    else:
        response = query_engine.query(question)
        logger.debug(f"Response object: type={type(response)}; str={str(response)[:200]}")
    
    answer_text = str(response)
    return answer_text, response


def execute_query_v3(
    query_engine: Any,
    question: str,
    enhanced_question: str,
    style: str,
    response_type: str,
    length: str,
    use_mock: bool = False
) -> Tuple[str, Any]:
    """
    Execute a v3 query with full prompt customization.
    
    Args:
        query_engine: Query engine instance
        question: Original question (for mock)
        enhanced_question: Question with prompt context
        style: Response style
        response_type: Response type
        length: Response length
        use_mock: If True, return mock response without LLM call
        
    Returns:
        Tuple of (answer_text, response_object)
    """
    if use_mock:
        response = MockResponseV3(question, style, response_type, length)
    else:
        response = query_engine.query(enhanced_question)
    
    answer_text = str(response)
    return answer_text, response


def _log_response_debug(response: Any) -> None:
    """Log debug information about a response object."""
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
                        first = val[0]
                        snippet = str(getattr(first, 'text', first))[:400]
                        logger.debug(f"Response.{attr}[0] snippet: {snippet}")
                except Exception:
                    logger.debug(f"Could not inspect {attr} on response")
    except Exception:
        logger.debug("Failed to introspect response object")


# =============================================================================
# Parameter Validation
# =============================================================================

def validate_style(style: Optional[str]) -> str:
    """Validate and normalize response style parameter."""
    style = (style or "formal").lower()
    if style not in ["formal", "casual", "technical"]:
        return "formal"
    return style


def validate_response_type(response_type: Optional[str]) -> str:
    """Validate and normalize response type parameter."""
    response_type = (response_type or "direct").lower()
    if response_type not in ["direct", "hinting", "socratic"]:
        return "direct"
    return response_type


def validate_length(length: Optional[str]) -> str:
    """Validate and normalize response length parameter."""
    length = (length or "medium").lower()
    if length not in ["short", "medium", "long"]:
        return "medium"
    return length


def parse_model_params(
    payload: Dict[str, Any]
) -> Tuple[str, float, int]:
    """
    Parse model parameters from request payload.
    
    Args:
        payload: Request JSON payload
        
    Returns:
        Tuple of (model, temperature, max_tokens)
    """
    model = payload.get("model") or OLLAMA_LLM
    
    try:
        temperature = float(payload.get("temperature", DEFAULT_TEMPERATURE))
    except Exception:
        temperature = DEFAULT_TEMPERATURE
    
    try:
        max_tokens = int(payload.get("max_tokens", DEFAULT_MAX_TOKENS))
    except Exception:
        max_tokens = DEFAULT_MAX_TOKENS
    
    return model, temperature, max_tokens


def should_use_mock(payload: Dict[str, Any]) -> bool:
    """
    Check if mock mode should be used for a query.
    
    Checks both request payload and environment variable.
    
    Args:
        payload: Request JSON payload
        
    Returns:
        True if mock mode should be used
    """
    return bool(
        payload.get("mock") or 
        payload.get("use_mock") or 
        os.environ.get("MOCK_LLM_ECHO")
    )


# =============================================================================
# Prompt Adapter (for llama-index compatibility)
# =============================================================================

class PromptAdapter:
    """
    Compatibility wrapper for llama-index prompt templates.
    
    Some versions of llama-index expect a Prompt-like object with a
    `partial_format(**kwargs)` method. This adapter wraps plain strings
    to provide that interface.
    """
    
    def __init__(self, template: str):
        """
        Initialize the adapter with a template string.
        
        Args:
            template: The prompt template string
        """
        self.template = template

    def partial_format(self, **kwargs) -> Any:
        """
        Format the template and return a llama-index compatible prompt.
        
        Args:
            **kwargs: Format arguments
            
        Returns:
            Wrapped prompt object
        """
        try:
            from llama_index.prompts.base import BasePromptTemplate
        except Exception:
            raise RuntimeError(
                "llama_index.prompts.base.BasePromptTemplate is required "
                "for prompt adaptation. Please ensure llama-index is installed."
            )

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

        return _WrappedPrompt(
            formatted, 
            list(kwargs.keys()) if isinstance(kwargs, dict) else []
        )

    def __contains__(self, item: str) -> bool:
        """Allow substring checks."""
        try:
            return item in self.template
        except Exception:
            return False

    def __str__(self) -> str:
        return str(self.template)
