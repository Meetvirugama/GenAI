import functools
from typing import Callable, Any
from core.logger import get_logger

logger = get_logger(__name__)


def safe_call(func: Callable) -> Callable:
    """
    Decorator that wraps a tool function in a try/except block.
    Any unhandled exception returns a clean error message instead of crashing.

    Usage:
        @safe_call
        def my_tool(input: str) -> str:
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            tool_name = func.__name__
            error_msg = f"[Tool '{tool_name}' failed] {type(e).__name__}: {e}"
            logger.error(error_msg)
            return f"⚠️ Error in {tool_name}: {str(e)}"
    return wrapper
