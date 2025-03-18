from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings.
    
    Attributes:
        # Server Settings
        APP_NAME: Name of the application
        DEBUG: Debug mode flag
        API_V1_PREFIX: API version 1 prefix
        
        # Processing Settings
        MAX_WORKERS: Maximum number of worker threads for background tasks
        CHUNK_SIZE: Size of text chunks for document processing (in tokens)
        CHUNK_OVERLAP: Overlap between chunks (in tokens)
        
        # Database Settings
        MONGODB_URL: MongoDB connection URL
        MONGODB_DB_NAME: MongoDB database name
        
        # Vector Store Settings
        QDRANT_URL: Qdrant server URL
        QDRANT_API_KEY: Qdrant API key
        COLLECTION_NAME: Name of the vector collection
        
        # LLM Settings
        GROQ_API_KEY: Groq API key
        MODEL_NAME: Name of the Groq model to use
        MAX_CONTEXT_LENGTH: Maximum context length for the model
        TEMPERATURE: Temperature for LLM responses
        
        # PDF Processing
        OCR_ENABLED: Whether to enable OCR for images in PDFs
        PDF_UPLOAD_DIR: Directory to store uploaded PDFs
    """
    
    # Server Settings
    APP_NAME: str = "Advanced RAG System"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Processing Settings
    MAX_WORKERS: int = 4  # Adjust based on server capacity
    CHUNK_SIZE: int = 512  # Tokens per chunk
    CHUNK_OVERLAP: int = 50  # Token overlap between chunks
    EMBEDDING_LENGTH: int = 768
    
    # Database Settings
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "rag_system"
    
    # Vector Store Settings
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    COLLECTION_NAME: str = "documents"
    
    # LLM Settings
    TOP_K: int = 10
    N_LAST_MESSAGE: int = -5
    RAG_THRESHOLD: float = 0.6
    GROQ_API_KEY: str
    MODEL_NAME: str = "mixtral-8x7b-32768"  # Groq's Mixtral model
    MAX_CONTEXT_LENGTH: int = 8192  # 8k context window
    TEMPERATURE: float = 0.7
    
    # PDF Processing
    OCR_ENABLED: bool = True
    PDF_UPLOAD_DIR: str = "uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()
