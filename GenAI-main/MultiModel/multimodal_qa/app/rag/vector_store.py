# pyrefly: ignore [missing-import]
from langchain_community.vectorstores import Chroma
# pyrefly: ignore [missing-import]
from langchain_pinecone import PineconeVectorStore
# pyrefly: ignore [missing-import]
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
# pyrefly: ignore [missing-import]
from langchain.schema import Document
from typing import List, Optional
from app.core.config import Config
from app.core.logger import get_logger
from app.rag.retrieval import RetrieverFactory, RetrievalStrategy
import os

logger = get_logger(__name__)


class VectorStore:
    """Manages ChromaDB or Pinecone vector store for document embeddings."""

    def __init__(self):
        self.is_pinecone = bool(Config.PINECONE_API_KEY and Config.PINECONE_INDEX)
        self._db = None
        self._embeddings = None

    @property
    def embeddings(self):
        """Lazy loads the HuggingFace embeddings model and wraps it in a cache."""
        if self._embeddings is None:
            logger.info(f"Initializing embeddings model: {Config.EMBEDDING_MODEL}")
            underlying_embeddings = HuggingFaceEmbeddings(
                model_name=Config.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"}
            )
            
            # Use LocalFileStore for embedding caching to avoid re-computing duplicates
            store_dir = os.path.join(os.getcwd(), "data", "embedding_cache")
            os.makedirs(store_dir, exist_ok=True)
            store = LocalFileStore(store_dir)
            
            self._embeddings = CacheBackedEmbeddings.from_bytes_store(
                underlying_embeddings,
                store,
                namespace=Config.EMBEDDING_MODEL
            )
        return self._embeddings

    def _get_or_init_db(self):
        if self._db is None:
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
                try:
                    self._db = Chroma(
                        persist_directory=Config.CHROMA_PERSIST_DIR,
                        embedding_function=self.embeddings
                    )
                except Exception:
                    pass
        return self._db

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
            
        self._get_or_init_db()

        if not self.is_pinecone and self._db is not None:
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
        
        # Batch Embeddings / Vector Batch Insert
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            logger.info(f"Inserting batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size}...")
            
            if self.is_pinecone:
                self._db.add_documents(batch)
            else:
                try:
                    collection_empty = self._db._collection.count() == 0
                except Exception:
                    collection_empty = False
                if not getattr(self, "_db_created", False) and collection_empty:
                    self._db = Chroma.from_documents(
                        documents=batch,
                        embedding=self.embeddings,
                        persist_directory=Config.CHROMA_PERSIST_DIR,
                    )
                    self._db_created = True
                else:
                    self._db.add_documents(batch)
                    self._db_created = True
                    
        logger.info("Documents added to vector store successfully.")

    def get_retriever(self, session_id: str, k: int = 5, strategy: str = "dense", use_reranker: bool = False):
        """
        Returns a LangChain retriever from the existing vector store for a specific session.

        Args:
            session_id: The active session ID to filter documents.
            k: Number of top documents to retrieve.
            strategy: The retrieval strategy to use (default: "dense").
            use_reranker: Whether to apply Cross-Encoder reranking (default: False).

        Returns:
            VectorStoreRetriever or None if no database is loaded.
        """
        self._get_or_init_db()
        if not self.is_pinecone and self._db is None:
            return None
                
        # Parse strategy enum
        try:
            strat_enum = RetrievalStrategy(strategy.lower())
        except ValueError:
            logger.warning(f"Invalid strategy '{strategy}', defaulting to DENSE.")
            strat_enum = RetrievalStrategy.DENSE
            
        return RetrieverFactory.get_retriever(
            strategy=strat_enum,
            vector_store=self._db,
            session_id=session_id,
            k=k,
            use_reranker=use_reranker
        )
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


