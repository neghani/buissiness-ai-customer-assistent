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
    
    # Create chunks collection if it doesn't exist
    if "chunks" not in collection_names:
        client.create_collection(
            collection_name="chunks",
            vectors_config=models.VectorParams(
                size=1536,  # OpenAI embedding size
                distance=models.Distance.COSINE
            )
        )
        print("Created 'chunks' collection in Qdrant")
    
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
