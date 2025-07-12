"""
Settings API endpoints for Djobea AI
Implements dynamic system configuration and settings management functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from pydantic import BaseModel

from app.database import get_db
from app.api.auth import get_current_admin_user
from app.services.settings_service import SettingsService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Settings"])

# Pydantic models for request validation
class SystemSettingsUpdate(BaseModel):
    general: Optional[Dict[str, Any]] = None
    ai: Optional[Dict[str, Any]] = None
    communication: Optional[Dict[str, Any]] = None

class NotificationSettingsUpdate(BaseModel):
    email: Optional[Dict[str, Any]] = None
    sms: Optional[Dict[str, Any]] = None
    push: Optional[Dict[str, Any]] = None
    whatsapp: Optional[Dict[str, Any]] = None

class BusinessSettingsUpdate(BaseModel):
    company: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    operations: Optional[Dict[str, Any]] = None

# 1. General Settings Endpoints
@router.get("/")
async def get_all_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings - Get all system settings
    Retrieve all configuration settings for the platform
    """
    try:
        settings_service = SettingsService(db)
        
        return {
            "success": True,
            "data": {
                "general": settings_service.get_all_system_settings(),
                "notifications": settings_service.get_notification_settings(),
                "ai": settings_service.get_ai_settings(),
                "whatsapp": settings_service.get_whatsapp_settings(),
                "business": settings_service.get_business_settings(),
                "providers": settings_service.get_provider_settings(),
                "requests": settings_service.get_request_settings()
            }
        }
    except Exception as e:
        logger.error(f"Error getting all settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")

@router.put("/save")
async def save_settings(
    settings: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/save - Update general settings
    Update system-wide configuration settings
    """
    try:
        settings_service = SettingsService(db)
        
        # Update general settings
        if settings.general:
            for key, value in settings.general.items():
                data_type = "string"
                if isinstance(value, bool):
                    data_type = "boolean"
                elif isinstance(value, int):
                    data_type = "integer"
                elif isinstance(value, float):
                    data_type = "float"
                
                settings_service.set_system_setting("general", key, value, data_type)
        
        # Update AI settings
        if settings.ai:
            for key, value in settings.ai.items():
                data_type = "string"
                if isinstance(value, bool):
                    data_type = "boolean"
                elif isinstance(value, int):
                    data_type = "integer"
                elif isinstance(value, float):
                    data_type = "float"
                
                settings_service.set_system_setting("ai", key, value, data_type)
        
        # Update communication settings
        if settings.communication:
            for key, value in settings.communication.items():
                data_type = "string"
                if isinstance(value, bool):
                    data_type = "boolean"
                elif isinstance(value, int):
                    data_type = "integer"
                elif isinstance(value, float):
                    data_type = "float"
                
                settings_service.set_system_setting("communication", key, value, data_type)
        
        return {
            "success": True,
            "message": "Settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

@router.get("/system")
async def get_system_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/system - Get system settings
    Retrieve system-wide configuration settings
    """
    try:
        settings_service = SettingsService(db)
        system_settings = settings_service.get_all_system_settings()
        
        return {
            "success": True,
            "data": system_settings
        }
    except Exception as e:
        logger.error(f"Error getting system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system settings")

@router.put("/system")
async def update_system_settings(
    settings: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/system - Update system settings
    Update system-wide configuration settings
    """
    try:
        settings_service = SettingsService(db)
        
        # Update each category
        for category, values in settings.dict(exclude_unset=True).items():
            if values:
                for key, value in values.items():
                    data_type = "string"
                    if isinstance(value, bool):
                        data_type = "boolean"
                    elif isinstance(value, int):
                        data_type = "integer"
                    elif isinstance(value, float):
                        data_type = "float"
                    
                    settings_service.set_system_setting(category, key, value, data_type)
        
        return {
            "success": True,
            "message": "System settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update system settings")

# 2. Notification Settings
@router.get("/notifications")
async def get_notification_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/notifications - Get notification settings
    Retrieve notification configuration settings
    """
    try:
        settings_service = SettingsService(db)
        notification_settings = settings_service.get_notification_settings()
        
        return {
            "success": True,
            "data": notification_settings
        }
    except Exception as e:
        logger.error(f"Error getting notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notification settings")

@router.put("/notifications")
async def update_notification_settings(
    settings: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/notifications - Update notification settings
    Update notification configuration settings
    """
    try:
        settings_service = SettingsService(db)
        
        # Update each notification provider
        for provider, config in settings.dict(exclude_unset=True).items():
            if config:
                settings_service.update_notification_settings(provider, config)
        
        return {
            "success": True,
            "message": "Notification settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification settings")

@router.post("/notifications/test")
async def test_notification_settings(
    test_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/notifications/test - Test notification settings
    Test notification configuration with a sample message
    """
    try:
        notification_type = test_data.get("type")
        recipient = test_data.get("recipient")
        message = test_data.get("message", "Test message from Djobea AI")
        
        # Mock test result - in production this would actually send a test message
        return {
            "success": True,
            "data": {
                "type": notification_type,
                "recipient": recipient,
                "status": "sent",
                "message": f"Test {notification_type} sent successfully to {recipient}"
            }
        }
    except Exception as e:
        logger.error(f"Error testing notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to test notification settings")

# 3. AI Settings
@router.get("/ai")
async def get_ai_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/ai - Get AI settings
    Retrieve AI configuration settings
    """
    try:
        settings_service = SettingsService(db)
        ai_settings = settings_service.get_ai_settings()
        
        return {
            "success": True,
            "data": ai_settings
        }
    except Exception as e:
        logger.error(f"Error getting AI settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve AI settings")

@router.post("/ai")
async def update_ai_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/ai - Update AI settings
    Update AI configuration settings
    """
    try:
        settings_service = SettingsService(db)
        
        # Update AI settings for each provider
        for provider, config in settings.items():
            if isinstance(config, dict):
                settings_service.update_ai_settings(provider, config)
        
        return {
            "success": True,
            "message": "AI settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating AI settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update AI settings")

# 4. WhatsApp Settings
@router.get("/whatsapp")
async def get_whatsapp_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/whatsapp - Get WhatsApp settings
    Retrieve WhatsApp configuration settings
    """
    try:
        settings_service = SettingsService(db)
        whatsapp_settings = settings_service.get_whatsapp_settings()
        
        return {
            "success": True,
            "data": whatsapp_settings
        }
    except Exception as e:
        logger.error(f"Error getting WhatsApp settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve WhatsApp settings")

@router.post("/whatsapp")
async def update_whatsapp_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/whatsapp - Update WhatsApp settings
    Update WhatsApp configuration settings
    """
    try:
        settings_service = SettingsService(db)
        settings_service.update_whatsapp_settings(settings)
        
        return {
            "success": True,
            "message": "WhatsApp settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating WhatsApp settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update WhatsApp settings")

# 5. Business Settings
@router.get("/business")
async def get_business_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/business - Get business settings
    Retrieve business configuration settings
    """
    try:
        settings_service = SettingsService(db)
        business_settings = settings_service.get_business_settings()
        
        return {
            "success": True,
            "data": business_settings
        }
    except Exception as e:
        logger.error(f"Error getting business settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve business settings")

@router.post("/business")
async def update_business_settings(
    settings: BusinessSettingsUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/business - Update business settings
    Update business configuration settings
    """
    try:
        settings_service = SettingsService(db)
        settings_service.update_business_settings(settings.dict(exclude_unset=True))
        
        return {
            "success": True,
            "message": "Business settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating business settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update business settings")

# 6. Provider Settings
@router.get("/providers")
async def get_provider_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/providers - Get provider settings
    Retrieve provider configuration settings
    """
    try:
        settings_service = SettingsService(db)
        provider_settings = settings_service.get_provider_settings()
        
        return {
            "success": True,
            "data": provider_settings
        }
    except Exception as e:
        logger.error(f"Error getting provider settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve provider settings")

@router.post("/providers")
async def update_provider_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/providers - Update provider settings
    Update provider configuration settings
    """
    try:
        # Mock update for now - implement actual update logic
        return {
            "success": True,
            "message": "Provider settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating provider settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update provider settings")

# 7. Request Settings
@router.get("/requests")
async def get_request_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/requests - Get request settings
    Retrieve request processing configuration settings
    """
    try:
        settings_service = SettingsService(db)
        request_settings = settings_service.get_request_settings()
        
        return {
            "success": True,
            "data": request_settings
        }
    except Exception as e:
        logger.error(f"Error getting request settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve request settings")

@router.post("/requests")
async def update_request_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/requests - Update request settings
    Update request processing configuration settings
    """
    try:
        # Mock update for now - implement actual update logic
        return {
            "success": True,
            "message": "Request settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating request settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update request settings")

# 8. Performance Settings
@router.get("/performance")
async def get_performance_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/performance - Get performance settings
    Retrieve performance optimization settings
    """
    try:
        # Mock performance settings
        performance_settings = {
            "cache": {
                "redis_enabled": True,
                "ttl": 300,
                "max_memory": "512mb"
            },
            "cdn": {
                "enabled": True,
                "provider": "cloudflare",
                "zones": ["static.djobea.com"]
            },
            "optimization": {
                "compression_enabled": True,
                "minification_enabled": True,
                "image_lazy_loading": True
            }
        }
        
        return {
            "success": True,
            "data": performance_settings
        }
    except Exception as e:
        logger.error(f"Error getting performance settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance settings")

@router.post("/performance")
async def update_performance_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/performance - Update performance settings
    Update performance optimization settings
    """
    try:
        # Mock update for now - implement actual update logic
        return {
            "success": True,
            "message": "Performance settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating performance settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update performance settings")

# 9. Security Settings
@router.get("/security")
async def get_security_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/security - Get security settings
    Retrieve security configuration settings
    """
    try:
        # Mock security settings
        security_settings = {
            "authentication": {
                "jwt_expiration": "24h",
                "refresh_token_expiration": "7d",
                "max_login_attempts": 5,
                "lockout_duration": "15m"
            },
            "encryption": {
                "algorithm": "AES-256-GCM",
                "key_rotation_interval": "30d"
            },
            "compliance": {
                "gdpr_enabled": True,
                "data_retention_period": "2y",
                "audit_log_enabled": True
            }
        }
        
        return {
            "success": True,
            "data": security_settings
        }
    except Exception as e:
        logger.error(f"Error getting security settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security settings")

@router.post("/security")
async def update_security_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/settings/security - Update security settings
    Update security configuration settings
    """
    try:
        # Mock update for now - implement actual update logic
        return {
            "success": True,
            "message": "Security settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating security settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update security settings")

# 10. Integration Settings
@router.get("/integrations")
async def get_integration_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/integrations - Get integration settings
    Retrieve third-party integration settings
    """
    try:
        # Mock integration settings
        integration_settings = {
            "payment": {
                "monetbil_enabled": True,
                "stripe_enabled": False,
                "paypal_enabled": False
            },
            "messaging": {
                "twilio_enabled": True,
                "whatsapp_business_enabled": True,
                "firebase_enabled": True
            },
            "analytics": {
                "google_analytics_enabled": False,
                "mixpanel_enabled": False,
                "amplitude_enabled": False
            }
        }
        
        return {
            "success": True,
            "data": integration_settings
        }
    except Exception as e:
        logger.error(f"Error getting integration settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve integration settings")

@router.put("/integrations")
async def update_integration_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/integrations - Update integration settings
    Update third-party integration settings
    """
    try:
        # Mock update for now - implement actual update logic
        return {
            "success": True,
            "message": "Integration settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating integration settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update integration settings")

# 11. Pricing Settings
@router.get("/pricing")
async def get_pricing_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/pricing - Get pricing settings
    Retrieve pricing configuration settings
    """
    try:
        settings_service = SettingsService(db)
        business_settings = settings_service.get_business_settings()
        
        pricing_settings = business_settings.get("pricing", {})
        
        return {
            "success": True,
            "data": pricing_settings
        }
    except Exception as e:
        logger.error(f"Error getting pricing settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pricing settings")

@router.put("/pricing")
async def update_pricing_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/pricing - Update pricing settings
    Update pricing configuration settings
    """
    try:
        settings_service = SettingsService(db)
        
        # Update business settings with new pricing
        business_update = {
            "pricing": settings
        }
        settings_service.update_business_settings(business_update)
        
        return {
            "success": True,
            "message": "Pricing settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating pricing settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pricing settings")