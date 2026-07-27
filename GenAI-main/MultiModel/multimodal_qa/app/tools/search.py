from langchain.tools import tool
from app.tools.base import safe_call
from app.core.logger import get_logger
import hashlib
from functools import lru_cache

logger = get_logger(__name__)


def _build_search_engine():
    """
    Try to build DuckDuckGoSearchRun using the best available backend.
    langchain-community >= 0.3 requires 'ddgs' package.
    Older versions (5.x) expose duckduckgo_search.DDGS directly.
    """
    # Try modern ddgs-backed langchain integration first
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        engine = DuckDuckGoSearchRun()
        logger.info("[WebSearch] Using LangChain DuckDuckGoSearchRun.")
        return engine
    except (ImportError, Exception) as e:
        logger.warning(f"[WebSearch] LangChain DuckDuckGoSearchRun failed: {e}. Falling back to direct DDGS.")

    # Fallback: use duckduckgo_search library directly
    try:
        from duckduckgo_search import DDGS

        class _DirectDDGS:
            """Thin wrapper around DDGS to mimic LangChain tool interface."""
            def run(self, query: str) -> str:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=5))
                if not results:
                    return "No results found."
                return "\n\n".join(
                    f"**{r.get('title', '')}**\n{r.get('body', '')}\nURL: {r.get('href', '')}"
                    for r in results
                )

        logger.info("[WebSearch] Using direct DDGS fallback.")
        return _DirectDDGS()
    except ImportError:
        logger.error("[WebSearch] No DuckDuckGo search backend available. Web search will be disabled.")
        return None


_search_engine = _build_search_engine()


# ── #4 Tool Call Caching ──────────────────────────────────────────────────────
@lru_cache(maxsize=256)
def _cached_search(query_hash: str, query: str) -> str:
    """Internal cached search — keyed by MD5 hash of query."""
    if _search_engine is None:
        return "⚠️ Web search is currently unavailable. Please install 'duckduckgo-search'."
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
