
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.logger import get_logger

logger = get_logger(__name__)

class DescribeImageInput(BaseModel):
    question: str = Field(description="The specific question or instruction about the image.")

class DescribeImageTool(BaseTool):
    name: str = "describe_image"
    description: str = (
        "Analyzes the currently uploaded image and answers questions about it "
        "using Groq Vision AI. Use this tool when the user asks about an image, "
        "asks what is shown in a picture, asks to describe visual content, or "
        "compares an image to document content."
    )
    args_schema: type[BaseModel] = DescribeImageInput

    def _run(self, question: str) -> str:
        from app.core.context import image_path_var
        current_image_path = image_path_var.get()
        if not current_image_path:
            return "No image has been uploaded. Please upload an image first."
        
        logger.info(f"[Vision] Analyzing image '{current_image_path}' with prompt: {question}")
        try:
            from app.services.vision.gemini_vision import gemini_vision
            return gemini_vision.describe_image(current_image_path, prompt=question)
        except Exception as e:
            logger.error(f"[Tool 'describe_image' failed] {e}")
            return f"⚠️ Error: {e}"

    async def _arun(self, question: str) -> str:
        from app.core.context import image_path_var
        current_image_path = image_path_var.get()
        if not current_image_path:
            return "No image has been uploaded. Please upload an image first."
        
        logger.info(f"[Vision Async] Analyzing image '{current_image_path}' with prompt: {question}")
        try:
            from app.services.vision.gemini_vision import gemini_vision
            return await gemini_vision.adescribe_image(current_image_path, prompt=question)
        except Exception as e:
            logger.error(f"[Tool 'describe_image' failed] {e}")
            return f"⚠️ Error: {e}"

describe_image = DescribeImageTool()
