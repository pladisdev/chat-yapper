#!/usr/bin/env python3
"""
Development runner for the chat-yapper FastAPI application.
Run this file directly in VS Code for debugging.
"""

if __name__ == "__main__":
    import uvicorn
    import os
    import sys
    
    # Load environment variables from .env file if available
    try:
        from dotenv import load_dotenv
        # Load from project root (parent directory)
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        load_dotenv(dotenv_path)
    except ImportError:
        # dotenv not available, continue without it
        pass
    except Exception:
        # Error loading .env, continue without it
        pass
    
    # Add the backend directory to Python path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    # Get configuration from environment variables
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8008))
    debug_mode = os.getenv('DEBUG', '').lower() in ('true', '1', 'yes', 'on')
    log_level = "debug" if debug_mode else "info"
    
    print("Starting Chat Yapper FastAPI application...")
    print("Working directory:", os.getcwd())
    print(f"Server will be available at: http://{host}:{port}")
    print(f"API endpoints at: http://{host}:{port}/api/")
    print(f"Debug mode: {debug_mode}")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run the FastAPI app with uvicorn
        uvicorn.run(
            "app:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=[backend_dir],
            log_level=log_level
        )
    except KeyboardInterrupt:
        print("\nServer stopped gracefully")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
