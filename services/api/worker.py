"""
Worker entry point
"""
from rq import Queue
from redis import Redis
from config import settings
from services.worker import process_document

def enqueue_ingestion_job(document_id: str):
    """Enqueue a document for processing"""
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue('document_processing', connection=redis_conn)
    job = queue.enqueue(process_document, document_id)
    print(f"Enqueued job {job.id} for document {document_id}")
    return job

if __name__ == "__main__":
    from services.worker import start_worker
    start_worker()
