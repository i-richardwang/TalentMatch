"""
Unified exception handling module

This module defines all custom exception classes used in the project 
to ensure consistency in exception handling.
"""

from typing import Optional, Dict, Any


class TalentMatchException(Exception):
    """Base exception class for the project"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class DatabaseError(TalentMatchException):
    """Database related exceptions"""
    pass


class StorageError(DatabaseError):
    """Storage related exceptions"""
    pass


class VectorDBError(DatabaseError):
    """Vector database related exceptions"""
    pass


class LLMError(TalentMatchException):
    """LLM call related exceptions"""
    pass


class ValidationError(TalentMatchException):
    """Data validation related exceptions"""
    pass


class ConfigurationError(TalentMatchException):
    """Configuration related exceptions"""
    pass