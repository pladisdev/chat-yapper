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
import subprocess
from pathlib import Path

import socket

# Add backend to Python path
backend_dir = Path(__file__).parent / "backend"
if not backend_dir.exists():
    print(f"Backend directory not found: {backend_dir}")
    print("Make sure you're running this from the Chat Yapper root directory")
    input("Press Enter to exit...")
    sys.exit(1)

sys.path.insert(0, str(backend_dir))

def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port"""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port to see if it's available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts}")

def start_backend(port):
    """Start the FastAPI backend server"""
    
    try:
        # Change to backend directory first
        original_cwd = os.getcwd()
        os.chdir(backend_dir)
        
        # Import dependencies
        print("Importing dependencies...")
        try:
            import uvicorn
        except ImportError:
            raise ImportError("uvicorn not found. Install with: pip install -r requirements.txt")
        
        # Import the app from the current directory
        try:
            import backend.app as backend_app
        except ImportError as e:
            if "fastapi.middleware" in str(e):
                raise ImportError(f"FastAPI import error: {e}. Install with: pip install -r requirements.txt")
            else:
                raise ImportError(f"Backend app import error: {e}")
        
        # Use the pre-determined available port
        print(f"Starting Chat Yapper backend server on port {port}...")
        uvicorn.run(backend_app.app, host="0.0.0.0", port=port, log_level="info")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed:")
        print(" pip install -r requirements.txt")
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to start backend: {e}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Backend directory: {backend_dir}")
        input("Press Enter to exit...")
        sys.exit(1)

def open_browser(port):
    """Open the web browser to the application"""
    time.sleep(3)  # Wait for server to start
    url = f"http://localhost:{port}/settings"
    print(f"Opening Chat Yapper in your browser: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not auto-open browser: {e}")
        print(f"Please manually open: {url}")

def main():
    
    print("=" * 50)
    print("Chat Yapper - Voice Avatar TTS System")
    print("=" * 50)
    print()
    
    # Find an available port before starting threads
    try:
        server_port = find_available_port(8000)
        print(f"Found available port: {server_port}")
    except RuntimeError as e:
        print(f"Could not find available port: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=start_backend, args=(server_port,), daemon=True)
    backend_thread.start()
    
    # Open browser after a short delay
    browser_thread = threading.Thread(target=open_browser, args=(server_port,), daemon=True)
    browser_thread.start()
    
    try:
        print("Chat Yapper is running!")
        print(f"Web interface: http://localhost:{server_port}/settings")
        print("Do not close this window while using Chat Yapper")
        print()
        print("Press Ctrl+C to stop the server")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down Chat Yapper...")
        sys.exit(0)

if __name__ == "__main__":
    main()
