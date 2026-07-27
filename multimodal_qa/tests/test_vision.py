from unittest.mock import patch

import pytest
from app.services.tools.vision import describe_image


@patch("app.services.vision.gemini_vision.gemini_vision")
@patch("app.core.context.image_path_var")
def test_describe_image_sync_no_image(mock_image_path, mock_vision):
    # Setup context to return None
    mock_image_path.get.return_value = None
    
    result = describe_image.run("What is in this image?")
    assert "No image has been uploaded" in result
    mock_vision.describe_image.assert_not_called()

@patch("app.services.vision.gemini_vision.gemini_vision")
@patch("app.core.context.image_path_var")
def test_describe_image_sync_success(mock_image_path, mock_vision):
    mock_image_path.get.return_value = "/tmp/test.jpg"
    mock_vision.describe_image.return_value = "A beautiful sunset."
    
    result = describe_image.run("Describe the image.")
    assert result == "A beautiful sunset."
    mock_vision.describe_image.assert_called_once_with("/tmp/test.jpg", prompt="Describe the image.")

@pytest.mark.asyncio
@patch("app.services.vision.gemini_vision.gemini_vision")
@patch("app.core.context.image_path_var")
async def test_describe_image_async_success(mock_image_path, mock_vision):
    mock_image_path.get.return_value = "/tmp/test.jpg"
    import asyncio
    future = asyncio.Future()
    future.set_result("A beautiful sunrise.")
    mock_vision.adescribe_image.return_value = future
    
    result = await describe_image.arun("Describe the image.")
    assert result == "A beautiful sunrise."
    mock_vision.adescribe_image.assert_called_once_with("/tmp/test.jpg", prompt="Describe the image.")
