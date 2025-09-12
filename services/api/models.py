"""
Pydantic models for the API
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INGESTED = "ingested"
    FAILED = "failed"

class Document(BaseModel):
    document_id: str
    user_id: str
    filename: str
    content_type: str
    storage_uri: str
    status: DocumentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    checksum: Optional[str] = None

class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    user_id: str
    text: str
    chunk_index: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    tags: Optional[List[str]] = None
    language: Optional[str] = None
    source: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5
    temperature: float = 0.7

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class IngestionJob(BaseModel):
    document_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
