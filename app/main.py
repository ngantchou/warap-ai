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
from app.models.settings_models import (
    SystemSettings, NotificationSettings, SecuritySettings, PerformanceSettings,
    AISettings, WhatsAppSettings, BusinessSettings, ProviderSettings as ProviderSettingsModel,
    RequestSettings, AdminSettings
)
from app.database import engine, get_db
from app.utils.logger import setup_logger
from app.config import get_settings
from app.services.cultural_data_service import CulturalDataService
from app.services.config_service import init_config

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
        
        # Initialize configuration service
        with next(get_db()) as db:
            config_service = init_config(db)
            config_service.settings_service.seed_default_settings()
        logger.info("Configuration service initialized successfully")
        
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
from app.api.auth_api import router as auth_api_router
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
# Add API auth routes under /api prefix
app.include_router(auth_router, prefix="/api", tags=["api-auth"])
app.include_router(auth_api_router, tags=["auth-api"])

# Add all comprehensive API modules
from app.api.analytics_complete import router as analytics_complete_router
from app.api.providers_complete import router as providers_complete_router
from app.api.requests_complete import router as requests_complete_router
from app.api.finances_complete import router as finances_complete_router
from app.api.ai_complete import router as ai_complete_router
from app.api.settings_complete import router as settings_complete_router
from app.api.geolocation import router as geolocation_router
from app.api.notifications import router as notifications_router
from app.api.export import router as export_router
from app.api.messages import router as messages_router

# Register comprehensive API endpoints
app.include_router(analytics_complete_router, prefix="/api/analytics", tags=["analytics-complete"])
app.include_router(providers_complete_router, prefix="/api/providers", tags=["providers-complete"])
app.include_router(requests_complete_router, prefix="/api/requests", tags=["requests-complete"])
app.include_router(finances_complete_router, prefix="/api/finances", tags=["finances-complete"])
app.include_router(ai_complete_router, prefix="/api/ai", tags=["ai-complete"])
app.include_router(settings_complete_router, prefix="/api/settings", tags=["settings-complete"])
app.include_router(geolocation_router, prefix="/api/geolocation", tags=["geolocation"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
app.include_router(export_router, prefix="/api/export", tags=["export"])
app.include_router(messages_router, prefix="/api/messages", tags=["messages"])

# Core admin interface (keep main admin)
from app.api.admin import router as admin_router
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# Essential external API endpoints (cleaned up - no duplicates)
from app.routes.web_chat_routes import router as web_chat_api_router

app.include_router(web_chat_api_router, prefix="/api/web-chat", tags=["web-chat"])
# All API endpoints now use the *_complete modules above

# Configuration API endpoints
from app.api.config import router as config_api_router
app.include_router(config_api_router, prefix="/api/config", tags=["configuration"])

# Chat widget endpoint
from app.api.chat import router as chat_router
app.include_router(chat_router, tags=["chat"])

# Main dashboard (remove demo dashboard duplicates)
from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])

# Dashboard API endpoint (as per documentation) - should be accessible as /api/dashboard
app.include_router(dashboard_router, prefix="/api", tags=["dashboard-api"])

# Landing page dynamic data
from app.api.landing_data import router as landing_data_router
app.include_router(landing_data_router, tags=["landing-data"])

# Communication metrics endpoint
from app.api.communication_metrics import router as communication_router
app.include_router(communication_router, prefix="/api/communication", tags=["communication"])

# AI Suggestions endpoint - removed (functionality integrated into ai_complete.py)
from app.api.llm_status import router as llm_status_router
app.include_router(llm_status_router, tags=["llm-management"])

# Monitoring API endpoint
from app.api.monitoring import router as monitoring_router
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])

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
