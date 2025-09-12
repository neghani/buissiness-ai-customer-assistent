# RAG Assistant App - Deployment Guide

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd vector-db-rag-implmentation
   ```

2. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Start the Application**
   ```bash
   ./start.sh
   # OR manually:
   docker-compose up -d
   ```

4. **Access the Application**
   - Streamlit UI: http://localhost:8501
   - API Docs: http://localhost:8000/docs
   - Qdrant Dashboard: http://localhost:6333/dashboard

## Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Streamlit │    │   FastAPI   │    │   Qdrant    │
│     UI      │◄──►│    API      │◄──►│ Vector DB   │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │   Redis     │
                   │   Queue     │
                   └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │   Worker    │
                   │  (RQ Job)   │
                   └─────────────┘
```

## Services

### 1. Qdrant (Vector Database)
- **Port**: 6333
- **Purpose**: Stores document embeddings and metadata
- **Data**: Persistent volume `qdrant_storage`

### 2. Redis (Message Queue)
- **Port**: 6379
- **Purpose**: Background job queue for document processing
- **Data**: Persistent volume `redis_data`

### 3. FastAPI (Backend API)
- **Port**: 8000
- **Purpose**: REST API for document upload, query, and management
- **Dependencies**: Qdrant, Redis

### 4. Worker (Background Processing)
- **Purpose**: Processes uploaded documents (chunk, embed, store)
- **Dependencies**: Qdrant, Redis, API

### 5. Streamlit (Frontend UI)
- **Port**: 8501
- **Purpose**: Web interface for document upload and Q&A
- **Dependencies**: API

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes* |
| `EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` | No |
| `LLM_MODEL` | OpenAI LLM model | `gpt-4o-mini` | No |
| `CHUNK_SIZE` | Document chunk size | `1000` | No |
| `CHUNK_OVERLAP` | Chunk overlap | `200` | No |
| `MAX_UPLOAD_SIZE_MB` | Max file size | `50` | No |

*Required unless using local models

### Local Models (Optional)

To use local models instead of OpenAI:

1. **Start Ollama**:
   ```bash
   docker-compose --profile local-llm up -d
   ```

2. **Pull a model**:
   ```bash
   docker exec rag_ollama ollama pull llama3.1:8b
   ```

3. **Update .env**:
   ```env
   USE_LOCAL_LLM=true
   OLLAMA_BASE_URL=http://ollama:11434
   LOCAL_LLM_MODEL=llama3.1:8b
   USE_LOCAL_EMBEDDINGS=true
   LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

## Usage

### 1. Upload Documents
- Supported formats: PDF, TXT, DOCX, HTML, Markdown
- Use the sidebar in the Streamlit UI
- Documents are processed asynchronously

### 2. Ask Questions
- Use the chat interface
- Questions are answered using RAG (Retrieval-Augmented Generation)
- Sources are provided with each answer

### 3. Monitor Processing
- Check document status in the sidebar
- View analytics in the Analytics tab

## API Endpoints

### Health Check
```bash
GET /v1/health
```

### Upload Document
```bash
POST /v1/upload
Content-Type: multipart/form-data
```

### List Documents
```bash
GET /v1/documents?skip=0&limit=100
```

### Query Documents
```bash
POST /v1/query
{
  "query": "What is the main topic?",
  "filters": {},
  "top_k": 5
}
```

### Delete Document
```bash
DELETE /v1/documents/{document_id}
```

## Troubleshooting

### Common Issues

1. **Services not starting**:
   ```bash
   docker-compose logs
   ```

2. **API not responding**:
   ```bash
   curl http://localhost:8000/v1/health
   ```

3. **Document processing stuck**:
   ```bash
   docker-compose logs worker
   ```

4. **Qdrant connection issues**:
   ```bash
   curl http://localhost:6333/health
   ```

### Health Checks

All services have health checks configured:
- Qdrant: `http://localhost:6333/health`
- Redis: `redis-cli ping`
- API: `http://localhost:8000/v1/health`
- UI: `http://localhost:8501/_stcore/health`

### Logs

```bash
# View all logs
docker-compose logs

# View specific service
docker-compose logs api
docker-compose logs worker
docker-compose logs ui
docker-compose logs qdrant
docker-compose logs redis

# Follow logs in real-time
docker-compose logs -f
```

## Production Considerations

### Security
- Set strong `SECRET_KEY`
- Use proper authentication (JWT tokens)
- Enable HTTPS with reverse proxy
- Restrict API access

### Scaling
- Add more API containers: `docker-compose up --scale api=3`
- Add more worker containers: `docker-compose up --scale worker=3`
- Use Qdrant clustering for large scale
- Add load balancer (nginx)

### Monitoring
- Add Prometheus/Grafana
- Monitor resource usage
- Set up alerts
- Track costs (OpenAI API usage)

### Backup
- Backup Qdrant data: `docker-compose exec qdrant tar -czf /backup/qdrant.tar.gz /qdrant/storage`
- Backup Redis data: `docker-compose exec redis redis-cli BGSAVE`
- Backup uploaded files: `docker-compose exec api tar -czf /backup/uploads.tar.gz /app/uploads`

## Development

### Local Development
```bash
# Start only infrastructure
docker-compose up -d qdrant redis

# Run API locally
cd services/api
pip install -r requirements.txt
python main.py

# Run worker locally
python -m worker

# Run UI locally
cd services/ui
pip install -r requirements.txt
streamlit run app.py
```

### Testing
```bash
# Run API tests
cd services/api
pytest test_api.py

# Test with curl
curl -X POST http://localhost:8000/v1/upload \
  -F "file=@example_documents/sample.txt"
```

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs
- Check service health
- Create an issue in the repository
