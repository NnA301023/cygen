from typing import List, Dict, Any
import uuid

from loguru import logger
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from fastembed.rerank.cross_encoder import TextCrossEncoder
from qdrant_client.http.models import PointStruct, Distance, VectorParams

from ..settings import get_settings

settings = get_settings()

class VectorStore:
    """
    Vector store utility using FastEmbed and Qdrant.
    Uses nomic-embed-text-v1.5 for high-quality embeddings.
    """
    
    def __init__(self):
        """Initialize the vector store with FastEmbed and Qdrant."""

        # Initialize Reranker
        self.reranker = TextCrossEncoder(
            model_name="Xenova/ms-marco-MiniLM-L-12-v2"
        )

        # Initialize FastEmbed
        self.embedding_model = TextEmbedding(
            model_name="nomic-ai/nomic-embed-text-v1.5",
            max_length=settings.EMBEDDING_LENGTH
        )
        
        # Initialize Qdrant client
        self.qdrant = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        
        # Ensure collection exists
        self._init_collection()
        logger.info("Initialized VectorStore")
    
    def _init_collection(self):
        """Initialize the vector collection if it doesn't exist."""
        try:
            collections = self.qdrant.get_collections().collections
            if not any(c.name == settings.COLLECTION_NAME for c in collections):
                self.qdrant.create_collection(
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
    
    async def add_texts(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Add texts to the vector store.
        
        Args:
            texts: List of texts to add
            metadatas: Optional list of metadata dicts
            
        Returns:
            List of IDs for the added texts
        """
        if not self.qdrant.collection_exists(collection_name=settings.COLLECTION_NAME):
            self._init_collection()
        try:
            points = []
            embeddings = list(self.embedding_model.embed(texts))
            ids = [str(uuid.uuid4()) for _ in texts]
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                point = PointStruct(
                    id=ids[i],
                    vector=embedding.tolist(),
                    payload={
                        "text": text,
                        **(metadatas[i] if metadatas else {})
                    }
                )
                points.append(point)
            
            # Upload to Qdrant
            self.qdrant.upsert(
                collection_name=settings.COLLECTION_NAME,
                points=points
            )
            
            logger.info(f"Added {len(texts)} texts to vector store")
            return ids
            
        except Exception as e:
            logger.error(f"Error adding texts to vector store: {str(e)}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar texts in the vector store.
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional filter for the search
            
        Returns:
            List of similar documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = list(self.embedding_model.embed([query]))[0]
            
            # Search in Qdrant
            results = self.qdrant.search(
                collection_name=settings.COLLECTION_NAME,
                query_vector=query_embedding.tolist(),
                limit=k,
                query_filter=filter
            )
            
            # Format results
            docs = []
            for res in results:
                doc = {
                    "id": res.id,
                    "score": res.score,
                    **res.payload
                }
                docs.append(doc)

            # Re Ranking Document
            
            return docs
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            raise 