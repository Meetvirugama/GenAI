import base64
from pathlib import Path
from groq import Groq
from app.core.config import Config
from app.core.logger import get_logger

logger = get_logger(__name__)


from io import BytesIO

def _encode_image(image_path: str) -> str:
    """Encodes a local image file to a base64 string, downscaling if necessary."""
    try:
        from app.vision.utils import prepare_image_for_api, encode_image_to_base64
        img = prepare_image_for_api(image_path)
        return encode_image_to_base64(img)
    except ImportError:
        logger.warning("Pillow not installed, falling back to raw base64 encoding")
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


class GroqVision:
    """Handles image analysis using the Groq Vision API."""

    def __init__(self):
        if not Config.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. Please configure it in your .env file."
            )
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = Config.VISION_MODEL

    def describe_image(self, image_path: str, prompt: str = "Describe this image in detail.") -> str:
        """
        Sends an image to Groq Vision and returns a description.

        Args:
            image_path: Absolute path to the image file.
            prompt: The question or instruction for the vision model.

        Returns:
            A string description of the image.
        """
        logger.info(f"Analyzing image: {image_path} | Prompt: {prompt}")
        try:
            ext = Path(image_path).suffix.lower()
            mime_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_type_map.get(ext, "image/jpeg")
            image_data = _encode_image(image_path)

            import random
            client = Groq(api_key=random.choice(Config.GROQ_API_KEYS))
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                max_tokens=1024
            )
            result = response.choices[0].message.content
            logger.info("Image analysis complete.")
            return result
        except Exception as e:
            logger.error(f"Groq Vision API error: {e}")
            raise

# Lazy singleton — only instantiated when first accessed
_groq_vision_instance = None

def _get_groq_vision():
    global _groq_vision_instance
    if _groq_vision_instance is None:
        _groq_vision_instance = GroqVision()
    return _groq_vision_instance

class _LazyGroqVision:
    """Lazy proxy for GroqVision singleton."""
    def __getattr__(self, name):
        return getattr(_get_groq_vision(), name)

groq_vision = _LazyGroqVision()
