"""
Settings API endpoints for Djobea AI
Implements system configuration and settings management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import logging

from app.database import get_db
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/settings", tags=["Settings"])

# Pydantic models for settings
class NotificationSettings(BaseModel):
    emailEnabled: bool = True
    smsEnabled: bool = True
    whatsappEnabled: bool = True
    pushEnabled: bool = False
    alertThresholds: Dict[str, int] = {
        "highVolume": 100,
        "lowSuccessRate": 80,
        "responseTimeDelay": 300
    }
    notificationChannels: Dict[str, bool] = {
        "newRequest": True,
        "requestCompleted": True,
        "providerAssigned": True,
        "paymentReceived": True,
        "systemAlerts": True
    }

class PerformanceSettings(BaseModel):
    autoAssignmentEnabled: bool = True
    maxResponseTime: int = 300  # seconds
    maxConcurrentRequests: int = 100
    cacheEnabled: bool = True
    cacheDuration: int = 3600  # seconds
    rateLimiting: Dict[str, int] = {
        "requestsPerMinute": 60,
        "requestsPerHour": 1000
    }
    optimization: Dict[str, Any] = {
        "enableCompression": True,
        "enableCaching": True,
        "enableLoadBalancing": False
    }

# In-memory settings storage (in production, this would be in database)
_notification_settings = NotificationSettings()
_performance_settings = PerformanceSettings()

@router.get("/notifications")
async def get_notification_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/notifications - Get notification settings
    Retrieve current notification configuration
    """
    try:
        logger.info("Fetching notification settings")
        
        # In a real implementation, this would fetch from database
        settings = {
            "emailEnabled": _notification_settings.emailEnabled,
            "smsEnabled": _notification_settings.smsEnabled,
            "whatsappEnabled": _notification_settings.whatsappEnabled,
            "pushEnabled": _notification_settings.pushEnabled,
            "alertThresholds": _notification_settings.alertThresholds,
            "notificationChannels": _notification_settings.notificationChannels,
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "updatedBy": current_user.username if hasattr(current_user, 'username') else "admin"
        }
        
        logger.info("Notification settings retrieved successfully")
        return settings
        
    except Exception as e:
        logger.error(f"Error fetching notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des paramètres de notification")


@router.put("/notifications")
async def update_notification_settings(
    settings: NotificationSettings,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/notifications - Update notification settings
    Update notification configuration
    """
    try:
        logger.info("Updating notification settings")
        
        # Validate settings
        if settings.alertThresholds["highVolume"] < 1:
            raise HTTPException(
                status_code=400, 
                detail="Le seuil de volume élevé doit être supérieur à 0"
            )
        
        if settings.alertThresholds["lowSuccessRate"] < 0 or settings.alertThresholds["lowSuccessRate"] > 100:
            raise HTTPException(
                status_code=400, 
                detail="Le seuil de taux de succès doit être entre 0 et 100"
            )
        
        if settings.alertThresholds["responseTimeDelay"] < 30:
            raise HTTPException(
                status_code=400, 
                detail="Le délai de réponse doit être d'au moins 30 secondes"
            )
        
        # Update global settings (in production, save to database)
        global _notification_settings
        _notification_settings = settings
        
        # Create response
        response = {
            "message": "Paramètres de notification mis à jour avec succès",
            "settings": {
                "emailEnabled": settings.emailEnabled,
                "smsEnabled": settings.smsEnabled,
                "whatsappEnabled": settings.whatsappEnabled,
                "pushEnabled": settings.pushEnabled,
                "alertThresholds": settings.alertThresholds,
                "notificationChannels": settings.notificationChannels
            },
            "updatedAt": datetime.utcnow().isoformat() + "Z",
            "updatedBy": current_user.username if hasattr(current_user, 'username') else "admin"
        }
        
        logger.info("Notification settings updated successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour des paramètres de notification")


@router.get("/performance")
async def get_performance_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/performance - Get performance settings
    Retrieve current performance configuration
    """
    try:
        logger.info("Fetching performance settings")
        
        # In a real implementation, this would fetch from database
        settings = {
            "autoAssignmentEnabled": _performance_settings.autoAssignmentEnabled,
            "maxResponseTime": _performance_settings.maxResponseTime,
            "maxConcurrentRequests": _performance_settings.maxConcurrentRequests,
            "cacheEnabled": _performance_settings.cacheEnabled,
            "cacheDuration": _performance_settings.cacheDuration,
            "rateLimiting": _performance_settings.rateLimiting,
            "optimization": _performance_settings.optimization,
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "updatedBy": current_user.username if hasattr(current_user, 'username') else "admin"
        }
        
        logger.info("Performance settings retrieved successfully")
        return settings
        
    except Exception as e:
        logger.error(f"Error fetching performance settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des paramètres de performance")


@router.put("/performance")
async def update_performance_settings(
    settings: PerformanceSettings,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/performance - Update performance settings
    Update performance configuration
    """
    try:
        logger.info("Updating performance settings")
        
        # Validate settings
        if settings.maxResponseTime < 30:
            raise HTTPException(
                status_code=400, 
                detail="Le temps de réponse maximum doit être d'au moins 30 secondes"
            )
        
        if settings.maxConcurrentRequests < 1:
            raise HTTPException(
                status_code=400, 
                detail="Le nombre maximum de requêtes concurrentes doit être supérieur à 0"
            )
        
        if settings.cacheDuration < 60:
            raise HTTPException(
                status_code=400, 
                detail="La durée de cache doit être d'au moins 60 secondes"
            )
        
        if settings.rateLimiting["requestsPerMinute"] < 1:
            raise HTTPException(
                status_code=400, 
                detail="Le nombre de requêtes par minute doit être supérieur à 0"
            )
        
        if settings.rateLimiting["requestsPerHour"] < settings.rateLimiting["requestsPerMinute"]:
            raise HTTPException(
                status_code=400, 
                detail="Le nombre de requêtes par heure doit être supérieur au nombre par minute"
            )
        
        # Update global settings (in production, save to database)
        global _performance_settings
        _performance_settings = settings
        
        # Create response
        response = {
            "message": "Paramètres de performance mis à jour avec succès",
            "settings": {
                "autoAssignmentEnabled": settings.autoAssignmentEnabled,
                "maxResponseTime": settings.maxResponseTime,
                "maxConcurrentRequests": settings.maxConcurrentRequests,
                "cacheEnabled": settings.cacheEnabled,
                "cacheDuration": settings.cacheDuration,
                "rateLimiting": settings.rateLimiting,
                "optimization": settings.optimization
            },
            "updatedAt": datetime.utcnow().isoformat() + "Z",
            "updatedBy": current_user.username if hasattr(current_user, 'username') else "admin",
            "restartRequired": False,  # Indicate if system restart is needed
            "affectedServices": [
                "rate_limiting",
                "caching",
                "auto_assignment"
            ]
        }
        
        logger.info("Performance settings updated successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating performance settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour des paramètres de performance")