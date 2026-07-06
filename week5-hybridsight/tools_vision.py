from langchain_core.tools import tool
from groq import Groq
import os

@tool
def describe_image(image_data: str) -> str:
    """Describe the content of an image. Use when the user uploads an
    image or asks what's in a picture. Input must be a base64 data URI
    (e.g. 'data:image/jpeg;base64,...')."""
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            }],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Could not process the image: {e}"
