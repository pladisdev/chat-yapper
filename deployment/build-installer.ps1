# Build and Create Installer for Chat Yapper
# This script:
# 1. Generates a self-signed certificate (optional)
# 2. Builds the executable with PyInstaller
# 3. Signs the executable with the certificate
# 4. Creates a Windows installer using Inno Setup

param(
    [switch]$SkipCertificate,
    [switch]$SkipBuild,
    [switch]$SkipSigning,
    [switch]$SkipInstaller,
    [switch]$Clean,
    [string]$CertPassword = ""
)

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "=== Chat Yapper Build & Installer Script ===" -ForegroundColor Cyan
Write-Host "Project Root: $projectRoot" -ForegroundColor Gray
Write-Host ""

# ============================================================================
# Helper Functions
# ============================================================================

function Test-Command {
    param($Command)
    try {
        if (Get-Command $Command -ErrorAction SilentlyContinue) {
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

function Write-Step {
    param($Message)
    Write-Host ""
    Write-Host ">>> $Message" -ForegroundColor Yellow
    Write-Host ""
}

# ============================================================================
# Step 0: Clean previous builds (if requested)
# ============================================================================

if ($Clean) {
    Write-Step "Cleaning previous builds..."
    
    $cleanPaths = @(
        ".\dist",
        ".\build",
        ".\_internal"
    )
    
    foreach ($path in $cleanPaths) {
        if (Test-Path $path) {
            Write-Host "Removing $path..." -ForegroundColor Gray
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "Clean complete!" -ForegroundColor Green
}

# ============================================================================
# Step 1: Generate Self-Signed Certificate (optional)
# ============================================================================

if (-not $SkipCertificate) {
    Write-Step "Step 1: Certificate Generation"
    
    $certPath = ".\dist\ChatYapper.pfx"
    $cerPath = ".\dist\ChatYapper.cer"
    $passwordPath = ".\dist\ChatYapper-password.txt"
    
    if (Test-Path $certPath) {
        Write-Host "Certificate already exists: $certPath" -ForegroundColor Yellow
        $recreate = Read-Host "Recreate certificate? (Y/N)"
        if ($recreate -ne 'Y' -and $recreate -ne 'y') {
            Write-Host "Using existing certificate" -ForegroundColor Green
            if (Test-Path $passwordPath -and [string]::IsNullOrEmpty($CertPassword)) {
                $CertPassword = Get-Content $passwordPath -Raw
                $CertPassword = $CertPassword.Trim()
                Write-Host "Loaded password from file" -ForegroundColor Green
            }
        }
        else {
            Write-Host "Generating new certificate..." -ForegroundColor Yellow
            & "$scriptPath\generate-certificate.ps1"
            if (Test-Path $passwordPath) {
                $CertPassword = Get-Content $passwordPath -Raw
                $CertPassword = $CertPassword.Trim()
            }
        }
    }
    else {
        Write-Host "No certificate found. Generating new certificate..." -ForegroundColor Yellow
        & "$scriptPath\generate-certificate.ps1"
        if (Test-Path $passwordPath) {
            $CertPassword = Get-Content $passwordPath -Raw
            $CertPassword = $CertPassword.Trim()
        }
    }
}
else {
    Write-Host "Skipping certificate generation (--SkipCertificate)" -ForegroundColor Gray
}

# ============================================================================
# Step 2: Build Executable with PyInstaller
# ============================================================================

if (-not $SkipBuild) {
    Write-Step "Step 2: Building Executable"
    
    # Check if Python is available
    if (-not (Test-Command "python")) {
        Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Running build.py..." -ForegroundColor Yellow
    python ".\deployment\build.py"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Build failed!" -ForegroundColor Red
        exit 1
    }
    
    # Verify executable was created
    $exePath = ".\dist\ChatYapper.exe"
    if (-not (Test-Path $exePath)) {
        Write-Host "ERROR: Executable not found at $exePath" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "Executable: $exePath" -ForegroundColor Cyan
}
else {
    Write-Host "Skipping build (--SkipBuild)" -ForegroundColor Gray
}

# ============================================================================
# Step 3: Sign the Executable
# ============================================================================

if (-not $SkipSigning) {
    Write-Step "Step 3: Code Signing"
    
    $exePath = ".\dist\ChatYapper.exe"
    $certPath = ".\dist\ChatYapper.pfx"
    
    if (-not (Test-Path $exePath)) {
        Write-Host "ERROR: Executable not found: $exePath" -ForegroundColor Red
        exit 1
    }
    
    if (Test-Path $certPath) {
        # Find signtool.exe
        $signtool = $null
        $possiblePaths = @(
            "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe",
            "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe",
            "C:\Program Files\Microsoft SDKs\Windows\*\bin\signtool.exe"
        )
        
        foreach ($pattern in $possiblePaths) {
            $found = Get-ChildItem $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) {
                $signtool = $found.FullName
                break
            }
        }
        
        if ($signtool) {
            Write-Host "Found signtool: $signtool" -ForegroundColor Green
            
            if ([string]::IsNullOrEmpty($CertPassword)) {
                Write-Host "No certificate password provided" -ForegroundColor Yellow
                $CertPassword = Read-Host "Enter certificate password" -AsSecureString
                $CertPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($CertPassword))
            }
            
            Write-Host "Waiting for file to be released by build process..." -ForegroundColor Yellow
            Start-Sleep -Seconds 2
            
            # Try to ensure file is not locked
            [System.GC]::Collect()
            [System.GC]::WaitForPendingFinalizers()
            
            Write-Host "Signing executable..." -ForegroundColor Yellow
            
            $signArgs = @(
                "sign",
                "/f", $certPath,
                "/p", $CertPassword,
                "/fd", "SHA256",
                "/tr", "http://timestamp.digicert.com",
                "/td", "SHA256",
                "/v",
                $exePath
            )
            
            # Retry signing up to 3 times if file is locked
            $maxRetries = 3
            $retryCount = 0
            $signed = $false
            
            while (-not $signed -and $retryCount -lt $maxRetries) {
                if ($retryCount -gt 0) {
                    Write-Host "Retry $retryCount of $maxRetries..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 3
                }
                
                & $signtool @signArgs
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Executable signed successfully!" -ForegroundColor Green
                    $signed = $true
                }
                else {
                    $retryCount++
                    if ($retryCount -lt $maxRetries) {
                        Write-Host "Signing failed, waiting for file to be released..." -ForegroundColor Yellow
                    }
                }
            }
            
            if (-not $signed) {
                Write-Host "WARNING: Code signing failed after $maxRetries attempts" -ForegroundColor Yellow
                Write-Host "The executable will work but may show security warnings" -ForegroundColor Yellow
                Write-Host "" -ForegroundColor Yellow
                Write-Host "Possible causes:" -ForegroundColor Yellow
                Write-Host "  - File locked by antivirus scanner" -ForegroundColor Gray
                Write-Host "  - File locked by Windows Defender" -ForegroundColor Gray
                Write-Host "  - File still open by build process" -ForegroundColor Gray
                Write-Host "" -ForegroundColor Yellow
                Write-Host "Try:" -ForegroundColor Yellow
                Write-Host "  - Temporarily disable antivirus" -ForegroundColor Gray
                Write-Host "  - Close all file explorers" -ForegroundColor Gray
                Write-Host "  - Run: .\build-installer.ps1 -SkipBuild" -ForegroundColor Gray
            }
        }
        else {
            Write-Host "WARNING: signtool.exe not found" -ForegroundColor Yellow
            Write-Host "Install Windows SDK to enable code signing" -ForegroundColor Yellow
            Write-Host "Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/" -ForegroundColor Cyan
        }
    }
    else {
        Write-Host "No certificate found for signing" -ForegroundColor Yellow
        Write-Host "The executable will work but may show security warnings" -ForegroundColor Yellow
    }
}
else {
    Write-Host "Skipping code signing (--SkipSigning)" -ForegroundColor Gray
}

# ============================================================================
# Step 4: Create Installer with Inno Setup
# ============================================================================

if (-not $SkipInstaller) {
    Write-Step "Step 4: Creating Installer"
    
    # Find Inno Setup compiler
    $iscc = $null
    $possiblePaths = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        "C:\Program Files\Inno Setup 5\ISCC.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $iscc = $path
            break
        }
    }
    
    if ($iscc) {
        Write-Host "Found Inno Setup: $iscc" -ForegroundColor Green
        
        $issFile = ".\deployment\setup.iss"
        if (-not (Test-Path $issFile)) {
            Write-Host "ERROR: Inno Setup script not found: $issFile" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Compiling installer..." -ForegroundColor Yellow
        & $iscc $issFile
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Installer created successfully!" -ForegroundColor Green
            
            $installerPath = ".\dist\installer\ChatYapper-Setup-1.0.0.exe"
            if (Test-Path $installerPath) {
                Write-Host "Installer location: $installerPath" -ForegroundColor Cyan
                
                # Get file size
                $size = (Get-Item $installerPath).Length / 1MB
                Write-Host "Installer size: $([math]::Round($size, 2)) MB" -ForegroundColor Cyan
            }
        }
        else {
            Write-Host "ERROR: Installer creation failed!" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "WARNING: Inno Setup not found" -ForegroundColor Yellow
        Write-Host "Install Inno Setup to create Windows installers" -ForegroundColor Yellow
        Write-Host "Download from: https://jrsoftware.org/isdl.php" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "You can still distribute the standalone .exe from .\dist\ChatYapper.exe" -ForegroundColor Yellow
    }
}
else {
    Write-Host "Skipping installer creation (--SkipInstaller)" -ForegroundColor Gray
}

# ============================================================================
# Complete!
# ============================================================================

Write-Host ""
Write-Host "=== Build Process Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Output files:" -ForegroundColor Cyan

if (Test-Path ".\dist\ChatYapper.exe") {
    Write-Host "  Executable: .\dist\ChatYapper.exe" -ForegroundColor White
}
if (Test-Path ".\dist\ChatYapper.cer") {
    Write-Host "  Certificate: .\dist\ChatYapper.cer" -ForegroundColor White
}
if (Test-Path ".\dist\installer\ChatYapper-Setup-1.0.0.exe") {
    Write-Host "  Installer: .\dist\installer\ChatYapper-Setup-1.0.0.exe" -ForegroundColor White
}

Write-Host ""
Write-Host "To install, run the installer as Administrator" -ForegroundColor Yellow
Write-Host ""
