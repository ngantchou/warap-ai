"""
Provider models for the Djobea AI platform
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from enum import Enum

class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class ProviderAvailability(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"

class PerformanceStatus(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    WARNING = "warning"
    POOR = "poor"

class ContactMethod(str, Enum):
    CALL = "call"
    WHATSAPP = "whatsapp"
    EMAIL = "email"

class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"

class SortBy(str, Enum):
    NAME = "name"
    RATING = "rating"
    MISSIONS = "missions"
    JOIN_DATE = "joinDate"
    LAST_ACTIVITY = "lastActivity"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class WorkingHours(BaseModel):
    start: str = Field(..., pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    end: str = Field(..., pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")

class Location(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None

class Pricing(BaseModel):
    hourlyRate: Optional[float] = Field(None, ge=0)
    fixedRates: Optional[Dict[str, float]] = Field(None, description="Service-specific fixed rates")

class Provider(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    whatsapp: Optional[str] = None
    services: List[str]
    coverageAreas: List[str]
    specialty: str
    zone: str
    rating: float = Field(..., ge=0, le=5)
    reviewCount: int = Field(..., ge=0)
    totalMissions: int = Field(..., ge=0)
    completedJobs: Optional[int] = Field(None, ge=0)
    cancelledJobs: Optional[int] = Field(None, ge=0)
    successRate: Optional[float] = Field(None, ge=0, le=100)
    responseTime: Optional[float] = Field(None, ge=0, description="Average response time in minutes")
    performanceStatus: Optional[PerformanceStatus] = None
    status: ProviderStatus
    availability: ProviderAvailability
    joinDate: date
    lastActivity: Optional[datetime] = None
    hourlyRate: Optional[float] = Field(None, ge=0)
    experience: Optional[int] = Field(None, ge=0)
    acceptanceRate: Optional[float] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    profileImage: Optional[str] = Field(None, description="Profile image URL")
    certifications: Optional[List[str]] = None
    location: Optional[Location] = None
    workingHours: Optional[Dict[str, Optional[WorkingHours]]] = None
    pricing: Optional[Pricing] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

class CreateProviderRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    whatsapp: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    services: List[str] = Field(..., min_items=1)
    coverageAreas: List[str] = Field(..., min_items=1)
    specialty: str = Field(..., min_length=1, max_length=50)
    zone: str = Field(..., min_length=1, max_length=50)
    hourlyRate: Optional[float] = Field(None, ge=0)
    experience: Optional[int] = Field(None, ge=0, le=50)
    description: Optional[str] = Field(None, max_length=1000)
    certifications: Optional[List[str]] = None
    workingHours: Optional[Dict[str, Optional[WorkingHours]]] = None

class UpdateProviderRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    whatsapp: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    services: Optional[List[str]] = Field(None, min_items=1)
    coverageAreas: Optional[List[str]] = Field(None, min_items=1)
    specialty: Optional[str] = Field(None, min_length=1, max_length=50)
    zone: Optional[str] = Field(None, min_length=1, max_length=50)
    hourlyRate: Optional[float] = Field(None, ge=0)
    experience: Optional[int] = Field(None, ge=0, le=50)
    description: Optional[str] = Field(None, max_length=1000)
    certifications: Optional[List[str]] = None
    status: Optional[ProviderStatus] = None
    availability: Optional[ProviderAvailability] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    performanceStatus: Optional[PerformanceStatus] = None
    workingHours: Optional[Dict[str, Optional[WorkingHours]]] = None

class UpdateProviderStatusRequest(BaseModel):
    status: ProviderStatus

class ContactProviderRequest(BaseModel):
    method: ContactMethod
    message: Optional[str] = Field(None, max_length=1000)

class AvailableProvidersRequest(BaseModel):
    serviceType: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    date: Optional[datetime] = None
    urgency: Optional[bool] = None

class ProvidersFilters(BaseModel):
    page: Optional[int] = Field(None, ge=1)
    limit: Optional[int] = Field(None, ge=1, le=100)
    search: Optional[str] = Field(None, max_length=255)
    status: Optional[ProviderStatus] = None
    specialty: Optional[str] = None
    zone: Optional[str] = None
    minRating: Optional[float] = Field(None, ge=0, le=5)
    services: Optional[List[str]] = None
    availability: Optional[ProviderAvailability] = None
    sortBy: Optional[SortBy] = None
    sortOrder: Optional[SortOrder] = None
    dateRange: Optional[Dict[str, date]] = None

class ExportProvidersRequest(BaseModel):
    filters: Optional[ProvidersFilters] = None
    format: Optional[ExportFormat] = ExportFormat.CSV

class Pagination(BaseModel):
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    totalPages: int = Field(..., ge=0)
    hasNext: bool
    hasPrev: bool

class ProvidersStats(BaseModel):
    total: int = Field(..., ge=0)
    active: int = Field(..., ge=0)
    inactive: int = Field(..., ge=0)
    suspended: int = Field(..., ge=0)
    available: int = Field(..., ge=0)
    avgRating: float = Field(..., ge=0, le=5)
    newThisMonth: int = Field(..., ge=0)
    topPerformers: List[Provider] = Field(default_factory=list)

class ProvidersResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None

class ProviderResponse(BaseModel):
    success: bool
    data: Provider
    message: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None