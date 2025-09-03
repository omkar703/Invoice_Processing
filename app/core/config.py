import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # API Configuration
    app_name: str = "Intelligent Invoice Processor API"
    app_description: str = "API for processing uploaded invoice files (PDFs and images), extracting data using LLM, standardizing, and returning merged CSV or JSON for RAG applications."
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # LLM Configuration
    groq_api_key: Optional[str] = None
    groq_model_extraction: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_model_standardization: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.0
    max_retries: int = 3
    
    # AWS Configuration - DEPRECATED (now using direct file uploads)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    
    # Image Processing Configuration
    pdf_zoom_factor: float = 2.0
    image_quality: int = 85
    image_format: str = "JPEG"
    
    # Logging Configuration
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Override with environment variables or hardcoded values
        self.groq_api_key = self.groq_api_key or os.getenv("GROQ_API_KEY")
        # AWS settings deprecated - now using direct file uploads
        self.aws_access_key_id = self.aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID") 
        self.aws_secret_access_key = self.aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY") 
        self.s3_bucket_name = self.s3_bucket_name or os.getenv("S3_BUCKET_NAME")
        self.aws_region = self.aws_region or os.getenv("AWS_REGION")
    
    def validate_settings(self) -> None:
        """Validate that all required settings are present."""
        required_settings = [
            ('groq_api_key', self.groq_api_key),
            # AWS settings no longer required - using direct file uploads
            # ('aws_access_key_id', self.aws_access_key_id),
            # ('aws_secret_access_key', self.aws_secret_access_key),
            # ('s3_bucket_name', self.s3_bucket_name)
        ]
        
        missing_settings = [name for name, value in required_settings if not value]
        
        if missing_settings:
            raise ValueError(f"Missing required settings: {', '.join(missing_settings)}")


# Global settings instance
settings = Settings()
