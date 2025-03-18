from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger

def chunk_text_recursive(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Split text into chunks using recursive character text splitter.
    This method is more context-aware than simple character splitting.
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        metadata: Optional metadata to attach to each chunk
        
    Returns:
        List of dictionaries containing chunk text and metadata
    """
    try:
        # Initialize the recursive splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Split the text
        chunks = splitter.split_text(text)
        
        # Prepare chunk documents with metadata
        chunk_docs = []
        for i, chunk in enumerate(chunks):
            doc = {
                "text": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            if metadata:
                doc.update(metadata)
            chunk_docs.append(doc)
        
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunk_docs
        
    except Exception as e:
        logger.error(f"Error chunking text: {str(e)}")
        raise 