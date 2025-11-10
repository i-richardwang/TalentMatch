"""
TalentMatch utilities module

This package provides various utility functions and classes used in the project,
with a clear modular design:
- config: Configuration management
- database: Database connections and tools  
- ai: AI models and related tools
- data: Data models and processing tools
- core: Core utilities (exceptions, logging, etc.)
"""

# Core utilities import
from .core.exceptions import (
    TalentMatchException,
    ConfigurationError,
    DatabaseError,
    StorageError,
    ValidationError,
    LLMError,
    VectorDBError
)

from .core.logging import (
    get_project_logger,
)

# Configuration management removed, using environment variables directly

# Optional imports (to avoid heavy dependencies)
try:
    from .ai.llm_client import (
        LanguageModelChain
    )
    from .ai.embedding_client import (
        get_embedding_model,
        get_embedding_client,
        get_embedding,
        get_embeddings_batch,
        get_embeddings_batch_async
    )
except ImportError:
    pass

# Data processing tools removed

# Version information
__version__ = "0.2.0"
__author__ = "TalentMatch Team"
__email__ = "dev@talentmatch.ai"

# Export list
__all__ = [
    # Exceptions
    "TalentMatchException",
    "ConfigurationError", 
    "DatabaseError",
    "StorageError",
    "ValidationError",
    "LLMError",
    "VectorDBError",
    
    # Logging
    "get_project_logger",
    
    # LLM tools (optional)
    "LanguageModelChain",
    
    # Embedding tools (optional)
    "get_embedding_model",
    "get_embedding_client",
    "get_embedding",
    "get_embeddings_batch",
    "get_embeddings_batch_async",
]