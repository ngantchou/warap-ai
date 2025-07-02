"""
Cultural and Emotional Intelligence Models for Djobea AI
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.models.database_models import Base


class CulturalContext(Base):
    """Cultural context and local information database"""
    __tablename__ = "cultural_context"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location context
    region = Column(String(100), nullable=False)  # Douala, Yaoundé, etc.
    district = Column(String(100), nullable=True)  # Bonamoussadi, Akwa, etc.
    neighborhood = Column(String(100), nullable=True)
    
    # Cultural elements
    primary_languages = Column(JSON, nullable=False)  # ["français", "english", "duala"]
    local_dialects = Column(JSON, nullable=True)  # ["duala", "ewondo", "bamileke"]
    common_expressions = Column(JSON, nullable=True)  # Local sayings and expressions
    greeting_patterns = Column(JSON, nullable=False)  # Time-based greetings
    
    # Social norms
    respect_hierarchy = Column(JSON, nullable=True)  # Elder/authority respect patterns
    community_values = Column(JSON, nullable=True)  # Collective vs individual focus
    business_customs = Column(JSON, nullable=True)  # Local business practices
    religious_considerations = Column(JSON, nullable=True)  # Christian, Muslim, traditional
    
    # Local characteristics
    economic_level = Column(String(20), nullable=True)  # low, middle, high
    education_level = Column(String(20), nullable=True)  # primary, secondary, university
    technology_adoption = Column(String(20), nullable=True)  # low, medium, high
    service_expectations = Column(JSON, nullable=True)  # Expected service standards
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CulturalCalendar(Base):
    """Cultural calendar with holidays, events, and seasonal information"""
    __tablename__ = "cultural_calendar"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Event details
    event_name = Column(String(200), nullable=False)
    event_type = Column(String(50), nullable=False)  # holiday, religious, cultural, seasonal
    description = Column(Text, nullable=True)
    
    # Timing
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50), nullable=True)  # yearly, monthly, etc.
    
    # Cultural significance
    religious_affiliation = Column(String(50), nullable=True)  # Christian, Muslim, traditional
    cultural_groups = Column(JSON, nullable=True)  # Affected cultural groups
    celebration_level = Column(String(20), nullable=True)  # national, regional, local
    
    # Business impact
    affects_business = Column(Boolean, default=False)
    service_modifications = Column(JSON, nullable=True)  # How services are affected
    communication_adjustments = Column(JSON, nullable=True)  # Message adaptations
    
    # Location relevance
    regions = Column(JSON, nullable=True)  # Relevant regions
    urban_rural = Column(String(20), nullable=True)  # urban, rural, both
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmotionalProfile(Base):
    """User emotional profile and state tracking"""
    __tablename__ = "emotional_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Reference to user
    
    # Current emotional state
    current_mood = Column(String(50), nullable=True)  # calm, stressed, excited, frustrated
    stress_level = Column(Float, default=0.0)  # 0.0 to 1.0
    frustration_level = Column(Float, default=0.0)  # 0.0 to 1.0
    satisfaction_level = Column(Float, default=0.5)  # 0.0 to 1.0
    
    # Communication preferences
    preferred_tone = Column(String(50), default="respectful")  # formal, casual, respectful
    response_style = Column(String(50), default="empathetic")  # direct, empathetic, encouraging
    cultural_sensitivity = Column(String(50), default="high")  # low, medium, high
    
    # Behavioral patterns
    typical_response_time = Column(String(50), nullable=True)  # immediate, slow, varied
    communication_frequency = Column(String(50), nullable=True)  # frequent, occasional, rare
    problem_escalation_tendency = Column(String(50), nullable=True)  # quick, moderate, patient
    
    # Success patterns
    celebrates_small_wins = Column(Boolean, default=True)
    appreciates_encouragement = Column(Boolean, default=True)
    values_community_feedback = Column(Boolean, default=True)
    
    # Cultural context
    cultural_context_id = Column(Integer, nullable=True)  # Reference to cultural context
    language_preference = Column(String(20), default="français")
    dialect_usage = Column(JSON, nullable=True)  # Preferred local expressions
    
    # Analysis metadata
    last_analysis = Column(DateTime(timezone=True), nullable=True)
    confidence_score = Column(Float, default=0.5)  # AI confidence in profile
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Note: Relationships will be handled via explicit queries due to complex foreign key dependencies


class ConversationEmotion(Base):
    """Emotional analysis of individual conversations"""
    __tablename__ = "conversation_emotions"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, nullable=False)  # Reference to conversation
    user_id = Column(Integer, nullable=False)          # Reference to user
    
    # Detected emotions
    primary_emotion = Column(String(50), nullable=False)  # joy, fear, anger, sadness, surprise
    emotion_intensity = Column(Float, nullable=False)  # 0.0 to 1.0
    secondary_emotions = Column(JSON, nullable=True)  # Additional emotions detected
    
    # Sentiment analysis
    sentiment_score = Column(Float, nullable=False)  # -1.0 to 1.0
    confidence_level = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Context indicators
    urgency_detected = Column(Boolean, default=False)
    stress_indicators = Column(JSON, nullable=True)  # Specific stress signals
    politeness_level = Column(Float, default=0.5)  # 0.0 to 1.0
    
    # Cultural markers
    cultural_expressions_used = Column(JSON, nullable=True)  # Local expressions detected
    respect_markers = Column(JSON, nullable=True)  # Formal/respect language
    community_references = Column(JSON, nullable=True)  # Family/community mentions
    
    # Response adaptation
    recommended_tone = Column(String(50), nullable=False)
    empathy_level = Column(String(50), nullable=False)  # low, medium, high
    cultural_sensitivity_needed = Column(String(50), default="medium")
    
    # Analysis metadata
    ai_model_version = Column(String(50), nullable=False)
    analysis_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships will be handled by back-references from foreign keys


class CommunityIntegration(Base):
    """Community leaders, influencers, and local business integration"""
    __tablename__ = "community_integration"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Entity details
    entity_type = Column(String(50), nullable=False)  # leader, influencer, business, organization
    name = Column(String(200), nullable=False)
    title = Column(String(100), nullable=True)  # Chief, Pastor, President, etc.
    
    # Contact information
    phone_number = Column(String(20), nullable=True)
    whatsapp_id = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    
    # Location and influence
    region = Column(String(100), nullable=False)
    districts = Column(JSON, nullable=True)  # Areas of influence
    influence_radius = Column(Float, nullable=True)  # Kilometers
    
    # Community role
    specialties = Column(JSON, nullable=True)  # Areas of expertise/influence
    languages_spoken = Column(JSON, nullable=False)
    cultural_affiliations = Column(JSON, nullable=True)
    religious_role = Column(String(100), nullable=True)
    
    # Partnership details
    partnership_type = Column(String(50), nullable=True)  # referral, endorsement, collaboration
    partnership_status = Column(String(20), default="potential")  # potential, active, inactive
    referral_commission = Column(Float, nullable=True)  # If applicable
    
    # Reputation and trust
    community_trust_level = Column(String(20), default="high")  # low, medium, high
    endorsement_value = Column(Float, default=0.5)  # 0.0 to 1.0
    testimonials = Column(JSON, nullable=True)  # Community testimonials
    
    # Engagement metrics
    referrals_made = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # Success rate of referrals
    last_interaction = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EmotionalResponse(Base):
    """Emotional response templates and patterns"""
    __tablename__ = "emotional_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Response context
    trigger_emotion = Column(String(50), nullable=False)  # frustration, excitement, fear
    trigger_situation = Column(String(100), nullable=False)  # emergency, success, delay
    severity_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Cultural context
    cultural_group = Column(String(50), nullable=True)  # duala, bamileke, ewondo, general
    language = Column(String(20), nullable=False, default="français")
    formality_level = Column(String(20), nullable=False)  # casual, respectful, formal
    
    # Response content
    response_template = Column(Text, nullable=False)
    alternative_responses = Column(JSON, nullable=True)  # Variations
    empathy_phrases = Column(JSON, nullable=True)  # Empathetic expressions
    cultural_expressions = Column(JSON, nullable=True)  # Local sayings/expressions
    
    # Response characteristics
    tone = Column(String(50), nullable=False)  # comforting, encouraging, celebratory
    urgency_level = Column(String(20), nullable=False)  # immediate, prompt, routine
    follow_up_recommended = Column(Boolean, default=False)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    effectiveness_rating = Column(Float, default=0.0)  # User feedback-based
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_by = Column(String(100), nullable=True)  # AI or human creator
    validated_by_community = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CulturalSensitivityRule(Base):
    """Cultural sensitivity rules and guidelines"""
    __tablename__ = "cultural_sensitivity_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Rule definition
    rule_name = Column(String(100), nullable=False)
    rule_category = Column(String(50), nullable=False)  # religious, social, business, linguistic
    description = Column(Text, nullable=False)
    
    # Scope
    applicable_regions = Column(JSON, nullable=True)
    cultural_groups = Column(JSON, nullable=True)
    religious_groups = Column(JSON, nullable=True)
    age_groups = Column(JSON, nullable=True)  # elder, adult, youth
    
    # Rule details
    prohibited_words = Column(JSON, nullable=True)  # Words to avoid
    required_expressions = Column(JSON, nullable=True)  # Must-use expressions
    tone_requirements = Column(JSON, nullable=True)  # Required tone elements
    timing_considerations = Column(JSON, nullable=True)  # When rule applies
    
    # Implementation
    severity = Column(String(20), nullable=False)  # warning, error, critical
    auto_correction = Column(Boolean, default=False)  # Auto-fix if possible
    alternative_suggestions = Column(JSON, nullable=True)
    
    # Examples
    good_examples = Column(JSON, nullable=True)  # Correct usage examples
    bad_examples = Column(JSON, nullable=True)  # Incorrect usage examples
    
    # Status
    is_active = Column(Boolean, default=True)
    priority_level = Column(Integer, default=1)  # 1=highest, 5=lowest
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())