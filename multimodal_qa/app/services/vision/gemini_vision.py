import asyncio

import google.generativeai as genai

from app.core.config import Config
from app.core.logger import get_logger

logger = get_logger(__name__)

class GeminiVision:
    """Handles image analysis using the Google Gemini Vision API."""

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please configure it in your .env file to use vision features."
            )
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(Config.VISION_MODEL or 'gemini-1.5-flash')

    def describe_image(self, image_path: str, prompt: str = "Describe this image in detail.") -> str:
        """
        Sends an image to Gemini Vision and returns a description.

        Args:
            image_path: Absolute path to the image file.
            prompt: The question or instruction for the vision model.

        Returns:
            A string description of the image.
        """
        logger.info(f"Analyzing image with Gemini: {image_path} | Prompt: {prompt}")
        try:
            from app.services.vision.utils import prepare_image_for_api
            img = prepare_image_for_api(image_path)
            
            response = self.model.generate_content([prompt, img])
            result = response.text
            logger.info("Image analysis complete.")
            return result
        except Exception as e:
            logger.error(f"Gemini Vision API error: {e}")
            raise

    async def adescribe_image(self, image_path: str, prompt: str = "Describe this image in detail.") -> str:
        """Asynchronous version of describe_image using asyncio.to_thread to offload blocking I/O."""
        return await asyncio.to_thread(self.describe_image, image_path, prompt)

    def pdf_to_markdown(self, pdf_path: str) -> str:
        """
        Uses Gemini's native document understanding to convert a PDF into perfectly structured Markdown.
        """
        logger.info(f"Uploading PDF to Gemini for Markdown conversion: {pdf_path}")
        try:
            # Upload the file to Gemini using the File API
            uploaded_file = genai.upload_file(pdf_path, mime_type="application/pdf")
            
            prompt = (
                "Convert this PDF document into perfectly structured Markdown. "
                "Preserve all hierarchical headings (#, ##, ###). "
                "Convert all tabular data into proper Markdown tables. "
                "If there are JSON schemas, code blocks, or specific technical requirements, wrap them in appropriate code blocks (e.g. ```json). "
                "Do not add any conversational filler, return ONLY the raw markdown content."
            )
            
            response = self.model.generate_content([prompt, uploaded_file])
            result = response.text
            
            # Clean up the file from Google's servers
            genai.delete_file(uploaded_file.name)
            
            return result
        except Exception as e:
            logger.error(f"Gemini PDF to Markdown error: {e}")
            raise

# Lazy singleton — only instantiated when first accessed
_gemini_vision_instance = None

def _get_gemini_vision():
    global _gemini_vision_instance
    if _gemini_vision_instance is None:
        _gemini_vision_instance = GeminiVision()
    return _gemini_vision_instance

# Keep backward-compat attribute
class _LazyGeminiVision:
    """Lazy proxy for GeminiVision singleton."""
    def __getattr__(self, name):
        return getattr(_get_gemini_vision(), name)

gemini_vision = _LazyGeminiVision()
