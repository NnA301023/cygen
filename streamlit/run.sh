#!/bin/bash
set -e  # Exit on error

# Activate virtual environment if it exists
if [ -d "/app/.venv" ]; then
    echo "Activating virtual environment..."
    . /app/.venv/bin/activate
fi

# Load environment variables from parent .env file if exists
if [ -f "../.env" ]; then
    echo "Loading environment variables from ../.env"
    export $(grep -v '^#' ../.env | xargs)
fi

# Set default values
export API_URL=${API_URL:-"http://localhost:8000"}
export WS_URL=${WS_URL:-"ws://localhost:8000"}
export STREAMLIT_SERVER_PORT=${STREAMLIT_SERVER_PORT:-8501}
export STREAMLIT_SERVER_HEADLESS=${STREAMLIT_SERVER_HEADLESS:-true}
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}

# Print environment settings
echo "Starting Streamlit app with:"
echo " - API_URL: $API_URL"
echo " - WS_URL: $WS_URL"
echo " - STREAMLIT_SERVER_PORT: $STREAMLIT_SERVER_PORT"
echo " - Python executable: $(which python)"

# Check app files and run the appropriate one
if [ -f "app.py" ]; then
    echo "Using app.py for Streamlit"
    exec streamlit run app.py
else
    echo "ERROR: No Streamlit app found in $(pwd)!"
    echo "Directory contents:"
    ls -la
    exit 1
fi 