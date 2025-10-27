"""
Build script for Chat Yapper using Nuitka
Nuitka compiles Python to native C code, resulting in FAR fewer antivirus false positives
compared to PyInstaller (0-2 detections vs 10-20+)

Run: python deployment/build-nuitka.py
"""
import os
import sys
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Change to project root directory
script_dir = Path(__file__).parent
project_root = script_dir.parent
os.chdir(project_root)
print(f"Working directory: {project_root}")

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    print("⚠ python-dotenv not installed (pip install python-dotenv)")
except Exception as e:
    print(f"⚠ Could not load .env: {e}")

# Set up logging
def setup_logging():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"build_nuitka_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('ChatYapper.NuitkaBuild')
    logger.info(f"Nuitka build log: {log_file}")
    return logger

logger = setup_logging()

def run_command(cmd, cwd=None):
    """Run a command and handle errors"""
    logger.info(f"Running: {cmd}" + (f" (cwd: {cwd})" if cwd else ""))
    print(f"→ {cmd}")
    
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Error: {result.stderr}")
        print(f"✗ Failed: {result.stderr}")
        sys.exit(1)
    
    if result.stdout.strip():
        logger.debug(f"Output: {result.stdout.strip()}")
    
    print("✓ Success")
    return result

def check_requirements():
    """Check if required tools are installed"""
    print("\n=== Checking Requirements ===")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("✗ Python 3.9+ required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check Nuitka
    try:
        result = subprocess.run(f'"{sys.executable}" -m nuitka --version', shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"✓ Nuitka {version}")
        else:
            print("✗ Nuitka not found")
            print(f"  Install: {sys.executable} -m pip install nuitka")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Nuitka check failed: {e}")
        sys.exit(1)
    
    # Check for C compiler (MinGW64)
    try:
        result = subprocess.run("gcc --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ GCC compiler found")
        else:
            print("⚠ GCC not found - Nuitka will download MinGW64 automatically")
    except:
        print("⚠ GCC not found - Nuitka will download MinGW64 automatically")
    
    print()

def build_frontend():
    """Build the React frontend"""
    print("\n=== Building Frontend ===")
    logger.info("Starting frontend build")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        logger.error("Frontend directory not found")
        print("✗ Frontend directory not found")
        sys.exit(1)
    
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        run_command("npm install", cwd=frontend_dir)
    
    # Build frontend
    print("Building React app...")
    run_command("npm run build", cwd=frontend_dir)
    
    # Vite builds directly to backend/public (configured in vite.config.js)
    public_dir = Path("backend/public")
    if public_dir.exists() and (public_dir / "index.html").exists():
        logger.info("Frontend build completed - files in backend/public")
        print("✓ Frontend built to backend/public")
    else:
        logger.error("Frontend build directory not found or incomplete")
        print("✗ Frontend build failed - backend/public/index.html not found")
        sys.exit(1)

def embed_credentials():
    """Embed credentials from .env into the build"""
    print("\n=== Embedding Credentials ===")
    logger.info("Creating embedded_config.py")
    
    credentials = {
        'TWITCH_CLIENT_ID': os.getenv('TWITCH_CLIENT_ID', ''),
        'TWITCH_CLIENT_SECRET': os.getenv('TWITCH_CLIENT_SECRET', ''),
        'YOUTUBE_CLIENT_ID': os.getenv('YOUTUBE_CLIENT_ID', ''),
        'YOUTUBE_CLIENT_SECRET': os.getenv('YOUTUBE_CLIENT_SECRET', ''),
    }
    
    # Check if any credentials are set
    has_creds = any(v for v in credentials.values())
    
    if has_creds:
        print("✓ Found credentials in .env")
        logger.info("Credentials found, embedding into build")
    else:
        print("⚠ No credentials found in .env file")
        logger.warning("No credentials found - OAuth features may not work")
    
    # Create embedded_config.py
    config_file = Path("backend/embedded_config.py")
    with open(config_file, 'w') as f:
        f.write('"""Embedded configuration from build time"""\n\n')
        for key, value in credentials.items():
            f.write(f'{key} = {repr(value)}\n')
    
    logger.info(f"Created {config_file}")

def build_with_nuitka():
    """Build executable using Nuitka"""
    print("\n=== Building with Nuitka ===")
    logger.info("Starting Nuitka compilation")
    
    # Check for icon
    icon_path = None
    for icon_file in ['assets/icon.ico', 'assets/logo.ico']:
        if Path(icon_file).exists():
            icon_path = icon_file
            print(f"✓ Using icon: {icon_file}")
            break
    
    if not icon_path:
        print("⚠ No icon found - using default")
    
    # Create dist directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Build Nuitka command
    cmd = [
        sys.executable, "-m", "nuitka",
        "--mingw64",  # Use MinGW64 compiler
        "--standalone",  # Include all dependencies
        "--onefile",  # Single executable
        "--enable-plugin=anti-bloat",  # Reduce size
        "--assume-yes-for-downloads",  # Auto-download dependencies
        "--windows-console-mode=force",  # Show console window
        "--follow-imports",  # Follow all imports
        # CRITICAL: Include backend as a proper Python package
        # This makes "from backend import app" work in the frozen executable
        "--include-package=backend",  # Include entire backend package
        "--include-package=backend.modules",  # Include modules subpackage
        "--include-package=backend.routers",  # Include routers subpackage
        # Include static files and data
        "--include-data-dir=backend/public=backend/public",  # Include frontend static files
        # Exclude test and unnecessary packages to reduce size
        "--nofollow-import-to=backend.tests",  # Exclude test files
        "--nofollow-import-to=pytest",  # Exclude pytest
        "--nofollow-import-to=testing",  # Exclude testing directory
        "--nofollow-import-to=matplotlib",  # Exclude matplotlib (not used)
        "--nofollow-import-to=numpy",  # Exclude numpy (unless needed)
        "--nofollow-import-to=pandas",  # Exclude pandas (not used)
        "--nofollow-import-to=PIL.ImageTk",  # Exclude Tkinter image support
        "--nofollow-import-to=tkinter",  # Exclude tkinter (not used)
        # Explicitly include critical runtime modules that may be missed
        # Uvicorn web server components
        "--include-module=uvicorn",
        "--include-module=uvicorn.loops.auto",
        "--include-module=uvicorn.protocols.http.auto",
        "--include-module=uvicorn.protocols.http.h11_impl",
        "--include-module=uvicorn.protocols.websockets.auto",
        "--include-module=uvicorn.protocols.websockets.websockets_impl",
        "--include-module=uvicorn.lifespan.on",
        # FastAPI and Starlette components
        "--include-module=fastapi",
        "--include-module=starlette.middleware.cors",
        "--include-module=starlette.staticfiles",
        "--include-module=h11",  # HTTP/1.1 protocol
        "--include-module=websockets",  # WebSocket library
        # Application-specific modules
        "--include-module=twitchio",
        "--include-module=twitchio.ext.commands",
        "--include-module=edge_tts",
        "--include-module=sqlmodel",
        "--include-module=sqlalchemy.engine",
        "--include-module=sqlalchemy.pool",
        "--include-module=aiohttp",
        "--include-module=boto3",  # AWS SDK (for Polly TTS)
        "--include-module=botocore",
        "--include-module=google.auth",  # Google auth (for YouTube)
        "--include-module=google.oauth2",
        "--include-module=googleapiclient",
        "--output-dir=dist",  # Output directory
        "--output-filename=ChatYapper.exe",  # Output filename
    ]
    
    # Add icon if available
    if icon_path:
        cmd.append(f"--windows-icon-from-ico={icon_path}")
    
    # Add main file
    cmd.append("main.py")
    
    # Join command for display
    cmd_str = " ".join(cmd)
    
    print("\nCompiling Python to C code (this may take 5-15 minutes)...")
    print("Progress will be shown below:\n")
    
    logger.info(f"Nuitka command: {cmd_str}")
    
    # Run Nuitka with real-time output
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output
        for line in process.stdout:
            print(line, end='')
            logger.debug(line.strip())
        
        process.wait()
        
        if process.returncode != 0:
            logger.error("Nuitka compilation failed")
            print("\n✗ Nuitka compilation failed")
            sys.exit(1)
        
        print("\n✓ Nuitka compilation successful")
        logger.info("Nuitka compilation completed successfully")
        
    except Exception as e:
        logger.error(f"Nuitka compilation error: {e}")
        print(f"\n✗ Nuitka error: {e}")
        sys.exit(1)
    
    # Check if executable was created
    exe_path = dist_dir / "ChatYapper.exe"
    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)
        logger.info(f"Executable created: {exe_path} ({file_size:.1f} MB)")
        print(f"\n✓ Executable created: {exe_path}")
        print(f"  Size: {file_size:.1f} MB")
        return exe_path
    else:
        logger.error("Executable not found after build")
        print("\n✗ Executable not found")
        sys.exit(1)

def generate_checksums(exe_path):
    """Generate SHA256 checksums"""
    print("\n=== Generating Checksums ===")
    logger.info("Generating checksums")
    
    try:
        import hashlib
        
        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        with open(exe_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        checksum = sha256_hash.hexdigest()
        
        # Save to file
        checksum_file = exe_path.parent / "ChatYapper.exe.sha256"
        with open(checksum_file, "w") as f:
            f.write(f"{checksum}  ChatYapper.exe\n")
        
        # Create detailed verification file
        metadata_file = exe_path.parent / "CHECKSUMS.txt"
        with open(metadata_file, "w") as f:
            f.write("Chat Yapper - File Verification\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Build Method: Nuitka (Native Compilation)\n")
            f.write(f"Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"File: ChatYapper.exe\n")
            f.write(f"Size: {exe_path.stat().st_size:,} bytes ({exe_path.stat().st_size / (1024*1024):.2f} MB)\n")
            f.write(f"\nSHA256: {checksum}\n")
            f.write("\nTo verify:\n")
            f.write("  Windows: certutil -hashfile ChatYapper.exe SHA256\n")
            f.write("  Linux:   sha256sum ChatYapper.exe\n")
            f.write("  Mac:     shasum -a 256 ChatYapper.exe\n")
            f.write("\nNote: This executable was built with Nuitka (native C compilation)\n")
            f.write("      which has significantly fewer antivirus false positives\n")
            f.write("      compared to PyInstaller.\n")
        
        print(f"✓ SHA256: {checksum}")
        print(f"✓ Saved to: {checksum_file}")
        print(f"✓ Verification file: {metadata_file}")
        logger.info(f"Checksums generated: {checksum}")
        
    except Exception as e:
        logger.error(f"Checksum generation failed: {e}")
        print(f"⚠ Warning: Could not generate checksums: {e}")

def cleanup():
    """Clean up build artifacts"""
    print("\n=== Cleaning Up ===")
    logger.info("Cleaning up build artifacts")
    
    cleanup_paths = [
        "backend/embedded_config.py",
        "main.build",
        "main.dist",
        "main.onefile-build",
    ]
    
    for path_str in cleanup_paths:
        path = Path(path_str)
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                logger.info(f"Removed: {path}")
            except Exception as e:
                logger.warning(f"Could not remove {path}: {e}")
    
    print("✓ Cleanup complete")

def main():
    print("=" * 60)
    print("Chat Yapper - Nuitka Build")
    print("=" * 60)
    print("\nBuilding with Nuitka for minimal antivirus false positives")
    print("This compiles Python to native C code (takes longer, better result)\n")
    
    logger.info("=== Starting Nuitka build process ===")
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        logger.error("main.py not found")
        print("✗ Please run from Chat Yapper root directory")
        sys.exit(1)
    
    try:
        # Check requirements
        check_requirements()
        
        # Build steps
        build_frontend()
        embed_credentials()
        exe_path = build_with_nuitka()
        generate_checksums(exe_path)
        cleanup()
        
        # Success!
        print("\n" + "=" * 60)
        print("✓ BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\nExecutable: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        print("\nBenefits of Nuitka build:")
        print("  ✓ Native C code (not bundled Python)")
        print("  ✓ 0-2 antivirus detections vs 10-20+ with PyInstaller")
        print("  ✓ Better performance")
        print("  ✓ Smaller file size")
        print("\nTo distribute:")
        print("  1. Share dist/ChatYapper.exe")
        print("  2. Include dist/CHECKSUMS.txt for verification")
        print("  3. Users should have FAR fewer antivirus issues!")
        print()
        
        logger.info("=== Build completed successfully ===")
        
    except KeyboardInterrupt:
        print("\n\n✗ Build cancelled by user")
        logger.warning("Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Build failed: {e}", exc_info=True)
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Chat Yapper Nuitka Build Script")
        print("================================")
        print()
        print("Usage: python deployment/build-nuitka.py")
        print()
        print("This script builds Chat Yapper using Nuitka, which compiles")
        print("Python to native C code. This results in far fewer antivirus")
        print("false positives compared to PyInstaller (0-2 vs 10-20+).")
        print()
        print("Requirements:")
        print("  - Python 3.9+")
        print("  - pip install nuitka")
        print("  - GCC compiler (auto-downloaded if missing)")
        print()
        print("The build process takes 5-15 minutes but produces a much")
        print("better executable with minimal false positives.")
        print()
        sys.exit(0)
    
    main()
