#!/bin/bash

# PDF-QA System Setup Script
# This script automates the installation of backend and frontend dependencies.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== PDF-QA System Setup ===${NC}"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}Detected Python $PYTHON_VERSION${NC}"

# 2. Check for Node.js
if ! command -v node &> /dev/null; then
    echo "Error: node is not installed."
    exit 1
fi

NODE_VERSION=$(node -v)
echo -e "${GREEN}Detected Node.js $NODE_VERSION${NC}"

# 3. Setup Backend
echo -e "${BLUE}--- Setting up Backend ---${NC}"
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating default .env for backend..."
    cat <<EOT >> .env
OLLAMA_MODEL="gemma4:e2b"
EMBEDDING_MODEL="google/embeddinggemma-300M"
EXA_API_KEY=""
BACKEND_PORT=8000
EOT
fi

cd ..

# 4. Setup Frontend
echo -e "${BLUE}--- Setting up Frontend ---${NC}"
cd frontend

echo "Installing npm dependencies..."
npm install

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating default .env for frontend..."
    echo "VITE_BACKEND_URL=http://localhost:8000" >> .env
fi

cd ..

echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo -e "To start the application:"
echo -e "  1. Backend: cd backend && source venv/bin/activate && python main.py"
echo -e "  2. Frontend: cd frontend && npm run dev"
