"""
Streamlit frontend for RAG Assistant App
"""
import streamlit as st
import requests
import json
import time
from typing import List, Dict, Any
import os

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")

# Page configuration
st.set_page_config(
    page_title="RAG Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .status-uploaded { background-color: #e3f2fd; color: #1976d2; }
    .status-processing { background-color: #fff3e0; color: #f57c00; }
    .status-ingested { background-color: #e8f5e8; color: #388e3c; }
    .status-failed { background-color: #ffebee; color: #d32f2f; }
    .source-card {
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #fafafa;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 2rem;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/v1/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def upload_document(file) -> Dict[str, Any]:
    """Upload a document to the API"""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(f"{API_BASE_URL}/v1/upload", files=files, timeout=30)
        return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

def get_documents() -> List[Dict[str, Any]]:
    """Get list of documents"""
    try:
        response = requests.get(f"{API_BASE_URL}/v1/documents", timeout=10)
        return response.json()["documents"] if response.status_code == 200 else []
    except:
        return []

def query_documents(query: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Query documents"""
    try:
        payload = {"query": query, "filters": filters or {}}
        response = requests.post(f"{API_BASE_URL}/v1/query", json=payload, timeout=30)
        return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

def delete_document(document_id: str) -> bool:
    """Delete a document"""
    try:
        response = requests.delete(f"{API_BASE_URL}/v1/documents/{document_id}", timeout=10)
        return response.status_code == 200
    except:
        return False

def get_status_badge(status: str) -> str:
    """Get status badge HTML"""
    status_classes = {
        "uploaded": "status-uploaded",
        "processing": "status-processing", 
        "ingested": "status-ingested",
        "failed": "status-failed"
    }
    class_name = status_classes.get(status, "status-uploaded")
    return f'<span class="status-badge {class_name}">{status.upper()}</span>'

def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 RAG Assistant</h1>', unsafe_allow_html=True)
    
    # Check API health
    if not check_api_health():
        st.error("⚠️ API is not available. Please check if the backend services are running.")
        return
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Documents")
        
        # Upload section
        st.subheader("Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'txt', 'docx', 'html', 'md'],
            help="Supported formats: PDF, TXT, DOCX, HTML, Markdown"
        )
        
        if uploaded_file is not None:
            if st.button("Upload", type="primary"):
                with st.spinner("Uploading..."):
                    result = upload_document(uploaded_file)
                    if "error" in result:
                        st.error(f"Upload failed: {result['error']}")
                    else:
                        st.success(f"✅ Uploaded: {result['filename']}")
                        st.rerun()
        
        # Document list
        st.subheader("Document Library")
        documents = get_documents()
        
        if not documents:
            st.info("No documents uploaded yet")
        else:
            for doc in documents:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{doc['filename']}**")
                        st.markdown(get_status_badge(doc['status']), unsafe_allow_html=True)
                    with col2:
                        if st.button("🗑️", key=f"delete_{doc['document_id']}", help="Delete document"):
                            if delete_document(doc['document_id']):
                                st.success("Document deleted")
                                st.rerun()
                            else:
                                st.error("Failed to delete document")
                    st.divider()
    
    # Main content area
    tab1, tab2 = st.tabs(["💬 Chat", "📊 Analytics"])
    
    with tab1:
        st.header("Ask Questions About Your Documents")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show sources if available
                if "sources" in message and message["sources"]:
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(message["sources"]):
                            st.markdown(f"**Source {i+1}:**")
                            st.markdown(f"*{source['text']}*")
                            if "metadata" in source:
                                st.markdown(f"**Document:** {source['metadata'].get('filename', 'Unknown')}")
        
        # Chat input
        if prompt := st.chat_input("Ask a question about your documents..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = query_documents(prompt)
                    
                    if "error" in response:
                        st.error(f"Query failed: {response['error']}")
                    else:
                        # Display answer
                        st.markdown(response["answer"])
                        
                        # Display sources
                        if response.get("sources"):
                            with st.expander("📚 Sources"):
                                for i, source in enumerate(response["sources"]):
                                    st.markdown(f"**Source {i+1}:**")
                                    st.markdown(f"*{source['text']}*")
                                    if "metadata" in source:
                                        st.markdown(f"**Document:** {source['metadata'].get('filename', 'Unknown')}")
                                        st.markdown(f"**Score:** {source.get('score', 'N/A')}")
                        
                        # Add assistant message to history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": response["answer"],
                            "sources": response.get("sources", [])
                        })
    
    with tab2:
        st.header("Document Analytics")
        
        # Document statistics
        col1, col2, col3, col4 = st.columns(4)
        
        total_docs = len(documents)
        ingested_docs = len([d for d in documents if d['status'] == 'ingested'])
        processing_docs = len([d for d in documents if d['status'] == 'processing'])
        failed_docs = len([d for d in documents if d['status'] == 'failed'])
        
        with col1:
            st.metric("Total Documents", total_docs)
        with col2:
            st.metric("Ingested", ingested_docs, delta=f"{ingested_docs/total_docs*100:.1f}%" if total_docs > 0 else "0%")
        with col3:
            st.metric("Processing", processing_docs)
        with col4:
            st.metric("Failed", failed_docs)
        
        # Document status chart
        if documents:
            import pandas as pd
            status_counts = pd.Series([d['status'] for d in documents]).value_counts()
            st.bar_chart(status_counts)
        
        # Recent activity
        st.subheader("Recent Activity")
        if documents:
            recent_docs = sorted(documents, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
            for doc in recent_docs:
                st.write(f"📄 {doc['filename']} - {doc['status']}")

if __name__ == "__main__":
    main()
