"""
Analytics API Package for Djobea AI
Contains all analytics-related endpoints organized by functionality
"""

from fastapi import APIRouter
from .kpis import router as kpis_router
from .performance import router as performance_router
from .services import router as services_router
from .geographic import router as geographic_router

# Create main analytics router
router = APIRouter()

# Include all analytics sub-routers
router.include_router(kpis_router, tags=["analytics-kpis"])
router.include_router(performance_router, tags=["analytics-performance"])
router.include_router(services_router, tags=["analytics-services"])
router.include_router(geographic_router, tags=["analytics-geographic"])