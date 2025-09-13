"""
Database connections and setup
"""
from qdrant_client import QdrantClient
from qdrant_client.http import models
import redis
from config import settings

# Global clients
_qdrant_client = None
_redis_client = None

def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client (singleton)"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        )
        # Ensure collections exist
        _ensure_collections()
    return _qdrant_client

def get_redis_client() -> redis.Redis:
    """Get Redis client (singleton)"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client

def _ensure_collections():
    """Ensure required Qdrant collections exist"""
    client = get_qdrant_client()
    
    # Check if collections exist
    collections = client.get_collections()
    collection_names = [col.name for col in collections.collections]
    
    # Determine vector dimensions based on embedding model
    if settings.USE_LOCAL_EMBEDDINGS:
        # For local embeddings, use 384 dimensions (all-MiniLM-L6-v2)
        vector_size = 384
        collection_name = "chunks_local"
    else:
        # For OpenAI embeddings, use 1536 dimensions
        vector_size = 1536
        collection_name = "chunks"
    
    # Create chunks collection if it doesn't exist
    if collection_name not in collection_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        print(f"Created '{collection_name}' collection in Qdrant with {vector_size} dimensions")
    
    # Create documents collection if it doesn't exist
    if "documents" not in collection_names:
        client.create_collection(
            collection_name="documents",
            vectors_config=models.VectorParams(
                size=1,  # Dummy size for metadata storage
                distance=models.Distance.COSINE
            )
        )
        print("Created 'documents' collection in Qdrant")
