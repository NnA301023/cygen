from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PyPDF2 import PdfReader
from loguru import logger

from ..settings import get_settings
from .text_chunking import chunk_text_recursive
from .vector_store import VectorStore

settings = get_settings()

class PDFProcessor:
    """
    PDF processor that extracts text directly from PDFs.
    
    This class handles:
    1. PDF text extraction
    2. Text chunking for vector storage
    3. Background processing with configurable threads
    """
    
    def __init__(self):
        """Initialize the PDF processor."""
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
        self.vector_store = VectorStore()
        self.semaphore = asyncio.Semaphore(settings.MAX_WORKERS)
        logger.info(f"Initialized PDFProcessor with {settings.MAX_WORKERS} workers")
    
    async def process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Process a PDF file asynchronously.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List[Dict[str, Any]]: List of processed text chunks with metadata
        """
        try:
            async with self.semaphore:  # Limit concurrent processing
                # Extract text from PDF pages
                pages = await self._extract_text_from_pdf(pdf_path)
                
                # Process chunks in batches
                all_chunks = []
                chunk_tasks = []
                
                for page_num, page_text in enumerate(pages, 1):
                    if not page_text.strip():
                        continue
                    
                    # Create chunk processing task
                    task = asyncio.create_task(self._process_page(
                        page_text=page_text,
                        page_num=page_num,
                        total_pages=len(pages),
                        pdf_path=pdf_path
                    ))
                    chunk_tasks.append(task)
                
                # Wait for all chunk processing to complete
                chunk_results = await asyncio.gather(*chunk_tasks)
                for chunks in chunk_results:
                    all_chunks.extend(chunks)
                
                logger.info(f"Successfully processed PDF: {pdf_path} into {len(all_chunks)} chunks")
                return all_chunks
                
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
    
    async def _process_page(
        self,
        page_text: str,
        page_num: int,
        total_pages: int,
        pdf_path: str
    ) -> List[Dict[str, Any]]:
        """Process a single page of text asynchronously."""
        try:
            # Run chunking in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                self.executor,
                chunk_text_recursive,
                page_text,
                settings.CHUNK_SIZE,
                settings.CHUNK_OVERLAP,
                {
                    "file_path": pdf_path,
                    "page_number": page_num,
                    "total_pages": total_pages
                }
            )
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {str(e)}")
            raise
    
    async def _extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Extract text from each page of the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List[str]: List of text content from each page
        """
        def _extract():
            try:
                reader = PdfReader(pdf_path)
                pages = []
                for page in reader.pages:
                    text = page.extract_text()
                    text = text.strip()
                    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
                    pages.append(text)
                
                logger.info(f"Extracted text from {len(pages)} pages in {pdf_path}")
                return pages
                
            except Exception as e:
                logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
                raise
        
        # Run extraction in thread pool
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _extract
        )
    
    def get_text_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about the processed text.
        
        Args:
            chunks: List of text chunks with metadata
            
        Returns:
            Dict[str, Any]: Statistics about the text
        """
        total_chars = sum(len(chunk["text"]) for chunk in chunks)
        total_chunks = len(chunks)
        avg_chunk_size = total_chars / total_chunks if total_chunks > 0 else 0
        
        return {
            "total_chunks": total_chunks,
            "total_characters": total_chars,
            "average_chunk_size": avg_chunk_size,
            "chunks_per_page": total_chunks / chunks[0]["total_pages"] if chunks else 0
        } 