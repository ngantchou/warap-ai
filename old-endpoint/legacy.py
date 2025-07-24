"""
Legacy API v1 - Compatibility Layer
Provides backward compatibility for existing API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from app.database import get_db
from app.models.database_models import AdminUser
from app.utils.auth import get_current_user
from loguru import logger

router = APIRouter()

# ==== REDIRECT MAPPINGS ====
# Map old endpoints to new unified structure

@router.get("/api/analytics/{path:path}")
async def redirect_analytics(path: str, request: Request):
    """Redirect old analytics endpoints to new structure"""
    new_url = f"/api/v1/analytics/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/providers/{path:path}")
async def redirect_providers(path: str, request: Request):
    """Redirect old providers endpoints to new structure"""
    new_url = f"/api/v1/providers/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/requests/{path:path}")
async def redirect_requests(path: str, request: Request):
    """Redirect old requests endpoints to new structure"""
    new_url = f"/api/v1/requests/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/messages/{path:path}")
async def redirect_messages(path: str, request: Request):
    """Redirect old messages endpoints to new structure"""
    new_url = f"/api/v1/communications/messages/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/notifications/{path:path}")
async def redirect_notifications(path: str, request: Request):
    """Redirect old notifications endpoints to new structure"""
    new_url = f"/api/v1/communications/notifications/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/ai/{path:path}")
async def redirect_ai(path: str, request: Request):
    """Redirect old AI endpoints to new structure"""
    new_url = f"/api/v1/system/ai/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/settings/{path:path}")
async def redirect_settings(path: str, request: Request):
    """Redirect old settings endpoints to new structure"""
    new_url = f"/api/v1/system/settings/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/finances/{path:path}")
async def redirect_finances(path: str, request: Request):
    """Redirect old finances endpoints to new structure"""
    new_url = f"/api/v1/external/finances/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/geolocation/{path:path}")
async def redirect_geolocation(path: str, request: Request):
    """Redirect old geolocation endpoints to new structure"""
    new_url = f"/api/v1/external/geolocation/{path}"
    return RedirectResponse(url=new_url, status_code=301)

@router.get("/api/export/{path:path}")
async def redirect_export(path: str, request: Request):
    """Redirect old export endpoints to new structure"""
    new_url = f"/api/v1/external/export/{path}"
    return RedirectResponse(url=new_url, status_code=301)

# ==== LEGACY ENDPOINT INFORMATION ====
@router.get("/migration-guide")
async def get_migration_guide():
    """Get API migration guide"""
    return {
        "success": True,
        "message": "API Migration Guide",
        "data": {
            "version": "v1",
            "globalPrefix": "/api/v1",
            "domains": {
                "analytics": {
                    "newPrefix": "/api/v1/analytics",
                    "oldEndpoints": [
                        "/api/analytics/*",
                        "/api/communication/*",
                        "/api/monitoring/*"
                    ],
                    "description": "Analytics, communication metrics, and monitoring"
                },
                "providers": {
                    "newPrefix": "/api/v1/providers",
                    "oldEndpoints": [
                        "/api/providers/*",
                        "/api/provider-dashboard/*",
                        "/api/public-profiles/*"
                    ],
                    "description": "Provider management, dashboard, and public profiles"
                },
                "requests": {
                    "newPrefix": "/api/v1/requests",
                    "oldEndpoints": [
                        "/api/requests/*",
                        "/api/tracking/*",
                        "/api/escalation/*"
                    ],
                    "description": "Request management, tracking, and escalation"
                },
                "communications": {
                    "newPrefix": "/api/v1/communications",
                    "oldEndpoints": [
                        "/api/messages/*",
                        "/api/notifications/*",
                        "/api/chat/*",
                        "/api/webhooks/*"
                    ],
                    "description": "Messages, notifications, chat, and webhooks"
                },
                "system": {
                    "newPrefix": "/api/v1/system",
                    "oldEndpoints": [
                        "/api/ai/*",
                        "/api/settings/*",
                        "/api/config/*",
                        "/api/knowledge/*",
                        "/api/validation/*"
                    ],
                    "description": "AI services, settings, configuration, and system management"
                },
                "admin": {
                    "newPrefix": "/api/v1/admin",
                    "oldEndpoints": [
                        "/api/admin/*",
                        "/api/auth/*",
                        "/api/dashboard/*"
                    ],
                    "description": "Administration, authentication, and dashboard"
                },
                "external": {
                    "newPrefix": "/api/v1/external",
                    "oldEndpoints": [
                        "/api/finances/*",
                        "/api/payments/*",
                        "/api/geolocation/*",
                        "/api/export/*"
                    ],
                    "description": "External services, finances, payments, and exports"
                }
            },
            "changes": {
                "globalPrefix": "All endpoints now use /api/v1 prefix",
                "domainGrouping": "Endpoints are grouped by business domain",
                "consistentNaming": "Consistent naming conventions across all endpoints",
                "versioning": "Proper API versioning for future updates",
                "deprecation": "Old endpoints will be deprecated in v2.0"
            },
            "migration": {
                "step1": "Update client applications to use /api/v1 prefix",
                "step2": "Update endpoint paths according to domain grouping",
                "step3": "Test all integrations with new endpoints",
                "step4": "Update documentation and API references"
            }
        }
    }

# ==== DEPRECATED ENDPOINT WARNINGS ====
@router.get("/deprecated-endpoints")
async def get_deprecated_endpoints():
    """Get list of deprecated endpoints"""
    return {
        "success": True,
        "message": "Deprecated Endpoints List",
        "data": {
            "deprecated": [
                {
                    "endpoint": "/api/analytics-complete/*",
                    "replacement": "/api/v1/analytics/*",
                    "deprecatedIn": "v1.0.0",
                    "removedIn": "v2.0.0"
                },
                {
                    "endpoint": "/api/providers-complete/*",
                    "replacement": "/api/v1/providers/*",
                    "deprecatedIn": "v1.0.0",
                    "removedIn": "v2.0.0"
                },
                {
                    "endpoint": "/api/requests-complete/*",
                    "replacement": "/api/v1/requests/*",
                    "deprecatedIn": "v1.0.0",
                    "removedIn": "v2.0.0"
                },
                {
                    "endpoint": "/api/finances-complete/*",
                    "replacement": "/api/v1/external/finances/*",
                    "deprecatedIn": "v1.0.0",
                    "removedIn": "v2.0.0"
                },
                {
                    "endpoint": "/api/ai-complete/*",
                    "replacement": "/api/v1/system/ai/*",
                    "deprecatedIn": "v1.0.0",
                    "removedIn": "v2.0.0"
                },
                {
                    "endpoint": "/api/settings-complete/*",
                    "replacement": "/api/v1/system/settings/*",
                    "deprecatedIn": "v1.0.0",
                    "removedIn": "v2.0.0"
                }
            ],
            "notice": "Please update your applications to use the new v1 API structure. Legacy endpoints will be removed in v2.0.0"
        }
    }

# ==== COMPATIBILITY HELPERS ====
@router.get("/api-status")
async def get_api_status():
    """Get API status and version information"""
    return {
        "success": True,
        "data": {
            "version": "v1.0.0",
            "status": "operational",
            "structure": "unified",
            "domains": 7,
            "endpoints": 150,
            "deprecatedEndpoints": 45,
            "lastUpdate": "2025-07-16",
            "features": {
                "versioning": True,
                "domainGrouping": True,
                "globalPrefix": True,
                "backwardCompatibility": True,
                "authentication": True,
                "rateLimit": True,
                "documentation": True
            }
        }
    }