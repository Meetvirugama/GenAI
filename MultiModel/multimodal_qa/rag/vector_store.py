# pyrefly: ignore [missing-import]
from langchain_community.vectorstores import Chroma
# pyrefly: ignore [missing-import]
from langchain_pinecone import PineconeVectorStore
# pyrefly: ignore [missing-import]
from langchain_community.embeddings import HuggingFaceEmbeddings
# pyrefly: ignore [missing-import]
from langchain.schema import Document
from typing import List, Optional
from core.config import Config
from core.logger import get_logger
import os

logger = get_logger(__name__)


class VectorStore:
    """Manages ChromaDB or Pinecone vector store for document embeddings."""

    def __init__(self):
        logger.info(f"Initializing embeddings model: {Config.EMBEDDING_MODEL}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=Config.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"}
        )
        self.is_pinecone = bool(Config.PINECONE_API_KEY and Config.PINECONE_INDEX)
        
        if self.is_pinecone:
            logger.info("Initializing Pinecone Vector Store...")
            self._db = PineconeVectorStore(
                index_name=Config.PINECONE_INDEX, 
                embedding=self.embeddings,
                pinecone_api_key=Config.PINECONE_API_KEY
            )
        else:
            logger.info("Initializing local ChromaDB Vector Store...")
            os.makedirs(Config.CHROMA_PERSIST_DIR, exist_ok=True)
            self._db = None

    def add_documents(self, documents: List[Document], session_id: str) -> None:
        """
        Adds a list of Document chunks to the vector store.

        Args:
            documents: Chunked LangChain Document objects.
            session_id: The unique session identifier to attach as metadata.
        """
        if not documents:
            logger.warning("No documents provided to add_documents().")
            return
            
        for doc in documents:
            doc.metadata["session_id"] = session_id
            
        if not self.is_pinecone:
            if self._db is None:
                try:
                    self._db = Chroma(
                        persist_directory=Config.CHROMA_PERSIST_DIR,
                        embedding_function=self.embeddings
                    )
                except Exception:
                    pass
            
            if self._db is not None:
                # Find all existing doc_hashes for this session
                existing = self._db.get(where={"session_id": session_id})
                existing_hashes = set(
                    met.get("doc_hash") for met in existing.get("metadatas", []) if met and "doc_hash" in met
                )
                
                # Filter out chunks that belong to already indexed documents
                filtered_docs = [doc for doc in documents if doc.metadata.get("doc_hash") not in existing_hashes]
                
                if not filtered_docs:
                    logger.info(f"All documents already exist in session {session_id}. Skipping upload.")
                    return
                
                logger.info(f"Skipped {len(documents) - len(filtered_docs)} duplicate chunks. Adding {len(filtered_docs)} new chunks.")
                documents = filtered_docs
        
        logger.info(f"Adding {len(documents)} chunks to vector store for session {session_id}...")
        
        if self.is_pinecone:
            self._db.add_documents(documents)
        else:
            if getattr(self, "_db_created", False) is False and self._db is None:
                self._db = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                    persist_directory=Config.CHROMA_PERSIST_DIR,
                )
                self._db_created = True
            else:
                self._db.add_documents(documents)
        logger.info("Documents added to vector store.")

    def get_retriever(self, session_id: str, k: int = 5):
        """
        Returns a LangChain retriever from the existing vector store for a specific session.

        Args:
            session_id: The active session ID to filter documents.
            k: Number of top documents to retrieve.

        Returns:
            VectorStoreRetriever or None if no database is loaded.
        """
        if not self.is_pinecone and self._db is None:
            # Try loading from persisted directory
            try:
                self._db = Chroma(
                    persist_directory=Config.CHROMA_PERSIST_DIR,
                    embedding_function=self.embeddings
                )
            except Exception as e:
                logger.error(f"Failed to load ChromaDB: {e}")
                return None
                
        vector_retriever = self._db.as_retriever(
            search_kwargs={"k": k, "filter": {"session_id": session_id}}
        )
        
        # Build Hybrid Retriever
        try:
            from langchain.retrievers import EnsembleRetriever
            from langchain_community.retrievers import BM25Retriever
            
            if not self.is_pinecone:
                results = self._db.get(where={"session_id": session_id})
                if results and results.get("documents"):
                    docs = [
                        Document(page_content=doc, metadata=met)
                        for doc, met in zip(results["documents"], results["metadatas"])
                    ]
                    if docs:
                        bm25_retriever = BM25Retriever.from_documents(docs)
                        bm25_retriever.k = k
                        
                        logger.info("Using Hybrid Search (BM25 + Semantic)")
                        return EnsembleRetriever(
                            retrievers=[bm25_retriever, vector_retriever], 
                            weights=[0.5, 0.5]
                        )
        except Exception as e:
            logger.warning(f"Failed to build Hybrid Retriever, falling back to Vector Search: {e}")
            
        return vector_retriever
    def is_ready(self) -> bool:
        """Check if the vector store has indexed documents."""
        try:
            if self.is_pinecone:
                return True
            elif self._db and self._db._collection.count() > 0:
                return True
        except Exception:
            pass
        return False

    def clear_session(self, session_id: str) -> None:
        """Clears all documents from the vector store for the given session."""
        try:
            if self.is_pinecone:
                # delete with metadata filter
                self._db.delete(filter={"session_id": session_id})
                logger.info(f"Pinecone vector store cleared for session {session_id}.")
            elif self._db:
                self._db._collection.delete(where={"session_id": session_id})
                logger.info(f"ChromaDB vector store cleared for session {session_id}.")
        except Exception as e:
            logger.error(f"Error clearing vector store for session {session_id}: {e}")


