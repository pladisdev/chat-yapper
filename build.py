"""
Build script for Chat Yapper Windows executable
Run this to create a distributable .exe file
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and print output"""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {result.stderr}")
        if result.stdout:
            print(f"📝 Output: {result.stdout}")
        sys.exit(1)
    if result.stdout.strip():
        print(f"✅ Success")
    return result

def build_frontend():
    """Build the React frontend"""
    print("📦 Building frontend...")
    frontend_dir = Path("frontend")
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        sys.exit(1)
    
    # Install dependencies and build
    run_command("npm install", cwd=frontend_dir)
    run_command("npm run build", cwd=frontend_dir)
    
    # Copy build to backend/public
    backend_public = Path("backend/public")
    if backend_public.exists():
        shutil.rmtree(backend_public)
    
    shutil.copytree(frontend_dir / "dist", backend_public)
    print("✅ Frontend built and copied to backend/public")

def create_executable():
    """Create executable with PyInstaller"""
    print("🎯 Creating Windows executable...")
    
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
        'uvicorn',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'edge_tts',
        'aiohttp',
        'PIL',
        'twitchio',
        'sqlmodel',
        'fastapi',
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
        print(f"✅ Executable created: dist/ChatYapper.exe ({file_size:.1f} MB)")
    else:
        print("❌ Executable not found after build")
        sys.exit(1)
    
    # Clean up build artifacts (optional)
    cleanup_paths = ["build", "ChatYapper.spec"]
    for path in cleanup_paths:
        if Path(path).exists():
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                Path(path).unlink()
    print("🧹 Cleaned up build artifacts")

def main():
    print("🏗️  Building Chat Yapper for Windows distribution...")
    print()
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Please run this script from the Chat Yapper root directory")
        sys.exit(1)
    
    try:
        # Build frontend
        build_frontend()
        
        # Create executable
        create_executable()
        
        print()
        print("🎉 Build complete!")
        print("📁 Executable location: dist/ChatYapper.exe")
        print("📋 Distribution folder: dist/")
        print()
        print("📤 To distribute:")
        print("   1. Copy the dist/ChatYapper.exe file")
        print("   2. Users can run it directly - no installation needed!")
        print("   3. It will start a local server and open their browser")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
