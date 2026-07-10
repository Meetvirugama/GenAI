# pyrefly: ignore [missing-import]
from langchain.tools import tool
# pyrefly: ignore [missing-import]
from langchain.tools import StructuredTool
from tools.base import safe_call
from core.logger import get_logger

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
        
    return StructuredTool.from_function(
        func=search_documents,
        name="search_documents",
        description="Searches the uploaded PDF documents using semantic similarity search. Use this tool when the user asks questions about content from uploaded PDF files, manuals, reports, or any local document.",
        args_schema=SearchDocumentsInput
    )
