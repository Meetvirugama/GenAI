"""
rag/retriever.py
================
Document retrieval with:
  #3 Cross-Encoder Re-Ranker  — re-ranks BM25+semantic results by true relevance
"""
from typing import Optional
from core.logger import get_logger

logger = get_logger(__name__)

# ── #3 Cross-Encoder Re-Ranker (lazy-loaded) ──────────────────────────────────
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Cross-encoder re-ranker loaded.")
        except Exception as e:
            logger.warning(f"Cross-encoder unavailable, skipping re-rank: {e}")
            _reranker = False  # sentinel — don't retry
    return _reranker if _reranker else None


def _rerank_docs(query: str, docs: list, top_k: int = 5) -> list:
    """Re-ranks docs using cross-encoder and returns top_k."""
    reranker = _get_reranker()
    if not reranker or len(docs) <= 1:
        return docs[:top_k]
    try:
        pairs = [(query, doc.page_content) for doc in docs]
        scores = reranker.predict(pairs)
        ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        logger.info(f"Re-ranked {len(docs)} docs → top {top_k}")
        return [doc for _, doc in ranked[:top_k]]
    except Exception as e:
        logger.warning(f"Re-ranking failed: {e}")
        return docs[:top_k]


class DocumentRetriever:
    """Handles semantic search over indexed documents with cross-encoder re-ranking."""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query: str, k: int = 8) -> str:
        """
        Performs hybrid (BM25 + semantic) search, then re-ranks with cross-encoder.

        Args:
            query: The user's question.
            k: Number of chunks to retrieve before re-ranking (retrieve more, keep best).

        Returns:
            A formatted XML string with retrieved context and source citations.
        """
        from core.context import session_id_var
        session_id = session_id_var.get()

        retriever = self.vector_store.get_retriever(session_id=session_id, k=k)
        if retriever is None:
            return "No documents are indexed yet. Please upload a PDF first."

        try:
            docs = retriever.invoke(query)
            if not docs:
                return "No relevant content found in the uploaded documents."

            # #3 Cross-encoder re-ranking: retrieve 8, keep best 5
            docs = _rerank_docs(query, docs, top_k=5)

            results = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "Unknown")
                headers = []
                for h in ["Header 1", "Header 2", "Header 3"]:
                    if h in doc.metadata:
                        headers.append(doc.metadata[h])
                hierarchy = " > ".join(headers) if headers else "Root"

                ai_summary = doc.metadata.get("summary", "N/A")
                ai_keywords = doc.metadata.get("keywords", "N/A")
                safe_content = doc.page_content.replace("<", "&lt;").replace(">", "&gt;")

                xml_block = f'''<document index="{i+1}">
  <source>{source}</source>
  <hierarchy>{hierarchy}</hierarchy>
  <ai_summary>{ai_summary}</ai_summary>
  <ai_keywords>{ai_keywords}</ai_keywords>
  <content>
{safe_content}
  </content>
</document>'''
                results.append(xml_block)

            joined_results = "\n\n".join(results)
            return f"<context>\n{joined_results}\n</context>"
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return f"Error searching documents: {e}"
