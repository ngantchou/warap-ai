"""
Main entry point for Djobea AI application
Imports and runs the FastAPI app from the app package
"""

import uvicorn
from app.main import app
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )