"""
Langfuse integration client

Provides unified interface for Langfuse monitoring and tracing functionality.
"""

from typing import Optional
import os
import uuid
from ..core.logging import get_project_logger

logger = get_project_logger(__name__)


class LangfuseClient:
    """Langfuse client wrapper class"""
    
    def __init__(self):
        """Initialize Langfuse client"""
        self.enabled = False
        self._handler = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Langfuse connection"""
        try:
            # Check required environment variables
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
            
            if not secret_key or not public_key:
                logger.warning("Langfuse configuration incomplete, monitoring features will not be available")
                return
            
            # Try to import langfuse
            try:
                from langfuse import Langfuse
                from langfuse.langchain import CallbackHandler
                
                self._client = Langfuse(
                    secret_key=secret_key,
                    public_key=public_key,
                    host=host
                )
                
                self._handler = CallbackHandler(
                    public_key=public_key
                )
                
                self.enabled = True
                logger.info("Langfuse client initialized successfully")
                
            except ImportError as e:
                logger.warning(f"Failed to import Langfuse: {e}, monitoring features will not be available")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                
        except Exception as e:
            logger.error(f"Langfuse configuration error: {e}")
    
    def get_handler(self):
        """Get Langfuse callback handler"""
        if not self.enabled:
            logger.debug("Langfuse not enabled, returning None handler")
            return None
        return self._handler


# Global Langfuse client instance
_langfuse_client = LangfuseClient()


def create_langfuse_config(
    session_id: Optional[str] = None,
    run_name: Optional[str] = None,
    task_name: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict:
    """
    Create Langfuse configuration dictionary
    
    Args:
        session_id: Session ID, auto-generated if not provided
        run_name: Run name
        task_name: Task name (used as tag)
        user_id: User ID
        metadata: Additional metadata
    
    Returns:
        Configuration dictionary with callbacks and metadata, returns empty callbacks list if Langfuse not enabled
    """
    handler = _langfuse_client.get_handler()
    if not handler:
        # If Langfuse not enabled, return empty configuration
        return {"callbacks": []}
    
    # Auto-generate UUID if session_id not provided
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    # Build configuration
    config = {"callbacks": [handler]}
    
    # Set run_name (trace name)
    if run_name:
        config["run_name"] = run_name
    
    # Build metadata
    langfuse_metadata = {"langfuse_session_id": session_id}
    if user_id:
        langfuse_metadata["langfuse_user_id"] = user_id
    
    # Set tags (task name only) - via langfuse_tags field in metadata
    if task_name:
        langfuse_metadata["langfuse_tags"] = [task_name]
    
    # Merge additional metadata if provided
    if metadata:
        langfuse_metadata.update(metadata)
    
    config["metadata"] = langfuse_metadata
    
    return config


