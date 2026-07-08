# pyrefly: ignore [missing-import]
from langchain.tools import tool
from tools.base import safe_call
from core.logger import get_logger
from core.config import Config

logger = get_logger(__name__)



from pydantic import BaseModel, Field

class DescribeImageInput(BaseModel):
    question: str = Field(description="The specific question or instruction about the image.")

@tool("describe_image", args_schema=DescribeImageInput)
@safe_call
def describe_image(question: str) -> str:
    """
    Analyzes the currently uploaded image and answers questions about it
    using Groq Vision AI. Use this tool when the user asks about an image,
    asks what is shown in a picture, asks to describe visual content, or
    compares an image to document content.

    Args:
        question: The specific question or instruction about the image.

    Returns:
        A detailed description or answer about the image content.
    """
    from core.context import image_path_var
    current_image_path = image_path_var.get()
    
    if not current_image_path:
        return "No image has been uploaded. Please upload an image first."

    logger.info(f"[Vision] Analyzing image '{current_image_path}' with prompt: {question}")
    # pyrefly: ignore [missing-import]
    from vision.gemini_vision import gemini_vision
    result = gemini_vision.describe_image(current_image_path, prompt=question)
    return result
