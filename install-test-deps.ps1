# Chat Yapper - Install Testing Dependencies
# Run this script to install all testing dependencies for both backend and frontend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Chat Yapper - Testing Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

# Function to check if command exists
function Test-Command {
    param($command)
    $null = Get-Command $command -ErrorAction SilentlyContinue
    return $?
}

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

if (-not (Test-Command "python")) {
    Write-Host "❌ Python not found. Please install Python 3.9 or higher." -ForegroundColor Red
    exit 1
} else {
    $pythonVersion = python --version
    Write-Host "✅ $pythonVersion found" -ForegroundColor Green
}

if (-not (Test-Command "npm")) {
    Write-Host "❌ npm not found. Please install Node.js 16 or higher." -ForegroundColor Red
    exit 1
} else {
    $npmVersion = npm --version
    Write-Host "✅ npm v$npmVersion found" -ForegroundColor Green
}

Write-Host ""

# Install backend dependencies
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Backend Dependencies" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (Test-Path $backendDir) {
    Push-Location $backendDir
    Write-Host "Installing Python packages..." -ForegroundColor Yellow
    
    try {
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        Write-Host "✅ Backend dependencies installed successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install backend dependencies: $_" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    Pop-Location
} else {
    Write-Host "❌ Backend directory not found at: $backendDir" -ForegroundColor Red
}

Write-Host ""

# Install frontend dependencies
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Frontend Dependencies" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    Write-Host "Installing npm packages..." -ForegroundColor Yellow
    
    try {
        npm install
        Write-Host "✅ Frontend dependencies installed successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install frontend dependencies: $_" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    Pop-Location
} else {
    Write-Host "❌ Frontend directory not found at: $frontendDir" -ForegroundColor Red
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Run Backend Tests:" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   pytest -v" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Run Frontend Tests:" -ForegroundColor White
Write-Host "   cd frontend" -ForegroundColor Gray
Write-Host "   npm test -- --run" -ForegroundColor Gray
Write-Host ""
Write-Host "3. View Coverage:" -ForegroundColor White
Write-Host "   Backend:  pytest --cov=. --cov-report=html" -ForegroundColor Gray
Write-Host "   Frontend: npm run test:coverage" -ForegroundColor Gray
Write-Host ""
Write-Host "For more information, see TESTING.md" -ForegroundColor Yellow
Write-Host ""
