@echo off
REM Quick build script for Chat Yapper MSI installer
REM This script builds both the executable and the MSI

echo ============================================================
echo Chat Yapper - Complete Build and Installer Creation
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Ask if user wants to clean first
echo.
set /p clean="Clean old build artifacts first? (recommended) (y/n): "
if /i "%clean%"=="y" (
    echo.
    echo Cleaning build artifacts...
    python deployment\clean_build.py --skip-confirmation
    echo.
)

echo Step 1: Building ChatYapper.exe...
echo.
cd /d "%~dp0.."
python deployment\build.py
if errorlevel 1 (
    echo.
    echo ERROR: Executable build failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Step 2: Building MSI installer...
echo ============================================================
echo.
python deployment\build_msi.py
if errorlevel 1 (
    echo.
    echo ERROR: MSI build failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Build Complete!
echo ============================================================
echo.
echo Files created:
dir /b dist\ChatYapper.exe 2>nul
dir /b deployment\ChatYapper-*.msi 2>nul
echo.
echo You can now distribute the MSI file to users!
echo.
pause
