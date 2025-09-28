#!/usr/bin/env python3
"""
Development runner for the chat-yapper FastAPI application.
Run this file directly in VS Code for debugging.
"""

if __name__ == "__main__":
    import uvicorn
    import os
    import sys
    
    # Add the backend directory to Python path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    print("Starting Chat Yapper FastAPI application...")
    print("Working directory:", os.getcwd())
    print("Server will be available at: http://localhost:8000")
    print("API endpoints at: http://localhost:8000/api/")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run the FastAPI app with uvicorn
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[backend_dir],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped gracefully")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
