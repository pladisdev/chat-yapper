"""
Shared dependencies and utilities for the application
"""
import os
import sys

def is_executable():
    """Detect if running as PyInstaller executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Import backend_logging after is_executable is defined to avoid circular import
from .backend_logging import setup_backend_logging

def get_env_var(key, default=""):
    """Get environment variable, checking embedded config if running as executable"""
    # First try regular environment variables
    value = os.environ.get(key)
    if value:
        return value
    
    # If running as executable, try embedded config
    if is_executable():
        try:
            from embedded_config import get_embedded_env
            return get_embedded_env(key, default)
        except ImportError:
            # Embedded config not found, use default
            pass
    
    return default

# Initialize logging
logger = setup_backend_logging()



def log_important(message):
    """Log important messages that should appear in both console and file"""
    logger.warning(f"IMPORTANT: {message}")  # WARNING level ensures console output