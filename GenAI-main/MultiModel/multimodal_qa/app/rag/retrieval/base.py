from enum import Enum
from abc import ABC, abstractmethod
from typing import Any

class RetrievalStrategy(str, Enum):
    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"
    RRF = "rrf"
    MMR = "mmr"
    PARENT = "parent"
    COMPRESSION = "compression"
    MULTI_QUERY = "multi_query"
    HYDE = "hyde"

class BaseRetrieverBuilder(ABC):
    """Abstract base class for building retrievers."""
    
    @abstractmethod
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs) -> Any:
        """
        Builds and returns a LangChain Retriever.
        
        Args:
            vector_store: The underlying VectorStore (Chroma or Pinecone).
            session_id: The session ID for metadata filtering.
            k: Number of documents to retrieve.
        """
        pass
