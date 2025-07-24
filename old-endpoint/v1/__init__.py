"""
API v1 - Unified API Structure
Professional API organization with domain-based routing
"""

from fastapi import APIRouter

# API Version Router
api_v1_router = APIRouter(prefix="/api/v1", tags=["api-v1"])

# Import only active routers (webhooks and communications)
from .communications import router as communications_router
from .webhooks import router as webhooks_router

# Register only active domain routers
api_v1_router.include_router(communications_router, prefix="/communications", tags=["communications"])
api_v1_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

# All other APIs moved to old-endpoint/ folder
# - Analytics API: old-endpoint/analytics.py
# - Providers API: old-endpoint/providers.py
# - Requests API: old-endpoint/requests.py
# - System API: old-endpoint/system.py
# - Admin API: old-endpoint/admin.py
# - External API: old-endpoint/external.py
# - Legacy API: old-endpoint/legacy.py