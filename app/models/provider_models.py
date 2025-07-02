"""
Provider-specific database models for Djobea AI Provider Dashboard
Enhanced models for provider session management, settings, and analytics
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, DECIMAL, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, timezone
from app.database import Base

class ProviderSession(Base):
    """Provider authentication sessions for dashboard access"""
    __tablename__ = "provider_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships (removed to avoid circular imports)
    
    @property
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        now = datetime.now(timezone.utc)
        return now < self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if session has recent activity (within 30 minutes)"""
        now = datetime.now(timezone.utc)
        return now - self.last_activity < timedelta(minutes=30)

class ProviderSettings(Base):
    """Provider dashboard and notification settings"""
    __tablename__ = "provider_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    provider_id = Column(Integer, ForeignKey("providers.id"), unique=True, nullable=False)
    
    # Notification preferences
    notifications_enabled = Column(Boolean, default=True)
    notification_sound = Column(Boolean, default=True)
    auto_accept_familiar_clients = Column(Boolean, default=False)
    
    # Working hours configuration
    working_hours = Column(JSON, default=lambda: {
        "start": "08:00",
        "end": "18:00", 
        "days": [1, 2, 3, 4, 5]  # Monday to Friday
    })
    
    # Dashboard preferences
    dashboard_layout = Column(JSON, default=lambda: {
        "show_revenue_chart": True,
        "show_activity_heatmap": True,
        "default_period": "week"
    })
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships - use string reference to avoid circular imports

class ProviderStatsCache(Base):
    """Cached provider statistics for performance optimization"""
    __tablename__ = "provider_stats_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    provider_id = Column(Integer, ForeignKey("providers.id"), unique=True, nullable=False)
    
    # Period configuration
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Core metrics
    total_requests = Column(Integer, default=0)
    completed_requests = Column(Integer, default=0)
    cancelled_requests = Column(Integer, default=0)
    declined_requests = Column(Integer, default=0)
    
    # Financial metrics
    total_earnings = Column(DECIMAL(10, 2), default=0)
    commission_paid = Column(DECIMAL(10, 2), default=0)
    net_earnings = Column(DECIMAL(10, 2), default=0)
    
    # Performance metrics
    average_rating = Column(DECIMAL(3, 2), default=0)
    response_time_avg = Column(Integer, default=0)  # in minutes
    acceptance_rate = Column(DECIMAL(5, 2), default=0)  # percentage
    completion_rate = Column(DECIMAL(5, 2), default=0)  # percentage
    
    # Service breakdown
    service_breakdown = Column(JSON, default=lambda: {
        "plomberie": 0,
        "électricité": 0,
        "réparation électroménager": 0
    })
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships - use string reference to avoid circular imports

class ProviderNotification(Base):
    """Provider-specific notifications and alerts"""
    __tablename__ = "provider_notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Notification details
    type = Column(String(50), nullable=False)  # new_request, payment_received, rating_received
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Related objects
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    
    # Status tracking
    is_read = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships - use string reference to avoid circular imports

class ProviderAvailability(Base):
    """Provider availability and absence management"""
    __tablename__ = "provider_availability"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Availability details
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=True)
    reason = Column(String(100), nullable=True)  # vacation, sick, maintenance
    
    # Time slots (for future implementation)
    available_slots = Column(JSON, default=lambda: {
        "morning": True,
        "afternoon": True,
        "evening": False
    })
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships - use string reference to avoid circular imports

class ProviderDashboardWidget(Base):
    """Customizable dashboard widgets for providers"""
    __tablename__ = "provider_dashboard_widgets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Widget configuration
    widget_type = Column(String(50), nullable=False)  # revenue_chart, request_summary, performance_metrics
    position = Column(Integer, default=0)  # for ordering
    size = Column(String(20), default="medium")  # small, medium, large
    
    # Widget settings
    settings = Column(JSON, default=lambda: {})
    is_visible = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships - use string reference to avoid circular imports