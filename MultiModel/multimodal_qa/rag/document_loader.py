import pymupdf4llm
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.schema import Document
from typing import List
from core.config import Config
import os
import hashlib
from core.logger import get_logger
from rag.enrichment import DocumentEnricher
from vision.gemini_vision import gemini_vision

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
                if path.lower().endswith(".pdf"):
                    logger.info(f"Converting PDF to Markdown using Gemini: {path}")
                    # Convert PDF to perfect Markdown using Gemini
                    md_text = gemini_vision.pdf_to_markdown(path)
                    
                    # Clean up the output in case Gemini wrapped it in ```markdown ... ```
                    if md_text.startswith("```markdown"):
                        md_text = md_text.replace("```markdown", "", 1)
                        if md_text.endswith("```"):
                            md_text = md_text[:-3]
                    md_text = md_text.strip()
                    
                    # Save the markdown text to an actual .md file on disk
                    md_path = path.rsplit('.', 1)[0] + '.md'
                    with open(md_path, 'w', encoding='utf-8') as f:
                        f.write(md_text)
                    logger.info(f"Saved Markdown file to: {md_path}")
                elif path.lower().endswith((".md", ".markdown")):
                    logger.info(f"Reading Markdown file: {path}")
                    with open(path, 'r', encoding='utf-8') as f:
                        md_text = f.read()
                else:
                    logger.warning(f"Unsupported file type: {path}")
                    continue
                
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
