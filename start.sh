#!/bin/bash
set -e  # Exit on error

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️ .env file not found! Creating from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example. Please update the values as needed."
    else
        echo "❌ .env.example not found! Please create a .env file manually."
        exit 1
    fi
fi

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║             ${GREEN}RAG System Launcher${BLUE}               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"

# Show options
echo -e "${YELLOW}Choose a launch option:${NC}"
echo -e "  ${GREEN}1)${NC} Start full system with Docker Compose"
echo -e "  ${GREEN}2)${NC} Start FastAPI backend only"
echo -e "  ${GREEN}3)${NC} Start Streamlit frontend only"
echo -e "  ${GREEN}4)${NC} Quit"

# Get user input
read -p "Enter your choice [1-4]: " choice

case $choice in
    1)
        echo -e "${YELLOW}Starting both backend and frontend with Docker Compose...${NC}"
        docker-compose up --build
        ;;
    2)
        echo -e "${YELLOW}Starting FastAPI backend service...${NC}"
        docker-compose up --build app
        ;;
    3)
        echo -e "${YELLOW}Starting Streamlit frontend service...${NC}"
        
        # Check if Docker is preferred
        read -p "Use Docker for Streamlit? (y/n): " use_docker
        
        if [[ $use_docker == "y" || $use_docker == "Y" ]]; then
            echo -e "${YELLOW}Starting Streamlit in Docker...${NC}"
            docker-compose up --build streamlit
        else
            echo -e "${YELLOW}Starting Streamlit directly...${NC}"
            
            # Check for Python virtual environment
            if [ -d "venv" ]; then
                source venv/bin/activate
            elif [ -d ".venv" ]; then
                source .venv/bin/activate
            else
                echo -e "${YELLOW}No Python virtual environment found. Using system Python.${NC}"
            fi
            
            # Check for installed dependencies
            if ! pip show streamlit &> /dev/null; then
                echo -e "${YELLOW}Streamlit not found. Installing dependencies...${NC}"
                pip install -e .
            fi
            
            # Start Streamlit
            cd streamlit && ./run.sh
        fi
        ;;
    4)
        echo -e "${YELLOW}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${YELLOW}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac 