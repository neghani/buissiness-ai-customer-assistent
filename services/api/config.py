"""
Configuration management
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str = "your-secret-key-here"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Vector Database
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: str = ""
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # Chunking Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    EMBEDDING_VERSION: str = "v1"
    
    # UI Configuration
    UI_PORT: int = 8501
    
    # Optional: Local LLM (Ollama)
    USE_LOCAL_LLM: bool = False
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    LOCAL_LLM_MODEL: str = "llama3.1:8b"
    
    # Optional: Local Embeddings
    USE_LOCAL_EMBEDDINGS: bool = False
    LOCAL_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
