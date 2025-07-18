import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse
import uvicorn

from app.models.database_models import Base, init_db
from app.models.cultural_models import CulturalContext
from app.models.personalization_models import UserPreferences, ServiceHistory
# Provider models are now in separate file for API use
from app.models.settings_models import (SystemSettings, NotificationSettings,
                                        SecuritySettings, PerformanceSettings,
                                        AISettings, WhatsAppSettings,
                                        BusinessSettings, ProviderSettings as
                                        ProviderSettingsModel, RequestSettings,
                                        AdminSettings)
from app.models.auth_models import (User, RefreshToken, UserRole, Permission,
                                    RolePermission, LoginAttempt, UserSession)
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

        # Initialize authentication permissions
        from app.services.permission_service import permission_service
        with next(get_db()) as db:
            permission_service.initialize_default_permissions(db)
        logger.info("Authentication permissions initialized")

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
    description=
    "Agent conversationnel WhatsApp pour services à domicile au Cameroun",
    version="1.0.0",
    lifespan=lifespan)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"])

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Essential external API endpoints (kept for existing integrations)
from app.routes.web_chat_routes import router as web_chat_api_router

app.include_router(web_chat_api_router,
                   prefix="/api/web-chat",
                   tags=["web-chat"])

# JWT Authentication API (comprehensive authentication system)
from app.api.auth import router as auth_router

app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])

# Dashboard API (real data dashboard endpoints)
from app.api.dashboard import router as dashboard_router

app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])

# Analytics API Package (comprehensive analytics endpoints)
from app.api.analytics import router as analytics_router

app.include_router(analytics_router, prefix="/api", tags=["analytics"])

# Provider API (complete provider management system)
from app.api.providers_complete import router as providers_router

app.include_router(providers_router)

# Remove the options handler since the middleware handles it now

# All other API endpoints moved to old-endpoint/ folder:
# - webhook.py -> old-endpoint/webhook.py
# - config.py -> old-endpoint/config.py
# - chat.py -> old-endpoint/chat.py
# - landing_data.py -> old-endpoint/landing_data.py
# - llm_status.py -> old-endpoint/llm_status.py

# ==== LEGACY COMPATIBILITY (DEPRECATED) ====
# ALL API files have been moved to old-endpoint/ folder
# Only essential web chat routes remain active
# No direct imports from old API files

# ==== END UNIFIED API STRUCTURE ====


# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - serve beautiful landing page"""
    return templates.TemplateResponse("landing_v2.html", {"request": request})


# Provider dashboard routes
@app.get("/provider-login", response_class=HTMLResponse)
async def provider_login_page(request: Request):
    """Provider login page"""
    return templates.TemplateResponse("provider_login.html",
                                      {"request": request})


@app.get("/provider-dashboard", response_class=HTMLResponse)
async def provider_dashboard_page(request: Request):
    """Provider dashboard page"""
    return templates.TemplateResponse("provider_dashboard.html",
                                      {"request": request})


@app.get("/provider-profile", response_class=HTMLResponse)
async def provider_profile_page(request: Request):
    """Provider profile management page"""
    return templates.TemplateResponse("provider_profile.html",
                                      {"request": request})


@app.get("/admin")
async def admin_redirect():
    """Redirect /admin to /admin/"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/", status_code=307)


@app.get("/agent-dashboard", response_class=HTMLResponse)
async def agent_dashboard_page(request: Request):
    """Agent dashboard page for human escalation"""
    return templates.TemplateResponse("agent_dashboard.html",
                                      {"request": request})


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "djobea-ai"}


@app.get("/api/config")
async def get_config():
    """Get client configuration"""
    return {"demo_mode": settings.demo_mode, "app_name": settings.app_name}


if __name__ == "__main__":
    # Run the application
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=5000,
                reload=True,
                log_level="info")
