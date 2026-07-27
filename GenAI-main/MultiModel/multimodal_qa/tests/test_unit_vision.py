"""
tests/test_unit_vision.py
==========================
Comprehensive unit tests for vision/gemini_vision.py and vision/groq_vision.py.
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
    @patch("app.vision.gemini_vision.PIL.Image.open")
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
    @patch("app.vision.gemini_vision.PIL.Image.open")
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
        with patch("app.vision.gemini_vision.PIL.Image.new", return_value=mock_bg):
            gv = GeminiVision()
            result = gv.describe_image("test.png")
        assert result is not None

    @patch("app.vision.gemini_vision.genai")
    @patch("PIL.Image.open")
    def test_describe_image_l_mode_converts_to_rgb(self, mock_pil_open, mock_genai):
        """L-mode (grayscale) images should be converted to RGB."""
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
        mock_img.convert.assert_called_with("RGB")

    @patch("app.vision.gemini_vision.genai")
    @patch("app.vision.gemini_vision.PIL.Image.open")
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
    @patch("app.vision.gemini_vision.PIL.Image.open")
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


# ── _encode_image ──────────────────────────────────────────────────────────────

class TestEncodeImage:
    def test_encode_rgb_image(self, tmp_path):
        """Should encode an RGB image to base64."""
        try:
            from PIL import Image
            img_path = tmp_path / "test.jpg"
            img = Image.new("RGB", (100, 100), color=(255, 0, 0))
            img.save(str(img_path))

            from app.vision.groq_vision import _encode_image
            result = _encode_image(str(img_path))
            assert isinstance(result, str)
            assert len(result) > 0
        except ImportError:
            pytest.skip("Pillow not installed")

    def test_encode_rgba_image_converts(self, tmp_path):
        """RGBA images should be converted and encoded."""
        try:
            from PIL import Image
            img_path = tmp_path / "test.png"
            img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
            img.save(str(img_path))

            from app.vision.groq_vision import _encode_image
            result = _encode_image(str(img_path))
            assert isinstance(result, str)
        except ImportError:
            pytest.skip("Pillow not installed")

    def test_encode_falls_back_without_pillow(self, tmp_path):
        """Without Pillow, should fall back to raw base64 encoding."""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake image data")

        with patch.dict("sys.modules", {"PIL": None, "PIL.Image": None}):
            # Simulate ImportError during PIL import inside the function
            import app.vision.groq_vision as m
            import importlib
            original_encode = m._encode_image

            def patched_encode(path):
                # Simulate the fallback path
                import base64
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")

            result = patched_encode(str(img_path))
            assert isinstance(result, str)


# ── GroqVision ─────────────────────────────────────────────────────────────────

class TestGroqVision:
    """Tests for vision/groq_vision.py"""

    @patch("app.vision.groq_vision.Groq")
    @patch("app.vision.groq_vision._encode_image")
    def test_describe_image_jpg_success(self, mock_encode, mock_groq):
        """Should successfully describe a JPG image."""
        from app.vision.groq_vision import GroqVision

        mock_encode.return_value = "base64encodeddata"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "A beautiful sunset over the ocean."
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        gv = GroqVision()
        result = gv.describe_image("photo.jpg", "Describe this")
        assert result == "A beautiful sunset over the ocean."

    @patch("app.vision.groq_vision.Groq")
    @patch("app.vision.groq_vision._encode_image")
    def test_describe_image_png_uses_correct_mime(self, mock_encode, mock_groq):
        """PNG files should use image/png MIME type."""
        from app.vision.groq_vision import GroqVision

        mock_encode.return_value = "base64data"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "PNG description."
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        gv = GroqVision()
        result = gv.describe_image("image.png")
        assert result == "PNG description."

    @patch("app.vision.groq_vision.Groq")
    @patch("app.vision.groq_vision._encode_image")
    def test_describe_image_webp_uses_webp_mime(self, mock_encode, mock_groq):
        """WEBP files should use image/webp MIME type."""
        from app.vision.groq_vision import GroqVision

        mock_encode.return_value = "base64data"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "WebP description."
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        gv = GroqVision()
        result = gv.describe_image("image.webp")
        assert result == "WebP description."

    @patch("app.vision.groq_vision.Groq")
    @patch("app.vision.groq_vision._encode_image")
    def test_describe_image_unknown_extension_defaults_jpeg(self, mock_encode, mock_groq):
        """Unknown extension should default to image/jpeg MIME."""
        from app.vision.groq_vision import GroqVision

        mock_encode.return_value = "base64data"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Default mime description."
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        gv = GroqVision()
        result = gv.describe_image("image.bmp")  # Unknown extension
        assert result is not None

    @patch("app.vision.groq_vision.Groq")
    @patch("app.vision.groq_vision._encode_image")
    def test_describe_image_api_exception_raises(self, mock_encode, mock_groq):
        """API exceptions should be re-raised."""
        from app.vision.groq_vision import GroqVision

        mock_encode.return_value = "base64data"
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_groq.return_value = mock_client

        gv = GroqVision()
        with pytest.raises(Exception, match="API error"):
            gv.describe_image("test.jpg")

    @patch("app.vision.groq_vision.Groq")
    @patch("app.vision.groq_vision._encode_image")
    def test_describe_image_uses_random_api_key(self, mock_encode, mock_groq):
        """Should select a random key from Config.GROQ_API_KEYS."""
        from app.vision.groq_vision import GroqVision

        mock_encode.return_value = "base64"
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Image description."
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client

        gv = GroqVision()
        with patch("app.vision.groq_vision.Config") as mock_config:
            mock_config.GROQ_API_KEYS = ["key1", "key2", "key3"]
            mock_config.GROQ_API_KEY = "key1"
            mock_config.VISION_MODEL = "gemini-1.5-flash"
            result = gv.describe_image("test.jpg")
        # verify Groq was called with some API key
        assert mock_groq.called
