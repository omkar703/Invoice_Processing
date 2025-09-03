import io
import base64
from typing import List
from PIL import Image
import fitz  # PyMuPDF

from app.core.config import settings
from app.core.logging import logger


def encode_image_pil(image: Image.Image) -> str:
    """
    Convert PIL Image to base64 string for API transmission.
    
    Args:
        image: PIL Image object
        
    Returns:
        Base64 encoded string
    """
    buffered = io.BytesIO()
    image = image.convert("RGB")
    image.save(
        buffered, 
        format=settings.image_format, 
        quality=settings.image_quality
    )
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def pdf_to_images(file_bytes: bytes) -> List[Image.Image]:
    """
    Convert PDF file bytes to list of PIL Image objects.
    
    Args:
        file_bytes: Raw bytes of PDF file
        
    Returns:
        List of PIL Image objects, one per page
        
    Raises:
        ValueError: If PDF processing fails
    """
    images = []
    try:
        logger.info("Converting PDF to images")
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            # Use configured zoom factor for better quality
            mat = fitz.Matrix(settings.pdf_zoom_factor, settings.pdf_zoom_factor)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
            logger.debug(f"Converted PDF page {page_num + 1} to image")
            
        pdf_document.close()
        logger.info(f"Successfully converted PDF to {len(images)} images")
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise ValueError(f"Error processing PDF: {str(e)}")
    
    return images


def bytes_to_image(file_bytes: bytes) -> Image.Image:
    """
    Convert raw bytes to PIL Image.
    
    Args:
        file_bytes: Raw image bytes
        
    Returns:
        PIL Image object
        
    Raises:
        ValueError: If image processing fails
    """
    try:
        image = Image.open(io.BytesIO(file_bytes))
        logger.debug(f"Successfully loaded image: {image.size} pixels, mode: {image.mode}")
        return image
    except Exception as e:
        logger.error(f"Error opening image: {str(e)}")
        raise ValueError(f"Error opening image: {str(e)}")


def is_pdf_file(content_type: str) -> bool:
    """
    Check if content type indicates a PDF file.
    
    Args:
        content_type: MIME content type
        
    Returns:
        True if PDF, False otherwise
    """
    return 'pdf' in content_type.lower()


def is_image_file(content_type: str) -> bool:
    """
    Check if content type indicates an image file.
    
    Args:
        content_type: MIME content type
        
    Returns:
        True if image, False otherwise
    """
    image_types = ['image/', 'jpeg', 'jpg', 'png', 'gif', 'bmp', 'tiff', 'webp']
    return any(img_type in content_type.lower() for img_type in image_types)


def validate_image_format(image: Image.Image) -> Image.Image:
    """
    Validate and normalize image format.
    
    Args:
        image: PIL Image object
        
    Returns:
        Normalized PIL Image object (RGB mode)
    """
    if image.mode != 'RGB':
        logger.debug(f"Converting image from {image.mode} to RGB")
        image = image.convert('RGB')
    
    return image
