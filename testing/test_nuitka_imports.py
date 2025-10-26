"""
Quick test script to check if backend module can be imported
Run this after building with Nuitka to verify the package structure
"""
import sys
import os
from pathlib import Path

print("=" * 60)
print("Testing Backend Import Capability")
print("=" * 60)
print()

# Check if running as frozen executable
is_frozen = getattr(sys, 'frozen', False)
print(f"Running as frozen executable: {is_frozen}")
print(f"sys.frozen: {getattr(sys, 'frozen', 'Not set')}")
print(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Not set')}")
print(f"sys.executable: {sys.executable}")
print(f"Current directory: {os.getcwd()}")
print()

print("sys.path (first 10 entries):")
for i, path in enumerate(sys.path[:10], 1):
    print(f"  {i}. {path}")
print()

# Try importing backend
print("Attempting to import 'backend' package...")
try:
    import backend
    print(f"SUCCESS: backend module imported")
    print(f"  backend.__file__: {getattr(backend, '__file__', 'No __file__ attribute')}")
    print(f"  backend.__path__: {getattr(backend, '__path__', 'No __path__ attribute')}")
except ImportError as e:
    print(f"FAILED: Could not import backend")
    print(f"  Error: {e}")
print()

# Try importing backend.app
print("Attempting to import 'backend.app' module...")
try:
    from backend import app
    print(f"SUCCESS: backend.app imported")
    print(f"  app.__file__: {getattr(app, '__file__', 'No __file__ attribute')}")
    print(f"  Has 'app' attribute: {hasattr(app, 'app')}")
except ImportError as e:
    print(f"FAILED: Could not import backend.app")
    print(f"  Error: {e}")
print()

# Check if backend directory exists
backend_dir = Path(__file__).parent / "backend"
print(f"Backend directory path: {backend_dir}")
print(f"Backend directory exists: {backend_dir.exists()}")
if backend_dir.exists():
    print(f"Backend directory contents:")
    for item in sorted(backend_dir.iterdir())[:15]:
        item_type = "DIR" if item.is_dir() else "FILE"
        print(f"  [{item_type}] {item.name}")
print()

print("=" * 60)
print("Test Complete")
print("=" * 60)
