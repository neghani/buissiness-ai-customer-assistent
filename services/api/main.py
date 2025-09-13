"""
FastAPI backend for RAG Assistant App
"""
import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from config import settings
from database import get_qdrant_client, get_redis_client
from models import Document, DocumentStatus, QueryRequest, QueryResponse, Chunk
from services.document_service import DocumentService
from services.rag_service import RAGService
from worker import enqueue_ingestion_job

app = FastAPI(
    title="RAG Assistant API",
    description="AI-driven document assistant with RAG capabilities",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection
def get_document_service():
    return DocumentService(get_qdrant_client(), get_redis_client())

def get_rag_service():
    return RAGService(get_qdrant_client())

# Pydantic models
class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str

class DocumentListResponse(BaseModel):
    documents: List[Document]
    total: int

# Routes
@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    try:
        qdrant = get_qdrant_client()
        redis = get_redis_client()
        
        # Check Qdrant
        qdrant.get_collections()
        
        # Check Redis
        redis.ping()
        
        return {
            "status": "healthy",
            "qdrant": "connected",
            "redis": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/v1/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    document_service: DocumentService = Depends(get_document_service)
):
    """Upload a document for processing"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Generate document ID
    document_id = str(uuid.uuid4())
    
    # Save file
    file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}_{file.filename}")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document record
    document = Document(
        document_id=document_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        storage_uri=file_path,
        status=DocumentStatus.UPLOADED,
        user_id="default_user",  # TODO: Implement proper auth
        created_at=datetime.utcnow()
    )
    
    # Save to database
    await document_service.create_document(document)
    
    # Enqueue for processing
    background_tasks.add_task(enqueue_ingestion_job, document_id)
    
    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        status="uploaded",
        message="Document uploaded successfully. Processing started."
    )

@app.get("/v1/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    document_service: DocumentService = Depends(get_document_service)
):
    """List all documents"""
    documents = await document_service.list_documents(skip=skip, limit=limit)
    total = await document_service.count_documents()
    
    return DocumentListResponse(documents=documents, total=total)

@app.get("/v1/documents/{document_id}")
async def get_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
):
    """Get a specific document"""
    document = await document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@app.delete("/v1/documents/{document_id}")
async def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Delete a document and its chunks"""
    # Delete chunks from vector DB
    await rag_service.delete_document_chunks(document_id)
    
    # Delete document record
    success = await document_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully"}

@app.post("/v1/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest
):
    """Query documents using RAG (with document retrieval)"""
    try:
        # Always use RAG service for document queries
        rag_service = get_rag_service()
        response = await rag_service.query(request.query, request.filters or {})
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/v1/chat")
async def simple_chat(
    request: QueryRequest
):
    """Simple chat endpoint that bypasses RAG entirely"""
    try:
        print(f"Chat request: {request.query}")
        print(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
        print(f"Model: {settings.LOCAL_LLM_MODEL}")
        
        # Use Ollama directly for simple chat
        import httpx
        async with httpx.AsyncClient() as client:
            ollama_response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.LOCAL_LLM_MODEL,
                    "prompt": request.query,
                    "stream": False
                },
                timeout=30.0
            )
            print(f"Ollama response status: {ollama_response.status_code}")
            ollama_data = ollama_response.json()
            answer = ollama_data.get("response", "Sorry, I couldn't generate a response.")
            
            return QueryResponse(
                answer=answer,
                sources=[],
                metadata={"model": settings.LOCAL_LLM_MODEL, "type": "direct_llm"}
            )
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/v1/query/stream")
async def query_documents_stream(
    query: str,
    filters: Optional[str] = None
):
    """Stream query response"""
    try:
        # For now, just return a simple response without streaming
        if settings.USE_LOCAL_LLM:
            import httpx
            async with httpx.AsyncClient() as client:
                ollama_response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.LOCAL_LLM_MODEL,
                        "prompt": query,
                        "stream": False
                    },
                    timeout=30.0
                )
                ollama_data = ollama_response.json()
                answer = ollama_data.get("response", "Sorry, I couldn't generate a response.")
                
                return StreamingResponse(
                    f"data: {json.dumps({'type': 'answer', 'content': answer})}\n\n",
                    media_type="text/plain",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
                )
        else:
            filter_dict = json.loads(filters) if filters else {}
            rag_service = get_rag_service()
            
            async def generate():
                async for chunk in rag_service.query_stream(query, filter_dict):
                    yield f"data: {json.dumps(chunk)}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming query failed: {str(e)}")

@app.post("/v1/ingest/{document_id}")
async def ingest_document(
    document_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Manually trigger document ingestion"""
    background_tasks.add_task(enqueue_ingestion_job, document_id)
    return {"message": "Ingestion job enqueued"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
