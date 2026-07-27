from langchain.schema import Document
from typing import List
from app.core.config import Config
import os
import hashlib
from app.core.logger import get_logger
from app.rag.enrichment import DocumentEnricher
from app.rag.parsers import ParserFactory
from app.rag.chunker import AdvancedChunker

logger = get_logger(__name__)


class DocumentLoader:
    """Handles PDF loading and text splitting for RAG ingestion."""

    def __init__(self):
        self.chunker = AdvancedChunker(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            parent_chunk_size=2000
        )
        self.enricher = DocumentEnricher()

    def load_documents(self, file_paths: List[str]) -> List[Document]:
        """
        Loads and splits one or more PDF or Markdown files.

        Args:
            file_paths: List of paths to files (.pdf or .md).

        Returns:
            List of LangChain Document chunks.
        """
        all_docs: List[Document] = []
        for path in file_paths:
            if not os.path.exists(path):
                logger.warning(f"File not found: {path}")
                continue
            try:
                parser = ParserFactory.get_parser(path)
                result = parser.extract(path)
                
                pages = result.get("pages", [])
                if not pages:
                    logger.warning(f"No pages extracted from {path}")
                    continue
                
                # Convert parsed pages into LangChain Documents with initial metadata
                page_docs = []
                for p in pages:
                    text_content = p.get("text", "")
                    page_num = p.get("page_num", 1)
                    if text_content.strip():
                        meta = {
                            "source": path,
                            "page_number": page_num,
                            "doc_hash": hashlib.md5(text_content.encode("utf-8")).hexdigest()
                        }
                        page_docs.append(Document(page_content=text_content, metadata=meta))
                
                # Apply advanced chunking (Semantic optional, Parent-Child active by default)
                chunks = self.chunker.chunk_documents(page_docs, use_semantic=False, use_parent_child=True)
                
                logger.info(f"  → {len(chunks)} chunks from '{os.path.basename(path)}'")
                
                # Enrich with AI metadata (Phase 2 Knowledge Layer)
                enriched_chunks = self.enricher.enrich_documents(chunks)
                
                all_docs.extend(enriched_chunks)
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")
        return all_docs
