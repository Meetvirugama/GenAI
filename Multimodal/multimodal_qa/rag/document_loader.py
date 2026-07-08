import pymupdf4llm
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.schema import Document
from typing import List
from core.config import Config
import os
import hashlib
from core.logger import get_logger
from rag.enrichment import DocumentEnricher

logger = get_logger(__name__)


class DocumentLoader:
    """Handles PDF loading and text splitting for RAG ingestion."""

    def __init__(self):
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self.markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=self.headers_to_split_on)
        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.enricher = DocumentEnricher()

    def load_pdfs(self, file_paths: List[str]) -> List[Document]:
        """
        Loads and splits one or more PDF files.

        Args:
            file_paths: List of paths to PDF files.

        Returns:
            List of LangChain Document chunks.
        """
        all_docs: List[Document] = []
        for path in file_paths:
            if not os.path.exists(path):
                logger.warning(f"File not found: {path}")
                continue
            try:
                logger.info(f"Converting PDF to Markdown: {path}")
                # Convert PDF to Markdown using pymupdf4llm
                md_text = pymupdf4llm.to_markdown(path)
                
                # Split semantically by Markdown headers
                md_header_splits = self.markdown_splitter.split_text(md_text)
                
                # Compute hash to avoid duplicates
                doc_hash = hashlib.md5(md_text.encode("utf-8")).hexdigest()
                
                # Inject source and hash metadata
                for doc in md_header_splits:
                    doc.metadata["source"] = path
                    doc.metadata["doc_hash"] = doc_hash
                
                # Further split to ensure chunk size limits
                chunks = self.char_splitter.split_documents(md_header_splits)
                
                logger.info(f"  → {len(chunks)} chunks from '{os.path.basename(path)}'")
                
                # Enrich with AI metadata (Phase 2 Knowledge Layer)
                enriched_chunks = self.enricher.enrich_documents(chunks)
                
                all_docs.extend(enriched_chunks)
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")
        return all_docs
