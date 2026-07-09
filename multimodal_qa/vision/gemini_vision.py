import google.generativeai as genai
import PIL.Image
from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

class GeminiVision:
    """Handles image analysis using the Google Gemini Vision API."""

    def __init__(self):
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
            img = PIL.Image.open(image_path)
            # Ensure it's in a compatible mode
            if img.mode not in ('RGB', 'L'):
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    alpha = img.convert('RGBA').split()[-1]
                    bg = PIL.Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=alpha)
                    img = bg
                else:
                    img = img.convert('RGB')
            
            response = self.model.generate_content([prompt, img])
            result = response.text
            logger.info("Image analysis complete.")
            return result
        except Exception as e:
            logger.error(f"Gemini Vision API error: {e}")
            raise

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


# Singleton
gemini_vision = GeminiVision()
