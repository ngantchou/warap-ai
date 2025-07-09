"""
Real-time Tracking Models for Djobea AI
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database_models import Base
import uuid

class RequestStatus(Base):
    """Track request status changes in real-time"""
    __tablename__ = "request_status"
    
    id = Column(Integer, primary_key=True, index=True)
    status_id = Column(String(255), unique=True, index=True)
    request_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Status information
    current_status = Column(String(100), nullable=False)
    previous_status = Column(String(100))
    status_reason = Column(Text)
    
    # Timing information
    status_timestamp = Column(DateTime, default=datetime.utcnow)
    estimated_completion = Column(DateTime)
    predicted_next_step = Column(String(100))
    next_step_eta = Column(DateTime)
    
    # Provider information
    provider_id = Column(String(255), index=True)
    provider_location = Column(String(255))
    provider_eta = Column(DateTime)
    
    # Additional data
    urgency_level = Column(String(20), default='normal')  # low, normal, high, urgent
    completion_percentage = Column(Float, default=0.0)
    additional_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("StatusHistory", back_populates="status")
    notifications = relationship("NotificationLog", back_populates="request_status")

class StatusHistory(Base):
    """Detailed history of all status changes"""
    __tablename__ = "status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(String(255), unique=True, index=True)
    status_id = Column(String(255), ForeignKey("request_status.status_id"))
    request_id = Column(String(255), nullable=False, index=True)
    
    # Change details
    from_status = Column(String(100))
    to_status = Column(String(100), nullable=False)
    change_reason = Column(Text)
    changed_by = Column(String(255))  # system, user, provider
    change_source = Column(String(100))  # webhook, manual, automatic
    
    # Timing
    change_timestamp = Column(DateTime, default=datetime.utcnow)
    duration_in_previous_status = Column(Integer)  # seconds
    
    # Performance metrics
    was_on_time = Column(Boolean, default=True)
    delay_reason = Column(String(255))
    impact_score = Column(Float, default=0.0)
    
    # Context
    context_data = Column(JSON)
    user_satisfaction = Column(Integer)  # 1-5 rating
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    status = relationship("RequestStatus", back_populates="history")

class NotificationRule(Base):
    """Rules for intelligent notifications"""
    __tablename__ = "notification_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(255), unique=True, index=True)
    rule_name = Column(String(255), nullable=False)
    
    # Trigger conditions
    trigger_status = Column(String(100))
    trigger_delay_minutes = Column(Integer)
    trigger_urgency_level = Column(String(20))
    trigger_condition = Column(JSON)  # Complex conditions
    
    # Notification settings
    notification_channels = Column(JSON)  # ['whatsapp', 'sms', 'email']
    notification_template = Column(String(255))
    notification_frequency = Column(String(50))  # immediate, hourly, daily
    max_notifications = Column(Integer, default=5)
    
    # Personalization
    user_type_filter = Column(String(50))  # all, new, returning, premium
    service_type_filter = Column(String(100))
    zone_filter = Column(String(100))
    
    # Behavior
    is_active = Column(Boolean, default=True)
    priority_level = Column(Integer, default=1)
    escalation_rule = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    logs = relationship("NotificationLog", back_populates="rule")

class NotificationLog(Base):
    """Log of all notifications sent"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String(255), unique=True, index=True)
    request_id = Column(String(255), nullable=False, index=True)
    status_id = Column(String(255), ForeignKey("request_status.status_id"))
    rule_id = Column(String(255), ForeignKey("notification_rules.rule_id"))
    user_id = Column(String(255), nullable=False, index=True)
    
    # Notification details
    notification_type = Column(String(100))  # status_update, delay_alert, completion
    channel = Column(String(50))  # whatsapp, sms, email
    template_used = Column(String(255))
    message_content = Column(Text)
    
    # Delivery information
    sent_timestamp = Column(DateTime, default=datetime.utcnow)
    delivery_status = Column(String(50), default='pending')  # pending, sent, delivered, failed
    delivery_timestamp = Column(DateTime)
    read_timestamp = Column(DateTime)
    
    # Response tracking
    user_response = Column(String(255))
    response_timestamp = Column(DateTime)
    satisfaction_score = Column(Integer)  # 1-5 rating
    
    # Performance
    send_delay = Column(Integer)  # milliseconds
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Additional data
    log_metadata = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    request_status = relationship("RequestStatus", back_populates="notifications")
    rule = relationship("NotificationRule", back_populates="logs")

class EscalationRule(Base):
    """Rules for automatic escalation"""
    __tablename__ = "escalation_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(255), unique=True, index=True)
    rule_name = Column(String(255), nullable=False)
    
    # Trigger conditions
    status_trigger = Column(String(100))
    delay_threshold_minutes = Column(Integer)
    urgency_level = Column(String(20))
    failure_count_threshold = Column(Integer)
    
    # Escalation actions
    escalation_type = Column(String(100))  # provider_reminder, find_new_provider, manager_alert
    escalation_target = Column(String(255))  # provider, manager, system
    escalation_message = Column(Text)
    escalation_channels = Column(JSON)
    
    # Behavior
    max_escalations = Column(Integer, default=3)
    escalation_interval_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    
    # Filters
    service_type_filter = Column(String(100))
    zone_filter = Column(String(100))
    provider_rating_threshold = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    escalations = relationship("EscalationLog", back_populates="rule")

class EscalationLog(Base):
    """Log of all escalations performed"""
    __tablename__ = "escalation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    escalation_id = Column(String(255), unique=True, index=True)
    rule_id = Column(String(255), ForeignKey("escalation_rules.rule_id"))
    request_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Escalation details
    escalation_type = Column(String(100))
    escalation_reason = Column(Text)
    escalation_level = Column(Integer, default=1)
    target_recipient = Column(String(255))
    
    # Timing
    escalation_timestamp = Column(DateTime, default=datetime.utcnow)
    resolved_timestamp = Column(DateTime)
    resolution_method = Column(String(255))
    
    # Status
    escalation_status = Column(String(50), default='pending')  # pending, in_progress, resolved, failed
    resolution_notes = Column(Text)
    
    # Performance
    response_time_minutes = Column(Integer)
    effectiveness_score = Column(Float)
    user_satisfaction = Column(Integer)  # 1-5 rating
    
    # Additional data
    escalation_metadata = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    rule = relationship("EscalationRule", back_populates="escalations")

class TrackingUserPreference(Base):
    """User notification preferences for tracking system"""
    __tablename__ = "tracking_user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, index=True)
    
    # Notification preferences
    preferred_channels = Column(JSON, default=['whatsapp'])  # ['whatsapp', 'sms', 'email']
    notification_frequency = Column(String(50), default='immediate')  # immediate, hourly, daily
    quiet_hours_start = Column(String(5), default='22:00')  # HH:MM
    quiet_hours_end = Column(String(5), default='07:00')  # HH:MM
    
    # Communication preferences
    language = Column(String(10), default='fr')  # fr, en
    communication_style = Column(String(50), default='friendly')  # formal, friendly, brief
    urgency_sensitivity = Column(String(20), default='normal')  # low, normal, high
    
    # Service preferences
    max_updates_per_day = Column(Integer, default=10)
    wants_completion_photos = Column(Boolean, default=True)
    wants_cost_updates = Column(Boolean, default=True)
    wants_provider_info = Column(Boolean, default=True)
    
    # Privacy
    share_location = Column(Boolean, default=True)
    share_contact_info = Column(Boolean, default=True)
    marketing_notifications = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TrackingAnalytics(Base):
    """Analytics and metrics for tracking system"""
    __tablename__ = "tracking_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    analytics_id = Column(String(255), unique=True, index=True)
    request_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Performance metrics
    total_duration_minutes = Column(Integer)
    status_changes_count = Column(Integer)
    notifications_sent = Column(Integer)
    escalations_count = Column(Integer)
    
    # Timing metrics
    response_time_minutes = Column(Integer)
    resolution_time_minutes = Column(Integer)
    provider_acceptance_time = Column(Integer)
    completion_time_minutes = Column(Integer)
    
    # Quality metrics
    user_satisfaction_score = Column(Float)
    provider_rating = Column(Float)
    service_quality_score = Column(Float)
    communication_effectiveness = Column(Float)
    
    # Status progression
    status_progression = Column(JSON)  # Detailed progression tracking
    delays_encountered = Column(JSON)
    issues_reported = Column(JSON)
    
    # Optimization data
    optimization_suggestions = Column(JSON)
    improvement_areas = Column(JSON)
    success_factors = Column(JSON)
    
    # Metadata
    service_type = Column(String(100))
    zone = Column(String(100))
    urgency_level = Column(String(20))
    completion_date = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)