"""
Dynamic Services System Models
Database models for zones, service categories, and services with intelligent search
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from app.models.database_models import Base
from app.models.validation_models import (
    ValidationLog, ErrorLog, RetryAttempt, EscalationRecord,
    PerformanceMetrics, ImprovementSuggestion, KeywordUpdate,
    ValidationError, SuggestionFeedback, SystemHealth,
    UserInteraction, AlertConfiguration, AlertHistory
)

class ServiceStatus(str, Enum):
    """Service availability status"""
    AVAILABLE = "available"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    MAINTENANCE = "maintenance"
    DISCONTINUED = "discontinued"

class ZoneType(str, Enum):
    """Geographic zone hierarchy types"""
    COUNTRY = "country"
    REGION = "region"
    CITY = "city"
    DISTRICT = "district"
    NEIGHBORHOOD = "neighborhood"
    STREET = "street"

class Zone(Base):
    """Geographic zones with hierarchical structure"""
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    name_fr = Column(String(200), nullable=True)  # French name
    name_en = Column(String(200), nullable=True)  # English name
    zone_type = Column(String(50), nullable=False)  # ZoneType enum
    parent_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    
    # Geographic data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_km = Column(Float, nullable=True)
    boundary_polygon = Column(JSON, nullable=True)  # GeoJSON polygon
    
    # Hierarchy and search
    level = Column(Integer, default=0)  # 0=country, 1=region, etc.
    full_path = Column(String(500), nullable=True)  # /cameroon/littoral/douala/bonamoussadi
    search_keywords = Column(JSON, nullable=True)  # Alternative names, synonyms
    
    # Metadata
    is_active = Column(Boolean, default=True)
    population = Column(Integer, nullable=True)
    area_km2 = Column(Float, nullable=True)
    timezone = Column(String(50), default="Africa/Douala")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent = relationship("Zone", remote_side=[id], backref="children")
    service_zones = relationship("ServiceZone", back_populates="zone")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_zone_code', 'code'),
        Index('idx_zone_type', 'zone_type'),
        Index('idx_zone_parent', 'parent_id'),
        Index('idx_zone_active', 'is_active'),
        Index('idx_zone_level', 'level'),
    )

class ServiceCategory(Base):
    """Service categories with hierarchical structure"""
    __tablename__ = "service_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    name_fr = Column(String(200), nullable=True)
    name_en = Column(String(200), nullable=True)
    parent_id = Column(Integer, ForeignKey("service_categories.id"), nullable=True)
    
    # Description and metadata
    description = Column(Text, nullable=True)
    description_fr = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    color = Column(String(20), nullable=True)
    
    # Hierarchy
    level = Column(Integer, default=0)
    full_path = Column(String(500), nullable=True)
    search_keywords = Column(JSON, nullable=True)
    
    # Business rules
    is_active = Column(Boolean, default=True)
    requires_quote = Column(Boolean, default=False)
    avg_duration_minutes = Column(Integer, nullable=True)
    base_price_xaf = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent = relationship("ServiceCategory", remote_side=[id], backref="children")
    services = relationship("Service", back_populates="category")
    
    # Indexes
    __table_args__ = (
        Index('idx_category_code', 'code'),
        Index('idx_category_parent', 'parent_id'),
        Index('idx_category_active', 'is_active'),
        Index('idx_category_level', 'level'),
    )

class Service(Base):
    """Individual services with dynamic configuration"""
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    name_fr = Column(String(200), nullable=True)
    name_en = Column(String(200), nullable=True)
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    
    # Service details
    description = Column(Text, nullable=True)
    description_fr = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    
    # Pricing
    base_price_xaf = Column(Float, nullable=True)
    min_price_xaf = Column(Float, nullable=True)
    max_price_xaf = Column(Float, nullable=True)
    price_per_hour_xaf = Column(Float, nullable=True)
    
    # Service configuration
    estimated_duration_minutes = Column(Integer, nullable=True)
    requires_materials = Column(Boolean, default=False)
    requires_quote = Column(Boolean, default=False)
    requires_advance_booking = Column(Boolean, default=False)
    
    # Availability
    status = Column(String(50), default=ServiceStatus.AVAILABLE)
    is_emergency_service = Column(Boolean, default=False)
    availability_24h = Column(Boolean, default=False)
    
    # Search and matching
    search_keywords = Column(JSON, nullable=True)
    synonyms = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Quality metrics
    avg_rating = Column(Float, default=0.0)
    total_bookings = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    category = relationship("ServiceCategory", back_populates="services")
    service_zones = relationship("ServiceZone", back_populates="service")
    
    # Indexes
    __table_args__ = (
        Index('idx_service_code', 'code'),
        Index('idx_service_category', 'category_id'),
        Index('idx_service_status', 'status'),
        Index('idx_service_emergency', 'is_emergency_service'),
        Index('idx_service_rating', 'avg_rating'),
    )

class ServiceZone(Base):
    """Many-to-many relationship between services and zones"""
    __tablename__ = "service_zones"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    
    # Service configuration per zone
    is_available = Column(Boolean, default=True)
    price_adjustment_percent = Column(Float, default=0.0)
    estimated_travel_time_minutes = Column(Integer, nullable=True)
    additional_cost_xaf = Column(Float, default=0.0)
    
    # Availability schedule
    available_days = Column(JSON, nullable=True)  # ["monday", "tuesday", ...]
    available_hours = Column(JSON, nullable=True)  # {"start": "08:00", "end": "18:00"}
    
    # Performance metrics
    demand_score = Column(Float, default=0.0)
    competition_level = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    service = relationship("Service", back_populates="service_zones")
    zone = relationship("Zone", back_populates="service_zones")
    
    # Indexes
    __table_args__ = (
        Index('idx_service_zone_service', 'service_id'),
        Index('idx_service_zone_zone', 'zone_id'),
        Index('idx_service_zone_available', 'is_available'),
    )

class DynamicServiceRequest(Base):
    """Service requests with dynamic service matching"""
    __tablename__ = "dynamic_service_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    
    # Request details
    original_query = Column(Text, nullable=False)
    matched_keywords = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Status and tracking
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    service = relationship("Service", foreign_keys=[service_id])
    zone = relationship("Zone", foreign_keys=[zone_id])

class ServiceSearchLog(Base):
    """Log of service searches for analytics and improvement"""
    __tablename__ = "service_search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    matched_service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    
    # Search results
    confidence_score = Column(Float, nullable=True)
    suggestions = Column(JSON, nullable=True)
    was_successful = Column(Boolean, default=False)
    
    # Context
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), nullable=True)
    language = Column(String(10), default="fr")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    matched_service = relationship("Service", foreign_keys=[matched_service_id])
    zone = relationship("Zone", foreign_keys=[zone_id])
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_search_query', 'query'),
        Index('idx_search_success', 'was_successful'),
        Index('idx_search_confidence', 'confidence_score'),
        Index('idx_search_created', 'created_at'),
    )