from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.routes import invoice_routes, ocr_routes, health_routes


def create_application() -> FastAPI:
   
    # Validate settings on startup
    try:
        settings.validate_settings()
        logger.info("Application settings validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health_routes.router, tags=["Health"])
    app.include_router(invoice_routes.router, tags=["Invoice Processing"])
    app.include_router(ocr_routes.router, tags=["OCR Data Extraction"])
    
    logger.info(f"FastAPI application created: {settings.app_name} v{settings.app_version}")
    return app


# Create the application instance
app = create_application()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Invoice Processor API starting up...")
    logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    logger.info(f"Configuration validated")
    logger.info(f"Ready to process uploaded invoice files!")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Invoice Processor API shutting down...")
    logger.info("Cleanup completed")
