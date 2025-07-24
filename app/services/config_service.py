"""
Configuration Service for Djobea AI
Central configuration management service that eliminates hard-coded values
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from sqlalchemy.orm import Session

from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """Configuration source types"""
    ENVIRONMENT = "environment"
    DATABASE = "database"
    FILE = "file"
    DEFAULT = "default"


@dataclass
class ConfigItem:
    """Configuration item with metadata"""
    key: str
    value: Any
    source: ConfigSource
    description: str = ""
    is_sensitive: bool = False
    last_updated: str = ""


class ConfigService:
    """Central configuration service for dynamic parameter management"""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.settings_service = SettingsService(db) if db else None
        self._config_cache: Dict[str, ConfigItem] = {}
        self._load_configurations()
    
    def _load_configurations(self):
        """Load configurations from all sources"""
        try:
            # Load from environment variables
            self._load_environment_configs()
            
            # Load from database if available
            if self.settings_service:
                self._load_database_configs()
            
            # Load defaults
            self._load_default_configs()
            
            logger.info(f"Loaded {len(self._config_cache)} configuration items")
            
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
    
    def _load_environment_configs(self):
        """Load configurations from environment variables"""
        env_configs = {
            # API Keys
            "ANTHROPIC_API_KEY": {"description": "Anthropic API key", "sensitive": True},
            "OPENAI_API_KEY": {"description": "OpenAI API key", "sensitive": True},
            "GEMINI_API_KEY": {"description": "Gemini API key", "sensitive": True},
            "TWILIO_ACCOUNT_SID": {"description": "Twilio Account SID", "sensitive": True},
            "TWILIO_AUTH_TOKEN": {"description": "Twilio Auth Token", "sensitive": True},
            "TWILIO_PHONE_NUMBER": {"description": "Twilio Phone Number", "sensitive": False},
            
            # Database
            "DATABASE_URL": {"description": "Database connection URL", "sensitive": True},
            "PGDATABASE": {"description": "PostgreSQL database name", "sensitive": False},
            "PGHOST": {"description": "PostgreSQL host", "sensitive": False},
            "PGPORT": {"description": "PostgreSQL port", "sensitive": False},
            "PGUSER": {"description": "PostgreSQL user", "sensitive": False},
            "PGPASSWORD": {"description": "PostgreSQL password", "sensitive": True},
            
            # Application
            "FLASK_ENV": {"description": "Flask environment", "sensitive": False},
            "DEBUG": {"description": "Debug mode", "sensitive": False},
            "HOST": {"description": "Application host", "sensitive": False},
            "PORT": {"description": "Application port", "sensitive": False},
        }
        
        for key, config in env_configs.items():
            value = os.getenv(key)
            if value is not None:
                self._config_cache[key] = ConfigItem(
                    key=key,
                    value=value,
                    source=ConfigSource.ENVIRONMENT,
                    description=config["description"],
                    is_sensitive=config["sensitive"]
                )
    
    def _load_database_configs(self):
        """Load configurations from database"""
        try:
            # Load system settings
            system_settings = self.settings_service.get_all_system_settings()
            for category, settings in system_settings.items():
                for key, value in settings.items():
                    config_key = f"{category}.{key}"
                    self._config_cache[config_key] = ConfigItem(
                        key=config_key,
                        value=value,
                        source=ConfigSource.DATABASE,
                        description=f"{category} setting: {key}"
                    )
            
            # Load business settings
            business_settings = self.settings_service.get_business_settings()
            for category, settings in business_settings.items():
                if isinstance(settings, dict):
                    for key, value in settings.items():
                        config_key = f"business.{category}.{key}"
                        self._config_cache[config_key] = ConfigItem(
                            key=config_key,
                            value=value,
                            source=ConfigSource.DATABASE,
                            description=f"Business {category} setting: {key}"
                        )
            
            # Load AI settings
            ai_settings = self.settings_service.get_ai_settings()
            for provider, settings in ai_settings.items():
                for key, value in settings.items():
                    config_key = f"ai.{provider}.{key}"
                    self._config_cache[config_key] = ConfigItem(
                        key=config_key,
                        value=value,
                        source=ConfigSource.DATABASE,
                        description=f"AI {provider} setting: {key}"
                    )
            
            # Load notification settings
            notification_settings = self.settings_service.get_notification_settings()
            for provider, settings in notification_settings.items():
                for key, value in settings.items():
                    config_key = f"notifications.{provider}.{key}"
                    self._config_cache[config_key] = ConfigItem(
                        key=config_key,
                        value=value,
                        source=ConfigSource.DATABASE,
                        description=f"Notification {provider} setting: {key}"
                    )
            
        except Exception as e:
            logger.error(f"Error loading database configs: {e}")
    
    def _load_default_configs(self):
        """Load default configurations"""
        defaults = {
            # Application defaults
            "app.name": "Djobea AI",
            "app.version": "2.0.0",
            "app.environment": "production",
            "app.debug": False,
            "app.host": "0.0.0.0",
            "app.port": 5000,
            
            # Business defaults
            "business.currency": "XAF",
            "business.tax_rate": 19.25,
            "business.commission_rate": 15.0,
            "business.minimum_order": 5000,
            "business.working_hours.start": "08:00",
            "business.working_hours.end": "18:00",
            "business.emergency_available": True,
            
            # AI defaults
            "ai.primary_model": "claude-sonnet-4-20250514",
            "ai.temperature": 0.7,
            "ai.max_tokens": 2048,
            "ai.confidence_threshold": 0.7,
            "ai.max_conversation_turns": 10,
            "ai.enable_auto_escalation": True,
            "ai.escalation_timeout_minutes": 15,
            
            # Provider defaults
            "provider.max_per_request": 5,
            "provider.timeout_minutes": 10,
            "provider.retry_attempts": 3,
            "provider.minimum_rating": 3.0,
            "provider.commission_rate": 15.0,
            "provider.minimum_payout": 10000,
            
            # Request defaults
            "request.auto_assignment": True,
            "request.assignment_timeout": 300,
            "request.max_retries": 3,
            "request.matching_algorithm": "distance_rating",
            "request.max_distance": 10.0,
            "request.rating_weight": 0.6,
            "request.distance_weight": 0.4,
            "request.require_phone": True,
            "request.minimum_description": 20,
            
            # Communication defaults
            "communication.whatsapp_enabled": True,
            "communication.sms_enabled": True,
            "communication.email_enabled": False,
            "communication.retry_attempts": 3,
            "communication.retry_delay_minutes": 2,
            
            # Security defaults
            "security.jwt_expiration": "24h",
            "security.refresh_token_expiration": "7d",
            "security.max_login_attempts": 5,
            "security.lockout_duration": "15m",
            
            # Performance defaults
            "performance.cache_ttl": 300,
            "performance.max_memory": "512mb",
            "performance.compression_enabled": True,
            "performance.rate_limit": 100,
            
            # Monitoring defaults
            "monitoring.health_check_interval": 60,
            "monitoring.error_threshold": 10,
            "monitoring.alert_cooldown": 300,
            "monitoring.log_retention_days": 30,
        }
        
        for key, value in defaults.items():
            if key not in self._config_cache:
                self._config_cache[key] = ConfigItem(
                    key=key,
                    value=value,
                    source=ConfigSource.DEFAULT,
                    description=f"Default value for {key}"
                )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        try:
            if key in self._config_cache:
                return self._config_cache[key].value
            
            # Try environment variable
            env_value = os.getenv(key.upper().replace(".", "_"))
            if env_value is not None:
                return env_value
            
            return default
            
        except Exception as e:
            logger.error(f"Error getting config {key}: {e}")
            return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get configuration value as integer"""
        try:
            value = self.get(key, default)
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get configuration value as float"""
        try:
            value = self.get(key, default)
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean"""
        try:
            value = self.get(key, default)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        except (ValueError, TypeError):
            return default
    
    def get_list(self, key: str, default: List = None) -> List:
        """Get configuration value as list"""
        try:
            value = self.get(key, default)
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value.split(",")
            return default or []
        except (ValueError, TypeError):
            return default or []
    
    def get_dict(self, key: str, default: Dict = None) -> Dict:
        """Get configuration value as dictionary"""
        try:
            value = self.get(key, default)
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return default or {}
            return default or {}
        except (ValueError, TypeError):
            return default or {}
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.DATABASE) -> bool:
        """Set configuration value"""
        try:
            # Update cache
            self._config_cache[key] = ConfigItem(
                key=key,
                value=value,
                source=source,
                description=f"Updated via ConfigService"
            )
            
            # Update database if available
            if self.settings_service and source == ConfigSource.DATABASE:
                category, setting_key = key.split(".", 1) if "." in key else ("general", key)
                data_type = "string"
                if isinstance(value, bool):
                    data_type = "boolean"
                elif isinstance(value, int):
                    data_type = "integer"
                elif isinstance(value, float):
                    data_type = "float"
                elif isinstance(value, (dict, list)):
                    data_type = "json"
                    value = json.dumps(value)
                
                return self.settings_service.set_system_setting(
                    category, setting_key, value, data_type
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting config {key}: {e}")
            return False
    
    def get_all_configs(self) -> Dict[str, ConfigItem]:
        """Get all configuration items"""
        return self._config_cache.copy()
    
    def get_configs_by_category(self, category: str) -> Dict[str, ConfigItem]:
        """Get configuration items by category"""
        return {
            key: item for key, item in self._config_cache.items()
            if key.startswith(f"{category}.")
        }
    
    def reload(self):
        """Reload configurations from all sources"""
        self._config_cache.clear()
        self._load_configurations()
    
    def get_business_config(self) -> Dict[str, Any]:
        """Get business configuration"""
        return {
            "currency": self.get("business.currency", "XAF"),
            "tax_rate": self.get_float("business.tax_rate", 19.25),
            "commission_rate": self.get_float("business.commission_rate", 15.0),
            "minimum_order": self.get_float("business.minimum_order", 5000),
            "working_hours": {
                "start": self.get("business.working_hours.start", "08:00"),
                "end": self.get("business.working_hours.end", "18:00")
            },
            "emergency_available": self.get_bool("business.emergency_available", True)
        }
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration"""
        return {
            "primary_model": self.get("ai.primary_model", "claude-sonnet-4-20250514"),
            "temperature": self.get_float("ai.temperature", 0.7),
            "max_tokens": self.get_int("ai.max_tokens", 2048),
            "confidence_threshold": self.get_float("ai.confidence_threshold", 0.7),
            "max_conversation_turns": self.get_int("ai.max_conversation_turns", 10),
            "enable_auto_escalation": self.get_bool("ai.enable_auto_escalation", True),
            "escalation_timeout_minutes": self.get_int("ai.escalation_timeout_minutes", 15)
        }
    
    def get_provider_config(self) -> Dict[str, Any]:
        """Get provider configuration"""
        return {
            "max_per_request": self.get_int("provider.max_per_request", 5),
            "timeout_minutes": self.get_int("provider.timeout_minutes", 10),
            "retry_attempts": self.get_int("provider.retry_attempts", 3),
            "minimum_rating": self.get_float("provider.minimum_rating", 3.0),
            "commission_rate": self.get_float("provider.commission_rate", 15.0),
            "minimum_payout": self.get_float("provider.minimum_payout", 10000)
        }
    
    def get_request_config(self) -> Dict[str, Any]:
        """Get request configuration"""
        return {
            "auto_assignment": self.get_bool("request.auto_assignment", True),
            "assignment_timeout": self.get_int("request.assignment_timeout", 300),
            "max_retries": self.get_int("request.max_retries", 3),
            "matching_algorithm": self.get("request.matching_algorithm", "distance_rating"),
            "max_distance": self.get_float("request.max_distance", 10.0),
            "rating_weight": self.get_float("request.rating_weight", 0.6),
            "distance_weight": self.get_float("request.distance_weight", 0.4),
            "require_phone": self.get_bool("request.require_phone", True),
            "minimum_description": self.get_int("request.minimum_description", 20)
        }
    
    def get_communication_config(self) -> Dict[str, Any]:
        """Get communication configuration"""
        return {
            "whatsapp_enabled": self.get_bool("communication.whatsapp_enabled", True),
            "sms_enabled": self.get_bool("communication.sms_enabled", True),
            "email_enabled": self.get_bool("communication.email_enabled", False),
            "retry_attempts": self.get_int("communication.retry_attempts", 3),
            "retry_delay_minutes": self.get_int("communication.retry_delay_minutes", 2)
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return {
            "jwt_expiration": self.get("security.jwt_expiration", "24h"),
            "refresh_token_expiration": self.get("security.refresh_token_expiration", "7d"),
            "max_login_attempts": self.get_int("security.max_login_attempts", 5),
            "lockout_duration": self.get("security.lockout_duration", "15m")
        }
    
    def export_config(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        result = {}
        for key, item in self._config_cache.items():
            if include_sensitive or not item.is_sensitive:
                result[key] = {
                    "value": item.value,
                    "source": item.source.value,
                    "description": item.description
                }
        return result


# Global configuration instance
_config_instance: Optional[ConfigService] = None


def get_config(db: Session = None) -> ConfigService:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigService(db)
    return _config_instance


def init_config(db: Session):
    """Initialize configuration service with database"""
    global _config_instance
    _config_instance = ConfigService(db)
    return _config_instance