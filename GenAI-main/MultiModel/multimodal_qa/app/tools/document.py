# pyrefly: ignore [missing-import]
from langchain.tools import StructuredTool
from app.tools.base import safe_call
from app.core.logger import get_logger

logger = get_logger(__name__)


from pydantic import BaseModel, Field

class SearchDocumentsInput(BaseModel):
    query: str = Field(description="The question or query to search for in the documents.")

def get_search_tool(document_retriever) -> StructuredTool:
    @safe_call
    def search_documents(query: str) -> str:
        """
        Searches the uploaded PDF documents using semantic similarity search.
        Use this tool when the user asks questions about content from uploaded 
        PDF files, manuals, reports, or any local document.
    
        Args:
            query: The question or query to search for in the documents.
    
        Returns:
            Relevant document excerpts with source citations.
        """
        logger.info(f"[DocSearch] Query: {query}")
        result = document_retriever.search(query)
        logger.info("[DocSearch] Retrieval complete.")
        return result

    async def asearch_documents(query: str) -> str:
        """
        Async version of search_documents.

        CRITICAL: In async streaming mode (agent.astream / graph.astream_events),
        LangGraph dispatches sync tools via loop.run_in_executor() which does NOT
        propagate ContextVar values (session_id_var, image_path_var) to the thread.
        This caused session_id_var.get() to return "default" inside the tool thread,
        making the retriever filter on {"session_id": "default"} and return zero docs.

        Fix: asyncio.to_thread() copies the ENTIRE current contextvars.Context to the
        worker thread (Python 3.9+ documented behaviour), so session_id_var.get() inside
        document_retriever.search() returns the correct per-request session ID.
        """
        import asyncio
        logger.info(f"[DocSearch Async] Query: {query}")
        result = await asyncio.to_thread(document_retriever.search, query)
        logger.info("[DocSearch Async] Retrieval complete.")
        return result

    return StructuredTool.from_function(
        func=search_documents,
        coroutine=asearch_documents,   # ← used by LangGraph in async (streaming) mode
        name="search_documents",
        description="Searches the uploaded PDF documents using semantic similarity search. Use this tool when the user asks questions about content from uploaded PDF files, manuals, reports, or any local document.",
        args_schema=SearchDocumentsInput
    )
