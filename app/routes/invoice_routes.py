import io
from typing import List
import pandas as pd
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse

from app.models.schemas import ErrorResponse
from app.services.ocr_service import ocr_service
from app.utils.image_processing import pdf_to_images, bytes_to_image, is_pdf_file
from app.utils.data_processing import merge_dataframes_intelligently, clean_dataframe, reorder_and_rename_columns
from app.utils.file_validation import validate_uploaded_files, get_file_content_type, read_file_bytes
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/process-invoices",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Successful response with CSV file"
        },
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Process invoices and return CSV",
    description="Process uploaded invoice files (PDFs and images), extract data, standardize columns, and return merged CSV file."
)
async def process_invoices(files: List[UploadFile] = File(..., description="Upload PDF or image files to process")):
    """
    Process uploaded invoices, extract data, standardize columns, merge, and return CSV.
    """
    # Validate uploaded files
    validate_uploaded_files(files)
    
    try:
        all_line_items_dfs = []
        processing_summary = {
            "files_processed": 0,
            "pages_processed": 0,
            "errors": []
        }
        
        # Process each uploaded file
        for uploaded_file in files:
            filename = uploaded_file.filename or "unknown_file"
            logger.info(f"Processing file: {filename}")
            file_processed = False
            
            try:
                # Read file content
                file_bytes = await read_file_bytes(uploaded_file)
                content_type = get_file_content_type(uploaded_file)
                
                # Convert to images
                images_to_process = []
                if is_pdf_file(content_type):
                    images_to_process = pdf_to_images(file_bytes)
                else:  # Assume image
                    image = bytes_to_image(file_bytes)
                    images_to_process = [image]
                
                # Process each page/image
                for page_idx, image in enumerate(images_to_process):
                    try:
                        extracted_data = ocr_service.extract_structured_data(image)
                        
                        # Convert line items to DataFrame
                        line_items = extracted_data.get('line_items', [])
                        if line_items:
                            line_items_df = pd.DataFrame(line_items)
                            line_items_df['source_file'] = filename
                            line_items_df['page_no'] = page_idx + 1
                            
                            # Add invoice header information to each line item
                            invoice_details = extracted_data.get('invoice_details', {})
                            line_items_df['invoice_number'] = invoice_details.get('invoice_number')
                            line_items_df['address'] = invoice_details.get('vendor_address')
                            line_items_df['date'] = invoice_details.get('invoice_date')
                            line_items_df['due_date'] = invoice_details.get('due_date')
                            line_items_df['company_name'] = invoice_details.get('vendor_name')
                            line_items_df['currency'] = invoice_details.get('currency')
                            
                            # Clean the DataFrame
                            line_items_df = clean_dataframe(line_items_df)
                            
                            if not line_items_df.empty:
                                all_line_items_dfs.append(line_items_df)
                                processing_summary["pages_processed"] += 1
                                file_processed = True
                                
                    except Exception as e:
                        error_msg = f"Error processing page {page_idx + 1} of {filename}: {str(e)}"
                        processing_summary["errors"].append(error_msg)
                        logger.error(error_msg)
                        continue
                
                if file_processed:
                    processing_summary["files_processed"] += 1
                    
            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                processing_summary["errors"].append(error_msg)
                logger.error(error_msg)
                continue
        
        if not all_line_items_dfs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No data extracted from any files."
            )
        
        # Standardize columns
        try:
            standardized_dfs = ocr_service.standardize_columns(all_line_items_dfs)
        except Exception as e:
            logger.error(f"LLM standardization failed: {str(e)}")
            logger.warning("Using simple rule-based column standardization as fallback")
            standardized_dfs = ocr_service.simple_column_standardization(all_line_items_dfs)
        
        # Merge all data
        final_df = merge_dataframes_intelligently(standardized_dfs)
        
        if final_df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid data after processing and standardization."
            )
        
        # Reorder columns and rename to proper titles
        final_df = reorder_and_rename_columns(final_df)
        
        # Generate CSV
        csv_buffer = io.StringIO()
        final_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Log processing summary
        logger.info(f"Processing completed: {processing_summary}")
        
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=processed_invoices.csv"}
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in process_invoices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Unexpected server error: {str(e)}"
        )
