"""
Background worker for document processing
"""
import asyncio
from rq import Worker, Connection
from redis import Redis
from services.document_service import DocumentService
from services.rag_service import RAGService
from database import get_qdrant_client, get_redis_client
from models import DocumentStatus
from config import settings

def process_document(document_id: str):
    """Process a document (chunk, embed, store)"""
    try:
        # Get services
        qdrant = get_qdrant_client()
        redis = get_redis_client()
        document_service = DocumentService(qdrant, redis)
        rag_service = RAGService(qdrant)
        
        # Get document
        document = asyncio.run(document_service.get_document(document_id))
        if not document:
            print(f"Document {document_id} not found")
            return False
        
        # Update status to processing
        asyncio.run(document_service.update_document_status(document_id, DocumentStatus.PROCESSING))
        
        # Process document
        success = asyncio.run(rag_service.ingest_document(
            document_id=document_id,
            file_path=document.storage_uri,
            content_type=document.content_type
        ))
        
        if success:
            # Update status to ingested
            asyncio.run(document_service.update_document_status(document_id, DocumentStatus.INGESTED))
            print(f"Document {document_id} processed successfully")
        else:
            # Update status to failed
            asyncio.run(document_service.update_document_status(document_id, DocumentStatus.FAILED))
            print(f"Document {document_id} processing failed")
        
        return success
    
    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
        # Update status to failed
        try:
            qdrant = get_qdrant_client()
            redis = get_redis_client()
            document_service = DocumentService(qdrant, redis)
            asyncio.run(document_service.update_document_status(document_id, DocumentStatus.FAILED))
        except:
            pass
        return False

def start_worker():
    """Start the RQ worker"""
    redis_conn = Redis.from_url(settings.REDIS_URL)
    
    with Connection(redis_conn):
        worker = Worker(['document_processing'])
        print("Starting worker...")
        worker.work()
