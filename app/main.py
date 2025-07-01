import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from app.models.database_models import Base, init_db
from app.database import engine, get_db
from app.utils.logger import setup_logger
from app.config import get_settings

# Setup logging
logger = setup_logger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Djobea AI application...")
    
    # Create database tables
    try:
        init_db(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Djobea AI application...")

# Create FastAPI app
app = FastAPI(
    title="Djobea AI",
    description="Agent conversationnel WhatsApp pour services à domicile au Cameroun",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Import routers after app creation to avoid circular imports
from app.api.webhook import router as webhook_router
from app.api.admin import router as admin_router

# Include routers
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirect to admin dashboard"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin", status_code=303)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "djobea-ai"}



if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
