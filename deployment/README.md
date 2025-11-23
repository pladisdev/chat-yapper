# Chat Yapper Deployment Scripts

This folder contains scripts for building and packaging Chat Yapper for distribution.

## Build Scripts

### Quick Build (Recommended)
```bash
deployment\build_all.bat
```
Builds both the executable and MSI installer. **Prompts to clean old build artifacts first** (recommended to avoid using cached/old files).

### Individual Build Steps

#### 1. Build Executable
```bash
python deployment\build.py
```
- Builds the frontend (React)
- Compiles Python backend with PyInstaller
- Creates `dist/ChatYapper.exe`

#### 2. Build MSI Installer
```bash
python deployment\build_msi.py
```
- Packages the executable into an MSI installer
- Creates `dist/msi/ChatYapper-{version}.msi`
- **Note:** Requires WiX Toolset 4 to be installed

### Clean Build Artifacts

**If you're getting old/cached versions in your builds**, run:

```bash
# Windows batch file
deployment\clean_build.bat

# Or Python script (cross-platform)
python deployment\clean_build.py

# Non-interactive (for scripts)
python deployment\clean_build.py --skip-confirmation
```

This removes:
- `dist/` folder (compiled executable and MSI)
- `build/` folder (PyInstaller cache)
- `ChatYapper.spec` (PyInstaller spec file)
- `backend/embedded_config.py` (build-time config)
- All `__pycache__` folders
- WiX build artifacts (`.wixobj`, `.wixpdb`)

## Common Issues

### MSI contains old version of application
**Problem:** The MSI installer has an old/cached version of the application.

**Solution:** 
1. Run `deployment\clean_build.bat` to remove all build artifacts
2. Then run `deployment\build_all.bat` to rebuild everything from scratch

**Why this happens:** PyInstaller and WiX cache build artifacts. If you rebuild the MSI without rebuilding the executable, it will package the old `.exe` file.

### PyInstaller uses cached modules
**Problem:** Code changes aren't reflected in the built executable.

**Solution:** The build scripts use `--clean` flag automatically, but if issues persist:
1. Manually delete `build/` and `dist/` folders
2. Delete `ChatYapper.spec`
3. Rebuild with `python deployment\build.py`

### WiX Build Errors
**Problem:** MSI build fails with WiX errors.

**Solution:**
1. Ensure WiX Toolset 4 is installed: `wix --version`
2. Install if needed: `dotnet tool install --global wix`
3. Install UI extension: `wix extension add WixToolset.UI.wixext`

## Build Requirements

- **Python 3.8+** with virtual environment
- **Node.js** and npm (for frontend)
- **PyInstaller** (`pip install pyinstaller`)
- **WiX Toolset 4** (for MSI creation)

## Output Files

After a successful build:
- **Executable:** `dist/ChatYapper.exe` (~150-200 MB)
- **MSI Installer:** `dist/msi/ChatYapper-{version}.msi` (~150-200 MB)

## Build Process Overview

1. **Frontend Build** (`npm run build` in `frontend/`)
   - Compiles React app
   - Outputs to `backend/public/`

2. **Executable Build** (PyInstaller)
   - Embeds frontend build
   - Packages Python backend
   - Creates standalone `.exe` in `dist/`

3. **MSI Creation** (WiX Toolset)
   - Packages `.exe` into installer
   - Adds install/uninstall support
   - Creates shortcuts

## Version Management

The version is stored in `backend/version.py`:
```python
__version__ = "1.1.0"
```

This version is automatically used by:
- Frontend build (via `VITE_APP_VERSION`)
- MSI installer filename
- WiX product version

## For Developers

### Testing Builds Locally
After building, you can test the executable without installing:
```bash
dist\ChatYapper.exe
```

### Creating Custom Installer Images
Place custom images in `deployment/`:
- `banner.bmp` - Top banner (493×58 pixels)
- `dialog.bmp` - Welcome dialog (493×312 pixels)

The build script will automatically use them if present.
