from typing import Optional
from core.logger import get_logger


logger = get_logger(__name__)


class DocumentRetriever:
    """Handles semantic search over indexed documents."""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query: str, k: int = 5) -> str:
        """
        Performs semantic search in the vector store.

        Args:
            query: The user's question.
            k: Number of top chunks to retrieve.

        Returns:
            A formatted string with retrieved context and source citations,
            or an error message if no documents are indexed.
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

            results = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "Unknown")
                # Extract markdown headers if they exist
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


