#!/bin/bash

# PhotoVault - Push to GitHub Script
# This script initializes a git repository and pushes to GitHub

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}PhotoVault - GitHub Push Script${NC}"
echo "=================================="

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not installed${NC}"
    exit 1
fi

# Check if gh CLI is installed (optional)
GH_CLI=false
if command -v gh &> /dev/null; then
    GH_CLI=true
fi

# Get repository information
read -p "Enter GitHub username: " GITHUB_USER
read -p "Enter repository name (default: photovault): " REPO_NAME
REPO_NAME=${REPO_NAME:-photovault}

read -p "Make repository private? (y/n, default: n): " PRIVATE
PRIVATE=${PRIVATE:-n}

# Navigate to project root
cd "$(dirname "$0")/.."

# Initialize git if not already
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Initializing git repository...${NC}"
    git init
fi

# Create .gitignore if not exists
if [ ! -f ".gitignore" ]; then
    echo -e "${YELLOW}Creating .gitignore...${NC}"
    cat > .gitignore << 'EOF'
# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
.venv/

# Node
node_modules/
dist/
.pnpm-store/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Logs
*.log
logs/

# Data
data/
*.db
*.sqlite

# AI Models (large files)
*.pt
*.pth
*.onnx
*.bin

# Thumbnails and media cache
thumbnails/
media_cache/

# Test coverage
.coverage
htmlcov/
.pytest_cache/

# Build
build/
*.egg-info/
EOF
fi

# Add all files
echo -e "${YELLOW}Adding files to git...${NC}"
git add -A

# Commit
echo -e "${YELLOW}Creating initial commit...${NC}"
git commit -m "Initial commit: PhotoVault - Self-hosted photo management with AI" || true

# Set main branch
git branch -M main

# Create GitHub repository if gh CLI is available
if [ "$GH_CLI" = true ]; then
    echo -e "${YELLOW}Creating GitHub repository...${NC}"
    
    VISIBILITY="--public"
    if [ "$PRIVATE" = "y" ] || [ "$PRIVATE" = "Y" ]; then
        VISIBILITY="--private"
    fi
    
    gh repo create "$REPO_NAME" $VISIBILITY --source=. --remote=origin --push || {
        echo -e "${YELLOW}Repository might already exist, trying to add remote...${NC}"
        git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || true
        git push -u origin main
    }
else
    # Manual setup
    echo -e "${YELLOW}Setting up remote...${NC}"
    git remote remove origin 2>/dev/null || true
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
    
    echo ""
    echo -e "${YELLOW}Please create the repository on GitHub first:${NC}"
    echo "1. Go to https://github.com/new"
    echo "2. Create repository: $REPO_NAME"
    echo "3. Do NOT initialize with README"
    echo ""
    read -p "Press Enter when ready to push..."
    
    git push -u origin main
fi

echo ""
echo -e "${GREEN}Success! Repository pushed to GitHub${NC}"
echo "URL: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "Next steps:"
echo "1. Clone on your server: git clone https://github.com/$GITHUB_USER/$REPO_NAME.git"
echo "2. Configure: cp .env.example .env && nano .env"
echo "3. Start: docker-compose up -d"
