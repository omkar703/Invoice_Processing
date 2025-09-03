import pandas as pd
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import HealthCheckResponse, ErrorResponse
from app.services.s3_service import s3_service
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    responses={
        200: {
            "model": HealthCheckResponse,
            "description": "System is healthy"
        },
        503: {"model": ErrorResponse}
    },
    summary="Health check endpoint",
    description="Check the health status of the application and its dependencies."
)
def health_check():
    """
    Perform a health check of the application and its dependencies.
    
    Returns:
        HealthCheckResponse with system status
    """
    try:
        logger.info("Performing health check")
        
        dependencies = {}
        overall_status = "healthy"
        
        # Check S3 connectivity
        try:
            # Try to list bucket contents (limited to 1 object)
            s3_service.list_files(max_keys=1)
            dependencies["s3"] = "healthy"
        except Exception as e:
            dependencies["s3"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"
            logger.warning(f"S3 health check failed: {str(e)}")
        
        # Check Groq API (we can't easily test without making a real call)
        if settings.groq_api_key:
            dependencies["groq_api"] = "configured"
        else:
            dependencies["groq_api"] = "not_configured"
            overall_status = "degraded"
        
        # Check configuration
        try:
            settings.validate_settings()
            dependencies["configuration"] = "valid"
        except Exception as e:
            dependencies["configuration"] = f"invalid: {str(e)}"
            overall_status = "unhealthy"
            logger.error(f"Configuration validation failed: {str(e)}")
        
        # Check pandas (basic dependency check)
        try:
            pd.DataFrame()  # Simple test
            dependencies["pandas"] = "healthy"
        except Exception as e:
            dependencies["pandas"] = f"unhealthy: {str(e)}"
            overall_status = "unhealthy"
        
        response = HealthCheckResponse(
            status=overall_status,
            timestamp=pd.Timestamp.now().isoformat(),
            version=settings.app_version,
            dependencies=dependencies
        )
        
        if overall_status == "unhealthy":
            logger.error(f"Health check failed: {dependencies}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unhealthy: {dependencies}"
            )
        
        logger.info(f"Health check passed: {overall_status}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get(
    "/",
    summary="API root endpoint",
    description="Basic information about the Invoice Processor API."
)
def read_root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": "Invoice Processor API",
        "version": settings.app_version,
        "description": settings.app_description,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "process_invoices": "/process-invoices",
            "extract_ocr_data": "/extract-ocr-data"
        }
    }
