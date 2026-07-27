import logging
from typing import List, Sequence, Optional, Any
from langchain.schema import Document
from langchain.callbacks.manager import Callbacks
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from pydantic import PrivateAttr

logger = logging.getLogger(__name__)

class BGEReranker(BaseDocumentCompressor):
    """
    Uses BAAI/bge-reranker-base (a Cross-Encoder) to re-score and re-rank documents.
    """
    model_name: str = "BAAI/bge-reranker-base"
    top_n: int = 5
    _model: Optional[Any] = PrivateAttr(default=None)

    def __init__(self, top_n: int = 5, model_name: str = "BAAI/bge-reranker-base", **kwargs):
        super().__init__(top_n=top_n, model_name=model_name, **kwargs)
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, max_length=512)
            logger.info(f"Loaded Cross-Encoder model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Reranker disabled.")
            self._model = None
        except Exception as e:
            logger.error(f"Failed to load Cross-Encoder {self.model_name}: {e}")
            self._model = None

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        Reranks the documents using the Cross-Encoder.
        """
        if not self._model or not documents:
            # Fallback to no reranking
            return documents[:self.top_n]

        # Prepare pairs: (Query, Document text)
        pairs = [[query, doc.page_content] for doc in documents]
        
        try:
            # Score the pairs
            scores = self._model.predict(pairs)
            
            # Attach scores and sort
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Return top N
            final_docs = []
            for doc, score in scored_docs[:self.top_n]:
                doc.metadata["rerank_score"] = float(score)
                final_docs.append(doc)
                
            return final_docs
        except Exception as e:
            logger.error(f"Reranking failed: {e}. Falling back to original order.")
            return documents[:self.top_n]
