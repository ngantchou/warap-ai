import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup structured logger with proper formatting"""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger

def log_conversation(logger: logging.Logger, user_id: str, message: str, response: str, extracted_data: Optional[dict] = None):
    """Log conversation for debugging and improvement"""
    log_data = {
        "user_id": user_id,
        "message": message,
        "response": response,
        "extracted_data": extracted_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"Conversation: {log_data}")

def log_error(logger: logging.Logger, component: str, error: Exception, details: Optional[dict] = None):
    """Log errors with context"""
    error_data = {
        "component": component,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.error(f"Error in {component}: {error_data}")
