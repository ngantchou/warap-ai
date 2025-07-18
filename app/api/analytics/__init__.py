"""
Analytics API Package for Djobea AI
Contains all analytics-related endpoints organized by functionality
"""

from fastapi import APIRouter
from .main_dashboard import router as main_dashboard_router
from .kpis import router as kpis_router
from .performance import router as performance_router
from .services import router as services_router
from .geographic import router as geographic_router
from .insights import router as insights_router
from .leaderboard import router as leaderboard_router
from .export import router as export_router
from .share import router as share_router

# Create main analytics router
router = APIRouter()

# Include main dashboard router (root endpoint)
router.include_router(main_dashboard_router, tags=["analytics-main"])

# Include all analytics sub-routers
router.include_router(kpis_router, tags=["analytics-kpis"])
router.include_router(performance_router, tags=["analytics-performance"])
router.include_router(services_router, tags=["analytics-services"])
router.include_router(geographic_router, tags=["analytics-geographic"])
router.include_router(insights_router, tags=["analytics-insights"])
router.include_router(leaderboard_router, tags=["analytics-leaderboard"])
router.include_router(export_router, tags=["analytics-export"])
router.include_router(share_router, tags=["analytics-share"])