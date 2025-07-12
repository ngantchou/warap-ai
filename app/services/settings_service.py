"""
Dynamic Settings Service for Djobea AI
Service for managing all system parameters dynamically
"""

import json
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.settings_models import (
    SystemSettings, NotificationSettings, SecuritySettings, PerformanceSettings,
    AISettings, WhatsAppSettings, BusinessSettings, ProviderSettings,
    RequestSettings, AdminSettings
)

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing dynamic settings"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # System Settings
    def get_system_setting(self, category: str, key: str) -> Optional[Any]:
        """Get a system setting value"""
        try:
            setting = self.db.query(SystemSettings).filter(
                and_(SystemSettings.category == category, SystemSettings.key == key)
            ).first()
            
            if not setting:
                return None
            
            return self._convert_value(setting.value, setting.data_type)
        except Exception as e:
            logger.error(f"Error getting system setting {category}.{key}: {e}")
            return None
    
    def set_system_setting(self, category: str, key: str, value: Any, data_type: str = "string", description: str = ""):
        """Set a system setting value"""
        try:
            setting = self.db.query(SystemSettings).filter(
                and_(SystemSettings.category == category, SystemSettings.key == key)
            ).first()
            
            if setting:
                setting.value = str(value)
                setting.data_type = data_type
                setting.description = description
            else:
                setting = SystemSettings(
                    category=category,
                    key=key,
                    value=str(value),
                    data_type=data_type,
                    description=description
                )
                self.db.add(setting)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting system setting {category}.{key}: {e}")
            self.db.rollback()
            return False
    
    def get_all_system_settings(self) -> Dict[str, Dict[str, Any]]:
        """Get all system settings grouped by category"""
        try:
            settings = self.db.query(SystemSettings).all()
            result = {}
            
            for setting in settings:
                if setting.category not in result:
                    result[setting.category] = {}
                
                result[setting.category][setting.key] = self._convert_value(
                    setting.value, setting.data_type
                )
            
            return result
        except Exception as e:
            logger.error(f"Error getting all system settings: {e}")
            return {}
    
    # Notification Settings
    def get_notification_settings(self) -> Dict[str, Any]:
        """Get all notification settings"""
        try:
            settings = self.db.query(NotificationSettings).all()
            result = {}
            
            for setting in settings:
                result[setting.provider] = {
                    "enabled": setting.enabled,
                    "config": setting.config,
                    "priority": setting.priority,
                    "retry_attempts": setting.retry_attempts,
                    "retry_delay": setting.retry_delay
                }
            
            return result
        except Exception as e:
            logger.error(f"Error getting notification settings: {e}")
            return {}
    
    def update_notification_settings(self, provider: str, config: Dict[str, Any]) -> bool:
        """Update notification settings for a provider"""
        try:
            setting = self.db.query(NotificationSettings).filter(
                NotificationSettings.provider == provider
            ).first()
            
            if setting:
                setting.enabled = config.get("enabled", setting.enabled)
                setting.config = config.get("config", setting.config)
                setting.priority = config.get("priority", setting.priority)
                setting.retry_attempts = config.get("retry_attempts", setting.retry_attempts)
                setting.retry_delay = config.get("retry_delay", setting.retry_delay)
            else:
                setting = NotificationSettings(
                    provider=provider,
                    enabled=config.get("enabled", True),
                    config=config.get("config", {}),
                    priority=config.get("priority", 1),
                    retry_attempts=config.get("retry_attempts", 3),
                    retry_delay=config.get("retry_delay", 300)
                )
                self.db.add(setting)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating notification settings for {provider}: {e}")
            self.db.rollback()
            return False
    
    # AI Settings
    def get_ai_settings(self) -> Dict[str, Any]:
        """Get all AI settings"""
        try:
            settings = self.db.query(AISettings).all()
            result = {}
            
            for setting in settings:
                result[setting.provider] = {
                    "model_name": setting.model_name,
                    "temperature": setting.temperature,
                    "max_tokens": setting.max_tokens,
                    "enabled": setting.enabled,
                    "priority": setting.priority,
                    "rate_limit": setting.rate_limit,
                    "config": setting.config
                }
            
            return result
        except Exception as e:
            logger.error(f"Error getting AI settings: {e}")
            return {}
    
    def update_ai_settings(self, provider: str, config: Dict[str, Any]) -> bool:
        """Update AI settings for a provider"""
        try:
            setting = self.db.query(AISettings).filter(
                AISettings.provider == provider
            ).first()
            
            if setting:
                setting.model_name = config.get("model_name", setting.model_name)
                setting.temperature = config.get("temperature", setting.temperature)
                setting.max_tokens = config.get("max_tokens", setting.max_tokens)
                setting.enabled = config.get("enabled", setting.enabled)
                setting.priority = config.get("priority", setting.priority)
                setting.rate_limit = config.get("rate_limit", setting.rate_limit)
                setting.config = config.get("config", setting.config)
            else:
                setting = AISettings(
                    provider=provider,
                    model_name=config.get("model_name", "gpt-4"),
                    temperature=config.get("temperature", 0.7),
                    max_tokens=config.get("max_tokens", 2048),
                    enabled=config.get("enabled", True),
                    priority=config.get("priority", 1),
                    rate_limit=config.get("rate_limit", 100),
                    config=config.get("config", {})
                )
                self.db.add(setting)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating AI settings for {provider}: {e}")
            self.db.rollback()
            return False
    
    # WhatsApp Settings
    def get_whatsapp_settings(self) -> Dict[str, Any]:
        """Get WhatsApp settings"""
        try:
            setting = self.db.query(WhatsAppSettings).first()
            if not setting:
                return {}
            
            return {
                "enabled": setting.enabled,
                "business_account_id": setting.business_account_id,
                "phone_number_id": setting.phone_number_id,
                "access_token": setting.access_token,
                "webhook_url": setting.webhook_url,
                "verify_token": setting.verify_token,
                "rate_limit": setting.rate_limit,
                "templates": setting.templates
            }
        except Exception as e:
            logger.error(f"Error getting WhatsApp settings: {e}")
            return {}
    
    def update_whatsapp_settings(self, config: Dict[str, Any]) -> bool:
        """Update WhatsApp settings"""
        try:
            setting = self.db.query(WhatsAppSettings).first()
            
            if setting:
                setting.enabled = config.get("enabled", setting.enabled)
                setting.business_account_id = config.get("business_account_id", setting.business_account_id)
                setting.phone_number_id = config.get("phone_number_id", setting.phone_number_id)
                setting.access_token = config.get("access_token", setting.access_token)
                setting.webhook_url = config.get("webhook_url", setting.webhook_url)
                setting.verify_token = config.get("verify_token", setting.verify_token)
                setting.rate_limit = config.get("rate_limit", setting.rate_limit)
                setting.templates = config.get("templates", setting.templates)
            else:
                setting = WhatsAppSettings(
                    enabled=config.get("enabled", True),
                    business_account_id=config.get("business_account_id"),
                    phone_number_id=config.get("phone_number_id"),
                    access_token=config.get("access_token"),
                    webhook_url=config.get("webhook_url"),
                    verify_token=config.get("verify_token"),
                    rate_limit=config.get("rate_limit", 1000),
                    templates=config.get("templates", [])
                )
                self.db.add(setting)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating WhatsApp settings: {e}")
            self.db.rollback()
            return False
    
    # Business Settings
    def get_business_settings(self) -> Dict[str, Any]:
        """Get business settings"""
        try:
            setting = self.db.query(BusinessSettings).first()
            if not setting:
                return {}
            
            return {
                "company": {
                    "name": setting.company_name,
                    "address": setting.address,
                    "phone": setting.phone,
                    "email": setting.email,
                    "website": setting.website
                },
                "pricing": {
                    "currency": setting.currency,
                    "tax_rate": setting.tax_rate,
                    "commission_rate": setting.commission_rate,
                    "minimum_order": setting.minimum_order
                },
                "operations": {
                    "working_hours": {
                        "start": setting.working_hours_start,
                        "end": setting.working_hours_end
                    },
                    "working_days": setting.working_days,
                    "emergency_available": setting.emergency_available
                }
            }
        except Exception as e:
            logger.error(f"Error getting business settings: {e}")
            return {}
    
    def update_business_settings(self, config: Dict[str, Any]) -> bool:
        """Update business settings"""
        try:
            setting = self.db.query(BusinessSettings).first()
            
            company = config.get("company", {})
            pricing = config.get("pricing", {})
            operations = config.get("operations", {})
            
            if setting:
                # Update company info
                setting.company_name = company.get("name", setting.company_name)
                setting.address = company.get("address", setting.address)
                setting.phone = company.get("phone", setting.phone)
                setting.email = company.get("email", setting.email)
                setting.website = company.get("website", setting.website)
                
                # Update pricing
                setting.currency = pricing.get("currency", setting.currency)
                setting.tax_rate = pricing.get("tax_rate", setting.tax_rate)
                setting.commission_rate = pricing.get("commission_rate", setting.commission_rate)
                setting.minimum_order = pricing.get("minimum_order", setting.minimum_order)
                
                # Update operations
                working_hours = operations.get("working_hours", {})
                setting.working_hours_start = working_hours.get("start", setting.working_hours_start)
                setting.working_hours_end = working_hours.get("end", setting.working_hours_end)
                setting.working_days = operations.get("working_days", setting.working_days)
                setting.emergency_available = operations.get("emergency_available", setting.emergency_available)
            else:
                setting = BusinessSettings(
                    company_name=company.get("name", "Djobea SARL"),
                    address=company.get("address", "Douala, Cameroun"),
                    phone=company.get("phone", "+237 6 XX XX XX XX"),
                    email=company.get("email", "contact@djobea.com"),
                    website=company.get("website", "https://djobea.com"),
                    currency=pricing.get("currency", "XAF"),
                    tax_rate=pricing.get("tax_rate", 19.25),
                    commission_rate=pricing.get("commission_rate", 15.0),
                    minimum_order=pricing.get("minimum_order", 5000),
                    working_hours_start=operations.get("working_hours", {}).get("start", "08:00"),
                    working_hours_end=operations.get("working_hours", {}).get("end", "18:00"),
                    working_days=operations.get("working_days", ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]),
                    emergency_available=operations.get("emergency_available", True)
                )
                self.db.add(setting)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating business settings: {e}")
            self.db.rollback()
            return False
    
    # Provider Settings
    def get_provider_settings(self) -> Dict[str, Any]:
        """Get provider settings"""
        try:
            setting = self.db.query(ProviderSettings).first()
            if not setting:
                return {}
            
            return {
                "validation": {
                    "require_documents": setting.require_documents,
                    "background_check": setting.background_check,
                    "minimum_rating": setting.minimum_rating,
                    "probation_period": setting.probation_period
                },
                "commission": {
                    "rate": setting.commission_rate,
                    "payment_schedule": setting.payment_schedule,
                    "minimum_payout": setting.minimum_payout
                },
                "rating": {
                    "minimum_reviews": setting.minimum_reviews,
                    "auto_suspend_threshold": setting.auto_suspend_threshold,
                    "improvement_period": setting.improvement_period
                }
            }
        except Exception as e:
            logger.error(f"Error getting provider settings: {e}")
            return {}
    
    # Request Settings
    def get_request_settings(self) -> Dict[str, Any]:
        """Get request settings"""
        try:
            setting = self.db.query(RequestSettings).first()
            if not setting:
                return {}
            
            return {
                "processing": {
                    "auto_assignment": setting.auto_assignment,
                    "assignment_timeout": setting.assignment_timeout,
                    "max_retries": setting.max_retries,
                    "priority_levels": setting.priority_levels
                },
                "matching": {
                    "algorithm": setting.matching_algorithm,
                    "max_distance": setting.max_distance,
                    "rating_weight": setting.rating_weight,
                    "distance_weight": setting.distance_weight
                },
                "validation": {
                    "require_phone": setting.require_phone,
                    "require_email": setting.require_email,
                    "minimum_description": setting.minimum_description
                }
            }
        except Exception as e:
            logger.error(f"Error getting request settings: {e}")
            return {}
    
    def _convert_value(self, value: str, data_type: str) -> Any:
        """Convert string value to appropriate type"""
        try:
            if data_type == "boolean":
                return value.lower() in ("true", "1", "yes", "on")
            elif data_type == "integer":
                return int(value)
            elif data_type == "float":
                return float(value)
            elif data_type == "json":
                return json.loads(value)
            else:
                return value
        except Exception as e:
            logger.error(f"Error converting value {value} to {data_type}: {e}")
            return value
    
    def seed_default_settings(self):
        """Seed default settings for first-time setup"""
        try:
            # System settings
            default_system_settings = [
                ("general", "app_name", "Djobea AI", "string", "Application name"),
                ("general", "timezone", "Africa/Douala", "string", "Default timezone"),
                ("general", "language", "fr", "string", "Default language"),
                ("general", "currency", "XAF", "string", "Default currency"),
                ("general", "commission_rate", "15.0", "float", "Default commission rate"),
                ("general", "max_providers_per_request", "5", "integer", "Maximum providers per request"),
                ("general", "request_timeout_minutes", "10", "integer", "Request timeout in minutes"),
                ("ai", "primary_model", "claude-sonnet-4-20250514", "string", "Primary AI model"),
                ("ai", "confidence_threshold", "0.7", "float", "AI confidence threshold"),
                ("ai", "max_conversation_turns", "10", "integer", "Maximum conversation turns"),
                ("ai", "enable_auto_escalation", "true", "boolean", "Enable automatic escalation"),
                ("ai", "escalation_timeout_minutes", "15", "integer", "Escalation timeout in minutes"),
                ("communication", "whatsapp_enabled", "true", "boolean", "Enable WhatsApp"),
                ("communication", "sms_enabled", "true", "boolean", "Enable SMS"),
                ("communication", "email_enabled", "false", "boolean", "Enable Email"),
                ("communication", "notification_retry_attempts", "3", "integer", "Notification retry attempts"),
                ("communication", "notification_retry_delay_minutes", "2", "integer", "Notification retry delay")
            ]
            
            for category, key, value, data_type, description in default_system_settings:
                existing = self.db.query(SystemSettings).filter(
                    and_(SystemSettings.category == category, SystemSettings.key == key)
                ).first()
                
                if not existing:
                    setting = SystemSettings(
                        category=category,
                        key=key,
                        value=value,
                        data_type=data_type,
                        description=description
                    )
                    self.db.add(setting)
            
            # Default business settings
            business_setting = self.db.query(BusinessSettings).first()
            if not business_setting:
                business_setting = BusinessSettings(
                    company_name="Djobea SARL",
                    address="Douala, Cameroun",
                    phone="+237 6 XX XX XX XX",
                    email="contact@djobea.com",
                    website="https://djobea.com",
                    currency="XAF",
                    tax_rate=19.25,
                    commission_rate=15.0,
                    minimum_order=5000,
                    working_hours_start="08:00",
                    working_hours_end="18:00",
                    working_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
                    emergency_available=True
                )
                self.db.add(business_setting)
            
            # Default provider settings
            provider_setting = self.db.query(ProviderSettings).first()
            if not provider_setting:
                provider_setting = ProviderSettings(
                    require_documents=True,
                    background_check=True,
                    minimum_rating=3.0,
                    probation_period=30,
                    commission_rate=15.0,
                    payment_schedule="weekly",
                    minimum_payout=10000,
                    minimum_reviews=5,
                    auto_suspend_threshold=2.0,
                    improvement_period=14
                )
                self.db.add(provider_setting)
            
            # Default request settings
            request_setting = self.db.query(RequestSettings).first()
            if not request_setting:
                request_setting = RequestSettings(
                    auto_assignment=True,
                    assignment_timeout=300,
                    max_retries=3,
                    priority_levels=["low", "normal", "high", "urgent"],
                    matching_algorithm="distance_rating",
                    max_distance=10.0,
                    rating_weight=0.6,
                    distance_weight=0.4,
                    require_phone=True,
                    require_email=False,
                    minimum_description=20
                )
                self.db.add(request_setting)
            
            self.db.commit()
            logger.info("Default settings seeded successfully")
            
        except Exception as e:
            logger.error(f"Error seeding default settings: {e}")
            self.db.rollback()