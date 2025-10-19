#!/usr/bin/env python3
"""
Chat Yapper - Main launcher
Starts the backend server and opens a browser
"""
import sys
import os
import threading
import time
import webbrowser
import logging
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
except ImportError:
    # dotenv not available, continue without it
    pass
except Exception:
    # Error loading .env, continue without it
    pass

def is_executable():
    """
    Detect if we're running as a PyInstaller executable.
    Returns True if running from .exe, False if running from source.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Set up logging
def setup_logging():
    """Set up logging to both file and console"""
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = logs_dir / f"chatyapper_{timestamp}.log"
    
    # Configure logging
    # File handler - logs everything
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Console handler - adjust level based on environment
    console_handler = logging.StreamHandler(sys.stdout)
    debug_mode = os.getenv('DEBUG', '').lower() in ('true', '1', 'yes', 'on')
    
    if debug_mode:
        # Debug mode enabled via environment variable
        console_handler.setLevel(logging.DEBUG)
    elif is_executable():
        # Production (.exe) - only show errors
        console_handler.setLevel(logging.ERROR)
    else:
        # Development - show warnings and errors  
        console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler]
    )
    
    logger = logging.getLogger('ChatYapper')
    logger.info(f"Logging initialized - log file: {log_filename}")
    return logger

# Initialize logging
logger = setup_logging()

def log_important(message):
    """Log important messages that should appear in both console and file"""
    logger.warning(f"IMPORTANT: {message}")  # WARNING level ensures console output
    print(f"{message}")  # Also print directly for immediate visibility

# Add backend to Python path
backend_dir = Path(__file__).parent / "backend"
if not backend_dir.exists():
    logger.error(f"Backend directory not found: {backend_dir}")
    logger.error("Make sure you're running this from the Chat Yapper root directory")
    input("Press Enter to exit...")
    sys.exit(1)

sys.path.insert(0, str(backend_dir))

def find_available_port(start_port=8008, max_attempts=10):
    """Find an available port starting from start_port"""
    import socket
    
    logger.info(f"Searching for available port starting from {start_port}")
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port to see if it's available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                logger.info(f"Found available port: {port}")
                return port
        except OSError as e:
            logger.debug(f"Port {port} not available: {e}")
            continue
    
    error_msg = f"Could not find an available port in range {start_port}-{start_port + max_attempts}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)

def start_backend(port):
    """Start the FastAPI backend server"""
    
    try:
        # Change to backend directory first
        original_cwd = os.getcwd()
        os.chdir(backend_dir)
        logger.info(f"Changed to backend directory: {backend_dir}")
        
        # Import dependencies
        logger.info("Importing dependencies...")
        try:
            import uvicorn
            logger.info(f"Uvicorn imported successfully, version: {uvicorn.__version__}")
        except ImportError as e:
            error_msg = f"uvicorn not found: {e}. Install with: pip install -r requirements.txt"
            logger.error(error_msg)
            raise ImportError(error_msg)
        
        # Import the app from the current directory (now in backend dir, so just import app)
        try:
            import app as backend_app
            logger.info("Backend app imported successfully")
        except ImportError as e:
            if "fastapi.middleware" in str(e):
                error_msg = f"FastAPI import error: {e}. Install with: pip install -r requirements.txt"
                logger.error(error_msg)
                raise ImportError(error_msg)
            else:
                error_msg = f"Backend app import error: {e}"
                logger.error(error_msg)
                raise ImportError(error_msg)
        
        # Use the pre-determined available port
        host = os.getenv('HOST', '0.0.0.0')
        logger.info(f"Starting Chat Yapper backend server on {host}:{port}...")
        log_important(f"Starting Chat Yapper backend server on {host}:{port}...")
        try:
            uvicorn.run(backend_app.app, host=host, port=port, log_level="warning")
        except OSError as e:
            if "10048" in str(e) or "already in use" in str(e).lower():
                error_msg = f"\n{'='*60}\nERROR: Port {port} is already in use!\n\nThis usually means Chat Yapper is already running.\n\nPlease either:\n  1. Close the other Chat Yapper window, or\n  2. Check Task Manager for 'ChatYapper.exe' and end it\n{'='*60}\n"
                logger.error(error_msg)
                logger.error(error_msg)
                input("Press Enter to exit...")
                sys.exit(1)
            raise
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Import error: {e}")
        logger.error("Make sure all dependencies are installed:")
        logger.error(" pip install -r requirements.txt")
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        logger.error(f"Current directory: {os.getcwd()}")
        logger.error(f"Backend directory: {backend_dir}")
        logger.error(f"Failed to start backend: {e}")
        logger.error(f"Current directory: {os.getcwd()}")
        logger.error(f"Backend directory: {backend_dir}")
        input("Press Enter to exit...")
        sys.exit(1)

def open_browser(port):
    """Open the web browser to the application"""
    logger.info("Waiting 3 seconds for server to start...")
    time.sleep(3)  # Wait for server to start
    host = os.getenv('HOST', '0.0.0.0')
    # Use localhost for browser opening even if server binds to 0.0.0.0
    browser_host = 'localhost' if host == '0.0.0.0' else host
    url = f"http://{browser_host}:{port}/settings"
    logger.info(f"Opening Chat Yapper in browser: {url}")
    logger.info(f"Opening Chat Yapper in your browser: {url}")
    try:
        webbrowser.open(url)
        logger.info("Browser opened successfully")
    except Exception as e:
        logger.error(f"Could not auto-open browser: {e}")
        logger.warning(f"Could not auto-open browser: {e}")
        logger.warning(f"Please manually open: {url}")

def main():
    logger.info("Starting Chat Yapper application...")
    
    print("=" * 50)
    print("Chat Yapper - Voice Avatar TTS System")
    print("=" * 50)
    print()
    
    # Find an available port before starting threads
    default_port = int(os.getenv('PORT', 8008))
    try:
        server_port = find_available_port(default_port)
        log_important(f"Found available port: {server_port}")
    except RuntimeError as e:
        logger.error(f"Could not find available port: {e}")
        logger.error(f"Could not find available port: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Start backend in a separate thread
    logger.info("Starting backend server thread...")
    backend_thread = threading.Thread(target=start_backend, args=(server_port,), daemon=True)
    backend_thread.start()
    
    # Open browser after a short delay
    logger.info("Starting browser opening thread...")
    browser_thread = threading.Thread(target=open_browser, args=(server_port,), daemon=True)
    browser_thread.start()
    
    try:
        logger.info("Chat Yapper application is now running")
        log_important("Chat Yapper is running!")
        print(f"Web interface: http://localhost:{server_port}/settings")
        print(f"Avatar display (copy into OBS and enable Audio): http://localhost:{server_port}/yappers")
        print("Do not close this window while using Chat Yapper")
        print()
        print("Press Ctrl+C to stop the server")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal (Ctrl+C)")
        print("\nShutting down Chat Yapper...")
        sys.exit(0)

if __name__ == "__main__":
    main()
