"""
Dynamic Settings Models for Djobea AI
Database models for managing all system parameters dynamically
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.models.database_models import Base


class SystemSettings(Base):
    """General system settings"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)
    data_type = Column(String(20), nullable=False)  # string, integer, float, boolean, json
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemSettings {self.category}.{self.key}>"


class NotificationSettings(Base):
    """Notification configuration settings"""
    __tablename__ = "notification_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)  # email, sms, push, whatsapp
    enabled = Column(Boolean, default=True)
    config = Column(JSON, nullable=False)
    priority = Column(Integer, default=1)
    retry_attempts = Column(Integer, default=3)
    retry_delay = Column(Integer, default=300)  # seconds
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<NotificationSettings {self.provider}>"


class SecuritySettings(Base):
    """Security configuration settings"""
    __tablename__ = "security_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    setting_name = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    data_type = Column(String(20), nullable=False)
    is_encrypted = Column(Boolean, default=False)
    last_rotation = Column(DateTime)
    rotation_interval = Column(Integer)  # days
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SecuritySettings {self.setting_name}>"


class PerformanceSettings(Base):
    """Performance optimization settings"""
    __tablename__ = "performance_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    component = Column(String(50), nullable=False, index=True)  # cache, cdn, optimization
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text, nullable=False)
    data_type = Column(String(20), nullable=False)
    environment = Column(String(20), default="production")  # production, staging, development
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<PerformanceSettings {self.component}.{self.setting_key}>"


class AISettings(Base):
    """AI and ML configuration settings"""
    __tablename__ = "ai_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)  # openai, claude, gemini
    model_name = Column(String(100), nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    rate_limit = Column(Integer, default=100)  # requests per minute
    config = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AISettings {self.provider}:{self.model_name}>"


class WhatsAppSettings(Base):
    """WhatsApp integration settings"""
    __tablename__ = "whatsapp_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    business_account_id = Column(String(100))
    phone_number_id = Column(String(100))
    access_token = Column(Text)
    webhook_url = Column(String(255))
    verify_token = Column(String(100))
    enabled = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=1000)  # messages per hour
    templates = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<WhatsAppSettings {self.business_account_id}>"


class BusinessSettings(Base):
    """Business configuration settings"""
    __tablename__ = "business_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200))
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(100))
    website = Column(String(255))
    currency = Column(String(10), default="XAF")
    tax_rate = Column(Float, default=19.25)
    commission_rate = Column(Float, default=15.0)
    minimum_order = Column(Float, default=5000)
    working_hours_start = Column(String(5), default="08:00")
    working_hours_end = Column(String(5), default="18:00")
    working_days = Column(JSON)
    emergency_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<BusinessSettings {self.company_name}>"


class ProviderSettings(Base):
    """Provider management settings"""
    __tablename__ = "provider_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    require_documents = Column(Boolean, default=True)
    background_check = Column(Boolean, default=True)
    minimum_rating = Column(Float, default=3.0)
    probation_period = Column(Integer, default=30)  # days
    commission_rate = Column(Float, default=15.0)
    payment_schedule = Column(String(20), default="weekly")
    minimum_payout = Column(Float, default=10000)
    minimum_reviews = Column(Integer, default=5)
    auto_suspend_threshold = Column(Float, default=2.0)
    improvement_period = Column(Integer, default=14)  # days
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ProviderSettings {self.id}>"


class RequestSettings(Base):
    """Request processing settings"""
    __tablename__ = "request_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    auto_assignment = Column(Boolean, default=True)
    assignment_timeout = Column(Integer, default=300)  # seconds
    max_retries = Column(Integer, default=3)
    priority_levels = Column(JSON)
    matching_algorithm = Column(String(50), default="distance_rating")
    max_distance = Column(Float, default=10.0)  # km
    rating_weight = Column(Float, default=0.6)
    distance_weight = Column(Float, default=0.4)
    require_phone = Column(Boolean, default=True)
    require_email = Column(Boolean, default=False)
    minimum_description = Column(Integer, default=20)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<RequestSettings {self.id}>"


class AdminSettings(Base):
    """Administration settings"""
    __tablename__ = "admin_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    max_users = Column(Integer, default=1000)
    default_role = Column(String(20), default="user")
    session_timeout = Column(Integer, default=86400)  # seconds
    audit_log_retention = Column(Integer, default=365)  # days
    backup_frequency = Column(String(20), default="daily")
    maintenance_mode = Column(Boolean, default=False)
    debug_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AdminSettings {self.id}>"