"""
Escalation Detection Models for Djobea AI
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.database_models import Base

class EscalationDetector(Base):
    """Main escalation detection configuration"""
    __tablename__ = "escalation_detectors"
    
    id = Column(Integer, primary_key=True, index=True)
    detector_id = Column(String(255), unique=True, index=True)
    detector_name = Column(String(255), nullable=False)
    detector_type = Column(String(100), nullable=False)  # failure_counter, sentiment_analysis, duration_based, complexity_scoring
    
    # Configuration
    is_active = Column(Boolean, default=True)
    priority_level = Column(Integer, default=1)  # 1=low, 2=medium, 3=high, 4=urgent
    escalation_threshold = Column(Float, default=0.7)  # Score threshold for escalation
    
    # Specific thresholds
    failure_count_threshold = Column(Integer, default=3)
    sentiment_threshold = Column(Float, default=-0.5)  # Negative sentiment threshold
    duration_threshold_minutes = Column(Integer, default=15)
    complexity_threshold = Column(Float, default=0.8)
    
    # Business rules
    service_type_filter = Column(String(100))  # Apply to specific service types
    zone_filter = Column(String(100))  # Apply to specific zones
    user_type_filter = Column(String(50))  # new, returning, premium
    time_window_minutes = Column(Integer, default=60)  # Detection window
    
    # Learning parameters
    learning_enabled = Column(Boolean, default=True)
    auto_adjust_thresholds = Column(Boolean, default=False)
    improvement_rate = Column(Float, default=0.05)  # Learning rate
    
    # Metadata
    configuration_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    detection_logs = relationship("EscalationDetectionLog", back_populates="detector")
    analytics = relationship("EscalationAnalytics", back_populates="detector")

class EscalationDetectionLog(Base):
    """Log of escalation detection events"""
    __tablename__ = "escalation_detection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String(255), unique=True, index=True)
    detector_id = Column(String(255), ForeignKey("escalation_detectors.detector_id"))
    
    # Context
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    request_id = Column(String(255), index=True)
    conversation_turn = Column(Integer, default=1)
    
    # Detection results
    escalation_triggered = Column(Boolean, default=False)
    escalation_score = Column(Float, default=0.0)
    escalation_reason = Column(Text)
    escalation_type = Column(String(100))  # frustration, complexity, failure, duration
    
    # Detailed scores
    failure_count = Column(Integer, default=0)
    sentiment_score = Column(Float, default=0.0)
    duration_minutes = Column(Float, default=0.0)
    complexity_score = Column(Float, default=0.0)
    
    # Message analysis
    message_content = Column(Text)
    message_sentiment = Column(String(50))  # positive, negative, neutral
    frustration_indicators = Column(JSON)  # List of detected frustration patterns
    comprehension_failures = Column(JSON)  # List of comprehension failures
    
    # Context factors
    service_type = Column(String(100))
    zone = Column(String(100))
    user_type = Column(String(50))
    urgency_level = Column(String(20))
    
    # Resolution
    escalation_resolved = Column(Boolean, default=False)
    resolution_method = Column(String(100))  # human_intervention, auto_resolution, user_satisfied
    resolution_time_minutes = Column(Integer)
    resolution_notes = Column(Text)
    
    # Metadata
    detection_metadata = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    detector = relationship("EscalationDetector", back_populates="detection_logs")

class EscalationBusinessRule(Base):
    """Business rules for escalation decisions"""
    __tablename__ = "escalation_business_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(255), unique=True, index=True)
    rule_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Rule conditions
    condition_type = Column(String(100))  # combined_score, individual_threshold, pattern_match
    primary_detector = Column(String(255))  # Main detector for this rule
    secondary_detectors = Column(JSON)  # Additional detectors to consider
    
    # Thresholds
    escalation_threshold = Column(Float, default=0.7)
    minimum_confidence = Column(Float, default=0.6)
    time_window_minutes = Column(Integer, default=30)
    
    # Filters and exceptions
    service_type_filter = Column(String(100))
    zone_filter = Column(String(100))
    user_type_filter = Column(String(50))
    exception_conditions = Column(JSON)  # Conditions to skip escalation
    
    # Actions
    escalation_action = Column(String(100))  # human_handoff, supervisor_alert, auto_resolution
    escalation_target = Column(String(255))  # Target person/system for escalation
    notification_channels = Column(JSON)  # Channels to notify on escalation
    
    # Configuration
    is_active = Column(Boolean, default=True)
    priority_order = Column(Integer, default=1)
    max_escalations_per_day = Column(Integer, default=50)
    cooldown_minutes = Column(Integer, default=60)
    
    # Metadata
    rule_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    executions = relationship("EscalationExecution", back_populates="business_rule")

class EscalationExecution(Base):
    """Log of escalation rule executions"""
    __tablename__ = "escalation_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(255), unique=True, index=True)
    rule_id = Column(String(255), ForeignKey("escalation_business_rules.rule_id"))
    detection_log_id = Column(String(255), ForeignKey("escalation_detection_logs.log_id"))
    
    # Execution context
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    request_id = Column(String(255), index=True)
    
    # Execution details
    execution_status = Column(String(50), default='pending')  # pending, executed, failed, skipped
    escalation_score = Column(Float)
    confidence_score = Column(Float)
    execution_reason = Column(Text)
    
    # Results
    escalation_successful = Column(Boolean, default=False)
    human_contacted = Column(Boolean, default=False)
    user_notified = Column(Boolean, default=False)
    resolution_time_minutes = Column(Integer)
    
    # Outcome
    outcome_type = Column(String(100))  # resolved, escalated_further, user_abandoned
    outcome_satisfaction = Column(Float)  # User satisfaction score
    outcome_notes = Column(Text)
    
    # Metadata
    execution_metadata = Column(JSON)
    execution_timestamp = Column(DateTime, default=datetime.utcnow)
    resolved_timestamp = Column(DateTime)
    
    # Relationships
    business_rule = relationship("EscalationBusinessRule", back_populates="executions")

class ComplexityScoring(Base):
    """Machine learning model for complexity scoring"""
    __tablename__ = "complexity_scoring"
    
    id = Column(Integer, primary_key=True, index=True)
    score_id = Column(String(255), unique=True, index=True)
    
    # Context
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    request_id = Column(String(255), index=True)
    
    # Input factors
    conversation_length = Column(Integer, default=0)
    message_complexity = Column(Float, default=0.0)
    technical_terms_count = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    clarification_requests = Column(Integer, default=0)
    
    # Behavioral factors
    user_frustration_level = Column(Float, default=0.0)
    response_time_variance = Column(Float, default=0.0)
    topic_switches = Column(Integer, default=0)
    repetition_count = Column(Integer, default=0)
    
    # Service factors
    service_type = Column(String(100))
    service_complexity = Column(Float, default=0.0)
    zone_complexity = Column(Float, default=0.0)
    provider_availability = Column(Float, default=1.0)
    
    # Calculated scores
    overall_complexity = Column(Float, default=0.0)
    escalation_probability = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)
    
    # Predictions
    predicted_resolution_time = Column(Integer)  # minutes
    predicted_escalation_type = Column(String(100))
    suggested_action = Column(String(100))
    
    # Learning data
    actual_outcome = Column(String(100))  # For training
    actual_resolution_time = Column(Integer)
    model_accuracy = Column(Float)
    
    # Metadata
    scoring_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EscalationAnalytics(Base):
    """Analytics data for escalation system"""
    __tablename__ = "escalation_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    analytics_id = Column(String(255), unique=True, index=True)
    detector_id = Column(String(255), ForeignKey("escalation_detectors.detector_id"))
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(50))  # hourly, daily, weekly, monthly
    
    # Detection metrics
    total_detections = Column(Integer, default=0)
    escalations_triggered = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)
    false_negatives = Column(Integer, default=0)
    
    # Performance metrics
    detection_accuracy = Column(Float, default=0.0)
    precision_score = Column(Float, default=0.0)
    recall_score = Column(Float, default=0.0)
    f1_score = Column(Float, default=0.0)
    
    # Business metrics
    resolution_rate = Column(Float, default=0.0)
    average_resolution_time = Column(Float, default=0.0)
    user_satisfaction = Column(Float, default=0.0)
    cost_per_escalation = Column(Float, default=0.0)
    
    # Trend analysis
    trend_direction = Column(String(50))  # improving, declining, stable
    trend_confidence = Column(Float, default=0.0)
    seasonal_patterns = Column(JSON)
    
    # Improvement suggestions
    optimization_opportunities = Column(JSON)
    threshold_adjustments = Column(JSON)
    pattern_insights = Column(JSON)
    
    # Metadata
    analytics_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    detector = relationship("EscalationDetector", back_populates="analytics")

class EscalationPattern(Base):
    """Learned patterns for escalation prediction"""
    __tablename__ = "escalation_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_id = Column(String(255), unique=True, index=True)
    pattern_name = Column(String(255), nullable=False)
    pattern_type = Column(String(100))  # linguistic, behavioral, temporal, contextual
    
    # Pattern definition
    pattern_rules = Column(JSON)  # Pattern matching rules
    pattern_strength = Column(Float, default=0.0)  # How strong this pattern is
    pattern_frequency = Column(Float, default=0.0)  # How often it appears
    
    # Context
    service_types = Column(JSON)  # Service types where this pattern applies
    zones = Column(JSON)  # Zones where this pattern applies
    user_types = Column(JSON)  # User types affected by this pattern
    
    # Performance
    accuracy_score = Column(Float, default=0.0)
    false_positive_rate = Column(Float, default=0.0)
    confidence_interval = Column(Float, default=0.0)
    
    # Learning
    training_samples = Column(Integer, default=0)
    last_training_date = Column(DateTime)
    pattern_version = Column(String(50), default="1.0")
    
    # Status
    is_active = Column(Boolean, default=True)
    validation_status = Column(String(50), default='pending')  # pending, validated, rejected
    
    # Metadata
    pattern_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EscalationFeedback(Base):
    """User and operator feedback on escalations"""
    __tablename__ = "escalation_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(String(255), unique=True, index=True)
    execution_id = Column(String(255), ForeignKey("escalation_executions.execution_id"))
    
    # Feedback context
    user_id = Column(String(255), nullable=False, index=True)
    feedback_type = Column(String(50))  # user_satisfaction, operator_assessment, system_evaluation
    feedback_source = Column(String(100))  # user, operator, system, automated
    
    # Ratings
    escalation_appropriateness = Column(Float)  # Was escalation appropriate? (1-5)
    timing_appropriateness = Column(Float)  # Was timing correct? (1-5)
    resolution_quality = Column(Float)  # Quality of resolution (1-5)
    overall_satisfaction = Column(Float)  # Overall satisfaction (1-5)
    
    # Detailed feedback
    positive_aspects = Column(JSON)  # List of positive aspects
    negative_aspects = Column(JSON)  # List of negative aspects
    improvement_suggestions = Column(JSON)  # Suggestions for improvement
    
    # Comments
    user_comments = Column(Text)
    operator_notes = Column(Text)
    system_observations = Column(Text)
    
    # Learning impact
    used_for_training = Column(Boolean, default=False)
    training_weight = Column(Float, default=1.0)
    feedback_reliability = Column(Float, default=1.0)
    
    # Metadata
    feedback_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)