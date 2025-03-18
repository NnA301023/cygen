#!/bin/bash
set -e

# Check runtime directory
echo "Current directory contents:"
ls -la

# Activate virtual environment
. .venv/bin/activate

# Install dependencies in development mode
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Installing dependencies in development mode..."
    uv pip install -e .
else
    echo "Installing dependencies in production mode..."
    uv pip install .
fi

# Run the application with hot reload in development
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Starting server in development mode with hot reload..."
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src
else
    echo "Starting server in production mode..."
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $MAX_WORKERS
fi 