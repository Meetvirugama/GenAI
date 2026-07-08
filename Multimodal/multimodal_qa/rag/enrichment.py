from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain.schema import Document
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

class ChunkMetadata(BaseModel):
    summary: str = Field(description="A concise 1-sentence summary of the text chunk.")
    keywords: List[str] = Field(description="A list of 5-10 highly relevant searchable keywords extracted from the text.")

class DocumentEnricher:
    """Enriches Markdown chunks with AI-generated metadata before embedding."""
    
    def __init__(self):
        # We use a fast, inexpensive model for enrichment
        self.llm = ChatGroq(
            api_key=Config.GROQ_API_KEYS[0],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            max_retries=2
        ).with_structured_output(ChunkMetadata)
        
    def enrich_chunk(self, doc: Document) -> Document:
        """Processes a single document chunk and injects metadata."""
        content = doc.page_content
        if not content.strip():
            return doc
            
        try:
            prompt = f"Analyze the following document chunk and extract a 1-sentence summary and 5-10 keywords.\n\nChunk:\n{content[:2000]}"
            result = self.llm.invoke(prompt)
            if isinstance(result, ChunkMetadata):
                doc.metadata["summary"] = result.summary
                doc.metadata["keywords"] = ", ".join(result.keywords)
        except Exception as e:
            logger.warning(f"Failed to enrich chunk metadata: {e}")
            
        return doc

    def enrich_documents(self, documents: List[Document], max_workers: int = 10) -> List[Document]:
        """Processes a list of chunks in parallel to minimize latency."""
        if not documents:
            return documents
            
        logger.info(f"Enriching {len(documents)} chunks with AI metadata (summary, keywords)...")
        enriched_docs = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_doc = {executor.submit(self.enrich_chunk, doc): doc for doc in documents}
            for future in as_completed(future_to_doc):
                try:
                    enriched_docs.append(future.result())
                except Exception as e:
                    logger.error(f"Error in enrichment thread: {e}")
                    enriched_docs.append(future_to_doc[future]) # fallback to unenriched
                    
        return enriched_docs
