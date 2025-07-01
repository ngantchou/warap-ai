from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
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
    CANCELLED = "annulée"

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

class Provider(Base):
    """Service provider model"""
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    whatsapp_id = Column(String(50), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    services = Column(JSON, nullable=False)  # List of services offered
    coverage_areas = Column(JSON, nullable=False)  # List of areas covered
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    rating = Column(Float, default=0.0)
    total_jobs = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    requests = relationship("ServiceRequest", back_populates="provider")

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
    
    # Status and timestamps
    status = Column(String(20), default=RequestStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Financial
    estimated_cost = Column(Float, nullable=True)
    final_cost = Column(Float, nullable=True)
    commission_amount = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="requests")
    provider = relationship("Provider", back_populates="requests")

class Conversation(Base):
    """Conversation log for debugging and improvement"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    
    message_type = Column(String(20), nullable=False)  # incoming, outgoing
    message_content = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")

class SystemLog(Base):
    """System logs for monitoring and debugging"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    component = Column(String(50), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def init_db(engine):
    """Initialize database tables"""
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
