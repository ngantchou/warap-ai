"""
Djobea AI Personalization Models
Advanced user preference learning and personalization system
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database_models import Base


class UserPreferences(Base):
    """Comprehensive user preferences and personalization settings"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True)  # Reference to user
    
    # Communication preferences
    communication_style = Column(String(20), default="respectful")  # formal, respectful, casual, friendly
    preferred_language = Column(String(20), default="français")
    language_mix_preference = Column(JSON, nullable=True)  # [français: 70%, english: 20%, pidgin: 10%]
    message_length_preference = Column(String(20), default="medium")  # brief, medium, detailed
    emoji_usage_preference = Column(String(20), default="moderate")  # none, minimal, moderate, frequent
    
    # Service preferences
    typical_locations = Column(JSON, nullable=True)  # Most used locations ranked by frequency
    preferred_time_slots = Column(JSON, nullable=True)  # Preferred scheduling times
    urgency_patterns = Column(JSON, nullable=True)  # Historical urgency preferences
    budget_preferences = Column(JSON, nullable=True)  # Service budget ranges by type
    
    # Provider preferences
    preferred_provider_attributes = Column(JSON, nullable=True)  # Rating, experience, specialization weights
    blacklisted_providers = Column(JSON, nullable=True)  # Providers to avoid
    favorite_providers = Column(JSON, nullable=True)  # Preferred providers by service type
    
    # Interaction patterns
    response_time_expectations = Column(String(20), default="normal")  # immediate, fast, normal, patient
    confirmation_level = Column(String(20), default="standard")  # minimal, standard, detailed
    update_frequency_preference = Column(String(20), default="regular")  # minimal, regular, frequent
    
    # Learning metadata
    preference_confidence = Column(Float, default=0.0)  # 0.0 to 1.0 - confidence in learned preferences
    last_learning_update = Column(DateTime(timezone=True), nullable=True)
    interaction_count = Column(Integer, default=0)
    
    # Privacy settings
    data_retention_consent = Column(Boolean, default=True)
    analytics_consent = Column(Boolean, default=True)
    personalization_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ServiceHistory(Base):
    """Detailed service history for preference learning"""
    __tablename__ = "service_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to user
    service_request_id = Column(Integer, nullable=True)  # Reference to service request
    
    # Service details
    service_type = Column(String(100), nullable=False)
    service_description = Column(Text, nullable=True)
    location = Column(String(200), nullable=False)
    urgency_level = Column(String(20), nullable=True)
    
    # Provider information
    provider_id = Column(Integer, nullable=True)  # Reference to provider
    provider_rating_given = Column(Float, nullable=True)
    provider_feedback = Column(Text, nullable=True)
    
    # Timing and scheduling
    requested_time = Column(DateTime(timezone=True), nullable=True)
    actual_service_time = Column(DateTime(timezone=True), nullable=True)
    completion_time = Column(DateTime(timezone=True), nullable=True)
    
    # Cost and value
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    cost_satisfaction = Column(String(20), nullable=True)  # satisfied, neutral, dissatisfied
    
    # Communication patterns
    total_messages_exchanged = Column(Integer, default=0)
    communication_satisfaction = Column(Float, nullable=True)  # 1.0 to 5.0
    response_time_satisfaction = Column(String(20), nullable=True)
    
    # Outcome and satisfaction
    service_outcome = Column(String(20), nullable=False)  # completed, cancelled, failed
    overall_satisfaction = Column(Float, nullable=True)  # 1.0 to 5.0
    would_use_again = Column(Boolean, nullable=True)
    
    # Learning insights
    preferences_updated = Column(Boolean, default=False)
    lessons_learned = Column(JSON, nullable=True)  # Key insights for future personalization
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BehavioralPatterns(Base):
    """Identified behavioral patterns for intelligent personalization"""
    __tablename__ = "behavioral_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to user
    
    # User classification
    user_type = Column(String(30), nullable=False)  # power_user, occasional, new_user, seasonal
    activity_level = Column(String(20), default="moderate")  # low, moderate, high, very_high
    loyalty_score = Column(Float, default=0.5)  # 0.0 to 1.0
    
    # Service patterns
    most_requested_services = Column(JSON, nullable=True)  # Service types ranked by frequency
    seasonal_patterns = Column(JSON, nullable=True)  # Service needs by month/season
    time_of_day_patterns = Column(JSON, nullable=True)  # Preferred request times
    location_patterns = Column(JSON, nullable=True)  # Location usage patterns
    
    # Urgency and planning patterns
    planning_behavior = Column(String(20), default="mixed")  # planner, spontaneous, mixed, emergency_only
    urgency_frequency = Column(Float, default=0.2)  # 0.0 to 1.0 - percentage of urgent requests
    cancellation_rate = Column(Float, default=0.0)  # Percentage of cancelled requests
    modification_frequency = Column(Float, default=0.0)  # How often user modifies requests
    
    # Communication patterns
    communication_frequency = Column(String(20), default="normal")  # minimal, normal, frequent, excessive
    question_asking_tendency = Column(String(20), default="moderate")  # low, moderate, high
    detail_orientation = Column(String(20), default="standard")  # minimal, standard, detailed, perfectionist
    
    # Provider interaction patterns
    provider_loyalty = Column(Float, default=0.3)  # Tendency to reuse same providers
    rating_behavior = Column(String(20), default="fair")  # harsh, fair, generous, non_rater
    feedback_detail_level = Column(String(20), default="moderate")
    
    # Learning and adaptation
    pattern_confidence = Column(Float, default=0.0)  # Confidence in identified patterns
    last_pattern_analysis = Column(DateTime(timezone=True), nullable=True)
    analysis_data_points = Column(Integer, default=0)  # Number of interactions analyzed
    
    # Predictive insights
    next_service_prediction = Column(JSON, nullable=True)  # Predicted next service need
    optimal_communication_style = Column(JSON, nullable=True)  # Learned optimal approach
    risk_factors = Column(JSON, nullable=True)  # Potential issues or concerns
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PreferenceLearningData(Base):
    """Raw data and insights for machine learning preference analysis"""
    __tablename__ = "preference_learning_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to user
    
    # Data source and context
    data_source = Column(String(50), nullable=False)  # conversation, feedback, behavior, rating
    interaction_type = Column(String(50), nullable=False)  # message, request, completion, rating
    context_data = Column(JSON, nullable=False)  # Full context information
    
    # Learning signals
    signal_type = Column(String(50), nullable=False)  # positive, negative, neutral, preference_indicator
    signal_strength = Column(Float, default=0.5)  # 0.0 to 1.0 - strength of the signal
    signal_data = Column(JSON, nullable=False)  # Specific signal information
    
    # Preference implications
    preference_category = Column(String(50), nullable=False)  # communication, service, provider, timing
    preference_insight = Column(Text, nullable=True)  # Human-readable insight
    confidence_level = Column(Float, default=0.5)  # Confidence in this insight
    
    # Processing status
    processed = Column(Boolean, default=False)
    applied_to_preferences = Column(Boolean, default=False)
    processing_notes = Column(Text, nullable=True)
    
    # Validation and feedback
    user_validated = Column(Boolean, nullable=True)  # User confirmed this preference
    system_validated = Column(Boolean, nullable=True)  # System confirmed effectiveness
    validation_score = Column(Float, nullable=True)  # Overall validation score
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class ContextualMemory(Base):
    """Long-term contextual memory for intelligent conversation continuity"""
    __tablename__ = "contextual_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to user
    
    # Memory type and context
    memory_type = Column(String(50), nullable=False)  # conversation, service, preference, relationship
    memory_category = Column(String(50), nullable=False)  # personal, service, provider, location
    context_tags = Column(JSON, nullable=True)  # Searchable tags for memory retrieval
    
    # Memory content
    memory_title = Column(String(200), nullable=False)
    memory_content = Column(Text, nullable=False)
    emotional_context = Column(String(50), nullable=True)  # Associated emotional state
    
    # Relevance and importance
    importance_score = Column(Float, default=0.5)  # 0.0 to 1.0 - how important this memory is
    recency_weight = Column(Float, default=1.0)  # Decreases over time
    access_frequency = Column(Integer, default=0)  # How often this memory is accessed
    
    # Associated entities
    related_service_types = Column(JSON, nullable=True)  # Relevant service types
    related_providers = Column(JSON, nullable=True)  # Associated provider IDs
    related_locations = Column(JSON, nullable=True)  # Associated locations
    
    # Memory lifecycle
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    auto_archive_after = Column(Integer, default=365)  # Days until auto-archive
    
    # Learning and adaptation
    reinforcement_count = Column(Integer, default=0)  # How many times this memory was reinforced
    conflict_indicators = Column(JSON, nullable=True)  # Conflicting information detected
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PersonalizationMetrics(Base):
    """Metrics and analytics for personalization system performance"""
    __tablename__ = "personalization_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to user
    
    # Personalization effectiveness
    personalization_accuracy = Column(Float, default=0.0)  # How accurate our personalization is
    user_satisfaction_impact = Column(Float, default=0.0)  # Impact on user satisfaction
    engagement_improvement = Column(Float, default=0.0)  # Improvement in user engagement
    
    # Learning progress
    preference_learning_progress = Column(Float, default=0.0)  # 0.0 to 1.0 - learning completion
    pattern_recognition_accuracy = Column(Float, default=0.0)  # Pattern recognition success rate
    prediction_accuracy = Column(Float, default=0.0)  # Prediction success rate
    
    # System performance
    response_relevance_score = Column(Float, default=0.0)  # How relevant our responses are
    communication_effectiveness = Column(Float, default=0.0)  # Communication success rate
    service_matching_improvement = Column(Float, default=0.0)  # Improvement in service matching
    
    # User feedback metrics
    explicit_feedback_score = Column(Float, nullable=True)  # Direct user feedback on personalization
    implicit_feedback_score = Column(Float, default=0.0)  # Derived from user behavior
    overall_experience_score = Column(Float, default=0.0)  # Overall experience rating
    
    # Business impact
    conversion_rate_impact = Column(Float, default=0.0)  # Impact on service completion rate
    retention_impact = Column(Float, default=0.0)  # Impact on user retention
    recommendation_acceptance_rate = Column(Float, default=0.0)  # Rate of recommendation acceptance
    
    # Measurement period
    measurement_start = Column(DateTime(timezone=True), nullable=False)
    measurement_end = Column(DateTime(timezone=True), nullable=False)
    data_points_count = Column(Integer, default=0)  # Number of data points in measurement
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())