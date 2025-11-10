"""
Environment configuration loading module

Responsible for loading environment variables and initializing application configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from ..core.logging import get_project_logger

logger = get_project_logger(__name__)


def get_project_root() -> Path:
    """Get project root directory"""
    return Path(__file__).parent.parent.parent


def load_env(env_file: str = ".env") -> bool:
    """
    Load environment variables file
    
    Args:
        env_file: Environment file name, defaults to .env
        
    Returns:
        bool: Whether the environment file was loaded successfully
    """
    project_root = get_project_root()
    env_path = project_root / env_file
    
    if not env_path.exists():
        logger.warning(f"Environment file {env_path} does not exist")
        return False
    
    try:
        load_dotenv(env_path)
        logger.info(f"Successfully loaded environment file: {env_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to load environment file: {e}")
        return False