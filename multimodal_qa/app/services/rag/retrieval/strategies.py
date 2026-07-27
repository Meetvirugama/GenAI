import logging
from typing import Any

from langchain.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
    MultiQueryRetriever,
)
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.schema import Document
from langchain_community.retrievers import BM25Retriever
from langchain_groq import ChatGroq

from app.core.config import Config

from .base import BaseRetrieverBuilder

logger = logging.getLogger(__name__)

def get_llm():
    return ChatGroq(
        api_key=Config.GROQ_API_KEYS[0],
        model=Config.LLM_MODEL,
        temperature=0
    )

class DenseStrategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):
        return vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k, "filter": {"session_id": session_id}}
        )

class MMRStrategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):
        return vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": k * 3, "filter": {"session_id": session_id}}
        )

class BM25Strategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):
        # We need the actual documents to build BM25.
        # This requires pulling docs from Chroma for the session.
        try:
            results = vector_store.get(where={"session_id": session_id})
            if results and results.get("documents"):
                docs = [
                    Document(page_content=doc, metadata=met)
                    for doc, met in zip(results["documents"], results["metadatas"])
                ]
                bm25_retriever = BM25Retriever.from_documents(docs)
                bm25_retriever.k = k
                return bm25_retriever
            else:
                logger.warning("No documents found for BM25. Falling back to Dense.")
                return DenseStrategy().build(vector_store, session_id, k)
        except Exception as e:
            logger.error(f"BM25 build failed: {e}")
            return DenseStrategy().build(vector_store, session_id, k)

class HybridStrategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):
        dense = DenseStrategy().build(vector_store, session_id, k)
        bm25 = BM25Strategy().build(vector_store, session_id, k)
        
        # If BM25 failed and returned Dense, don't ensemble
        if type(dense) == type(bm25):
            return dense
            
        return EnsembleRetriever(retrievers=[bm25, dense], weights=[0.5, 0.5])

class RRFStrategy(BaseRetrieverBuilder):
    """Custom Retriever that implements Reciprocal Rank Fusion on top of Hybrid."""
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):

        from langchain.callbacks.manager import CallbackManagerForRetrieverRun
        from langchain.schema import BaseRetriever
        
        class RRFRetriever(BaseRetriever):
            retriever1: BaseRetriever
            retriever2: BaseRetriever
            k: int
            
            def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
                docs1 = self.retriever1.invoke(query)
                docs2 = self.retriever2.invoke(query)
                
                # RRF Algorithm
                rrf_score = {}
                c = 60 # Constant
                
                for rank, doc in enumerate(docs1):
                    doc_str = doc.page_content
                    rrf_score[doc_str] = rrf_score.get(doc_str, 0) + 1 / (rank + c)
                    
                for rank, doc in enumerate(docs2):
                    doc_str = doc.page_content
                    rrf_score[doc_str] = rrf_score.get(doc_str, 0) + 1 / (rank + c)
                    
                # Map strings back to docs
                all_docs = {doc.page_content: doc for doc in docs1 + docs2}
                
                # Sort by score
                sorted_docs = sorted(rrf_score.items(), key=lambda x: x[1], reverse=True)
                
                # Return top k
                return [all_docs[doc_str] for doc_str, score in sorted_docs[:self.k]]
        
        return RRFRetriever(
            retriever1=DenseStrategy().build(vector_store, session_id, k),
            retriever2=BM25Strategy().build(vector_store, session_id, k),
            k=k
        )

class ParentStrategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):

        from langchain.callbacks.manager import CallbackManagerForRetrieverRun
        from langchain.schema import BaseRetriever
        
        class CustomParentRetriever(BaseRetriever):
            base_retriever: BaseRetriever
            
            def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
                child_docs = self.base_retriever.invoke(query)
                parent_docs = []
                seen_parents = set()
                
                for child in child_docs:
                    parent_text = child.metadata.get("parent_text")
                    parent_id = child.metadata.get("parent_id")
                    
                    if parent_text and parent_id:
                        if parent_id not in seen_parents:
                            seen_parents.add(parent_id)
                            parent_docs.append(Document(page_content=parent_text, metadata=child.metadata))
                    else:
                        parent_docs.append(child)
                return parent_docs
                
        return CustomParentRetriever(base_retriever=DenseStrategy().build(vector_store, session_id, k))

class CompressionStrategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):
        llm = get_llm()
        compressor = LLMChainExtractor.from_llm(llm)
        base_retriever = DenseStrategy().build(vector_store, session_id, k)
        return ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=base_retriever
        )

class MultiQueryStrategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):
        llm = get_llm()
        base_retriever = DenseStrategy().build(vector_store, session_id, k)
        return MultiQueryRetriever.from_llm(
            retriever=base_retriever, llm=llm
        )

class HyDEStrategy(BaseRetrieverBuilder):
    def build(self, vector_store: Any, session_id: str, k: int = 5, **kwargs):

        from langchain.callbacks.manager import CallbackManagerForRetrieverRun
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        from langchain.schema import BaseRetriever
        
        prompt = PromptTemplate(
            input_variables=["question"],
            template="Please write a detailed, factual paragraph answering the following question to be used for search:\nQuestion: {question}\nAnswer:"
        )
        llm = get_llm()
        hyde_chain = LLMChain(llm=llm, prompt=prompt)
        
        class CustomHyDERetriever(BaseRetriever):
            base_retriever: BaseRetriever
            hyde_chain: LLMChain
            
            def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
                hypothetical_doc = self.hyde_chain.run(query)
                logger.info(f"HyDE generated doc: {hypothetical_doc[:100]}...")
                return self.base_retriever.invoke(hypothetical_doc)
                
        return CustomHyDERetriever(
            base_retriever=DenseStrategy().build(vector_store, session_id, k),
            hyde_chain=hyde_chain
        )
