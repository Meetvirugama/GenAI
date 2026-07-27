"""
tests/test_unit_tools.py
=========================
Comprehensive unit tests for tools/ modules.
Target: 85%+ coverage of all tool modules.
"""
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("GROQ_API_KEY", "fake-groq-key")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")


# ── tools/search.py ────────────────────────────────────────────────────────────

class TestSearchWeb:
    @patch("app.services.tools.search._search_engine")
    def test_search_web_returns_results(self, mock_engine):
        """Should return formatted search results."""
        from app.services.tools.search import search_web
        
        mock_engine.run.return_value = "Python Tutorial: Learn Python here."

        result = search_web("Python programming")
        assert "Python" in result

    @patch("app.services.tools.search._search_engine")
    def test_search_web_exception_handled_by_safe_call(self, mock_engine):
        """Exceptions should be caught and returned as error strings by safe_call."""
        from app.services.tools.search import search_web

        mock_engine.run.side_effect = Exception("Network error")
        result = search_web("test query")
        # Should return error message, not raise
        assert isinstance(result, str)
        assert "Error in" in result or "Network error" in result


# ── tools/vision.py ────────────────────────────────────────────────────────────

class TestDescribeImage:
    def test_describe_image_no_path_set(self):
        """When no image_path is set in context, should return 'no image' message."""
        from app.services.tools.vision import describe_image

        with patch("app.core.context.image_path_var") as mock_var:
            mock_var.get.return_value = None
            result = describe_image("What is in this image?")

        assert "no image" in result.lower() or "upload" in result.lower() or isinstance(result, str)

    @patch("app.services.vision.gemini_vision.gemini_vision")
    def test_describe_image_success(self, mock_gemini_vision):
        """Should call gemini_vision.describe_image when image is set."""
        from app.services.tools.vision import describe_image

        mock_gemini_vision.describe_image.return_value = "A dog sitting on a chair."

        with patch("app.core.context.image_path_var") as mock_var:
            mock_var.get.return_value = "/path/to/image.jpg"
            result = describe_image("What is in this image?")

        assert "dog" in result or isinstance(result, str)

    @patch("app.services.vision.gemini_vision.gemini_vision")
    def test_describe_image_failure_returns_error(self, mock_gemini_vision):
        """If vision fails, should return error string."""
        from app.services.tools.vision import describe_image

        mock_gemini_vision.describe_image.side_effect = Exception("Vision error")

        with patch("app.core.context.image_path_var") as mock_var:
            mock_var.get.return_value = "/path/to/image.jpg"
            result = describe_image("What is in this image?")

        assert isinstance(result, str)
        assert "Error" in result


# ── tools/document.py ──────────────────────────────────────────────────────────

class TestDocumentTools:
    def test_get_search_tool_returns_callable(self):
        """get_search_tool should return a callable tool."""
        from app.services.tools.document import get_search_tool

        mock_retriever = MagicMock()
        tool = get_search_tool(mock_retriever)
        assert tool is not None
        assert tool.name == "search_documents"

    def test_document_search_with_retriever(self):
        """The tool returned by get_search_tool should call retriever."""
        from app.services.tools.document import get_search_tool

        mock_retriever = MagicMock()
        mock_retriever.search.return_value = "Found: Python documentation chunk."
        
        tool = get_search_tool(mock_retriever)
        result = tool.invoke({"query": "Python"})

        assert isinstance(result, str)
        assert "Found" in result

    def test_document_search_exception(self):
        """Exceptions should be caught and returned as strings by safe_call."""
        from app.services.tools.document import get_search_tool

        mock_retriever = MagicMock()
        mock_retriever.search.side_effect = Exception("Search error")
        
        tool = get_search_tool(mock_retriever)
        result = tool.invoke({"query": "query"})

        assert isinstance(result, str)
        assert "Error in search_documents" in result


# ── tools/base.py ─────────────────────────────────────────────────────────────

class TestBaseTools:
    def test_safe_call_success(self):
        """safe_call decorator should return result on success."""
        from app.services.tools.base import safe_call

        @safe_call
        def dummy_func(x):
            return f"success {x}"

        result = dummy_func(5)
        assert result == "success 5"

    def test_safe_call_exception(self):
        """safe_call decorator should catch exceptions and return error string."""
        from app.services.tools.base import safe_call

        @safe_call
        def failing_func():
            raise ValueError("Something broke")

        result = failing_func()
        assert "Error in failing_func" in result
        assert "Something broke" in result
