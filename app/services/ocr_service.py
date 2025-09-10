import json
from typing import Dict, Any, List
from PIL import Image
import pandas as pd
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import logger
from app.utils.image_processing import encode_image_pil


class OCRService:
    """Service for OCR and data extraction using Groq LLM."""
    
    def __init__(self):
        """Initialize OCR service."""
        self.extraction_llm = None
        self.standardization_llm = None
    
    def _get_extraction_llm(self) -> ChatGroq:
        """Get or create extraction LLM instance."""
        if self.extraction_llm is None:
            self.extraction_llm = ChatGroq(
                groq_api_key=settings.groq_api_key,
                model_name=settings.groq_model_extraction,
                temperature=settings.llm_temperature
            )
        return self.extraction_llm
    
    def _get_standardization_llm(self) -> ChatGroq:
        """Get or create standardization LLM instance."""
        if self.standardization_llm is None:
            self.standardization_llm = ChatGroq(
                groq_api_key=settings.groq_api_key,
                model_name=settings.groq_model_standardization,
                temperature=settings.llm_temperature
            )
        return self.standardization_llm
    
    def extract_structured_data(self, image_obj: Image.Image) -> Dict[str, Any]:
        """
        Extract structured invoice data from image using Groq LLM.
        
        Args:
            image_obj: PIL Image object containing invoice
            
        Returns:
            Dictionary with invoice details and line items
            
        Raises:
            ValueError: If extraction fails after max retries
        """
        for attempt in range(settings.max_retries):
            try:
                logger.info(f"Extracting structured data (attempt {attempt + 1})")
                
                groq_llm = self._get_extraction_llm()
                image_data_url = f"data:image/jpeg;base64,{encode_image_pil(image_obj)}"

                extraction_prompt = """
You are an expert invoice data extractor. Analyze the uploaded invoice image and extract ALL tabular data.

CRITICAL: You MUST respond with ONLY a valid JSON object. Do not include any text before or after the JSON.

Instructions:
- Extract invoice header information and all line items from tables
- Use null for missing fields
- Convert numbers to numeric values (not strings)
- Handle various column names intelligently
- IMPORTANT: Detect and extract the currency symbol or code used in the invoice (e.g., $, €, £, USD, EUR, GBP, etc.)

Required JSON format (respond with ONLY this JSON, nothing else):
{
  "invoice_details": {
    "invoice_number": "value or null",
    "vendor_name": "value or null", 
    "vendor_address": "value or null",
    "invoice_date": "value or null",
    "due_date": "value or null",
    "total_amount": 0.00,
    "tax_amount": 0.00,
    "subtotal": 0.00,
    "currency": "$ or € or £ or USD or EUR or other currency symbol/code or null"
  },
  "line_items": [
    {
      "description": "item description",
      "quantity": 1,
      "unit_price": 10.00,
      "total_price": 10.00,
      "item_code": "code or null"
    }
  ]
}
                """

                messages = [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": extraction_prompt},
                            {"type": "image_url", "image_url": {"url": image_data_url}}
                        ]
                    }
                ]

                response = groq_llm.invoke(messages)
                response_content = response.content.strip()
                
                # Log the raw response for debugging
                logger.debug(f"Raw LLM response (attempt {attempt + 1}): {response_content[:200]}...")
                
                # Handle empty response
                if not response_content:
                    logger.warning(f"Empty response from LLM on attempt {attempt + 1}")
                    if attempt < settings.max_retries - 1:
                        continue
                    else:
                        return {"invoice_details": {}, "line_items": []}
                
                # Clean the response
                cleaned_content = self._clean_json_response(response_content)
                
                # Parse JSON response
                structured_data = json.loads(cleaned_content)
                
                # Validate the structure
                if not isinstance(structured_data, dict):
                    raise ValueError("Response is not a dictionary")
                
                # Ensure required keys exist
                if "invoice_details" not in structured_data:
                    structured_data["invoice_details"] = {}
                if "line_items" not in structured_data:
                    structured_data["line_items"] = []
                
                logger.info(f"Successfully extracted data with {len(structured_data.get('line_items', []))} line items")
                return structured_data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error on attempt {attempt + 1}: {str(e)}")
                if attempt < settings.max_retries - 1:
                    continue
                else:
                    raise ValueError(f"Failed to parse LLM response as JSON after {settings.max_retries} attempts")
                    
            except Exception as e:
                logger.error(f"Error in extract_structured_data attempt {attempt + 1}: {str(e)}")
                if attempt < settings.max_retries - 1:
                    continue
                else:
                    raise ValueError(f"Error extracting data after {settings.max_retries} attempts: {str(e)}")
    
    def _clean_json_response(self, response_content: str) -> str:
        """
        Clean LLM response to extract valid JSON.
        
        Args:
            response_content: Raw LLM response
            
        Returns:
            Cleaned JSON string
        """
        cleaned_content = response_content
        
        # Remove markdown code blocks if present
        if cleaned_content.startswith('```json'):
            cleaned_content = cleaned_content[7:]
        elif cleaned_content.startswith('```'):
            cleaned_content = cleaned_content[3:]
            
        if cleaned_content.endswith('```'):
            cleaned_content = cleaned_content[:-3]
        
        cleaned_content = cleaned_content.strip()
        
        # Attempt to find JSON in the response
        if not cleaned_content.startswith('{'):
            # Try to find the first { and last }
            start_idx = cleaned_content.find('{')
            end_idx = cleaned_content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                cleaned_content = cleaned_content[start_idx:end_idx+1]
            else:
                raise ValueError(f"No JSON object found in response: {cleaned_content}")
        
        return cleaned_content
    
    def standardize_columns(self, list_of_dataframes: List[pd.DataFrame]) -> List[pd.DataFrame]:
        """
        Standardize column names across multiple DataFrames using LLM reasoning.
        
        Args:
            list_of_dataframes: List of DataFrames with potentially different column names
            
        Returns:
            List of DataFrames with standardized column names
        """
        if not list_of_dataframes:
            return []
        
        # Collect all unique column names
        all_columns = set()
        for df in list_of_dataframes:
            all_columns.update(df.columns.tolist())
        
        all_columns = list(all_columns)
        
        if len(all_columns) <= 1:
            return list_of_dataframes
        
        for attempt in range(settings.max_retries):
            try:
                logger.info(f"Standardizing columns (attempt {attempt + 1})")
                
                groq_llm = self._get_standardization_llm()

                standardization_prompt = f"""
You are an expert data analyst. Create a JSON mapping to standardize these column names from invoice datasets.

Column names: {all_columns}

CRITICAL: Respond with ONLY a valid JSON object, no other text.

Rules:
- Group similar columns: "Item"/"Product"/"Description" → "description"  
- "Qty"/"Quantity" → "quantity"
- "Rate"/"Unit Price"/"Price" → "unit_price"
- "Total"/"Amount"/"Line Total" → "total_price"
- "Code"/"Item Code"/"SKU" → "item_code"
- "Address"/"Vendor Address" → "address"
- "Company"/"Vendor Name" → "company_name"
- "Invoice Number"/"Invoice No" → "invoice_number"
- "Date"/"Invoice Date" → "date"
- "Due Date" → "due_date"
- "Page"/"Page Number"/"Page No" → "page_no"
- "Currency" → "currency"
- Keep different concepts separate
- Use only these standard names: source_file, address, description, company_name, invoice_number, date, due_date, item_code, quantity, unit_price, total_price, page_no, currency

Example format (respond with ONLY JSON like this):
{{"Item": "description", "Qty": "quantity", "Rate": "unit_price", "Total": "total_price"}}
                """

                response = groq_llm.invoke([{"role": "user", "content": standardization_prompt}])
                response_content = response.content.strip()
                
                # Log response for debugging
                logger.debug(f"Column standardization response (attempt {attempt + 1}): {response_content[:200]}...")
                
                # Handle empty response
                if not response_content:
                    logger.warning(f"Empty response from LLM on attempt {attempt + 1}")
                    if attempt < settings.max_retries - 1:
                        continue
                    else:
                        return list_of_dataframes
                
                # Clean JSON response
                cleaned_content = self._clean_json_response(response_content)
                
                # Parse mapping
                column_mapping = json.loads(cleaned_content)
                
                # Validate mapping is a dictionary
                if not isinstance(column_mapping, dict):
                    raise ValueError("Mapping is not a dictionary")
                
                # Apply mapping to DataFrames
                standardized_dfs = []
                for df in list_of_dataframes:
                    df_copy = df.copy()
                    # Create rename dictionary, keeping unmapped columns as-is
                    rename_dict = {}
                    for col in df_copy.columns:
                        if col in column_mapping:
                            rename_dict[col] = column_mapping[col]
                    
                    if rename_dict:  # Only rename if there are mappings
                        df_copy.rename(columns=rename_dict, inplace=True)
                    standardized_dfs.append(df_copy)
                
                logger.info(f"Successfully standardized columns with mapping: {column_mapping}")
                return standardized_dfs
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in standardize_columns attempt {attempt + 1}: {str(e)}")
                if attempt < settings.max_retries - 1:
                    continue
                else:
                    logger.warning(f"Failed to parse column standardization response after {settings.max_retries} attempts. Using original column names.")
                    return list_of_dataframes
                    
            except Exception as e:
                logger.error(f"Error in standardize_columns attempt {attempt + 1}: {str(e)}")
                if attempt < settings.max_retries - 1:
                    continue
                else:
                    logger.warning(f"Error standardizing columns after {settings.max_retries} attempts. Using original column names.")
                    return list_of_dataframes
    
    def simple_column_standardization(self, list_of_dataframes: List[pd.DataFrame]) -> List[pd.DataFrame]:
        """
        Simple rule-based column standardization as fallback.
        
        Args:
            list_of_dataframes: List of DataFrames
            
        Returns:
            List of DataFrames with standardized columns
        """
        simple_mapping = {
            'item': 'description',
            'product': 'description', 
            'product_name': 'description',
            'description': 'description',
            'item_description': 'description',
            'qty': 'quantity',
            'quantity': 'quantity',
            'units': 'quantity',
            'rate': 'unit_price',
            'unit_price': 'unit_price',
            'price': 'unit_price',
            'unit_cost': 'unit_price',
            'cost': 'unit_price',
            'total': 'total_price',
            'total_price': 'total_price',
            'line_total': 'total_price',
            'amount': 'total_price',
            'value': 'total_price',
            'code': 'item_code',
            'item_code': 'item_code',
            'product_code': 'item_code',
            'sku': 'item_code',
            'address': 'address',
            'vendor_address': 'address',
            'company': 'company_name',
            'vendor_name': 'company_name',
            'company_name': 'company_name',
            'invoice_number': 'invoice_number',
            'invoice_no': 'invoice_number',
            'date': 'date',
            'invoice_date': 'date',
            'date_and_time': 'date',
            'due_date': 'due_date',
            'page': 'page_no',
            'page_number': 'page_no',
            'page_no': 'page_no',
            'currency': 'currency'
        }
        
        standardized_dfs = []
        for df in list_of_dataframes:
            df_copy = df.copy()
            rename_dict = {}
            
            for col in df_copy.columns:
                col_lower = col.lower().strip()
                if col_lower in simple_mapping:
                    rename_dict[col] = simple_mapping[col_lower]
            
            if rename_dict:
                df_copy.rename(columns=rename_dict, inplace=True)
            standardized_dfs.append(df_copy)
        
        logger.info("Applied simple column standardization")
        return standardized_dfs


# Global OCR service instance
ocr_service = OCRService()
