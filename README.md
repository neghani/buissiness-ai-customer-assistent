# RAG Assistant App

An AI-driven document assistant application that uses Retrieval-Augmented Generation (RAG) to answer questions about uploaded documents.

## Features

- 📄 **Document Upload**: Support for PDF, TXT, DOCX, HTML, and Markdown files
- 🤖 **AI-Powered Q&A**: Ask questions about your documents using OpenAI GPT models
- 🔍 **Vector Search**: Uses Qdrant vector database for semantic search
- 💬 **Streamlit UI**: Clean, modern web interface
- 🐳 **Docker-based**: Fully containerized application
- ⚡ **Background Processing**: Asynchronous document processing
- 📊 **Analytics**: Document statistics and processing status

## Architecture

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

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (optional, can use local models)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd vector-db-rag-implmentation
```

### 2. Configure Environment

```bash
cp env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

### 3. Start the Application

```bash
docker-compose up -d
```

### 4. Access the Application

- **Streamlit UI**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Usage

1. **Upload Documents**: Use the sidebar to upload PDF, TXT, DOCX, HTML, or Markdown files
2. **Wait for Processing**: Documents are processed in the background (check status in sidebar)
3. **Ask Questions**: Use the chat interface to ask questions about your documents
4. **View Sources**: Click on source citations to see relevant document excerpts

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM | Required |
| `EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` |
| `LLM_MODEL` | OpenAI LLM model | `gpt-4o-mini` |
| `CHUNK_SIZE` | Document chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap | `200` |
| `MAX_UPLOAD_SIZE_MB` | Max file upload size | `50` |

### Local Models (Optional)

To use local models instead of OpenAI:

```bash
# Start with Ollama
docker-compose --profile local-llm up -d

# Pull a model
docker exec rag_ollama ollama pull llama3.1:8b

# Update .env
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://ollama:11434
LOCAL_LLM_MODEL=llama3.1:8b
```

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

## Development

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start services individually:
```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Start Redis
docker run -p 6379:6379 redis:7-alpine

# Start API
cd services/api
python main.py

# Start Worker
python -m worker

# Start UI
cd services/ui
streamlit run app.py
```

### Testing

```bash
# Run API tests
cd services/api
pytest

# Test API endpoints
curl http://localhost:8000/v1/health
```

## Troubleshooting

### Common Issues

1. **API not responding**: Check if all services are running with `docker-compose ps`
2. **Document processing stuck**: Check worker logs with `docker-compose logs worker`
3. **Qdrant connection issues**: Ensure Qdrant is healthy with `curl http://localhost:6333/health`
4. **OpenAI API errors**: Verify your API key and check usage limits

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs api
docker-compose logs worker
docker-compose logs ui
```

## Production Deployment

### Security Considerations

1. Set strong `SECRET_KEY` in production
2. Use proper authentication (JWT tokens)
3. Enable HTTPS with reverse proxy
4. Set up proper backup for Qdrant data
5. Monitor resource usage and costs

### Scaling

- **Horizontal scaling**: Add more API and worker containers
- **Qdrant clustering**: For large-scale deployments
- **Load balancing**: Use nginx or similar
- **Monitoring**: Add Prometheus/Grafana

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation at `/docs`
