"""
Build script for Chat Yapper Windows executable
Run this to create a distributable .exe file
"""
import os
import sys
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Set up build logging
def setup_build_logging():
    """Set up logging for the build process"""
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = logs_dir / f"build_{timestamp}.log"
    
    # Configure logging
    # File handler - logs everything
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Console handler - only errors and warnings
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler]
    )
    
    logger = logging.getLogger('ChatYapper.Build')
    logger.info(f"Build logging initialized - log file: {log_filename}")
    return logger

# Initialize logging
logger = setup_build_logging()

def log_important(message):
    """Log important messages that should appear in both console and file"""
    logger.warning(f"IMPORTANT: {message}")  # WARNING level ensures console output

def run_command(cmd, cwd=None):
    """Run a command and print output"""
    logger.info(f"Running command: {cmd}" + (f" (cwd: {cwd})" if cwd else ""))
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed with return code {result.returncode}: {cmd}")
        logger.error(f"Error output: {result.stderr}")
        print(f"❌ Command failed: {result.stderr}")
        if result.stdout:
            logger.info(f"Command stdout: {result.stdout}")
            print(f"📝 Output: {result.stdout}")
        sys.exit(1)
    if result.stdout.strip():
        logger.info(f"Command output: {result.stdout.strip()}")
        print(f"✅ Success")
    return result

def build_frontend():
    """Build the React frontend"""
    logger.info("Starting frontend build process")
    log_important("Building frontend...")
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found: {frontend_dir}")
        print("❌ Frontend directory not found")
        sys.exit(1)
    
    # Install dependencies and build
    run_command("npm install", cwd=frontend_dir)
    run_command("npm run build", cwd=frontend_dir)
    
    # Copy build to backend/public
    backend_public = Path("backend/public")
    if backend_public.exists():
        logger.info("Removing existing backend/public directory")
        shutil.rmtree(backend_public)
    
    logger.info(f"Copying frontend build from {frontend_dir / 'dist'} to {backend_public}")
    shutil.copytree(frontend_dir / "dist", backend_public)
    logger.info("Frontend built and copied successfully")
    log_important("Frontend built and copied to backend/public")

def create_executable():
    """Create executable with PyInstaller"""
    logger.info("Starting executable creation process")
    log_important("Creating Windows executable...")
    
    # Install Python dependencies first
    logger.info("Installing Python dependencies")
    print("📦 Installing Python dependencies...")
    if Path("requirements.txt").exists():
        logger.info("Found requirements.txt, installing from file")
        run_command("pip install -r requirements.txt")
    else:
        # Install core dependencies manually if requirements.txt doesn't exist
        logger.warning("requirements.txt not found, installing core dependencies manually")
        print("📦 Installing core dependencies...")
        run_command("pip install fastapi uvicorn sqlmodel aiohttp pillow edge-tts twitchio")
    
    # Verify critical dependencies are now available
    print("🔍 Verifying dependencies...")
    try:
        import uvicorn
        print(f"✅ uvicorn found: {uvicorn.__version__}")
    except ImportError:
        print("❌ uvicorn still not found after installation")
        sys.exit(1)

    try:
        import fastapi
        print(f"✅ fastapi found: {fastapi.__version__}")
    except ImportError:
        print("❌ fastapi still not found after installation")
        sys.exit(1)
    
    # Install PyInstaller
    run_command("pip install pyinstaller")
    
    # Check for icon file
    icon_path = None
    for icon_file in ['icon.ico', 'logo.ico', 'app.ico']:
        if Path(icon_file).exists():
            icon_path = icon_file
            print(f"✅ Found icon: {icon_file}")
            break
    
    if not icon_path:
        print("ℹ️  No icon file found - executable will use default icon")
    
    # Create spec file for PyInstaller
    icon_line = f"icon='{icon_path}'" if icon_path else "icon=None"
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Define paths and collect all files
import glob
backend_dir = Path('backend')

# Collect all backend Python files
backend_py_files = glob.glob('backend/*.py')
backend_py_data = [(f, 'backend') for f in backend_py_files]

# Collect all public directory files recursively
public_files = []
for root, dirs, files in os.walk('backend/public'):
    for file in files:
        src_path = os.path.join(root, file)
        # Convert to relative path for destination
        rel_path = os.path.relpath(src_path, 'backend')
        dest_dir = os.path.dirname(rel_path)
        if dest_dir:
            dest_path = os.path.join('backend', dest_dir)
        else:
            dest_path = 'backend'
        public_files.append((src_path, dest_path))

data_files = backend_py_data + public_files + [
    ('backend/settings_defaults.json', 'backend'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        # Uvicorn and all its components
        'uvicorn',
        'uvicorn.main',
        'uvicorn.server',
        'uvicorn.config',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.middleware',
        'uvicorn.middleware.proxy_headers',
        'uvicorn.supervisors',
        'uvicorn.supervisors.basereload',
        'uvicorn.supervisors.multiprocess',
        'uvicorn.supervisors.statreload',
        'uvicorn.supervisors.watchgodreload',
        # FastAPI and dependencies
        'fastapi',
        'fastapi.applications',
        'fastapi.routing',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.staticfiles',
        'fastapi.responses',
        'fastapi.exceptions',
        'starlette',
        'starlette.applications',
        'starlette.routing',
        'starlette.middleware',
        'starlette.responses',
        'starlette.staticfiles',
        'starlette.websockets',
        # Other dependencies
        'pydantic',
        'pydantic.main',
        'anyio',
        'sniffio',
        'h11',
        'websockets',
        'websockets.server',
        'websockets.client',
        'edge_tts',
        'aiohttp',
        'aiohttp.client',
        'aiohttp.web',
        'PIL',
        'PIL.Image',
        'twitchio',
        'sqlmodel',
        'sqlalchemy',
        'sqlalchemy.engine',
        'sqlalchemy.pool',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ChatYapper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_line}
)
'''
    
    with open('ChatYapper.spec', 'w') as f:
        f.write(spec_content)
    
    # Build with PyInstaller using Python module execution (most reliable)
    print("🛠️  Running PyInstaller...")
    try:
        # First try as a Python module (most reliable method)
        run_command("python -m PyInstaller --clean ChatYapper.spec")
    except:
        try:
            # Try direct command
            run_command("pyinstaller --clean ChatYapper.spec")
        except:
            try:
                # Try with pip show to find the scripts directory
                result = subprocess.run("pip show pyinstaller", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    # PyInstaller is installed, but maybe not in PATH
                    print("📝 PyInstaller is installed but not in PATH, trying alternative methods...")
                    
                    # Try using python -c to execute PyInstaller directly
                    run_command('python -c "import PyInstaller.__main__; PyInstaller.__main__.run([\'--clean\', \'ChatYapper.spec\'])"')
                else:
                    print("❌ PyInstaller not found. Please install it manually: pip install pyinstaller")
                    sys.exit(1)
            except Exception as e:
                print(f"❌ Failed to run PyInstaller: {e}")
                print("💡 Try running this manually: python -m PyInstaller --clean ChatYapper.spec")
                sys.exit(1)
    
    # Check if the executable was created successfully
    exe_path = Path("dist/ChatYapper.exe")
    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
        logger.info(f"Executable created successfully: {exe_path} ({file_size:.1f} MB)")
        print(f"✅ Executable created: dist/ChatYapper.exe ({file_size:.1f} MB)")
    else:
        logger.error("Executable not found after build process completed")
        print("❌ Executable not found after build")
        sys.exit(1)
    
    # Clean up build artifacts (optional)
    cleanup_paths = ["build", "ChatYapper.spec"]
    logger.info("Cleaning up build artifacts")
    for path in cleanup_paths:
        if Path(path).exists():
            logger.info(f"Removing {path}")
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                Path(path).unlink()
    logger.info("Build artifacts cleaned up successfully")
    print("🧹 Cleaned up build artifacts")

def main():
    logger.info("=== Starting Chat Yapper build process ===")
    print("🏗️  Building Chat Yapper for Windows distribution...")
    print()
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        logger.error("main.py not found - script must be run from Chat Yapper root directory")
        print("❌ Please run this script from the Chat Yapper root directory")
        sys.exit(1)
    
    try:
        # Build frontend
        build_frontend()
        
        # Create executable
        create_executable()
        
        logger.info("=== Build process completed successfully ===")
        log_important("Build complete!")
        print()
        print("📁 Executable location: dist/ChatYapper.exe")
        print("📋 Distribution folder: dist/")
        print()
        print("📤 To distribute:")
        print("   1. Copy the dist/ChatYapper.exe file")
        print("   2. Users can run it directly - no installation needed!")
        print("   3. It will start a local server and open their browser")
        
    except Exception as e:
        logger.error(f"Build process failed: {e}", exc_info=True)
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
