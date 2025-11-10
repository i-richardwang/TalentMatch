"""
Core Utilities Module

Provides fundamental tools for the project, including:
- Exception handling
- Logging configuration
- Basic utility functions
"""

from .exceptions import (
    TalentMatchException,
    ConfigurationError,
    DatabaseError,
    StorageError,
    ValidationError,
    LLMError,
    VectorDBError
)

from .logging import (
    get_project_logger,
)

__all__ = [
    "TalentMatchException",
    "ConfigurationError",
    "DatabaseError", 
    "StorageError",
    "ValidationError",
    "LLMError",
    "VectorDBError",
    "get_project_logger",
]