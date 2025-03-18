FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/root/.local/bin:$PATH" \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files for dependency installation
COPY pyproject.toml .
COPY .env.example .

# Create required directories
RUN mkdir -p uploads logs && chmod 777 uploads logs

# Create venv and install dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync

# Copy Streamlit application files
COPY streamlit/ ./streamlit/

# Create a copy of the app.py directly in the root for easy access
RUN cp ./streamlit/app.py ./streamlit/docker-app.py /app/ || true

# Set working directory to the streamlit directory
WORKDIR /app/streamlit

# Make sure the run script is directly available and executable
COPY streamlit/run.sh /app/streamlit/run.sh
RUN chmod +x /app/streamlit/run.sh

# Also copy it to the root as a fallback
COPY streamlit/run.sh /run.sh
RUN chmod +x /run.sh

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start Streamlit app
ENTRYPOINT ["/run.sh"] 