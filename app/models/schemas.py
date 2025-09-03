from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# Using FastAPI's UploadFile for direct file uploads
from fastapi import UploadFile, File

class InvoiceProcessRequest(BaseModel):
    """Request model for invoice processing endpoint."""
    # Note: This is now handled by FastAPI Form parameters directly in route functions
    # since UploadFile can't be used directly in Pydantic models
    pass


class OCRDataRequest(BaseModel):
    """Request model for OCR data extraction endpoint."""
    # Note: This is now handled by FastAPI Form parameters directly in route functions
    # since UploadFile can't be used directly in Pydantic models
    pass


class InvoiceDetails(BaseModel):
    """Model for invoice header details."""
    invoice_number: Optional[str] = Field(None, description="Invoice number")
    vendor_name: Optional[str] = Field(None, description="Vendor/company name")
    vendor_address: Optional[str] = Field(None, description="Vendor address")
    invoice_date: Optional[str] = Field(None, description="Invoice date")
    due_date: Optional[str] = Field(None, description="Invoice due date")
    total_amount: Optional[float] = Field(None, description="Total invoice amount")
    tax_amount: Optional[float] = Field(None, description="Tax amount")
    subtotal: Optional[float] = Field(None, description="Subtotal amount")


class LineItem(BaseModel):
    """Model for invoice line item."""
    description: Optional[str] = Field(None, description="Item description")
    quantity: Optional[int] = Field(None, description="Quantity")
    unit_price: Optional[float] = Field(None, description="Unit price")
    total_price: Optional[float] = Field(None, description="Total price")
    item_code: Optional[str] = Field(None, description="Item/product code")


class RawTextContent(BaseModel):
    """Model for raw text content summaries."""
    invoice_summary: str = Field(..., description="Summary of invoice details")
    line_items_summary: str = Field(..., description="Summary of line items")


class DocumentMetadata(BaseModel):
    """Model for document processing metadata."""
    has_line_items: bool = Field(..., description="Whether document has line items")
    line_items_count: int = Field(..., description="Number of line items")
    has_invoice_details: bool = Field(..., description="Whether document has invoice details")
    extracted_fields: List[str] = Field(..., description="List of extracted field names")
    processing_status: str = Field(..., description="Processing status (success/error)")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class DocumentData(BaseModel):
    """Model for extracted document data."""
    document_id: str = Field(..., description="Unique document identifier")
    source_file: str = Field(..., description="Original filename")
    page_number: int = Field(..., description="Page number")
    total_pages: int = Field(..., description="Total pages in document")
    file_type: str = Field(..., description="File MIME type")
    extraction_timestamp: str = Field(..., description="ISO timestamp of extraction")
    invoice_details: InvoiceDetails = Field(..., description="Extracted invoice details")
    line_items: List[LineItem] = Field(..., description="Extracted line items")
    raw_text_content: RawTextContent = Field(..., description="Text summaries for RAG")
    metadata: DocumentMetadata = Field(..., description="Processing metadata")


class OCRDataResponse(BaseModel):
    """Response model for OCR data extraction endpoint."""
    success: bool = Field(..., description="Whether extraction was successful")
    message: str = Field(..., description="Human-readable status message")
    data: List[DocumentData] = Field(..., description="List of extracted document data")
    total_files_processed: int = Field(..., description="Number of files processed")
    total_pages_processed: int = Field(..., description="Number of pages processed")
    processing_errors: Optional[List[str]] = Field(None, description="List of processing errors")
    total_errors: Optional[int] = Field(None, description="Total number of errors")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    detail: str = Field(..., description="Error details")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: Optional[str] = Field(None, description="Error timestamp")


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Check timestamp")
    version: str = Field(..., description="Application version")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")
