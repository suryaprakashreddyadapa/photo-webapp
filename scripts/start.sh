#!/bin/bash

# PhotoVault - Startup Script
# One-command startup for PhotoVault

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                      PhotoVault                            ║"
echo "║         Self-hosted Photo Management with AI               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env with your configuration before continuing.${NC}"
    echo "Required settings:"
    echo "  - POSTGRES_PASSWORD (change from default)"
    echo "  - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "  - NAS_PATH (path to your photo storage)"
    echo ""
    read -p "Press Enter after editing .env to continue..."
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Determine docker-compose command
COMPOSE_CMD="docker-compose"
if ! command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker compose"
fi

# Build and start services
echo -e "${YELLOW}Building Docker images...${NC}"
$COMPOSE_CMD build

echo -e "${YELLOW}Starting services...${NC}"
$COMPOSE_CMD up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check service health
echo -e "${YELLOW}Checking service health...${NC}"
$COMPOSE_CMD ps

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
$COMPOSE_CMD exec -T backend alembic upgrade head || {
    echo -e "${YELLOW}Migrations may have already been applied or backend is still starting...${NC}"
}

# Get ports from .env or use defaults
FRONTEND_PORT=$(grep FRONTEND_PORT .env 2>/dev/null | cut -d '=' -f2 || echo "3000")
BACKEND_PORT=$(grep BACKEND_PORT .env 2>/dev/null | cut -d '=' -f2 || echo "8000")

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                 PhotoVault is running!                     ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Access the application:"
echo "  Frontend:  http://localhost:${FRONTEND_PORT:-3000}"
echo "  API:       http://localhost:${BACKEND_PORT:-8000}"
echo "  API Docs:  http://localhost:${BACKEND_PORT:-8000}/docs"
echo ""
echo "Default admin credentials (change immediately!):"
echo "  Email:    admin@photovault.local"
echo "  Password: admin123"
echo ""
echo "Useful commands:"
echo "  View logs:     $COMPOSE_CMD logs -f"
echo "  Stop:          $COMPOSE_CMD down"
echo "  Restart:       $COMPOSE_CMD restart"
echo "  Update:        git pull && $COMPOSE_CMD up -d --build"
echo ""
