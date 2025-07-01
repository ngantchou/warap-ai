"""
Unit tests for database models
"""
import pytest
from datetime import datetime
from models import User, Provider, ServiceRequest, RequestStatus, ServiceType


def test_user_creation():
    """Test user model creation"""
    user = User(
        whatsapp_id="whatsapp:+237123456789",
        name="Test User",
        phone_number="+237123456789"
    )
    
    assert user.whatsapp_id == "whatsapp:+237123456789"
    assert user.name == "Test User"
    assert user.phone_number == "+237123456789"


def test_provider_creation():
    """Test provider model creation"""
    provider = Provider(
        name="Test Provider",
        whatsapp_id="whatsapp:+237987654321",
        phone_number="+237987654321",
        services=["plomberie", "électricité"],
        coverage_areas=["Bonamoussadi", "Akwa"],
        is_available=True,
        is_active=True,
        rating=4.5,
        total_jobs=10
    )
    
    assert provider.name == "Test Provider"
    assert "plomberie" in provider.services
    assert provider.is_available is True
    assert provider.rating == 4.5


def test_service_request_creation():
    """Test service request model creation"""
    request = ServiceRequest(
        user_id=1,
        service_type=ServiceType.PLUMBING,
        description="Robinet qui fuit",
        location="Bonamoussadi",
        preferred_time="Ce soir",
        urgency="urgent",
        status=RequestStatus.PENDING
    )
    
    assert request.service_type == ServiceType.PLUMBING
    assert request.description == "Robinet qui fuit"
    assert request.status == RequestStatus.PENDING
    assert request.urgency == "urgent"


def test_service_type_enum():
    """Test service type enum values"""
    assert ServiceType.PLUMBING == "plomberie"
    assert ServiceType.ELECTRICAL == "électricité"
    assert ServiceType.APPLIANCE_REPAIR == "réparation électroménager"


def test_request_status_enum():
    """Test request status enum values"""
    assert RequestStatus.PENDING == "en attente"
    assert RequestStatus.ASSIGNED == "assignée"
    assert RequestStatus.IN_PROGRESS == "en cours"
    assert RequestStatus.COMPLETED == "terminée"
    assert RequestStatus.CANCELLED == "annulée"