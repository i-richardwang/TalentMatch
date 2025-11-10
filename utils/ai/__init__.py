"""
AI Tools Module

Provides AI models and related tools, including:
- LLM client management
- Langfuse integration
- Vector encoder
"""

from .llm_client import (
    LanguageModelChain,
    init_language_model
)

from .embedding_client import (
    get_embedding_model,
    get_embedding_client,
    get_embedding,
    get_embeddings_batch,
    get_embeddings_batch_async
)

from .langfuse_client import (
    create_langfuse_config,
)

__all__ = [
    "LanguageModelChain",
    "init_language_model",
    "get_embedding_model",
    "get_embedding_client",
    "get_embedding",
    "get_embeddings_batch",
    "get_embeddings_batch_async",
    "create_langfuse_config",
]