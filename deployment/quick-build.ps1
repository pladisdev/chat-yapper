# Quick Test Build Script
# For rapid testing during development - creates installer without certificate fuss

param(
    [switch]$RunAfter
)

$ErrorActionPreference = "Stop"

Write-Host "=== Quick Test Build ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build executable
Write-Host "Building executable..." -ForegroundColor Yellow
python .\deployment\build.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Check if Inno Setup is available
$iscc = $null
$possiblePaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $iscc = $path
        break
    }
}

if ($iscc) {
    # Step 3: Create installer
    Write-Host "Creating installer..." -ForegroundColor Yellow
    & $iscc ".\deployment\setup.iss"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Build complete!" -ForegroundColor Green
        $installerPath = ".\dist\installer\ChatYapper-Setup-1.0.0.exe"
        Write-Host "Installer: $installerPath" -ForegroundColor Cyan
        
        if ($RunAfter -and (Test-Path $installerPath)) {
            Write-Host ""
            Write-Host "Launching installer..." -ForegroundColor Yellow
            Start-Process $installerPath
        }
    }
}
else {
    Write-Host ""
    Write-Host "Inno Setup not found - created executable only" -ForegroundColor Yellow
    Write-Host "Executable: .\dist\ChatYapper.exe" -ForegroundColor Cyan
    
    if ($RunAfter) {
        Start-Process ".\dist\ChatYapper.exe"
    }
}

Write-Host ""
