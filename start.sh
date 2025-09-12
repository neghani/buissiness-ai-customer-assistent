#!/bin/bash

# RAG Assistant App Startup Script

echo "🚀 Starting RAG Assistant App..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file and add your OpenAI API key before continuing."
    echo "   You can also use local models by setting USE_LOCAL_LLM=true"
    read -p "Press Enter to continue after editing .env file..."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads
mkdir -p qdrant_data
mkdir -p redis_data

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Qdrant
if curl -f http://localhost:6333/health > /dev/null 2>&1; then
    echo "✅ Qdrant is healthy"
else
    echo "❌ Qdrant is not responding"
fi

# Check Redis
if docker exec rag_redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis is not responding"
fi

# Check API
if curl -f http://localhost:8000/v1/health > /dev/null 2>&1; then
    echo "✅ API is healthy"
else
    echo "❌ API is not responding"
fi

# Check UI
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✅ UI is healthy"
else
    echo "❌ UI is not responding"
fi

echo ""
echo "🎉 RAG Assistant App is starting up!"
echo ""
echo "📱 Access the application:"
echo "   • Streamlit UI: http://localhost:8501"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Qdrant Dashboard: http://localhost:6333/dashboard"
echo ""
echo "📋 Useful commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo ""
echo "🔧 To use local models (optional):"
echo "   • Start Ollama: docker-compose --profile local-llm up -d"
echo "   • Pull model: docker exec rag_ollama ollama pull llama3.1:8b"
echo "   • Update .env: USE_LOCAL_LLM=true"
echo ""
