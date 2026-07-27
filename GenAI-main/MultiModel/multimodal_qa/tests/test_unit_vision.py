"""
tests/test_unit_vision.py
==========================
Comprehensive unit tests for vision/gemini_vision.py.
Target: 80%+ coverage of both vision modules.
"""
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from io import BytesIO

os.environ.setdefault("GROQ_API_KEY", "fake-groq-key")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")


# ── GeminiVision ───────────────────────────────────────────────────────────────

class TestGeminiVision:
    """Tests for vision/gemini_vision.py"""

    @patch("app.vision.gemini_vision.genai")
    @patch("app.vision.utils.PIL.Image.open")
    def test_describe_image_rgb_success(self, mock_pil_open, mock_genai):
        """Standard RGB image should be described successfully."""
        from app.vision.gemini_vision import GeminiVision

        mock_img = MagicMock()
        mock_img.mode = "RGB"
        mock_pil_open.return_value.__enter__ = MagicMock(return_value=mock_img)
        mock_pil_open.return_value = mock_img

        mock_response = MagicMock()
        mock_response.text = "A beautiful landscape photo."
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()

        gv = GeminiVision()
        result = gv.describe_image("test.jpg", "Describe this image")
        assert result == "A beautiful landscape photo."

    @patch("app.vision.gemini_vision.genai")
    @patch("app.vision.utils.PIL.Image.open")
    def test_describe_image_rgba_converts_to_rgb(self, mock_pil_open, mock_genai):
        """RGBA images should be converted to RGB."""
        from app.vision.gemini_vision import GeminiVision

        mock_img = MagicMock()
        mock_img.mode = "RGBA"
        mock_img.info = {"transparency": True}
        mock_rgba = MagicMock()
        mock_rgba.split.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_img.convert.return_value = mock_rgba
        mock_pil_open.return_value = mock_img

        mock_bg = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Converted image description."
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        with patch("app.vision.utils.PIL.Image.new", return_value=mock_bg):
            gv = GeminiVision()
            result = gv.describe_image("test.png")
        assert result is not None

    @patch("app.vision.gemini_vision.genai")
    @patch("app.vision.utils.PIL.Image.open")
    def test_describe_image_l_mode_is_accepted(self, mock_pil_open, mock_genai):
        """L-mode (grayscale) images should be accepted without conversion."""
        from app.vision.gemini_vision import GeminiVision

        mock_img = MagicMock()
        mock_img.mode = "L"
        mock_img.info = {}
        mock_converted = MagicMock()
        mock_img.convert.return_value = mock_converted
        mock_pil_open.return_value = mock_img

        mock_response = MagicMock()
        mock_response.text = "Grayscale image."
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()

        gv = GeminiVision()
        result = gv.describe_image("grayscale.jpg")
        mock_img.convert.assert_not_called()

    @patch("app.vision.gemini_vision.genai")
    @patch("app.vision.utils.PIL.Image.open")
    def test_describe_image_exception_raises(self, mock_pil_open, mock_genai):
        """Exceptions from the API should be re-raised."""
        from app.vision.gemini_vision import GeminiVision

        mock_pil_open.side_effect = Exception("File not found")
        mock_genai.configure = MagicMock()
        mock_genai.GenerativeModel.return_value = MagicMock()

        gv = GeminiVision()
        with pytest.raises(Exception, match="File not found"):
            gv.describe_image("nonexistent.jpg")

    @patch("app.vision.gemini_vision.genai")
    @patch("app.vision.utils.PIL.Image.open")
    @pytest.mark.asyncio
    async def test_adescribe_image_async(self, mock_pil_open, mock_genai):
        """Async describe_image should return description."""
        from app.vision.gemini_vision import GeminiVision

        mock_img = MagicMock()
        mock_img.mode = "RGB"
        mock_pil_open.return_value = mock_img

        mock_response = MagicMock()
        mock_response.text = "Async image description."
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()

        gv = GeminiVision()
        result = await gv.adescribe_image("test.jpg")
        assert result == "Async image description."

    @patch("app.vision.gemini_vision.genai")
    def test_pdf_to_markdown_success(self, mock_genai):
        """pdf_to_markdown should upload, generate, and delete file."""
        from app.vision.gemini_vision import GeminiVision

        mock_uploaded = MagicMock()
        mock_uploaded.name = "file_123"
        mock_genai.upload_file.return_value = mock_uploaded

        mock_response = MagicMock()
        mock_response.text = "# Document Title\n\nConverted content."
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        mock_genai.delete_file = MagicMock()

        gv = GeminiVision()
        result = gv.pdf_to_markdown("document.pdf")
        assert "Document Title" in result
        mock_genai.delete_file.assert_called_once_with("file_123")

    @patch("app.vision.gemini_vision.genai")
    def test_pdf_to_markdown_exception_raises(self, mock_genai):
        """pdf_to_markdown exceptions should be re-raised."""
        from app.vision.gemini_vision import GeminiVision

        mock_genai.upload_file.side_effect = Exception("Upload failed")
        mock_genai.configure = MagicMock()
        mock_genai.GenerativeModel.return_value = MagicMock()

        gv = GeminiVision()
        with pytest.raises(Exception, match="Upload failed"):
            gv.pdf_to_markdown("document.pdf")


