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

# Import routers after app creation to avoid circular imports
from app.api.webhook import router as webhook_router
from app.api.webhook_v2 import router as webhook_v2_router
from app.api.webhook_v3 import router as webhook_v3_router
from app.api.webhook_v4 import router as webhook_v4_router
from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.payment import router as payment_router
from app.api.public_profiles import router as public_profiles_router
from app.api.analytics import router as analytics_router
from app.api.provider_dashboard import router as provider_router
from app.api.demo_provider_auth import router as demo_auth_router
from app.api.demo_dashboard import router as demo_dashboard_router
from app.api.dynamic_services_api import router as dynamic_services_router
from app.api.validation_api import router as validation_router
from app.api.request_management_standalone import router as request_management_router
from app.api.knowledge_base_api import router as knowledge_base_router
from app.api.tracking_api import router as tracking_router
from app.api.escalation_detection_api import router as escalation_router
from app.api.human_escalation_api import router as human_escalation_router
from app.api.gestionnaire_chat import router as gestionnaire_chat_router
from app.api.simple_gestionnaire_chat import router as simple_gestionnaire_chat_router
from app.api.dashboard import router as dashboard_router

# Import new API modules (fixed import issues)
from app.api.analytics import router as analytics_api_router
from app.api.providers import router as providers_api_router
from app.api.requests import router as requests_api_router
from app.api.finances import router as finances_api_router
from app.api.system import router as system_api_router
from app.api.ai import router as ai_api_router
from app.api.settings import router as settings_api_router

# Include routers
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
app.include_router(webhook_v2_router, prefix="/webhook", tags=["webhook-v2"])
app.include_router(webhook_v3_router, prefix="/webhook", tags=["webhook-v3"])
app.include_router(webhook_v4_router, prefix="/webhook", tags=["webhook-v4"])
app.include_router(chat_router, tags=["chat"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(payment_router, tags=["payments"])
app.include_router(public_profiles_router, tags=["public-profiles"])
app.include_router(analytics_router, tags=["analytics"])
app.include_router(provider_router, prefix="/api", tags=["provider-dashboard"])
app.include_router(demo_auth_router, prefix="/api", tags=["demo-auth"])
app.include_router(demo_dashboard_router, prefix="/api", tags=["demo-dashboard"])
app.include_router(dynamic_services_router, tags=["dynamic-services"])
app.include_router(validation_router, tags=["validation"])
app.include_router(request_management_router, tags=["request-management"])
app.include_router(knowledge_base_router, tags=["knowledge-base"])
app.include_router(tracking_router, tags=["tracking"])
app.include_router(escalation_router, tags=["escalation"])
app.include_router(human_escalation_router, tags=["human-escalation"])
app.include_router(gestionnaire_chat_router, tags=["gestionnaire-chat"])
app.include_router(simple_gestionnaire_chat_router, tags=["simple-gestionnaire-chat"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])

# New API routers for mobile/web interface
app.include_router(analytics_api_router, prefix="/api", tags=["analytics-api"])
app.include_router(providers_api_router, prefix="/api", tags=["providers-api"])
app.include_router(requests_api_router, prefix="/api", tags=["requests-api"])
app.include_router(finances_api_router, prefix="/api", tags=["finances-api"])
app.include_router(system_api_router, prefix="/api", tags=["system-api"])
app.include_router(ai_api_router, prefix="/api", tags=["ai-api"])
app.include_router(settings_api_router, prefix="/api", tags=["settings-api"])

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
