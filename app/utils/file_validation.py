from typing import List, Tuple
from fastapi import UploadFile, HTTPException, status
import magic
import os

from app.core.logging import logger


# Supported file types
SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/jpg', 
    'image/png',
    'image/tiff',
    'image/bmp',
    'image/webp'
}

SUPPORTED_EXTENSIONS = {
    '.pdf',
    '.jpg',
    '.jpeg',
    '.png',
    '.tiff',
    '.tif',
    '.bmp',
    '.webp'
}

# File size limits (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB for all files combined


def validate_file_type(file: UploadFile) -> bool:
    """
    Validate if the uploaded file is a supported type.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        True if file type is supported, False otherwise
    """
    try:
        # Check file extension
        file_extension = os.path.splitext(file.filename.lower())[1] if file.filename else ""
        if file_extension not in SUPPORTED_EXTENSIONS:
            return False
            
        # Check MIME type from content type
        if file.content_type and file.content_type.lower() not in SUPPORTED_MIME_TYPES:
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error validating file type for {file.filename}: {str(e)}")
        return False


def validate_file_size(file: UploadFile) -> bool:
    """
    Validate if the uploaded file size is within limits.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        True if file size is within limits, False otherwise
    """
    try:
        # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        return file_size <= MAX_FILE_SIZE
        
    except Exception as e:
        logger.error(f"Error validating file size for {file.filename}: {str(e)}")
        return False


def validate_total_size(files: List[UploadFile]) -> bool:
    """
    Validate if the total size of all uploaded files is within limits.
    
    Args:
        files: List of FastAPI UploadFile objects
        
    Returns:
        True if total size is within limits, False otherwise
    """
    try:
        total_size = 0
        for file in files:
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning
            total_size += file_size
            
        return total_size <= MAX_TOTAL_SIZE
        
    except Exception as e:
        logger.error(f"Error validating total file size: {str(e)}")
        return False


def validate_uploaded_files(files: List[UploadFile]) -> None:
    """
    Comprehensive validation of uploaded files.
    
    Args:
        files: List of FastAPI UploadFile objects
        
    Raises:
        HTTPException: If validation fails
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 20:  # Limit number of files
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many files. Maximum 20 files allowed"
        )
    
    # Validate total size first
    if not validate_total_size(files):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Total file size exceeds limit of {MAX_TOTAL_SIZE // (1024*1024)}MB"
        )
    
    # Validate each file
    for i, file in enumerate(files):
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {i+1} has no filename"
            )
        
        if not validate_file_type(file):
            supported_types = ", ".join(SUPPORTED_EXTENSIONS)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' has unsupported type. Supported types: {supported_types}"
            )
        
        if not validate_file_size(file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' exceeds size limit of {MAX_FILE_SIZE // (1024*1024)}MB"
            )
    
    logger.info(f"Successfully validated {len(files)} uploaded files")


def get_file_content_type(file: UploadFile) -> str:
    """
    Get the content type of the uploaded file.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Content type string
    """
    if file.content_type:
        return file.content_type
    
    # Fallback based on file extension
    if file.filename:
        ext = os.path.splitext(file.filename.lower())[1]
        if ext == '.pdf':
            return 'application/pdf'
        elif ext in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        elif ext == '.png':
            return 'image/png'
        elif ext in ['.tiff', '.tif']:
            return 'image/tiff'
        elif ext == '.bmp':
            return 'image/bmp'
        elif ext == '.webp':
            return 'image/webp'
    
    return 'application/octet-stream'


async def read_file_bytes(file: UploadFile) -> bytes:
    """
    Read file content as bytes and reset file pointer.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        File content as bytes
    """
    content = await file.read()
    file.file.seek(0)  # Reset file pointer for potential re-reading
    return content
