
import logging
from typing import List
from celery import shared_task


logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_document_task(self, file_paths: List[str], session_id: str):
    """
    Background task to parse documents, chunk them, and upload embeddings to VectorStore.
    """
    from app.rag.document_loader import DocumentLoader
    from app.rag.vector_store import VectorStore
    
    try:
        # State: PARSING
        self.update_state(state='PARSING', meta={'progress': 10, 'message': 'Parsing documents...'})
        logger.info(f"[Task {self.request.id}] Starting parsing for session {session_id}")
        
        doc_loader = DocumentLoader()
        chunks = doc_loader.load_documents(file_paths)
        
        if not chunks:
            logger.warning(f"[Task {self.request.id}] No text could be extracted from files.")
            return {"status": "SUCCESS", "message": "No text extracted", "chunks": 0}
            
        # State: EMBEDDING
        self.update_state(state='EMBEDDING', meta={'progress': 50, 'message': f'Embedding {len(chunks)} chunks...'})
        logger.info(f"[Task {self.request.id}] Embedding {len(chunks)} chunks...")
        
        vector_store = VectorStore()
        vector_store.add_documents(chunks, session_id)
        
        # State: SUCCESS
        logger.info(f"[Task {self.request.id}] Successfully completed indexing.")
        return {"status": "SUCCESS", "message": "Documents indexed successfully", "chunks": len(chunks)}
        
    except Exception as exc:
        logger.error(f"[Task {self.request.id}] Failed: {exc}")
        # Automatically retry the task
        raise self.retry(exc=exc)
