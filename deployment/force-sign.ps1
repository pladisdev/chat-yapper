# Force Sign - Aggressive signing with file handle release
# This uses more aggressive techniques to release file locks

param(
    [string]$ExePath = ".\dist\ChatYapper.exe"
)

Write-Host "=== Force Sign Executable ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: File not found: $ExePath" -ForegroundColor Red
    exit 1
}

# Load certificate info
$certPath = ".\dist\ChatYapper.pfx"
$passwordPath = ".\dist\ChatYapper-password.txt"

if (-not (Test-Path $certPath)) {
    Write-Host "ERROR: Certificate not found: $certPath" -ForegroundColor Red
    exit 1
}

if (Test-Path $passwordPath) {
    $password = (Get-Content $passwordPath -Raw).Trim()
} else {
    Write-Host "ERROR: Password file not found: $passwordPath" -ForegroundColor Red
    exit 1
}

# Find signtool
$signtool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $signtool) {
    Write-Host "ERROR: signtool.exe not found" -ForegroundColor Red
    exit 1
}
$signtool = $signtool.FullName

Write-Host "Step 1: Killing any processes that might hold the file..." -ForegroundColor Yellow
# Kill Windows Defender if it's scanning
Get-Process -Name "MsMpEng" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "MpCmdRun" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Step 2: Forcing garbage collection..." -ForegroundColor Yellow
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
[System.GC]::Collect()

Write-Host "Step 3: Waiting 10 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "Step 4: Attempting to sign..." -ForegroundColor Yellow
Write-Host ""

& $signtool sign /f $certPath /p $password /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /v $ExePath

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS! Executable signed!" -ForegroundColor Green
    Write-Host ""
    
    # Verify
    & $signtool verify /pa /v $ExePath
} else {
    Write-Host ""
    Write-Host "FAILED - Try these steps:" -ForegroundColor Red
    Write-Host "1. Open Windows Security" -ForegroundColor Yellow
    Write-Host "2. Virus & threat protection > Manage settings" -ForegroundColor Yellow
    Write-Host "3. Turn OFF 'Real-time protection'" -ForegroundColor Yellow
    Write-Host "4. Run: .\sign-exe.ps1" -ForegroundColor Yellow
    Write-Host "5. Turn protection back ON" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "OR add exclusion:" -ForegroundColor Yellow
    Write-Host "  Windows Security > Exclusions > Add folder: l:\Code\chat-yapper\dist" -ForegroundColor Yellow
}
