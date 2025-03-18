from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import asyncio
from collections import deque

from tqdm import tqdm
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from ..settings import get_settings
from .pdf_processor import PDFProcessor
from .vector_store import VectorStore

settings = get_settings()

class BackgroundTaskManager:
    """
    Manages background tasks for PDF processing and vector storage.
    
    This class handles:
    1. PDF processing using PDFProcessor
    2. Vector storage in Qdrant with FastEmbed
    3. Task status tracking in MongoDB
    4. Task queuing and concurrency control
    """
    
    def __init__(self):
        """Initialize the background task manager."""
        self.pdf_processor = PDFProcessor()
        self.mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.vector_store = VectorStore()
        self.task_queue = deque()
        self.processing_semaphore = asyncio.Semaphore(settings.MAX_WORKERS)
        self.queue_processor_task = None
        
        # Ensure vector collection exists
        self._init_vector_collection()
        logger.info("Initialized BackgroundTaskManager")
    
    def _init_vector_collection(self):
        """Initialize the vector collection in Qdrant if it doesn't exist."""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_exists = any(c.name == settings.COLLECTION_NAME for c in collections)
            
            if collection_exists:
                collection_info = self.qdrant_client.get_collection(settings.COLLECTION_NAME)
                if collection_info.config.params.model_dump()["vectors"]["size"] != settings.EMBEDDING_LENGTH:
                    self.qdrant_client.delete_collection(collection_name=settings.COLLECTION_NAME)
                    self.qdrant_client.create_collection(
                        collection_name=settings.COLLECTION_NAME,
                        vectors_config=VectorParams(
                            size=settings.EMBEDDING_LENGTH,
                            distance=Distance.COSINE
                        )
                    )
            else:
                self.qdrant_client.create_collection(
                    collection_name=settings.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_LENGTH,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created vector collection: {settings.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Error initializing vector collection: {str(e)}")
            raise
    
    async def process_pdf_task(self, file_path: str, task_id: str):
        """
        Process a PDF file in the background.
        
        Args:
            file_path: Path to the PDF file
            task_id: Unique identifier for the task
        """
        # Add task to queue
        self.task_queue.append((file_path, task_id))
        
        # Start queue processor if not running
        if self.queue_processor_task is None or self.queue_processor_task.done():
            self.queue_processor_task = asyncio.create_task(self._process_queue())
        
        logger.info(f"Added task {task_id} to queue for file {file_path}")
    
    async def _process_queue(self):
        """Process tasks from the queue with concurrency control."""
        while self.task_queue:
            async with self.processing_semaphore:
                try:
                    file_path, task_id = self.task_queue.popleft()
                    await self._process_single_task(file_path, task_id)
                except Exception as e:
                    logger.error(f"Error processing task from queue: {str(e)}")
    
    async def _process_single_task(self, file_path: str, task_id: str):
        """Process a single PDF task."""
        try:
            # Update task status
            await self._update_task_status(task_id, "processing")
            
            # Process PDF
            documents = await self.pdf_processor.process_pdf(file_path)
            
            # Export HTML versions
            output_dir = Path(settings.PDF_UPLOAD_DIR) / "html"
            output_dir.mkdir(exist_ok=True)
            
            html_paths = []
            chunk_ids = []
            
            for document in tqdm(documents, desc="Processing Document"):
                # Extract text and metadata
                content = document["text"]
                metadata = {k: v for k, v in document.items() if k != "text"}
                
                # Store in vector store
                ids = await self.vector_store.add_texts(
                    texts=[content],
                    metadatas=[metadata]
                )
                chunk_ids.extend(ids)
            
            # Store results
            result = {
                "status": "completed",
                "file_path": file_path,
                "html_paths": html_paths,
                "chunk_ids": chunk_ids,
                "num_pages": len(documents),
                "num_chunks": len(chunk_ids),
                "completed_at": datetime.utcnow()
            }
            
            await self._update_task_status(task_id, "completed", result)
            logger.info(f"Completed task {task_id} with {len(chunk_ids)} chunks")
            
        except Exception as e:
            error_msg = f"Error processing PDF: {str(e)}"
            logger.error(error_msg)
            await self._update_task_status(task_id, "failed", {"error": error_msg})
    
    async def _update_task_status(
        self, 
        task_id: str, 
        status: str, 
        result: Dict[str, Any] = None
    ):
        """
        Update task status in MongoDB.
        
        Args:
            task_id: Task identifier
            status: Current status
            result: Optional result data
        """
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        if result:
            update_data.update(result)
        
        await self.mongo_client[settings.MONGODB_DB_NAME].tasks.update_one(
            {"task_id": task_id},
            {"$set": update_data}
        ) 