import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> logging.Logger:
    # logging config
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Create console handler (where the log goes)
    console_handler = logging.StreamHandler(sys.stdout) # standard output -> terminal
    console_handler.setFormatter(formatter)


    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        handlers=[console_handler],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and return application logger
    logger = logging.getLogger("invoice_processor")
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    return logger


# Global logger instance
logger = setup_logging()
