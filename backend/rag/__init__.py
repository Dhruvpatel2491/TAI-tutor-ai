"""
RAG (Retrieval-Augmented Generation) package.

This package contains:
- vector_store_generator: Document parsing and vector index creation
- index_manager: Thread-safe index loading, caching, and rebuild management
- retrieval_chat: Query execution and response caching

Usage:
    from rag.index_manager import get_index, trigger_async_rebuild
    from rag.retrieval_chat import get_cache, execute_query
    from rag.vector_store_generator import get_or_create_index
"""

__all__ = [
    "vector_store_generator",
    "index_manager",
    "retrieval_chat",
]
