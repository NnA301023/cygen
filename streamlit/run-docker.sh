#!/bin/bash
set -e  # Exit on error

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║             ${GREEN}Streamlit Docker Runner${BLUE}             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker is not installed. Please install Docker to continue.${NC}"
    exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}docker-compose.yml not found. Make sure you're in the streamlit directory.${NC}"
    exit 1
fi

echo -e "${YELLOW}Building and starting Streamlit container...${NC}"
echo -e "${YELLOW}This will connect to a FastAPI backend running on your host machine.${NC}"
echo -e "${YELLOW}Make sure the FastAPI backend is running on port 8000.${NC}"

# Start with docker-compose
docker-compose build
docker-compose up

# Script never reaches here if docker-compose up is running in foreground 