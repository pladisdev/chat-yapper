"""
Build script for Chat Yapper Windows executable
Run this to create a distributable .exe file
"""
import os
import sys
import shutil
import subprocess
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
    print("Loaded .env file for build configuration")
except ImportError:
    print("python-dotenv not installed, using system environment only")
    print("   Run: pip install python-dotenv")
except Exception as e:
    print(f"Could not load .env file: {e}")
    print("   Continuing with system environment variables...")

def is_executable():
    """
    Detect if we're running as a PyInstaller executable.
    Returns True if running from .exe, False if running from source.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

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
    
    # Console handler - adjust level based on environment
    console_handler = logging.StreamHandler(sys.stdout)
    if is_executable():
        # Production (.exe) - only show errors
        console_handler.setLevel(logging.ERROR)
    else:
        # Development - show warnings and errors
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
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed with return code {result.returncode}: {cmd}")
        logger.error(f"Error output: {result.stderr}")
        print(f"Command failed: {result.stderr}")
        if result.stdout:
            logger.info(f"Command stdout: {result.stdout}")
            print(f"Output: {result.stdout}")
        sys.exit(1)
    if result.stdout.strip():
        logger.info(f"Command output: {result.stdout.strip()}")
        print(f"Success")
    return result

def build_frontend():
    """Build the React frontend"""
    logger.info("Starting frontend build process")
    log_important("Building frontend...")
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        logger.error(f"Frontend directory not found: {frontend_dir}")
        print("Frontend directory not found")
        sys.exit(1)
    
    # Install dependencies and build
    # Note: vite.config.js is configured to build directly to backend/public
    run_command("npm install", cwd=frontend_dir)
    run_command("npm run build", cwd=frontend_dir)
    
    # Verify the build output exists
    backend_public = Path("backend/public")
    if not backend_public.exists() or not (backend_public / "index.html").exists():
        logger.error(f"Frontend build failed - {backend_public / 'index.html'} not found")
        print("Frontend build failed - output not found in backend/public")
        sys.exit(1)
    
    logger.info("Frontend built successfully")
    log_important("Frontend built to backend/public")

def create_embedded_env_config():
    """Create embedded environment configuration for the executable"""
    logger.info("Creating embedded environment configuration...")
    
    # Read Twitch environment variables from .env
    twitch_client_id = os.environ.get("TWITCH_CLIENT_ID", "")
    twitch_client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "")
    
    # Read YouTube environment variables from .env
    youtube_client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    youtube_client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    
    logger.info(f"Found Twitch Client ID: {'Yes' if twitch_client_id else 'No'}")
    logger.info(f"Found Twitch Client Secret: {'Yes' if twitch_client_secret else 'No'}")
    logger.info(f"Found YouTube Client ID: {'Yes' if youtube_client_id else 'No'}")
    logger.info(f"Found YouTube Client Secret: {'Yes' if youtube_client_secret else 'No'}")
    
    # Create embedded config Python file
    config_content = f'''"""
Embedded environment configuration for Chat Yapper executable.
Generated during build process from .env file.
"""

# Twitch OAuth Configuration embedded from build-time .env file
EMBEDDED_TWITCH_CLIENT_ID = "{twitch_client_id}"
EMBEDDED_TWITCH_CLIENT_SECRET = "{twitch_client_secret}"

# YouTube OAuth Configuration embedded from build-time .env file
EMBEDDED_YOUTUBE_CLIENT_ID = "{youtube_client_id}"
EMBEDDED_YOUTUBE_CLIENT_SECRET = "{youtube_client_secret}"

def get_embedded_env(key, default=""):
    """Get embedded environment variable by key"""
    embedded_vars = {{
        "TWITCH_CLIENT_ID": EMBEDDED_TWITCH_CLIENT_ID,
        "TWITCH_CLIENT_SECRET": EMBEDDED_TWITCH_CLIENT_SECRET,
        "YOUTUBE_CLIENT_ID": EMBEDDED_YOUTUBE_CLIENT_ID,
        "YOUTUBE_CLIENT_SECRET": EMBEDDED_YOUTUBE_CLIENT_SECRET,
    }}
    return embedded_vars.get(key, default)
'''
    
    # Write to backend directory so it gets included in the build
    config_path = Path("backend/embedded_config.py")
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    logger.info(f"Created embedded config: {config_path}")
    log_important(f"Embedded Twitch config {'with' if twitch_client_id else 'without'} credentials")
    log_important(f"Embedded YouTube config {'with' if youtube_client_id else 'without'} credentials")
    
    return config_path

def create_executable():
    """Create executable with PyInstaller"""
    logger.info("Starting executable creation process")
    log_important("Creating Windows executable...")
    
    # Create embedded environment configuration first
    create_embedded_env_config()
    
    # Install Python dependencies first
    logger.info("Installing Python dependencies")
    print("Installing Python dependencies...")
    if Path("requirements.txt").exists():
        logger.info("Found requirements.txt, installing from file")
        run_command("pip install -r requirements.txt")
    else:
        # Install core dependencies manually if requirements.txt doesn't exist
        logger.warning("requirements.txt not found, installing core dependencies manually")
        print("Installing core dependencies...")
        run_command("pip install fastapi uvicorn sqlmodel aiohttp pillow edge-tts twitchio boto3")
    
    # Verify critical dependencies are now available
    print("Verifying dependencies...")
    try:
        import uvicorn
        print(f"uvicorn found: {uvicorn.__version__}")
    except ImportError:
        print("uvicorn still not found after installation")
        sys.exit(1)

    try:
        import fastapi
        print(f"fastapi found: {fastapi.__version__}")
    except ImportError:
        print("fastapi still not found after installation")
        sys.exit(1)
    
    try:
        import twitchio
        print(f"twitchio found: {twitchio.__version__}")
    except ImportError:
        print("twitchio still not found after installation")
        sys.exit(1)
    
    # Install PyInstaller
    run_command("pip install pyinstaller")
    
    # Check for icon file
    icon_path = None
    for icon_file in ['icon.ico', 'logo.ico', 'app.ico']:
        if Path(icon_file).exists():
            icon_path = icon_file
            print(f"Found icon: {icon_file}")
            break
    
    if not icon_path:
        print("No icon file found - executable will use default icon")
    
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

# Collect all modules directory files (Python and JSON)
modules_files = []
for root, dirs, files in os.walk('backend/modules'):
    for file in files:
        if file.endswith('.py') or file.endswith('.json'):
            src_path = os.path.join(root, file)
            # Convert to relative path for destination
            rel_path = os.path.relpath(src_path, 'backend')
            dest_dir = os.path.dirname(rel_path)
            if dest_dir:
                dest_path = os.path.join('backend', dest_dir)
            else:
                dest_path = 'backend'
            modules_files.append((src_path, dest_path))

# Collect all routers directory files
routers_files = []
for root, dirs, files in os.walk('backend/routers'):
    for file in files:
        if file.endswith('.py'):
            src_path = os.path.join(root, file)
            # Convert to relative path for destination
            rel_path = os.path.relpath(src_path, 'backend')
            dest_dir = os.path.dirname(rel_path)
            if dest_dir:
                dest_path = os.path.join('backend', dest_dir)
            else:
                dest_path = 'backend'
            routers_files.append((src_path, dest_path))

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

data_files = backend_py_data + modules_files + routers_files + public_files + [
    # settings_defaults.json is now collected automatically via modules_files
    ('backend/embedded_config.py', 'backend'),
]

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all jaraco and pkg_resources submodules
jaraco_modules = collect_submodules('jaraco')
pkg_resources_modules = collect_submodules('pkg_resources')

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
        'asyncio',
        'concurrent',
        'concurrent.futures',
        'websockets',
        'websockets.server',
        'websockets.client',
        'websockets.protocol',
        'websockets.exceptions',
        'edge_tts',
        'edge_tts.communicate',
        'edge_tts.exceptions',
        'aiohttp',
        'aiohttp.client',
        'aiohttp.web',
        'PIL',
        'PIL.Image',
        'twitchio',
        'twitchio.ext',
        'twitchio.ext.commands',
        'twitchio.websocket',
        'twitchio.client',
        'twitchio.channel',
        'twitchio.user',
        'twitchio.message',
        'twitchio.errors',
        'sqlmodel',
        'sqlalchemy',
        'sqlalchemy.engine',
        'sqlalchemy.pool',
        'sqlite3',
        # AWS boto3 for Amazon Polly TTS
        'boto3',
        'boto3.client',
        'boto3.session',
        'botocore',
        'botocore.client',
        'botocore.session',
        'botocore.config',
        'botocore.exceptions',
        'botocore.exceptions.BotoCoreError',
        'botocore.exceptions.ClientError',
        # Google API for YouTube integration
        'google',
        'google.auth',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google.oauth2',
        'google.oauth2.credentials',
        'google_auth_oauthlib',
        'google_auth_oauthlib.flow',
        'googleapiclient',
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'googleapiclient.http',
        # Fix for jaraco.text missing dependency
        'jaraco',
        'jaraco.text',
        'jaraco.functools',
        'jaraco.context',
        'pkg_resources',
        'pkg_resources._vendor',
        'pkg_resources._vendor.packaging',
        'pkg_resources._vendor.packaging.version',
        'setuptools',
        'setuptools.dist',
        # Embedded configuration
        'embedded_config',
    ] + jaraco_modules + pkg_resources_modules,
    hookspath=[],
    hooksconfig={{
        # Configure matplotlib hook to avoid numpy issues
        'matplotlib': {{
            'backends': [],  # Don't include any matplotlib backends
        }},
    }},
    runtime_hooks=[],
    excludes=[
        # Exclude matplotlib and related packages that cause numpy import issues
        'matplotlib',
        'matplotlib.pyplot',
        'pandas',
        'scipy',
        'sklearn',
        'jupyter',
        'notebook', 
        'IPython',
        # Exclude other heavy packages we don't need
        'tensorflow',
        'torch',
        'numpy.distutils',
        'pip',
        'wheel',
        'distutils',
        # Exclude test and dev packages
        'pytest',
        'unittest',
        'test',
        'tests',
        # Exclude railroad (used by pyparsing for diagram generation, not needed at runtime)
        'railroad',
    ],
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
    print("Running PyInstaller...")
    try:
        # First try as a Python module (most reliable method) with additional exclusions
        cmd = "python -m PyInstaller --clean --exclude-module matplotlib --exclude-module numpy --exclude-module pandas ChatYapper.spec"
        run_command(cmd)
    except:
        try:
            # Try direct command with exclusions
            run_command("pyinstaller --clean --exclude-module matplotlib --exclude-module numpy --exclude-module pandas ChatYapper.spec")
        except:
            try:
                # Try with pip show to find the scripts directory
                result = subprocess.run("pip show pyinstaller", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    # PyInstaller is installed, but maybe not in PATH
                    print("PyInstaller is installed but not in PATH, trying alternative methods...")
                    
                    # Try using python -c to execute PyInstaller directly
                    run_command('python -c "import PyInstaller.__main__; PyInstaller.__main__.run([\'--clean\', \'ChatYapper.spec\'])"')
                else:
                    print("PyInstaller not found. Please install it manually: pip install pyinstaller")
                    sys.exit(1)
            except Exception as e:
                print(f"Failed to run PyInstaller: {e}")
                print("Try running this manually: python -m PyInstaller --clean ChatYapper.spec")
                sys.exit(1)
    
    # Check if the executable was created successfully
    exe_path = Path("dist/ChatYapper.exe")
    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
        logger.info(f"Executable created successfully: {exe_path} ({file_size:.1f} MB)")
        print(f"Executable created: dist/ChatYapper.exe ({file_size:.1f} MB)")
    else:
        logger.error("Executable not found after build process completed")
        print("Executable not found after build")
        sys.exit(1)
    
    # Clean up build artifacts (optional)
    cleanup_paths = ["build", "ChatYapper.spec", "backend/embedded_config.py"]
    logger.info("Cleaning up build artifacts")
    for path in cleanup_paths:
        if Path(path).exists():
            logger.info(f"Removing {path}")
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                Path(path).unlink()
    logger.info("Build artifacts cleaned up successfully")
    print("Cleaned up build artifacts")

def test_executable():
    """Test the built executable to ensure it works correctly"""
    logger.info("=== Starting executable validation tests ===")
    print()
    print("Testing built executable...")
    
    exe_path = Path("dist") / "ChatYapper.exe"
    if not exe_path.exists():
        logger.error(f"Executable not found at {exe_path}")
        print("[ERROR] Executable file not found")
        return False
    
    print(f"Found executable: {exe_path}")
    print(f"File size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    all_tests_passed = True
    
    # Test 1: Basic startup test
    print("\nTest 1: Basic startup validation...")
    try:
        import subprocess
        import time
        import signal
        
        # Start the executable with a timeout
        logger.info("Starting executable for startup test")
        process = subprocess.Popen(
            [str(exe_path)], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        # Wait a few seconds to see if it starts properly
        time.sleep(3)
        
        if process.poll() is None:
            print("[PASS] Executable started successfully")
            logger.info("Executable startup test passed")
            
            # Test 2: HTTP endpoint test
            print("\nTest 2: HTTP server validation...")
            try:
                import urllib.request
                import json
                
                # Wait a bit more for the server to be ready
                time.sleep(2)
                
                # Test the status endpoint
                response = urllib.request.urlopen("http://localhost:8000/api/status", timeout=5)
                if response.getcode() == 200:
                    data = json.loads(response.read().decode())
                    if data.get("status") == "running":
                        print("[PASS] HTTP server is responding correctly")
                        logger.info("HTTP server validation passed")
                    else:
                        print("[FAIL] HTTP server returned unexpected response")
                        logger.error(f"HTTP server returned: {data}")
                        all_tests_passed = False
                else:
                    print(f"[FAIL] HTTP server returned status code: {response.getcode()}")
                    logger.error(f"HTTP server validation failed with code {response.getcode()}")
                    all_tests_passed = False
                    
            except Exception as e:
                print(f"[FAIL] HTTP server test failed: {e}")
                logger.error(f"HTTP server validation failed: {e}")
                all_tests_passed = False
            
            # Test 3: TTS functionality test
            print("\nTest 3: TTS functionality validation...")
            try:
                # Test TTS endpoint with simulation
                test_data = {
                    'user': 'BuildTester',
                    'text': 'Build validation test message',
                    'eventType': 'chat'
                }
                
                data = urllib.parse.urlencode(test_data).encode()
                req = urllib.request.Request(
                    "http://localhost:8000/api/simulate", 
                    data=data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                response = urllib.request.urlopen(req, timeout=10)
                if response.getcode() == 200:
                    result = json.loads(response.read().decode())
                    if result.get("ok"):
                        print("[PASS] TTS functionality is working")
                        logger.info("TTS validation passed")
                    else:
                        print(f"[FAIL] TTS test failed: {result.get('error', 'Unknown error')}")
                        logger.error(f"TTS validation failed: {result}")
                        all_tests_passed = False
                else:
                    print(f"[FAIL] TTS test returned status code: {response.getcode()}")
                    logger.error(f"TTS validation failed with code {response.getcode()}")
                    all_tests_passed = False
                    
            except Exception as e:
                print(f"[FAIL] TTS test failed: {e}")
                logger.error(f"TTS validation failed: {e}")
                all_tests_passed = False
                
        else:
            print("[FAIL] Executable failed to start or crashed immediately")
            logger.error("Executable startup test failed - process terminated")
            all_tests_passed = False
            
        # Clean shutdown
        if process.poll() is None:
            print("\nShutting down test instance...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
                process.wait(timeout=2)
            logger.info("Test process terminated cleanly")
            
    except Exception as e:
        print(f"[FAIL] Startup test failed: {e}")
        logger.error(f"Startup validation failed: {e}")
        all_tests_passed = False
    
    # Test 4: Dependency validation
    print("\nTest 4: Dependency validation...")
    try:
        # Check that the executable exists (onefile build)
        dist_dir = Path("dist")
        expected_patterns = [
            "ChatYapper.exe"
        ]
        
        missing_items = []
        for pattern in expected_patterns:
            if not any(dist_dir.glob(pattern)):
                missing_items.append(pattern)
        
        if not missing_items:
            print("[PASS] All expected files and directories are present")
            logger.info("Dependency validation passed")
        else:
            print(f"[FAIL] Missing expected items: {missing_items}")
            logger.error(f"Missing dependencies: {missing_items}")
            all_tests_passed = False
            
    except Exception as e:
        print(f"[FAIL] Dependency validation failed: {e}")
        logger.error(f"Dependency validation failed: {e}")
        all_tests_passed = False
    
    # Final results
    print(f"\n{'='*50}")
    if all_tests_passed:
        print("All validation tests PASSED!")
        print("   The executable is ready for distribution")
        logger.info("All validation tests passed")
    else:
        print("Some validation tests FAILED!")
        print("   Review the errors above before distributing")
        logger.error("Some validation tests failed")
    print(f"{'='*50}")
    
    return all_tests_passed

def main():
    # Check for command line arguments
    test_only = "--test-only" in sys.argv
    
    if test_only:
        logger.info("=== Running executable validation tests only ===")
        print("Testing existing executable...")
        print()
        
        if test_executable():
            print("\n[SUCCESS] All tests passed!")
            sys.exit(0)
        else:
            print("\n[ERROR] Tests failed!")
            sys.exit(1)
    
    logger.info("=== Starting Chat Yapper build process ===")
    print(" Building Chat Yapper for Windows distribution...")
    print()
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        logger.error("main.py not found - script must be run from Chat Yapper root directory")
        print("Please run this script from the Chat Yapper root directory")
        sys.exit(1)
    
    try:
        # Build frontend
        build_frontend()
        
        # Create executable
        create_executable()
        
        logger.info("=== Build process completed successfully ===")
        log_important("Build complete!")
        
        # Test the built executable
        if test_executable():
            logger.info("=== Build validation tests PASSED ===")
            log_important("All tests passed - executable is working correctly!")
            print()
            print("[SUCCESS] Build validation successful!")
        else:
            logger.error("=== Build validation tests FAILED ===")
            log_important("Build validation failed - executable may have issues")
            print()
            print("[ERROR] Build validation failed!")
            print("   Check the logs for details")
            return False
            
        print()
        print("Executable location: dist/ChatYapper.exe")
        print("Distribution folder: dist/")
        print()
        print("To distribute:")
        print("   1. Copy the dist/ChatYapper.exe file")
        print("   2. Users can run it directly - no installation needed!")
        print("   3. It will start a local server and open their browser")
        print()
        print("TIP: Run 'python build.py --test-only' to test an existing executable")
        
    except Exception as e:
        logger.error(f"Build process failed: {e}", exc_info=True)
        print(f"Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("Chat Yapper Build Script")
        print("=======================")
        print()
        print("Usage:")
        print("  python build.py              Build the application and run validation tests")
        print("  python build.py --test-only  Test an existing executable without rebuilding")
        print("  python build.py --help       Show this help message")
        print()
        print("The build script will:")
        print("  1. Build the React frontend")
        print("  2. Create Windows executable with PyInstaller")
        print("  3. Run comprehensive validation tests")
        print("  4. Report success/failure with detailed logs")
        print()
        sys.exit(0)
    
    main()
