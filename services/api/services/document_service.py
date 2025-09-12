"""
Document management service
"""
import uuid
from datetime import datetime
from typing import List, Optional
from qdrant_client.http import models
from models import Document, DocumentStatus
from database import get_qdrant_client, get_redis_client

class DocumentService:
    def __init__(self, qdrant_client, redis_client):
        self.qdrant = qdrant_client
        self.redis = redis_client
    
    async def create_document(self, document: Document) -> bool:
        """Create a new document record"""
        try:
            # Store in Qdrant documents collection
            point = models.PointStruct(
                id=str(uuid.uuid4()),
                vector=[0.0],  # Dummy vector for metadata storage
                payload={
                    "document_id": document.document_id,
                    "user_id": document.user_id,
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "storage_uri": document.storage_uri,
                    "status": document.status.value,
                    "created_at": document.created_at.isoformat(),
                    "updated_at": document.updated_at.isoformat() if document.updated_at else None,
                    "tags": document.tags or [],
                    "checksum": document.checksum
                }
            )
            
            self.qdrant.upsert(
                collection_name="documents",
                points=[point]
            )
            return True
        except Exception as e:
            print(f"Error creating document: {e}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        try:
            # Search for document in Qdrant
            results = self.qdrant.scroll(
                collection_name="documents",
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if not results[0]:
                return None
            
            point = results[0][0]
            payload = point.payload
            
            return Document(
                document_id=payload["document_id"],
                user_id=payload["user_id"],
                filename=payload["filename"],
                content_type=payload["content_type"],
                storage_uri=payload["storage_uri"],
                status=DocumentStatus(payload["status"]),
                created_at=datetime.fromisoformat(payload["created_at"]),
                updated_at=datetime.fromisoformat(payload["updated_at"]) if payload["updated_at"] else None,
                tags=payload["tags"],
                checksum=payload["checksum"]
            )
        except Exception as e:
            print(f"Error getting document: {e}")
            return None
    
    async def list_documents(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """List documents with pagination"""
        try:
            results = self.qdrant.scroll(
                collection_name="documents",
                limit=limit,
                offset=skip
            )
            
            documents = []
            for point in results[0]:
                payload = point.payload
                documents.append(Document(
                    document_id=payload["document_id"],
                    user_id=payload["user_id"],
                    filename=payload["filename"],
                    content_type=payload["content_type"],
                    storage_uri=payload["storage_uri"],
                    status=DocumentStatus(payload["status"]),
                    created_at=datetime.fromisoformat(payload["created_at"]),
                    updated_at=datetime.fromisoformat(payload["updated_at"]) if payload["updated_at"] else None,
                    tags=payload["tags"],
                    checksum=payload["checksum"]
                ))
            
            return documents
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []
    
    async def count_documents(self) -> int:
        """Count total documents"""
        try:
            result = self.qdrant.count(collection_name="documents")
            return result.count
        except Exception as e:
            print(f"Error counting documents: {e}")
            return 0
    
    async def update_document_status(self, document_id: str, status: DocumentStatus) -> bool:
        """Update document status"""
        try:
            # Get current document
            document = await self.get_document(document_id)
            if not document:
                return False
            
            # Update status
            document.status = status
            document.updated_at = datetime.utcnow()
            
            # Update in Qdrant
            await self.create_document(document)
            return True
        except Exception as e:
            print(f"Error updating document status: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        try:
            # Find and delete from Qdrant
            results = self.qdrant.scroll(
                collection_name="documents",
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if results[0]:
                point_id = results[0][0].id
                self.qdrant.delete(
                    collection_name="documents",
                    points_selector=models.PointIdsList(points=[point_id])
                )
                return True
            return False
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
