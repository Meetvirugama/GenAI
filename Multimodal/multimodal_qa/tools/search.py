# pyrefly: ignore [missing-import]
from langchain.tools import tool
# pyrefly: ignore [missing-import]
from langchain_community.tools import DuckDuckGoSearchRun
from tools.base import safe_call
from core.logger import get_logger

logger = get_logger(__name__)

_search_engine = DuckDuckGoSearchRun()


@tool
@safe_call
def search_web(query: str) -> str:
    """
    Searches the live web for current information using DuckDuckGo.
    Use this tool when the user asks about recent events, news, or 
    information that may not be in uploaded documents.

    Args:
        query: The search query string.

    Returns:
        Web search results as a string.
    """
    logger.info(f"[WebSearch] Query: {query}")
    result = _search_engine.run(query)
    logger.info("[WebSearch] Search complete.")
    return result
