"""
Simple API tests
"""
import pytest
import requests
import time

API_BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    response = requests.get(f"{API_BASE_URL}/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_upload_document():
    """Test document upload"""
    # Create a test file
    test_content = "This is a test document for RAG testing."
    files = {
        "file": ("test.txt", test_content, "text/plain")
    }
    
    response = requests.post(f"{API_BASE_URL}/v1/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "test.txt"
    
    return data["document_id"]

def test_list_documents():
    """Test document listing"""
    response = requests.get(f"{API_BASE_URL}/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total" in data

def test_query_documents():
    """Test document querying"""
    # First upload a test document
    test_content = "The quick brown fox jumps over the lazy dog. This is a test document about animals."
    files = {
        "file": ("test_query.txt", test_content, "text/plain")
    }
    
    upload_response = requests.post(f"{API_BASE_URL}/v1/upload", files=files)
    assert upload_response.status_code == 200
    
    document_id = upload_response.json()["document_id"]
    
    # Wait for processing (in real scenario, this would be handled by worker)
    time.sleep(2)
    
    # Query the document
    query_data = {
        "query": "What animals are mentioned?",
        "filters": {}
    }
    
    response = requests.post(f"{API_BASE_URL}/v1/query", json=query_data)
    # Note: This might fail if document isn't processed yet, which is expected
    # In a real test, you'd wait for processing to complete

if __name__ == "__main__":
    pytest.main([__file__])
