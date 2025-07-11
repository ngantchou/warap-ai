import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from app.models.database_models import Base, init_db
from app.models.cultural_models import CulturalContext
from app.models.personalization_models import UserPreferences, ServiceHistory
from app.models.provider_models import (
    ProviderSession, ProviderSettings, ProviderStatsCache, 
    ProviderNotification, ProviderAvailability, ProviderDashboardWidget
)
from app.database import engine, get_db
from app.utils.logger import setup_logger
from app.config import get_settings
from app.services.cultural_data_service import CulturalDataService

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
        
        # Seed cultural data
        cultural_service = CulturalDataService()
        with next(get_db()) as db:
            cultural_service.seed_all_cultural_data(db)
        logger.info("Cultural data seeded successfully")
        
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

# Setup security middleware
from app.middleware.security import setup_security_middleware
setup_security_middleware(app)

# ==== CLEAN API STRUCTURE - ONLY ESSENTIAL ENDPOINTS ====

# Core webhook endpoint (remove v2, v3, v4 duplicates)
from app.api.webhook import router as webhook_router
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])

# Core authentication (remove demo auth duplicates)
from app.api.auth import router as auth_router
app.include_router(auth_router, prefix="/auth", tags=["authentication"])

# Core admin interface (keep main admin)
from app.api.admin import router as admin_router
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# Essential external API endpoints (cleaned up)
from app.api.analytics import router as analytics_api_router
from app.api.ai import router as ai_api_router
from app.api.settings import router as settings_api_router
from app.api.finances import router as finances_api_router

app.include_router(analytics_api_router, prefix="/api", tags=["analytics-api"])
app.include_router(ai_api_router, prefix="/api", tags=["ai-api"])
app.include_router(settings_api_router, prefix="/api", tags=["settings-api"])
app.include_router(finances_api_router, prefix="/api", tags=["finances-api"])

# Essential provider and request endpoints (simplified)
from app.api.providers import router as providers_api_router
from app.api.requests import router as requests_api_router

app.include_router(providers_api_router, prefix="/api", tags=["providers-api"])
app.include_router(requests_api_router, prefix="/api", tags=["requests-api"])

# Chat widget endpoint
from app.api.chat import router as chat_router
app.include_router(chat_router, tags=["chat"])

# Main dashboard (remove demo dashboard duplicates)
from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])

# Landing page dynamic data
from app.api.landing_data import router as landing_data_router
app.include_router(landing_data_router, tags=["landing-data"])

# Communication metrics endpoint
from app.api.communication_metrics import router as communication_router
app.include_router(communication_router, prefix="/api/communication", tags=["communication"])

# AI Suggestions endpoint
from app.api.ai_suggestions import router as ai_suggestions_router
from app.api.llm_status import router as llm_status_router
app.include_router(ai_suggestions_router, tags=["ai-suggestions"])
app.include_router(llm_status_router, tags=["llm-management"])

# ==== END CLEAN API STRUCTURE ====

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - serve beautiful landing page"""
    return templates.TemplateResponse("landing_v2.html", {"request": request})

# Provider dashboard routes
@app.get("/provider-login", response_class=HTMLResponse)
async def provider_login_page(request: Request):
    """Provider login page"""
    return templates.TemplateResponse("provider_login.html", {"request": request})

@app.get("/provider-dashboard", response_class=HTMLResponse)
async def provider_dashboard_page(request: Request):
    """Provider dashboard page"""
    return templates.TemplateResponse("provider_dashboard.html", {"request": request})

@app.get("/provider-profile", response_class=HTMLResponse)
async def provider_profile_page(request: Request):
    """Provider profile management page"""
    return templates.TemplateResponse("provider_profile.html", {"request": request})

@app.get("/admin")
async def admin_redirect():
    """Redirect /admin to /admin/"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/", status_code=307)

@app.get("/agent-dashboard", response_class=HTMLResponse)
async def agent_dashboard_page(request: Request):
    """Agent dashboard page for human escalation"""
    return templates.TemplateResponse("agent_dashboard.html", {"request": request})

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "djobea-ai"}

@app.get("/api/config")
async def get_config():
    """Get client configuration"""
    return {
        "demo_mode": settings.demo_mode,
        "app_name": settings.app_name
    }



if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
