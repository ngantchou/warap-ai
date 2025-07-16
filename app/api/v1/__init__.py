"""
API v1 - Unified API Structure
Professional API organization with domain-based routing
"""

from fastapi import APIRouter

# API Version Router
api_v1_router = APIRouter(prefix="/api/v1", tags=["api-v1"])

# Import all domain routers
from .analytics import router as analytics_router
from .providers import router as providers_router
from .requests import router as requests_router
from .communications import router as communications_router
from .system import router as system_router
from .admin import router as admin_router
from .external import router as external_router

# Register domain routers
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_v1_router.include_router(providers_router, prefix="/providers", tags=["providers"])
api_v1_router.include_router(requests_router, prefix="/requests", tags=["requests"])
api_v1_router.include_router(communications_router, prefix="/communications", tags=["communications"])
api_v1_router.include_router(system_router, prefix="/system", tags=["system"])
api_v1_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(external_router, prefix="/external", tags=["external"])

# Legacy compatibility routes (will be deprecated)
from .legacy import router as legacy_router
api_v1_router.include_router(legacy_router, prefix="/legacy", tags=["legacy"])