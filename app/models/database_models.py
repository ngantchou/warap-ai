from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class ServiceType(str, Enum):
    PLUMBING = "plomberie"
    ELECTRICAL = "électricité"
    APPLIANCE_REPAIR = "réparation électroménager"

class RequestStatus(str, Enum):
    PENDING = "en attente"
    ASSIGNED = "assignée"
    IN_PROGRESS = "en cours"
    COMPLETED = "terminée"
    PAYMENT_PENDING = "paiement en attente"
    PAYMENT_COMPLETED = "paiement terminé"
    CANCELLED = "annulée"


class TransactionStatus(str, Enum):
    PENDING = "en attente"
    INITIATED = "initiée"
    PROCESSING = "en cours"
    COMPLETED = "terminée"
    FAILED = "échouée"
    CANCELLED = "annulée"
    REFUNDED = "remboursée"


class AdminRole(str, Enum):
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class ActionType(str, Enum):
    STATUS_CHECK = "status_check"
    MODIFY_REQUEST = "modify_request"
    CANCEL_REQUEST = "cancel_request"
    HELP_REQUEST = "help_request"
    PROVIDER_PROFILE = "provider_profile"
    CONTACT_PROVIDER = "contact_provider"


class SupportTicketStatus(str, Enum):
    OPEN = "open"


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class ProblemSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    EMERGENCY = "emergency"


class PhotoType(str, Enum):
    BEFORE = "before"
    DURING = "during"
    AFTER = "after"
    OVERVIEW = "overview"
    DETAIL = "detail"
    ANGLE1 = "angle1"
    ANGLE2 = "angle2"
    ANGLE3 = "angle3"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class User(Base):
    """User model for WhatsApp users"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    whatsapp_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    requests = relationship("ServiceRequest", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    sessions = relationship("ConversationSession", back_populates="user")
    modifications = relationship("RequestModification", back_populates="user")
    support_tickets = relationship("SupportTicket", back_populates="user")
    user_actions = relationship("UserAction", back_populates="user")
    communication_logs = relationship("CommunicationLog", back_populates="user")

class Provider(Base):
    """Service provider model with comprehensive profile features"""
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    whatsapp_id = Column(String(50), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    services = Column(JSON, nullable=False)  # List of services offered
    coverage_areas = Column(JSON, nullable=False)  # List of areas covered
    
    # Add single service_type field for backward compatibility
    service_type = Column(String(50), nullable=True)  # Primary service type for compatibility
    location = Column(String(100), nullable=True)  # Primary location for compatibility 
    coverage_zone = Column(String(100), nullable=True)  # Primary coverage zone for compatibility
    
    # Basic status and metrics
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="active")  # active, inactive, suspended
    rating = Column(Float, default=0.0)
    total_jobs = Column(Integer, default=0)
    
    # Enhanced profile information
    years_experience = Column(Integer, default=0)
    specialties = Column(JSON, nullable=True)  # Detailed specializations
    profile_photo_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    certifications = Column(JSON, nullable=True)  # List of certifications
    
    # Performance metrics
    response_time_avg = Column(Float, default=0.0)  # Average response time in minutes
    acceptance_rate = Column(Float, default=0.0)  # Percentage of accepted requests
    completion_rate = Column(Float, default=0.0)  # Percentage of completed jobs
    last_active = Column(DateTime(timezone=True), nullable=True)
    
    # Trust and verification
    verification_status = Column(String(20), default="unverified")  # verified, pending, unverified
    verification_documents = Column(JSON, nullable=True)  # Document URLs and types
    insurance_verified = Column(Boolean, default=False)
    id_verified = Column(Boolean, default=False)
    
    # Work preferences
    preferred_hours = Column(JSON, nullable=True)  # Working hours preference
    emergency_availability = Column(Boolean, default=False)  # Available for urgent requests
    minimum_job_value = Column(Float, default=0.0)  # Minimum job value they accept
    
    # Public profile settings
    public_profile_slug = Column(String(100), unique=True, nullable=True, index=True)
    profile_views = Column(Integer, default=0)
    profile_shares = Column(Integer, default=0)
    is_profile_public = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    requests = relationship("ServiceRequest", back_populates="provider")
    reviews = relationship("ProviderReview", back_populates="provider")
    photos = relationship("ProviderPhoto", back_populates="provider")
    availability_schedule = relationship("ProviderAvailability", back_populates="provider")
    
    @property
    def trust_score(self) -> float:
        """Calculate trust score based on various factors"""
        score = 0.0
        
        # Base score from rating (0-50 points)
        if self.rating > 0:
            score += (self.rating / 5.0) * 50
        
        # Verification bonus (0-20 points)
        if self.verification_status == "verified":
            score += 10
        if self.id_verified:
            score += 5
        if self.insurance_verified:
            score += 5
        
        # Experience bonus (0-15 points)
        experience_bonus = min(self.years_experience * 2, 15)
        score += experience_bonus
        
        # Performance bonus (0-15 points)
        if self.completion_rate > 0:
            score += (self.completion_rate / 100) * 15
        
        return min(score, 100.0)
    
    @property
    def response_time_category(self) -> str:
        """Categorize response time for display"""
        if self.response_time_avg <= 5:
            return "Très rapide"
        elif self.response_time_avg <= 15:
            return "Rapide"
        elif self.response_time_avg <= 30:
            return "Moyen"
        else:
            return "Lent"
    
    @property
    def is_online(self) -> bool:
        """Check if provider is currently online (active in last 30 minutes)"""
        if not self.last_active:
            return False
        from datetime import datetime, timedelta
        return datetime.utcnow() - self.last_active < timedelta(minutes=30)
    
    @property
    def trust_score(self) -> float:
        """Calculate comprehensive trust score based on multiple factors"""
        score = 0.0
        max_score = 100.0
        
        # Base rating score (40% of total)
        if self.rating:
            score += (self.rating / 5.0) * 40
        
        # Experience score (20% of total)
        if hasattr(self, 'years_experience') and self.years_experience:
            experience_score = min(self.years_experience / 10.0, 1.0) * 20
            score += experience_score
        
        # Job completion score (15% of total)
        if self.total_jobs:
            completion_score = min(self.total_jobs / 100.0, 1.0) * 15
            score += completion_score
        
        # Verification score (15% of total)
        verification_score = 0
        if hasattr(self, 'id_verified') and self.id_verified:
            verification_score += 5
        if hasattr(self, 'insurance_verified') and self.insurance_verified:
            verification_score += 5
        if hasattr(self, 'verification_status') and self.verification_status == 'verified':
            verification_score += 5
        score += verification_score
        
        # Performance score (10% of total)
        performance_score = 0
        if hasattr(self, 'acceptance_rate') and self.acceptance_rate:
            performance_score += (self.acceptance_rate / 100.0) * 5
        if hasattr(self, 'completion_rate') and self.completion_rate:
            performance_score += (self.completion_rate / 100.0) * 5
        score += performance_score
        
        return min(score, max_score)

class ProviderReview(Base):
    """Provider review and rating system"""
    __tablename__ = "provider_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    
    # Review details
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    service_quality = Column(Integer, nullable=True)  # 1-5
    punctuality = Column(Integer, nullable=True)  # 1-5
    professionalism = Column(Integer, nullable=True)  # 1-5
    value_for_money = Column(Integer, nullable=True)  # 1-5
    
    # Metadata
    is_verified = Column(Boolean, default=True)  # Verified purchase
    is_featured = Column(Boolean, default=False)  # Featured review
    helpful_count = Column(Integer, default=0)  # How many found this helpful
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    provider = relationship("Provider", back_populates="reviews")
    user = relationship("User")
    request = relationship("ServiceRequest")

class ProviderPhoto(Base):
    """Provider work photos and portfolio"""
    __tablename__ = "provider_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Photo details
    photo_url = Column(String(500), nullable=False)
    photo_type = Column(String(20), nullable=False)  # profile, work, before, after, certificate
    title = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    service_type = Column(String(50), nullable=True)  # Related service type
    
    # Display settings
    is_featured = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    provider = relationship("Provider", back_populates="photos")

class ProviderCertification(Base):
    """Provider certifications and qualifications"""
    __tablename__ = "provider_certifications"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Certification details
    name = Column(String(200), nullable=False)
    issuing_authority = Column(String(200), nullable=False)
    certificate_number = Column(String(100), nullable=True)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    certificate_url = Column(String(500), nullable=True)  # Document URL
    
    # Display
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    provider = relationship("Provider")

class ProviderSpecialization(Base):
    """Detailed provider specializations"""
    __tablename__ = "provider_specializations"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Specialization details
    service_type = Column(String(50), nullable=False)  # plomberie, électricité, etc.
    specialization = Column(String(100), nullable=False)  # specific skill
    skill_level = Column(String(20), default="intermediate")  # beginner, intermediate, expert
    years_experience = Column(Integer, default=0)
    
    # Pricing
    min_rate = Column(Float, nullable=True)
    max_rate = Column(Float, nullable=True)
    rate_type = Column(String(20), default="fixed")  # hourly, fixed, negotiable
    
    # Availability
    is_available = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    provider = relationship("Provider")

class ProviderProfileView(Base):
    """Track provider profile views for analytics"""
    __tablename__ = "provider_profile_views"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # View details
    view_date = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(50), nullable=True)  # whatsapp, direct, search, etc.
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    referrer = Column(String(500), nullable=True)
    
    # Session tracking
    session_id = Column(String(100), nullable=True)
    
    # Relationships
    provider = relationship("Provider")

class ServiceRequest(Base):
    """Service request model"""
    __tablename__ = "service_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    
    # Request details
    service_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(200), nullable=False)
    preferred_time = Column(String(100), nullable=True)
    urgency = Column(String(20), default="normal")  # urgent, normal, flexible
    
    # Enhanced scheduling
    scheduling_preference = Column(String(50), nullable=True)  # URGENT, TODAY, TOMORROW_MORNING, etc.
    preferred_time_start = Column(DateTime(timezone=True), nullable=True)
    preferred_time_end = Column(DateTime(timezone=True), nullable=True)
    urgency_supplement = Column(Float, default=0.0)  # Additional cost for urgent requests
    
    # Enhanced location
    landmark_references = Column(Text, nullable=True)  # Nearby landmarks mentioned by user
    location_confirmed = Column(Boolean, default=False)
    location_coordinates = Column(String(100), nullable=True)  # "lat,lng" format
    location_accuracy = Column(String(20), default="approximate")  # exact, approximate, unclear
    
    # Status and timestamps
    status = Column(String(20), default=RequestStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # Confirmed appointment time
    
    # Financial
    estimated_cost = Column(Float, nullable=True)
    final_cost = Column(Float, nullable=True)
    commission_amount = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="requests")
    provider = relationship("Provider", back_populates="requests")
    modifications = relationship("RequestModification", back_populates="request")
    support_tickets = relationship("SupportTicket", back_populates="request")
    user_actions = relationship("UserAction", back_populates="request")
    communication_logs = relationship("CommunicationLog", back_populates="request")
    media_uploads = relationship("MediaUpload", back_populates="service_request")

class Conversation(Base):
    """Enhanced conversation log with action code system for debugging and improvement"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    session_id = Column(String(50), ForeignKey("conversation_sessions.session_id"), nullable=True)  # Link to session
    
    message_type = Column(String(20), nullable=False)  # incoming, outgoing
    message_content = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    
    # Action code system fields
    action_code = Column(String(50), nullable=True)  # Action code executed
    conversation_state = Column(String(50), nullable=True)  # Current conversation state
    confidence_score = Column(Float, nullable=True)  # LLM confidence score
    action_success = Column(Boolean, default=True)  # Whether action executed successfully
    execution_time = Column(Float, nullable=True)  # Action execution time in seconds
    action_metadata = Column(JSON, nullable=True)  # Additional metadata from action execution
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    session = relationship("ConversationSession", back_populates="messages")


class ConversationSession(Base):
    """
    Conversation session with state management and persistence
    """
    __tablename__ = "conversation_sessions"
    
    # Primary identification
    session_id = Column(String(50), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    
    # State management
    current_state = Column(String(20), nullable=False, default="INITIAL")
    previous_state = Column(String(20), nullable=True)
    current_phase = Column(String(20), nullable=True)
    state_history = Column(JSON, nullable=True)  # History of state changes
    
    # Data collection
    collected_data = Column(JSON, nullable=True)  # Structured collected data
    session_metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Conversation history (limited, full history in conversations table)
    conversation_summary = Column(JSON, nullable=True)  # Summary of key exchanges
    
    # Session lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Performance metrics
    metrics = Column(JSON, nullable=True)  # Performance and automation metrics
    
    # Configuration
    max_history_size = Column(Integer, default=10)
    timeout_minutes = Column(Integer, default=120)
    max_collection_attempts = Column(Integer, default=3)
    
    # Status flags
    is_active = Column(Boolean, default=True)
    is_expired = Column(Boolean, default=False)
    escalation_triggered = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Conversation", back_populates="session")
    
    @property
    def is_session_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at
    
    @property
    def session_duration(self) -> timedelta:
        """Get session duration"""
        end_time = self.completed_at or datetime.now()
        return end_time - self.created_at

class SystemLog(Base):
    """System logs for monitoring and debugging"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    component = Column(String(50), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AdminUser(Base):
    """Admin user model for authentication"""
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=AdminRole.ADMIN, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Security fields
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), server_default=func.now())


class SecurityLog(Base):
    """Security events logging"""
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # login, logout, failed_login, etc.
    user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RateLimitLog(Base):
    """Rate limiting tracking"""
    __tablename__ = "rate_limit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(255), nullable=False)  # IP or user ID
    endpoint = Column(String(255), nullable=False)
    requests_count = Column(Integer, default=1)
    window_start = Column(DateTime(timezone=True), server_default=func.now())
    is_blocked = Column(Boolean, default=False)


class Transaction(Base):
    """Transaction model for payment processing with Monetbil"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Financial details
    amount = Column(Float, nullable=False)  # Total amount in XAF
    commission = Column(Float, nullable=False)  # Platform commission
    provider_payout = Column(Float, nullable=False)  # Amount for provider
    currency = Column(String(3), default="XAF", nullable=False)
    
    # Payment references
    payment_reference = Column(String(255), unique=True, index=True, nullable=False)
    monetbil_transaction_id = Column(String(255), nullable=True)
    monetbil_payment_url = Column(String(500), nullable=True)
    
    # Status and timestamps
    status = Column(String(20), default=TransactionStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    service_request = relationship("ServiceRequest")
    customer = relationship("User")
    provider = relationship("Provider")


def init_db(engine):
    """Initialize database tables"""
    # Import provider models to ensure their tables are created
    from app.models import provider_models
    
    # Import dynamic services models to register them
    from app.models.dynamic_services import Zone, ServiceCategory, Service, ServiceZone, DynamicServiceRequest, ServiceSearchLog
    
    Base.metadata.create_all(bind=engine)
    
    # Create some initial data if needed
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as session:
        # Check if we have any providers, if not create some sample ones
        if session.query(Provider).count() == 0:
            sample_providers = [
                Provider(
                    name="Jean Baptiste Plombier",
                    whatsapp_id="+237690000001",
                    phone_number="+237690000001",
                    services=["plomberie"],
                    coverage_areas=["Bonamoussadi"],
                    is_available=True,
                    is_active=True
                ),
                Provider(
                    name="Marie Electricienne",
                    whatsapp_id="+237690000002", 
                    phone_number="+237690000002",
                    services=["électricité"],
                    coverage_areas=["Bonamoussadi"],
                    is_available=True,
                    is_active=True
                ),
                Provider(
                    name="Paul Réparateur",
                    whatsapp_id="+237690000003",
                    phone_number="+237690000003", 
                    services=["réparation électroménager"],
                    coverage_areas=["Bonamoussadi"],
                    is_available=True,
                    is_active=True
                )
            ]
            
            for provider in sample_providers:
                session.add(provider)
            
            session.commit()


class RequestModification(Base):
    """Track modifications made to service requests"""
    __tablename__ = "request_modifications"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_modified = Column(String(50), nullable=False)  # description, location, urgency
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)
    modification_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    request = relationship("ServiceRequest", back_populates="modifications")
    user = relationship("User")


class SupportTicket(Base):
    """Support tickets for complex issues and escalations"""
    __tablename__ = "support_tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default=SupportTicketStatus.OPEN)
    priority = Column(String(10), nullable=False, default="medium")  # low, medium, high, urgent
    assigned_to = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    request = relationship("ServiceRequest", back_populates="support_tickets")
    admin = relationship("AdminUser")


class UserAction(Base):
    """Track user actions for analytics and improvement"""
    __tablename__ = "user_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    action_type = Column(String(30), nullable=False)  # ActionType enum
    action_details = Column(JSON, nullable=True)  # Store additional context
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    request = relationship("ServiceRequest")


class CommunicationLog(Base):
    """Log all communication for audit and improvement"""
    __tablename__ = "communication_log"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    message_type = Column(String(20), nullable=False)  # incoming, outgoing, system
    message_content = Column(Text, nullable=False)
    whatsapp_message_id = Column(String(100), nullable=True)
    delivered = Column(Boolean, nullable=False, default=False)
    read = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    request = relationship("ServiceRequest")

class Landmark(Base):
    """Cameroon landmarks database for location recognition"""
    __tablename__ = "landmarks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    landmark_type = Column(String(50), nullable=False)  # market, hospital, school, pharmacy, etc.
    
    # Location details
    area = Column(String(100), nullable=False)  # Bonamoussadi, Akwa, etc.
    city = Column(String(50), default="Douala")
    coordinates = Column(String(100), nullable=True)  # "lat,lng" format
    address = Column(Text, nullable=True)
    
    # Recognition data
    aliases = Column(JSON, nullable=True)  # Alternative names and references
    common_references = Column(JSON, nullable=True)  # "près du marché", "derrière la pharmacie"
    nearby_landmarks = Column(JSON, nullable=True)  # Related landmarks for context
    
    # Status
    is_active = Column(Boolean, default=True)
    verification_status = Column(String(20), default="unverified")  # verified, unverified, disputed
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ProviderAvailability(Base):
    """Provider availability schedule"""
    __tablename__ = "provider_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Schedule details
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Availability type
    availability_type = Column(String(20), default="regular")  # regular, emergency, flexible
    emergency_supplement = Column(Float, default=0.0)  # Extra cost for emergency hours
    
    # Status
    is_active = Column(Boolean, default=True)
    effective_from = Column(Date, nullable=True)
    effective_until = Column(Date, nullable=True)
    
    # Relationships
    provider = relationship("Provider")

class AppointmentSlot(Base):
    """Appointment booking and scheduling"""
    __tablename__ = "appointment_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    
    # Appointment details
    scheduled_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=120)  # Estimated duration
    
    # Status
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled, completed
    confirmation_method = Column(String(20), nullable=True)  # whatsapp, call, automatic
    
    # Notifications
    reminder_sent = Column(Boolean, default=False)
    confirmation_sent = Column(Boolean, default=False)
    
    # Pricing for time slot
    time_slot_supplement = Column(Float, default=0.0)  # Extra cost for specific time
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    service_request = relationship("ServiceRequest")
    provider = relationship("Provider")

class LocationMatch(Base):
    """Successful location matches for learning and improvement"""
    __tablename__ = "location_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Input and match
    user_input = Column(Text, nullable=False)  # Original user location description
    matched_location = Column(String(200), nullable=False)  # Normalized location
    landmark_id = Column(Integer, ForeignKey("landmarks.id"), nullable=True)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Context
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    user_confirmed = Column(Boolean, default=False)  # User confirmed this match
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    landmark = relationship("Landmark")
    service_request = relationship("ServiceRequest")


class MediaUpload(Base):
    """Media uploads (images, videos, audio) for service requests"""
    __tablename__ = "media_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    
    # Media details
    file_url = Column(String(500), nullable=False)  # S3/Cloud storage URL
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    media_type = Column(String(20), nullable=False)  # image, video, audio
    mime_type = Column(String(100), nullable=False)  # image/jpeg, video/mp4, etc.
    
    # Content details
    duration_seconds = Column(Float, nullable=True)  # For video/audio
    width = Column(Integer, nullable=True)  # For images/video
    height = Column(Integer, nullable=True)  # For images/video
    
    # Photo classification
    photo_type = Column(String(20), nullable=True)  # before, after, overview, detail, etc.
    angle_description = Column(String(200), nullable=True)  # Description of angle/view
    
    # Processing status
    analysis_completed = Column(Boolean, default=False)
    analysis_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    processing_error = Column(Text, nullable=True)
    
    # Security and privacy
    encrypted = Column(Boolean, default=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)  # Auto-cleanup
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    service_request = relationship("ServiceRequest", back_populates="media_uploads")
    visual_analysis = relationship("VisualAnalysis", back_populates="media_upload", uselist=False)


class VisualAnalysis(Base):
    """AI-powered visual analysis results"""
    __tablename__ = "visual_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    media_id = Column(Integer, ForeignKey("media_uploads.id"), nullable=False)
    
    # Problem detection
    detected_problems = Column(JSON, nullable=True)  # List of detected issues
    primary_problem = Column(String(200), nullable=True)
    problem_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Severity assessment
    severity = Column(String(20), nullable=True)  # minor, moderate, major, emergency
    severity_confidence = Column(Float, nullable=True)
    safety_hazards = Column(JSON, nullable=True)  # List of safety concerns
    
    # Technical assessment
    required_expertise = Column(String(100), nullable=True)  # experienced plumber, electrician, etc.
    tools_needed = Column(JSON, nullable=True)  # List of required tools
    materials_needed = Column(JSON, nullable=True)  # List of materials
    estimated_duration = Column(String(50), nullable=True)  # "2-3 hours"
    
    # Cost estimation
    estimated_cost_min = Column(Float, nullable=True)
    estimated_cost_max = Column(Float, nullable=True)
    cost_factors = Column(JSON, nullable=True)  # Factors affecting cost
    
    # Damage assessment
    damage_visible = Column(Boolean, default=False)
    damage_description = Column(Text, nullable=True)
    damage_extent = Column(String(50), nullable=True)  # minor, moderate, extensive
    
    # AI analysis metadata
    ai_model_version = Column(String(50), nullable=True)
    analysis_prompt = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)  # Full AI response
    
    # Quality metrics
    image_quality = Column(String(20), nullable=True)  # excellent, good, fair, poor
    lighting_quality = Column(String(20), nullable=True)
    angle_quality = Column(String(20), nullable=True)
    focus_quality = Column(String(20), nullable=True)
    
    # Recommendations
    additional_photos_needed = Column(JSON, nullable=True)  # Suggested additional angles
    photo_guidance = Column(Text, nullable=True)  # Tips for better photos
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    media_upload = relationship("MediaUpload", back_populates="visual_analysis")


class ProblemPhoto(Base):
    """Categorized photos for different stages of problem resolution"""
    __tablename__ = "problem_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("media_uploads.id"), nullable=False)
    
    # Photo categorization
    photo_type = Column(String(20), nullable=False)  # before, during, after, overview, detail
    stage_description = Column(String(200), nullable=True)
    sequence_number = Column(Integer, default=1)  # Order of photos in sequence
    
    # Analysis results
    analysis_confidence = Column(Float, nullable=True)
    ai_description = Column(Text, nullable=True)
    problem_visible = Column(Boolean, default=True)
    
    # Photo quality assessment
    quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    quality_feedback = Column(Text, nullable=True)
    
    # Comparison features
    comparison_base_photo_id = Column(Integer, ForeignKey("problem_photos.id"), nullable=True)
    progress_percentage = Column(Float, nullable=True)  # For during/after photos
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    service_request = relationship("ServiceRequest")
    media_upload = relationship("MediaUpload")
    comparison_base = relationship("ProblemPhoto", remote_side=[id])


class VisualProgress(Base):
    """Visual progress tracking throughout service lifecycle"""
    __tablename__ = "visual_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    service_request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=False)
    
    # Progress details
    stage = Column(String(50), nullable=False)  # assessment, in_progress, completed, quality_check
    stage_description = Column(String(200), nullable=True)
    progress_percentage = Column(Float, default=0.0)  # 0.0 to 100.0
    
    # Photo documentation
    photo_url = Column(String(500), nullable=True)
    photo_description = Column(Text, nullable=True)
    photo_type = Column(String(20), nullable=True)  # overview, detail, progress, completion
    
    # Provider submission
    submitted_by_provider = Column(Boolean, default=False)
    provider_comments = Column(Text, nullable=True)
    quality_approved = Column(Boolean, default=False)
    
    # Customer verification
    customer_approved = Column(Boolean, default=False)
    customer_feedback = Column(Text, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    service_request = relationship("ServiceRequest")


# Import cultural models to ensure they're registered with the Base
from app.models.cultural_models import *
