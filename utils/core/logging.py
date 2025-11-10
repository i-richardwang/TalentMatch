"""
Logging configuration module

Provides unified logging configuration and management functionality 
to support logging needs for different modules.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Get project root directory"""
    return Path(__file__).parent.parent.parent


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up logger
    
    Args:
        name: Logger name
        level: Log level
        log_file: Log file path
        format_string: Log format string
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate configuration
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_project_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get project logger instance
    
    Args:
        name: Module name
        level: Log level, uses environment variable or default if None
        
    Returns:
        logging.Logger: Configured logger instance
    """
    if level is None:
        level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, level_str, logging.INFO)
    
    # Use logs folder under project root
    project_root = get_project_root()
    log_file = project_root / "logs" / "backend.log"
    
    return setup_logger(
        name=name,
        level=level,
        log_file=str(log_file)
    )