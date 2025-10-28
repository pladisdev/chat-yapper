"""
Build MSI installer for Chat Yapper using WiX Toolset 4
Requires WiX Toolset 4.x to be installed
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and handle errors"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout.strip())
    return result

def check_wix_installed():
    """Check if WiX Toolset is installed"""
    try:
        result = subprocess.run("wix --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"WiX Toolset found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("ERROR: WiX Toolset 4 not found!")
    print("Please install WiX Toolset 4 from:")
    print("  https://wixtoolset.org/docs/intro/")
    print("\nInstallation:")
    print("  dotnet tool install --global wix")
    print("  wix extension add WixToolset.UI.wixext")
    return False

def check_wix_extensions():
    """Check if required WiX extensions are installed"""
    try:
        result = subprocess.run("wix extension list", shell=True, capture_output=True, text=True)
        if "WixToolset.UI.wixext" in result.stdout:
            print("WiX UI extension found")
            return True
        else:
            print("\nWARNING: WiX UI extension not found!")
            print("Installing WixToolset.UI.wixext...")
            install_result = subprocess.run("wix extension add WixToolset.UI.wixext", 
                                          shell=True, capture_output=True, text=True)
            if install_result.returncode == 0:
                print("✓ WiX UI extension installed successfully")
                return True
            else:
                print(f"Failed to install extension: {install_result.stderr}")
                print("\nPlease install manually:")
                print("  wix extension add WixToolset.UI.wixext")
                return False
    except Exception as e:
        print(f"Could not check extensions: {e}")
        print("Attempting to install WixToolset.UI.wixext...")
        try:
            install_result = subprocess.run("wix extension add WixToolset.UI.wixext", 
                                          shell=True, capture_output=True, text=True)
            if install_result.returncode == 0:
                print("✓ WiX UI extension installed successfully")
                return True
        except:
            pass
        print("\nPlease install the UI extension manually:")
        print("  wix extension add WixToolset.UI.wixext")
        return False

def build_msi():
    """Build the MSI installer"""
    print("\n" + "="*60)
    print("Chat Yapper MSI Builder")
    print("="*60 + "\n")
    
    # Check for WiX
    if not check_wix_installed():
        sys.exit(1)
    
    # Check for required extensions
    if not check_wix_extensions():
        sys.exit(1)
    
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    deployment_dir = script_dir
    dist_dir = project_root / "dist"
    msi_output_dir = dist_dir / "msi"
    
    # Create msi output directory if it doesn't exist
    msi_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if executable exists
    exe_path = dist_dir / "ChatYapper.exe"
    if not exe_path.exists():
        print(f"ERROR: ChatYapper.exe not found at {exe_path}")
        print("Please build the executable first using build.py")
        sys.exit(1)
    
    print(f"Found executable: {exe_path}")
    print(f"Output directory: {msi_output_dir}")
    
    # Change to deployment directory
    os.chdir(deployment_dir)
    print(f"Working directory: {deployment_dir}\n")
    
    # Read version from backend/version.py
    version = "1.1.0"  # default
    version_file = project_root / "backend" / "version.py"
    if version_file.exists():
        with open(version_file) as f:
            for line in f:
                if line.startswith('__version__'):
                    version = line.split('=')[1].strip().strip('"').strip("'")
                    print(f"Building installer version: {version}\n")
                    break
    
    # Update version in WXS file
    wxs_path = deployment_dir / "ChatYapper.wxs"
    if wxs_path.exists():
        with open(wxs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace version
        import re
        content = re.sub(
            r'Version="[\d\.]+"',
            f'Version="{version}"',
            content,
            count=1
        )
        
        with open(wxs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated version in {wxs_path.name}\n")
    
    # Check for custom images
    banner_bmp = deployment_dir / "banner.bmp"
    dialog_bmp = deployment_dir / "dialog.bmp"
    
    if banner_bmp.exists() and dialog_bmp.exists():
        print("Custom installer images found:")
        print(f"  Banner: {banner_bmp} ({banner_bmp.stat().st_size} bytes)")
        print(f"  Dialog: {dialog_bmp} ({dialog_bmp.stat().st_size} bytes)")
    else:
        print("WARNING: Custom images not found, installer will use defaults")
        if not banner_bmp.exists():
            print(f"  Missing: {banner_bmp}")
        if not dialog_bmp.exists():
            print(f"  Missing: {dialog_bmp}")
    print()
    
    # Build with WiX
    print("Building MSI installer...\n")
    
    # Set source directory to dist folder
    source_dir = str(dist_dir.resolve())
    
    # Build command
    # WiX 4 uses: wix build -o output.msi source.wxs -d VariableName=Value
    output_msi = msi_output_dir / f"ChatYapper-{version}.msi"
    
    # Include UI extension for WixUI
    cmd = f'wix build -o "{output_msi}" ChatYapper.wxs -d SourceDir="{source_dir}" -ext WixToolset.UI.wixext'
    
    try:
        run_command(cmd, cwd=deployment_dir)
        print("\n" + "="*60)
        print("MSI installer created successfully!")
        print("="*60)
        print(f"\nInstaller location: {output_msi}")
        
        # Get file size
        file_size = output_msi.stat().st_size / (1024 * 1024)
        print(f"Installer size: {file_size:.1f} MB")
        
        print("\nInstaller features:")
        print("  ✓ User-selectable install location")
        print("  ✓ Desktop shortcut (optional)")
        print("  ✓ Start Menu shortcut")
        print("  ✓ Logs folder with write permissions")
        print("  ✓ Launch application after install (optional)")
        print("  ✓ Proper uninstall support")
        
        print("\nNext steps:")
        print(f"  1. Test the installer: {output_msi.name}")
        print("  2. Distribute the MSI file to users")
        
    except Exception as e:
        print(f"\nBuild failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure WiX Toolset 4 is installed")
        print("  2. Check that ChatYapper.exe exists in dist/")
        print("  3. Verify ChatYapper.wxs has no syntax errors")
        sys.exit(1)

if __name__ == "__main__":
    build_msi()
