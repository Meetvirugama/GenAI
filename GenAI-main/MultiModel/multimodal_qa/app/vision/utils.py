import base64
from io import BytesIO
import PIL.Image

def prepare_image_for_api(image_path: str, max_size: tuple = (1024, 1024)) -> PIL.Image.Image:
    """
    Opens an image, handles transparency flattening if needed, and resizes it.
    
    Args:
        image_path: Path to the image file.
        max_size: Maximum width and height for downscaling.
        
    Returns:
        A PIL.Image object in RGB mode ready for API consumption.
    """
    img = PIL.Image.open(image_path)
    
    # Handle transparency
    if img.mode not in ('RGB', 'L'):
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            alpha = img.convert('RGBA').split()[-1]
            bg = PIL.Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=alpha)
            img = bg
        else:
            img = img.convert('RGB')
            
    # Downscale while maintaining aspect ratio
    img.thumbnail(max_size)
    return img

def encode_image_to_base64(img: PIL.Image.Image) -> str:
    """
    Encodes a PIL Image to a base64 JPEG string.
    """
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
