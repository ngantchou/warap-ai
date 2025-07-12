"""
Settings API endpoints for Djobea AI
Implements system configuration and settings management functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.database import get_db
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Settings"])

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
        # Mock system settings - in production these would come from a settings table
        settings = {
            "general": {
                "app_name": "Djobea AI",
                "app_version": "2.0.0",
                "default_language": "fr",
                "timezone": "Africa/Douala",
                "currency": "XAF",
                "commission_rate": 15.0,
                "max_providers_per_request": 5,
                "request_timeout_minutes": 10
            },
            "ai": {
                "primary_model": "claude-sonnet-4-20250514",
                "confidence_threshold": 0.7,
                "max_conversation_turns": 10,
                "enable_auto_escalation": True,
                "escalation_timeout_minutes": 15
            },
            "communication": {
                "whatsapp_enabled": True,
                "sms_enabled": True,
                "email_enabled": False,
                "notification_retry_attempts": 3,
                "notification_retry_delay_minutes": 2
            },
            "business": {
                "service_zones": ["Bonamoussadi", "Akwa", "Douala", "Bonaberi"],
                "operating_hours": {
                    "start": "07:00",
                    "end": "20:00",
                    "timezone": "Africa/Douala"
                },
                "emergency_services_24h": True,
                "price_ranges": {
                    "plomberie": {"min": 5000, "max": 15000},
                    "électricité": {"min": 3000, "max": 10000},
                    "électroménager": {"min": 2000, "max": 8000}
                }
            }
        }
        
        return {
            "settings": settings,
            "last_updated": datetime.utcnow().isoformat(),
            "updated_by": getattr(current_user, "username", "system")
        }
    except Exception as e:
        logger.error(f"Error retrieving system settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des paramètres système")


@router.put("/system")
async def update_system_settings(
    settings_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/system - Update system settings
    Update system-wide configuration settings
    """
    try:
        # Validate required sections
        required_sections = ["general", "ai", "communication", "business"]
        for section in required_sections:
            if section not in settings_data:
                raise HTTPException(status_code=422, detail=f"Section '{section}' manquante")
        
        # In production, this would update a settings table
        # For now, return success with the provided data
        
        updated_settings = settings_data
        updated_settings["last_updated"] = datetime.utcnow().isoformat()
        updated_settings["updated_by"] = getattr(current_user, "username", "admin")
        
        logger.info(f"System settings updated by {getattr(current_user, 'username', 'admin')}")
        
        return {
            "success": True,
            "message": "Paramètres système mis à jour avec succès",
            "settings": updated_settings
        }
    except Exception as e:
        logger.error(f"Error updating system settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour des paramètres")


@router.get("/notifications")
async def get_notification_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/notifications - Get notification settings
    Retrieve notification configuration and templates
    """
    try:
        notification_settings = {
            "channels": {
                "whatsapp": {
                    "enabled": True,
                    "priority": 1,
                    "retry_attempts": 3,
                    "retry_delay_minutes": 2
                },
                "sms": {
                    "enabled": True,
                    "priority": 2,
                    "retry_attempts": 2,
                    "retry_delay_minutes": 5
                },
                "email": {
                    "enabled": False,
                    "priority": 3,
                    "retry_attempts": 1,
                    "retry_delay_minutes": 10
                }
            },
            "templates": {
                "request_confirmation": {
                    "whatsapp": "✅ Votre demande de {service_type} a été reçue. Référence: {request_id}. Nous recherchons un prestataire dans votre zone.",
                    "sms": "Demande {request_id} reçue pour {service_type}. Recherche de prestataire en cours."
                },
                "provider_assigned": {
                    "whatsapp": "🔧 Prestataire trouvé ! {provider_name} va vous contacter sous peu. Note: {rating}/5 ⭐",
                    "sms": "Prestataire {provider_name} assigné. Il vous contactera bientôt."
                },
                "service_completed": {
                    "whatsapp": "✅ Service terminé ! Coût: {cost} FCFA. Merci d'évaluer {provider_name} /5 ⭐",
                    "sms": "Service terminé. Coût: {cost} FCFA. Merci d'évaluer le prestataire."
                }
            },
            "timing": {
                "confirmation_delay_seconds": 30,
                "provider_search_timeout_minutes": 10,
                "status_update_interval_minutes": 5,
                "quiet_hours": {
                    "start": "22:00",
                    "end": "07:00",
                    "timezone": "Africa/Douala"
                }
            }
        }
        
        return {
            "notification_settings": notification_settings,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des paramètres de notification")


@router.put("/notifications")
async def update_notification_settings(
    notification_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/notifications - Update notification settings
    Update notification configuration and templates
    """
    try:
        # Validate notification channels
        if "channels" in notification_data:
            valid_channels = ["whatsapp", "sms", "email"]
            for channel in notification_data["channels"]:
                if channel not in valid_channels:
                    raise HTTPException(status_code=422, detail=f"Canal de notification invalide: {channel}")
        
        # In production, this would update notification settings in database
        updated_settings = notification_data
        updated_settings["last_updated"] = datetime.utcnow().isoformat()
        updated_settings["updated_by"] = getattr(current_user, "username", "admin")
        
        logger.info(f"Notification settings updated by {getattr(current_user, 'username', 'admin')}")
        
        return {
            "success": True,
            "message": "Paramètres de notification mis à jour avec succès",
            "settings": updated_settings
        }
    except Exception as e:
        logger.error(f"Error updating notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour des paramètres de notification")


@router.get("/pricing")
async def get_pricing_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/pricing - Get pricing settings
    Retrieve pricing configuration and service rates
    """
    try:
        pricing_settings = {
            "commission": {
                "rate_percentage": 15.0,
                "minimum_amount_xaf": 500,
                "maximum_amount_xaf": 5000,
                "calculation_method": "percentage"
            },
            "service_rates": {
                "plomberie": {
                    "min_price_xaf": 5000,
                    "max_price_xaf": 15000,
                    "base_rate_xaf": 7500,
                    "currency": "XAF",
                    "urgency_multiplier": 1.5
                },
                "électricité": {
                    "min_price_xaf": 3000,
                    "max_price_xaf": 10000,
                    "base_rate_xaf": 5000,
                    "currency": "XAF",
                    "urgency_multiplier": 1.5
                },
                "électroménager": {
                    "min_price_xaf": 2000,
                    "max_price_xaf": 8000,
                    "base_rate_xaf": 4000,
                    "currency": "XAF",
                    "urgency_multiplier": 1.3
                }
            },
            "payment": {
                "methods": ["Mobile Money", "Cash", "Bank Transfer"],
                "default_method": "Mobile Money",
                "payment_timeout_hours": 24,
                "auto_refund_enabled": True,
                "refund_timeout_hours": 72
            },
            "discounts": {
                "first_time_user": 10.0,
                "loyalty_program": {
                    "enabled": True,
                    "tiers": {
                        "bronze": {"min_orders": 5, "discount": 5.0},
                        "silver": {"min_orders": 15, "discount": 10.0},
                        "gold": {"min_orders": 30, "discount": 15.0}
                    }
                }
            }
        }
        
        return {
            "pricing_settings": pricing_settings,
            "currency": "XAF",
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving pricing settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des paramètres de tarification")


@router.put("/pricing")
async def update_pricing_settings(
    pricing_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/pricing - Update pricing settings
    Update pricing configuration and service rates
    """
    try:
        # Validate pricing data
        if "commission" in pricing_data:
            commission = pricing_data["commission"]
            if "rate_percentage" in commission:
                rate = commission["rate_percentage"]
                if not (0 <= rate <= 50):
                    raise HTTPException(status_code=422, detail="Le taux de commission doit être entre 0 et 50%")
        
        if "service_rates" in pricing_data:
            for service, rates in pricing_data["service_rates"].items():
                if "min_price_xaf" in rates and "max_price_xaf" in rates:
                    if rates["min_price_xaf"] >= rates["max_price_xaf"]:
                        raise HTTPException(status_code=422, detail=f"Prix minimum supérieur au prix maximum pour {service}")
        
        # In production, this would update pricing settings in database
        updated_settings = pricing_data
        updated_settings["last_updated"] = datetime.utcnow().isoformat()
        updated_settings["updated_by"] = getattr(current_user, "username", "admin")
        
        logger.info(f"Pricing settings updated by {getattr(current_user, 'username', 'admin')}")
        
        return {
            "success": True,
            "message": "Paramètres de tarification mis à jour avec succès",
            "settings": updated_settings
        }
    except Exception as e:
        logger.error(f"Error updating pricing settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour des paramètres de tarification")


@router.get("/integrations")
async def get_integration_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/settings/integrations - Get integration settings
    Retrieve external service integrations configuration
    """
    try:
        integration_settings = {
            "ai_services": {
                "claude": {
                    "enabled": True,
                    "model": "claude-sonnet-4-20250514",
                    "api_version": "2024-06-01",
                    "rate_limit": 1000,
                    "timeout_seconds": 30
                },
                "openai": {
                    "enabled": True,
                    "model": "gpt-4-turbo",
                    "api_version": "v1",
                    "rate_limit": 500,
                    "timeout_seconds": 30
                },
                "gemini": {
                    "enabled": True,
                    "model": "gemini-pro",
                    "api_version": "v1",
                    "rate_limit": 300,
                    "timeout_seconds": 30
                }
            },
            "communication": {
                "twilio": {
                    "enabled": True,
                    "whatsapp_enabled": True,
                    "sms_enabled": True,
                    "webhook_url": "/webhook/whatsapp",
                    "rate_limit": 200
                }
            },
            "payment": {
                "monetbil": {
                    "enabled": True,
                    "service_key": "configured",
                    "service_secret": "configured",
                    "webhook_url": "/webhook/monetbil",
                    "supported_operators": ["MTN", "Orange", "Express Union"]
                }
            },
            "analytics": {
                "google_analytics": {
                    "enabled": False,
                    "tracking_id": "",
                    "enhanced_ecommerce": False
                },
                "internal_analytics": {
                    "enabled": True,
                    "retention_days": 365,
                    "real_time_updates": True
                }
            }
        }
        
        return {
            "integration_settings": integration_settings,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving integration settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des paramètres d'intégration")


@router.put("/integrations")
async def update_integration_settings(
    integration_data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/settings/integrations - Update integration settings
    Update external service integrations configuration
    """
    try:
        # Validate integration data
        if "ai_services" in integration_data:
            valid_ai_services = ["claude", "openai", "gemini"]
            for service in integration_data["ai_services"]:
                if service not in valid_ai_services:
                    raise HTTPException(status_code=422, detail=f"Service IA invalide: {service}")
        
        # In production, this would update integration settings in database
        updated_settings = integration_data
        updated_settings["last_updated"] = datetime.utcnow().isoformat()
        updated_settings["updated_by"] = getattr(current_user, "username", "admin")
        
        logger.info(f"Integration settings updated by {getattr(current_user, 'username', 'admin')}")
        
        return {
            "success": True,
            "message": "Paramètres d'intégration mis à jour avec succès",
            "settings": updated_settings
        }
    except Exception as e:
        logger.error(f"Error updating integration settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour des paramètres d'intégration")