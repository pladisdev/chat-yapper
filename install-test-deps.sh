#!/bin/bash
# Chat Yapper - Install Testing Dependencies
# Run this script to install all testing dependencies for both backend and frontend

set -e

echo "========================================"
echo "Chat Yapper - Testing Setup"
echo "========================================"
echo ""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}Python not found. Please install Python 3.9 or higher.${NC}"
    exit 1
else
    PYTHON_CMD=$(command -v python3 || command -v python)
    PYTHON_VERSION=$($PYTHON_CMD --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION found${NC}"
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}npm not found. Please install Node.js 16 or higher.${NC}"
    exit 1
else
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}npm v$NPM_VERSION found${NC}"
fi

echo ""

# Install backend dependencies
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Installing Backend Dependencies${NC}"
echo -e "${CYAN}========================================${NC}"

echo -e "${YELLOW}Installing Python packages...${NC}"

$PYTHON_CMD -m pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}Backend dependencies installed successfully!${NC}"

echo ""

# Install frontend dependencies
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Installing Frontend Dependencies${NC}"
echo -e "${CYAN}========================================${NC}"

if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    echo -e "${YELLOW}Installing npm packages...${NC}"
    
    npm install
    
    echo -e "${GREEN}Frontend dependencies installed successfully!${NC}"
    cd "$PROJECT_ROOT"
else
    echo -e "${RED}Frontend directory not found at: $FRONTEND_DIR${NC}"
fi

echo ""

# Summary
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Installation Complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "1. Run Backend Tests:"
echo -e "   ${NC}cd backend${NC}"
echo -e "   ${NC}pytest -v${NC}"
echo ""
echo -e "2. Run Frontend Tests:"
echo -e "   ${NC}cd frontend${NC}"
echo -e "   ${NC}npm test -- --run${NC}"
echo ""
echo -e "3. View Coverage:"
echo -e "   Backend:  ${NC}pytest --cov=. --cov-report=html${NC}"
echo -e "   Frontend: ${NC}npm run test:coverage${NC}"
echo ""
echo -e "${YELLOW}For more information, see TESTING.md${NC}"
echo ""
