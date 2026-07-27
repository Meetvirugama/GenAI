import logging
from typing import Any

from .base import RetrievalStrategy
from .strategies import (
    BM25Strategy,
    CompressionStrategy,
    DenseStrategy,
    HybridStrategy,
    HyDEStrategy,
    MMRStrategy,
    MultiQueryStrategy,
    ParentStrategy,
    RRFStrategy,
)

logger = logging.getLogger(__name__)

class RetrieverFactory:
    """Factory to build standard LangChain retrievers from various strategies."""
    
    @staticmethod
    def get_retriever(strategy: RetrievalStrategy, vector_store: Any, session_id: str, k: int = 5, use_reranker: bool = False) -> Any:
        logger.info(f"Building retriever with strategy: {strategy} (Reranker: {use_reranker})")
        
        builders = {
            RetrievalStrategy.DENSE: DenseStrategy(),
            RetrievalStrategy.MMR: MMRStrategy(),
            RetrievalStrategy.BM25: BM25Strategy(),
            RetrievalStrategy.HYBRID: HybridStrategy(),
            RetrievalStrategy.RRF: RRFStrategy(),
            RetrievalStrategy.PARENT: ParentStrategy(),
            RetrievalStrategy.COMPRESSION: CompressionStrategy(),
            RetrievalStrategy.MULTI_QUERY: MultiQueryStrategy(),
            RetrievalStrategy.HYDE: HyDEStrategy()
        }
        
        builder = builders.get(strategy)
        if not builder:
            logger.warning(f"Strategy {strategy} not found, falling back to DENSE.")
            builder = DenseStrategy()
            
        # If reranking, we fetch more documents initially (e.g. 20) to give the reranker a good pool
        fetch_k = 20 if use_reranker else k
        base_retriever = builder.build(vector_store, session_id, k=fetch_k)
        
        if use_reranker:
            from langchain.retrievers import ContextualCompressionRetriever

            from .reranker import BGEReranker
            
            compressor = BGEReranker(top_n=k)
            return ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )
            
        return base_retriever
