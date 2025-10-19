# Sign Existing Executable
# Use this to sign an executable that's already been built
# Useful when the main build script fails due to file locking

param(
    [string]$ExePath = ".\dist\ChatYapper.exe",
    [string]$CertPath = ".\dist\ChatYapper.pfx",
    [string]$CertPassword = ""
)

$ErrorActionPreference = "Stop"

Write-Host "=== Sign Existing Executable ===" -ForegroundColor Cyan
Write-Host ""

# Check if executable exists
if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: Executable not found: $ExePath" -ForegroundColor Red
    exit 1
}

# Check if certificate exists
if (-not (Test-Path $CertPath)) {
    Write-Host "ERROR: Certificate not found: $CertPath" -ForegroundColor Red
    Write-Host "Run generate-certificate.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Load password if not provided
if ([string]::IsNullOrEmpty($CertPassword)) {
    $passwordPath = ".\dist\ChatYapper-password.txt"
    if (Test-Path $passwordPath) {
        $CertPassword = Get-Content $passwordPath -Raw
        $CertPassword = $CertPassword.Trim()
        Write-Host "Loaded password from file" -ForegroundColor Green
    }
    else {
        Write-Host "No password file found" -ForegroundColor Yellow
        $CertPassword = Read-Host "Enter certificate password" -AsSecureString
        $CertPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($CertPassword))
    }
}

# Find signtool.exe
Write-Host "Looking for signtool.exe..." -ForegroundColor Yellow
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

if (-not $signtool) {
    Write-Host "ERROR: signtool.exe not found" -ForegroundColor Red
    Write-Host "Install Windows SDK: https://developer.microsoft.com/windows/downloads/windows-sdk" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found signtool: $signtool" -ForegroundColor Green
Write-Host ""

# Check if file is currently locked
Write-Host "Checking if file is accessible..." -ForegroundColor Yellow
try {
    $fileStream = [System.IO.File]::Open($ExePath, 'Open', 'Read', 'None')
    $fileStream.Close()
    Write-Host "File is accessible" -ForegroundColor Green
}
catch {
    Write-Host "WARNING: File appears to be locked" -ForegroundColor Yellow
    Write-Host "Waiting 5 seconds for processes to release the file..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "Signing executable..." -ForegroundColor Yellow
Write-Host "  File: $ExePath" -ForegroundColor Gray
Write-Host "  Cert: $CertPath" -ForegroundColor Gray
Write-Host ""

$signArgs = @(
    "sign",
    "/f", $CertPath,
    "/p", $CertPassword,
    "/fd", "SHA256",
    "/tr", "http://timestamp.digicert.com",
    "/td", "SHA256",
    "/v",
    $ExePath
)

# Retry signing up to 5 times
$maxRetries = 5
$retryCount = 0
$signed = $false

while (-not $signed -and $retryCount -lt $maxRetries) {
    if ($retryCount -gt 0) {
        Write-Host ""
        Write-Host "Attempt $($retryCount + 1) of $maxRetries..." -ForegroundColor Yellow
        Write-Host "Waiting for file to be released..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # Force garbage collection
        [System.GC]::Collect()
        [System.GC]::WaitForPendingFinalizers()
    }
    
    & $signtool @signArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "SUCCESS: Executable signed!" -ForegroundColor Green
        $signed = $true
    }
    else {
        $retryCount++
    }
}

if (-not $signed) {
    Write-Host ""
    Write-Host "ERROR: Failed to sign executable after $maxRetries attempts" -ForegroundColor Red
    Write-Host ""
    Write-Host "The file may be locked by:" -ForegroundColor Yellow
    Write-Host "  - Windows Defender or antivirus" -ForegroundColor Gray
    Write-Host "  - File Explorer" -ForegroundColor Gray
    Write-Host "  - Another running process" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Try these solutions:" -ForegroundColor Yellow
    Write-Host "  1. Temporarily disable Windows Defender real-time protection" -ForegroundColor Gray
    Write-Host "  2. Close all File Explorer windows" -ForegroundColor Gray
    Write-Host "  3. Restart your computer and try again immediately" -ForegroundColor Gray
    Write-Host "  4. Add dist folder to antivirus exclusions" -ForegroundColor Gray
    Write-Host ""
    
    # Show what processes have the file open
    Write-Host "Checking for processes using the file..." -ForegroundColor Yellow
    $handle = Get-Process | Where-Object { $_.Modules.FileName -like "*$([System.IO.Path]::GetFileName($ExePath))*" } -ErrorAction SilentlyContinue
    if ($handle) {
        Write-Host "Processes with file open:" -ForegroundColor Yellow
        $handle | Format-Table Name, Id, Path -AutoSize
    }
    
    exit 1
}

Write-Host ""
Write-Host "Verifying signature..." -ForegroundColor Yellow
& $signtool "verify" "/pa" "/v" $ExePath

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Signature verified successfully!" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "WARNING: Signature verification failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Signing Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Your signed executable is ready at:" -ForegroundColor Cyan
Write-Host "  $ExePath" -ForegroundColor White
Write-Host ""
