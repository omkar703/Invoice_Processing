from typing import Dict, Any, List
import pandas as pd
from fastapi import APIRouter, HTTPException, status, UploadFile, File

from app.models.schemas import (
    OCRDataResponse, ErrorResponse,
    DocumentData, InvoiceDetails, LineItem, RawTextContent, DocumentMetadata
)
from app.services.ocr_service import ocr_service
from app.utils.image_processing import pdf_to_images, bytes_to_image, is_pdf_file
from app.utils.file_validation import validate_uploaded_files, get_file_content_type, read_file_bytes
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/extract-ocr-data",
    response_model=OCRDataResponse,
    responses={
        200: {
            "model": OCRDataResponse,
            "description": "Successfully extracted OCR data in JSON format"
        },
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Extract OCR data for RAG applications",
    description="Extract OCR data from uploaded invoice files (PDFs and images) and return structured JSON for RAG applications."
)
async def extract_ocr_data(files: List[UploadFile] = File(..., description="Upload PDF or image files to process")):
    """
    Extract OCR data from uploaded invoices and return structured JSON for RAG applications.
    
    This endpoint processes uploaded invoice files and returns the raw extracted data
    in JSON format without any standardization or CSV conversion. Perfect for
    building RAG (Retrieval-Augmented Generation) applications that need
    access to structured invoice data.
    
    Args:
        files: List of uploaded files (PDFs and images)
        
    Returns:
        OCRDataResponse with extracted data in JSON format
    """
    # Validate uploaded files
    validate_uploaded_files(files)
    
    try:
        all_extracted_data = []
        total_files_processed = 0
        total_pages_processed = 0
        processing_errors = []
        
        # Process each uploaded file
        for uploaded_file in files:
            filename = uploaded_file.filename or "unknown_file"
            logger.info(f"Extracting OCR data from file: {filename}")
            file_processed = False
            
            try:
                # Read file content
                file_bytes = await read_file_bytes(uploaded_file)
                content_type = get_file_content_type(uploaded_file)
                
                # Convert to images
                images_to_process = []
                if is_pdf_file(content_type):
                    try:
                        images_to_process = pdf_to_images(file_bytes)
                    except Exception as e:
                        processing_errors.append(f"Error processing PDF {filename}: {str(e)}")
                        logger.error(f"Error processing PDF {filename}: {str(e)}")
                        continue
                else:  # Assume image
                    try:
                        image = bytes_to_image(file_bytes)
                        images_to_process = [image]
                    except Exception as e:
                        processing_errors.append(f"Error opening image {filename}: {str(e)}")
                        logger.error(f"Error opening image {filename}: {str(e)}")
                        continue
                
                # Process each page/image
                for page_idx, image in enumerate(images_to_process):
                    try:
                        extracted_data = ocr_service.extract_structured_data(image)
                        
                        # Create comprehensive data structure for RAG
                        document_data = _create_document_data(
                            filename=filename,
                            page_idx=page_idx,
                            total_pages=len(images_to_process),
                            file_type=content_type,
                            extracted_data=extracted_data
                        )
                        
                        all_extracted_data.append(document_data)
                        total_pages_processed += 1
                        file_processed = True
                        
                        logger.info(f"Successfully extracted OCR data from {filename} page {page_idx + 1}")
                        
                    except Exception as e:
                        error_msg = f"Error extracting data from page {page_idx + 1} of {filename}: {str(e)}"
                        processing_errors.append(error_msg)
                        logger.error(error_msg)
                        
                        # Add error document for failed pages
                        error_document = _create_error_document(
                            filename=filename,
                            page_idx=page_idx,
                            total_pages=len(images_to_process),
                            file_type=content_type,
                            error=str(e)
                        )
                        all_extracted_data.append(error_document)
                        continue
                
                if file_processed:
                    total_files_processed += 1
                    
            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                processing_errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        # Prepare response
        success = len(all_extracted_data) > 0
        
        if success:
            if processing_errors:
                message = f"Successfully processed {total_files_processed} files and {total_pages_processed} pages with {len(processing_errors)} errors. Extracted data ready for RAG application."
            else:
                message = f"Successfully processed {total_files_processed} files and {total_pages_processed} pages. All OCR data extracted without errors."
        else:
            message = "Failed to extract data from any files. Check uploaded files and try again."
            if not processing_errors:
                processing_errors = ["No files were successfully processed"]
        
        # Build response data
        response_data = {
            "success": success,
            "message": message,
            "data": all_extracted_data,
            "total_files_processed": total_files_processed,
            "total_pages_processed": total_pages_processed
        }
        
        # Add processing errors as metadata if any occurred
        if processing_errors:
            response_data["processing_errors"] = processing_errors[:10]  # Limit to first 10 errors
            response_data["total_errors"] = len(processing_errors)
        
        logger.info(f"OCR extraction completed: {total_files_processed} files, {total_pages_processed} pages, {len(processing_errors)} errors")
        
        return OCRDataResponse(**response_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in extract_ocr_data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Unexpected server error: {str(e)}"
        )


def _create_document_data(filename: str, page_idx: int, total_pages: int, 
                         file_type: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create comprehensive document data structure for RAG applications.
    
    Args:
        filename: Original filename
        page_idx: Page index (0-based)
        total_pages: Total pages in document
        file_type: MIME type of file
        extracted_data: Raw extracted data from OCR
        
    Returns:
        Structured document data dictionary
    """
    invoice_details = extracted_data.get('invoice_details', {})
    line_items = extracted_data.get('line_items', [])
    
    return {
        "document_id": f"{filename}_page_{page_idx + 1}",
        "source_file": filename,
        "page_number": page_idx + 1,
        "total_pages": total_pages,
        "file_type": file_type,
        "extraction_timestamp": pd.Timestamp.now().isoformat(),
        "invoice_details": invoice_details,
        "line_items": line_items,
        "raw_text_content": {
            "invoice_summary": f"Invoice from {invoice_details.get('vendor_name', 'Unknown Vendor')} dated {invoice_details.get('invoice_date', 'Unknown Date')} with total amount {invoice_details.get('total_amount', 0)}",
            "line_items_summary": f"Contains {len(line_items)} line items"
        },
        "metadata": {
            "has_line_items": len(line_items) > 0,
            "line_items_count": len(line_items),
            "has_invoice_details": bool(invoice_details),
            "extracted_fields": list(invoice_details.keys()),
            "processing_status": "success"
        }
    }


def _create_error_document(filename: str, page_idx: int, total_pages: int, 
                          file_type: str, error: str) -> Dict[str, Any]:
    """
    Create error document structure for failed extractions.
    
    Args:
        filename: Original filename
        page_idx: Page index (0-based)
        total_pages: Total pages in document
        file_type: MIME type of file
        error: Error message
        
    Returns:
        Error document data dictionary
    """
    return {
        "document_id": f"{filename}_page_{page_idx + 1}_error",
        "source_file": filename,
        "page_number": page_idx + 1,
        "total_pages": total_pages,
        "file_type": file_type,
        "extraction_timestamp": pd.Timestamp.now().isoformat(),
        "invoice_details": {},
        "line_items": [],
        "raw_text_content": {
            "invoice_summary": "Failed to extract data",
            "line_items_summary": "No line items extracted due to error"
        },
        "metadata": {
            "has_line_items": False,
            "line_items_count": 0,
            "has_invoice_details": False,
            "extracted_fields": [],
            "processing_status": "error",
            "error_message": error
        }
    }
