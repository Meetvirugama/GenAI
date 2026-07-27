import hashlib
from typing import List, Dict
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from app.core.logger import get_logger

logger = get_logger(__name__)

class AdvancedChunker:
    """
    Implements multiple chunking strategies:
    1. Parent-Child Chunking (Hierarchical)
    2. Heading-based Chunking (Markdown)
    3. Recursive Chunking (Fallback)
    4. Semantic Chunking (Optional)
    """
    
    def __init__(self, chunk_size=500, chunk_overlap=100, parent_chunk_size=2000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parent_chunk_size = parent_chunk_size
        
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self.markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=self.headers_to_split_on)
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.parent_chunk_size,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        self.semantic_chunker = None

    def _init_semantic_chunker(self):
        if not self.semantic_chunker:
            try:
                from langchain_experimental.text_splitter import SemanticChunker
                from langchain_community.embeddings import HuggingFaceEmbeddings
                from app.core.config import Config
                
                embeddings = HuggingFaceEmbeddings(
                    model_name=Config.EMBEDDING_MODEL,
                    model_kwargs={"device": "cpu"}
                )
                self.semantic_chunker = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
                logger.info("SemanticChunker initialized successfully.")
            except ImportError as e:
                logger.warning(f"Semantic chunking dependencies missing: {e}")

    def chunk_documents(self, documents: List[Document], use_semantic=False, use_parent_child=True) -> List[Document]:
        """
        Splits LangChain documents using advanced strategies.
        """
        all_chunks = []
        
        for doc in documents:
            text = doc.page_content
            metadata = doc.metadata.copy()
            
            # Step 1: Heading-based splitting if markdown is detected
            # Docling exports markdown natively, so this helps structure sections
            header_splits = self.markdown_splitter.split_text(text)
            
            for hs in header_splits:
                # Merge the markdown header metadata (e.g. 'Header 1') with the original document metadata
                merged_meta = {**metadata, **hs.metadata}
                
                if use_semantic:
                    self._init_semantic_chunker()
                    if self.semantic_chunker:
                        sem_chunks = self.semantic_chunker.split_documents([Document(page_content=hs.page_content, metadata=merged_meta)])
                        all_chunks.extend(sem_chunks)
                        continue
                
                if use_parent_child:
                    parent_chunks = self.parent_splitter.split_text(hs.page_content)
                    for pc in parent_chunks:
                        parent_id = hashlib.md5(pc.encode("utf-8")).hexdigest()
                        child_chunks = self.child_splitter.split_text(pc)
                        
                        for cc in child_chunks:
                            child_meta = merged_meta.copy()
                            child_meta["parent_id"] = parent_id
                            child_meta["parent_text"] = pc
                            all_chunks.append(Document(page_content=cc, metadata=child_meta))
                else:
                    # Basic Recursive Chunking
                    basic_chunks = self.child_splitter.split_text(hs.page_content)
                    for bc in basic_chunks:
                        all_chunks.append(Document(page_content=bc, metadata=merged_meta.copy()))
                        
        return all_chunks
