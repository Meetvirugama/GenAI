# pyrefly: ignore [missing-import]
from langchain.tools import tool
# pyrefly: ignore [missing-import]
from langchain_community.tools import DuckDuckGoSearchRun
from tools.base import safe_call
from core.logger import get_logger
import hashlib
from functools import lru_cache

logger = get_logger(__name__)

_search_engine = DuckDuckGoSearchRun()


# ── #4 Tool Call Caching ──────────────────────────────────────────────────────
@lru_cache(maxsize=256)
def _cached_search(query_hash: str, query: str) -> str:
    """Internal cached search — keyed by MD5 hash of query."""
    logger.info(f"[WebSearch] Cache MISS → Running search: {query}")
    return _search_engine.run(query)


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
    q_hash = hashlib.md5(query.strip().lower().encode()).hexdigest()
    result = _cached_search(q_hash, query.strip())
    logger.info("[WebSearch] Search complete.")
    return result
