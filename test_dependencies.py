"""
Test script to verify Chat Yapper backend dependencies
Run this to check if all required packages are installed
"""
import sys
from pathlib import Path

def test_imports():
    """Test all required imports"""
    print("🧪 Testing Chat Yapper dependencies...")
    print()
    
    tests = [
        ("FastAPI", "fastapi"),
        ("Uvicorn", "uvicorn"),
        ("SQLModel", "sqlmodel"),
        ("Pydantic", "pydantic"),
        ("AIOHTTP", "aiohttp"),
        ("Edge TTS", "edge_tts"),
        ("TwitchIO", "twitchio"),
        ("Pillow", "PIL"),
        ("Python Multipart", "python_multipart"),
    ]
    
    failed_imports = []
    
    for name, module in tests:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError as e:
            print(f"❌ {name}: {e}")
            failed_imports.append(module)
    
    print()
    
    if failed_imports:
        print("❌ Some dependencies are missing!")
        print("📦 Install missing packages with:")
        print("   pip install -r requirements.txt")
        print()
        print("Missing packages:")
        for module in failed_imports:
            print(f"   - {module}")
        return False
    else:
        print("✅ All dependencies are installed!")
        return True

def test_backend_import():
    """Test importing the backend app"""
    print("🧪 Testing backend import...")
    
    backend_dir = Path(__file__).parent / "backend"
    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        return False
    
    # Add backend to path and try importing
    sys.path.insert(0, str(backend_dir))
    
    try:
        import app
        print("✅ Backend app imported successfully")
        print(f"📍 App object: {app.app}")
        return True
    except Exception as e:
        print(f"❌ Failed to import backend app: {e}")
        return False

def main():
    print("🔍 Chat Yapper Dependency Checker")
    print("=" * 40)
    print()
    
    # Test imports
    imports_ok = test_imports()
    print()
    
    # Test backend import
    backend_ok = test_backend_import()
    print()
    
    if imports_ok and backend_ok:
        print("🎉 All tests passed! Chat Yapper should work correctly.")
        print("▶️  Run 'python main.py' to start Chat Yapper")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("💡 Make sure you're in the Chat Yapper root directory")
        print("💡 Make sure all dependencies are installed")

if __name__ == "__main__":
    main()
