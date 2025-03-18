from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import asyncio

from .settings import get_settings
from .router import upload, chat

# Load settings
settings = get_settings()

# Configure logger
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """

    # Service Startup...
    app.state.max_workers = settings.MAX_WORKERS
    app.state.processing_semaphore = asyncio.Semaphore(settings.MAX_WORKERS)
    logger.info(f"Server starting with {settings.MAX_WORKERS} workers")
    
    yield  # Server is running
    
    # Service Shutdown
    logger.info("Server shutting down")

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Advanced RAG System with Groq LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    upload.router,
    prefix=f"{settings.API_V1_PREFIX}/documents",
    tags=["Document Processing"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_PREFIX}/chat",
    tags=["Chat"]
)

# Health check endpoint
@app.get("/", include_in_schema=False)
async def root_handler():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "workers": settings.MAX_WORKERS,
        "version": "1.0.0"
    }

# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )