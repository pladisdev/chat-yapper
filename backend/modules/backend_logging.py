import logging
from datetime import datetime
from pathlib import Path
from . import is_executable

def setup_backend_logging():
    """Set up logging for the backend"""
    # Create logs directory
    logs_dir = Path("../logs") if Path("../logs").exists() else Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = logs_dir / f"backend_{timestamp}.log"
    
    # Configure logging for this module
    backend_logger = logging.getLogger('ChatYapper.Backend')
    backend_logger.setLevel(logging.INFO)
    
    # Only add handlers if not already configured
    if not backend_logger.handlers:
        # File handler - logs everything
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Console handler - adjust level based on environment
        console_handler = logging.StreamHandler()
        if is_executable():
            # Production (.exe) - only show errors
            console_handler.setLevel(logging.ERROR)
            backend_logger.info("Production mode detected (.exe) - console logging set to ERROR level only")
        else:
            # Development - show warnings and errors
            console_handler.setLevel(logging.WARNING)
            backend_logger.info("Development mode detected - console logging set to WARNING level")
        
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        backend_logger.addHandler(file_handler)
        backend_logger.addHandler(console_handler)
    
    backend_logger.info(f"Backend logging initialized - log file: {log_filename}")
    return backend_logger

# Initialize backend logging
logger = setup_backend_logging()

