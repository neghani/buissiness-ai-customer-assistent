## RAG Assistant App – Technical Specification

### 1) Overview
- **Goal**: Users upload broad-topic documents. The system chunks, embeds, and stores them in a vector index. UI queries run a RAG pipeline to retrieve relevant chunks and generate answers.
- **Constraints**:
  - **Docker-only** deployment.
  - **Python-only** for both frontend and backend.
  - Use a **recommended vector DB**.
  - Choose libraries for simplicity, reliability, and performance.

### 2) High-Level Architecture
- **Services (containers)**:
  - **api**: FastAPI service (ingestion, retrieval, chat endpoints).
  - **worker**: Background jobs for heavy ingestion and re-indexing.
  - **ui**: Streamlit app consuming `api`.
  - **vector-db**: Qdrant (vector database).
  - **redis**: Message broker for background jobs.
  - (Optional) **ollama**: Local LLM for fully offline deployments.
  - (Optional) **nginx**: Reverse proxy and TLS termination.

- **Data flow**:
  1. User uploads file in `ui` → sent to `api`.
  2. `api` stores file (filesystem or object storage) → enqueues ingestion job.
  3. `worker` extracts text, chunks, embeds, and upserts to **Qdrant**.
  4. User asks a question in `ui` → `api` runs retrieve-then-read (RAG) with Qdrant and an LLM → streams response to `ui`.

### 3) Technology Choices (Python-first)
- **Frontend (Python)**: Streamlit
  - Pros: Fast to build, Python-native, streaming UI is simple.
- **Backend**: FastAPI + Pydantic v2 + Uvicorn
  - Pros: Modern, typed, great performance, first-class async, easy OpenAPI.
- **Vector DB**: Qdrant
  - Rationale: Open-source, production-ready, HNSW + product quantization, great filters, easy Docker, strong ecosystem.
- **RAG Orchestration**: LlamaIndex
  - Rationale: Clean abstractions for loaders, chunking, embeddings, retrieval, and evaluators. Works well with Qdrant.
  - Alternative: LangChain or Haystack (both viable; choose based on team familiarity).
- **Embeddings**:
  - Default: OpenAI `text-embedding-3-large` (highest quality) or `-small` (cost-effective).
  - Local fallback: `sentence-transformers` (e.g., `gte-large`, `e5-large-v2`) via Hugging Face.
- **LLM**:
  - Default: OpenAI GPT-4o-mini / GPT-4.1 for quality and function calling.
  - Local fallback: **Ollama** with Llama 3.1 8B/70B or Qwen models.
- **Background Jobs**: RQ or Celery (pick one; spec assumes RQ for simplicity) + Redis.
- **Document Parsing**:
  - PDFs: `pymupdf` (fitz) for robust extraction.
  - DOCX: `docx2txt` or `python-docx`.
  - HTML/MD/TXT: `beautifulsoup4` / native parsing.
  - Optional richer parsing: `unstructured` (heavier, use if high-fidelity layout matters).
- **Observability**: Python `logging` + OpenTelemetry traces (optional) + Prometheus metrics (optional).
- **Config**: `python-dotenv` for local, environment variables in Docker for prod.

### 4) Data Model & Indexing
- **Collections**:
  - `documents`: metadata per uploaded file
    - `document_id`, `user_id`, `filename`, `content_type`, `storage_uri`, `checksum`, `status`, `created_at`, `tags`
  - `chunks` (in Qdrant as vectors; payload mirrors metadata)
    - `chunk_id`, `document_id`, `user_id`, `text`, `vector`, `chunk_index`, `page_number`, `section`, `tags`, `language`, `source`
- **Chunking Strategy**:
  - Recursive semantic/character splitter:
    - Target size: 800–1,200 tokens, overlap 150–250 tokens.
    - Optional semantic boundaries (headers, sections) when parseable.
  - Store full source refs and page/section for citations.
- **Embedding Strategy**:
  - Normalize vectors, store in Qdrant with cosine similarity.
  - Batch embedding (e.g., 64–128 chunks/batch) with retry/backoff.
  - Keep an embedding version to allow migrations.

### 5) Retrieval & RAG
- **Retrieval**:
  - Hybrid retriever: dense vector similarity + optional keyword BM25 fallback (LlamaIndex `BM25Retriever` or Qdrant’s filters + local BM25).
  - Filters: by `user_id`, `tags`, `document_id`, and `embedding_version`.
  - Top-k: 4–8; apply MMR for diversity.
- **Augmentation**:
  - Context window assembly: deduplicate and merge overlapping chunks; truncate to fit model token limits.
  - Optional context re-ranking: `cross-encoder/ms-marco-MiniLM-L-12-v2`.
- **Generation**:
  - Prompt template with strict instructions and style:
    - System: role, persona, guardrails.
    - User: question + context.
    - Developer: citation and refusal policy.
  - Output with citations pointing to `document_id` and `chunk_index`.
  - Streaming tokens to the UI.
- **Caching**:
  - In-memory LRU for recent queries; embedding cache keyed by text hash.

### 6) API Design (FastAPI)
- Auth: API key or JWT (per user/tenant).
- Endpoints (summary):
  - `POST /v1/upload` – multipart file upload; returns `document_id`.
  - `POST /v1/ingest/{document_id}` – enqueue or synchronous (dev-only) ingestion.
  - `GET /v1/documents` – list user documents, with status.
  - `DELETE /v1/documents/{document_id}` – delete doc + chunks.
  - `POST /v1/query` – { query, filters? } → non-streaming RAG answer + citations.
  - `GET /v1/query/stream` – SSE/websocket for streamed answers.
  - `GET /v1/health` – liveness/readiness.
  - `POST /v1/reindex` – re-embed with a new embedding version (admin).
- Pagination, rate limits, and structured error responses included.

### 7) Frontend (Streamlit)
- Pages:
  - Upload page: drag-and-drop, file list with status/progress.
  - Search/Chat page: prompt input, streaming answer, citations, source preview.
  - Documents page: filters, tags, delete/reindex actions.
- UX details:
  - Show chunk-level citations and expand-on-click to reveal source text.
  - Loading indicators for ingestion and query.
  - Persist session state; allow saving conversations (optional).
- Connectivity: calls `api` endpoints; websockets/SSE for streaming.

### 8) Docker & Deployment
- **Volumes**:
  - Qdrant storage volume.
  - Document storage volume (or S3/MinIO for object storage).
- **Networking**:
  - Each service on the same Docker network; `ui` talks to `api`, `api` to `vector-db` and `redis`.
- **Example docker-compose (trimmed)**:
```yaml
version: "3.9"
services:
  api:
    build: ./services/api
    env_file: ./.env
    depends_on: [vector-db, redis]
    ports: ["8000:8000"]
  worker:
    build: ./services/api
    command: ["python", "-m", "worker.run"]
    env_file: ./.env
    depends_on: [api, redis, vector-db]
  ui:
    build: ./services/ui
    env_file: ./.env
    depends_on: [api]
    ports: ["8501:8501"]
  vector-db:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_storage:/qdrant/storage
    ports: ["6333:6333"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  # ollama (optional local LLM)
  # ollama:
  #   image: ollama/ollama:latest
  #   ports: ["11434:11434"]
volumes:
  qdrant_storage:
```
- **Config via .env**:
  - `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `LLM_PROVIDER`, `QDRANT_URL`, `REDIS_URL`, `AUTH_SECRET`, `MAX_UPLOAD_MB`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `EMBEDDING_VERSION`.

### 9) Background Ingestion
- Queue: Redis + RQ workers.
- Steps:
  1) Fetch document from storage.
  2) Parse to text with metadata (pages/sections).
  3) Chunk via LlamaIndex splitters.
  4) Embed in batches; retry with exponential backoff.
  5) Upsert into Qdrant with payloads.
  6) Mark `documents.status = ingested` or `failed`.
- Idempotency: content-hash to skip reprocessing identical files.
- Concurrency: configurable worker pool size.

### 10) Security & Privacy
- File validation: size/type limits, reject executables; virus scan (optional ClamAV).
- Sandboxed parsing; limit PDF resource usage.
- AuthN/Z: API key or JWT; enforce `user_id` scoping on all queries and filters.
- PII handling: redact patterns (emails, phones) optionally before storage.
- Secrets: mounted as env vars; never commit.
- Backups: Qdrant snapshots; document store backups; retention policy.

### 11) Observability & Ops
- Logging: structured JSON logs, correlation IDs per request/job.
- Metrics: request latency, retrieval time, tokens used, Qdrant query time, ingestion throughput, failures.
- Tracing: OpenTelemetry (optional) spanning `ui` → `api` → Qdrant/LLM.
- Health checks: `/v1/health` (readiness includes Qdrant and Redis).
- Cost control: track tokens and embedding calls per user; quotas and alerts.

### 12) Quality, Testing, and Evaluation
- Unit tests: parsing, chunking, embedding wrappers, retriever filters.
- Integration tests: end-to-end ingestion and RAG flow using test docs.
- RAG evaluation: RAGAS or LlamaIndex evals with curated Q/A sets; track precision@k, faithfulness, answer relevancy.
- Prompt tests: golden prompts with snapshot diffs.
- Load tests: concurrent ingestion and queries; target p95 latencies.

### 13) Performance & Scalability
- Batch embedding and upsert; reuse HTTP sessions.
- Use MMR and re-ranking to improve quality without increasing k excessively.
- Scale:
  - Horizontally scale `api` and `worker`.
  - Qdrant can scale vertically; for large scale, consider Qdrant distributed.
- Caching:
  - Short-term query cache; persistent embedding cache keyed by text hash and model.
- Cold start mitigation: warm up embedding and LLM clients.

### 14) Configuration Matrix
- **Providers**:
  - Cloud: OpenAI embeddings + LLM, Qdrant self-hosted.
  - Fully local: `sentence-transformers` + Ollama + Qdrant.
- **Toggles**:
  - `USE_LOCAL_LLM=true|false`
  - `USE_LOCAL_EMBEDDINGS=true|false`
  - `RERANKER_MODEL_NAME=<name|empty>`

### 15) Milestones
- M1: Core ingestion → Qdrant; simple query → answer with citations.
- M2: Background workers; UI polish; streaming responses.
- M3: Auth, multi-user scoping, filters/tags.
- M4: Observability, RAG evals, re-indexing/embedding versioning.
- M5: Optional local LLM/embeddings via Ollama; cost monitoring.

### 16) Risks & Mitigations
- Parsing quality on complex PDFs → allow `unstructured` path as fallback.
- Token costs → default to `-small` embeddings; add caching.
- Latency with large contexts → MMR + re-ranking; strict context windowing.
- Multi-tenancy data leakage → strict filters by `user_id` on every query.
- Model/provider changes → embed/generation versioning; reindex tooling.

### 17) Open Questions
- Will deployment be internet-restricted (local LLM/embeddings required)?
- Do we need SSO or simple API keys suffice initially?
- Storage choice: local volume vs S3/MinIO?
- Required document types and maximum sizes?
- Retention and deletion policies (compliance/GDPR)?

### 18) Library List (condensed)
- Backend: `fastapi`, `pydantic`, `uvicorn`, `llama-index`, `qdrant-client`, `redis`, `rq`, `tenacity`, `python-dotenv`
- Parsing: `pymupdf`, `docx2txt`, `beautifulsoup4`, `markdown`
- LLM: `openai` (or `ollama` client), `sentence-transformers`
- Frontend: `streamlit`
- Testing: `pytest`, `httpx`, `pytest-asyncio`
- Observability: `opentelemetry-sdk` (optional), `prometheus-client` (optional)

### 19) What was added beyond your list
- Background job system for scalable ingestion.
- Auth, multi-tenancy scoping, and security controls.
- Observability, cost tracking, and evaluation (RAGAS).
- Re-indexing and embedding version control.
- Optional local-only mode (Ollama + sentence-transformers).
- Explicit data model, API endpoints, and performance practices.

### 20) Acceptance Criteria (Phase 1)
- Upload a PDF → ingestion completes → chunks visible in Qdrant.
- Ask a query → top-k retrieval → streamed answer with at least 2 citations.
- Multi-user isolation demonstrated via filters.
- Docker Compose up/down works locally; health checks pass.

---

- I can turn this spec into a minimal scaffold (compose, FastAPI skeleton, Streamlit pages) if you want.