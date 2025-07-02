"""
Test configuration and fixtures for Djobea AI
Comprehensive test infrastructure for production readiness testing
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.database_models import (
    User, Provider, ServiceRequest, Transaction, AdminUser, Conversation
)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test function"""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_client():
    """Create a test client with database override"""
    return TestClient(app)


@pytest.fixture(scope="function")
def mock_external_services():
    """Mock all external services for testing"""
    with patch('app.services.ai_service.AIService.extract_service_request') as mock_ai, \
         patch('app.services.whatsapp_service.WhatsAppService.send_message') as mock_whatsapp, \
         patch('app.services.monetbil_service.MonetbilService.create_payment') as mock_payment:
        
        # Configure mocks
        mock_ai.return_value = {
            "confidence": 0.9,
            "service_type": "plomberie",
            "description": "Test service request",
            "location": "Bonamoussadi",
            "urgency": "normal",
            "preferred_time": "maintenant"
        }
        
        mock_whatsapp.return_value = True
        
        mock_payment.return_value = {
            "success": True,
            "payment_url": "https://api.monetbil.com/pay/test123",
            "payment_reference": "test_ref_123",
            "transaction_id": 1
        }
        
        yield {
            "ai": mock_ai,
            "whatsapp": mock_whatsapp,
            "payment": mock_payment
        }


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def security_test_headers():
    """Headers for security testing"""
    return {
        "User-Agent": "DjobeaAI-Test/1.0",
        "X-Forwarded-For": "127.0.0.1",
        "X-Real-IP": "127.0.0.1"
    }


@pytest.fixture(scope="function")
def cameroon_test_data():
    """Cameroon-specific test data"""
    return {
        "phone_numbers": [
            "+237690000001",  # MTN
            "+237650000001",  # Orange
            "+237670000001"   # Express Union
        ],
        "locations": [
            "Bonamoussadi",
            "Akwa",
            "Bonapriso",
            "Deido",
            "New Bell"
        ],
        "service_types": [
            "plomberie",
            "électricité",
            "réparation électroménager"
        ],
        "messages": {
            "french": [
                "J'ai un problème de plomberie",
                "Mon robinet fuit",
                "Besoin d'un électricien urgente"
            ],
            "pidgin": [
                "Light don go for my house",
                "Water dey pour for kitchen",
                "Na urgent something"
            ],
            "english": [
                "I need a plumber",
                "Electrical problem in my house",
                "Urgent repair needed"
            ]
        }
    }


def override_get_db(test_db):
    """Override the get_db dependency"""
    def _override():
        try:
            yield test_db
        finally:
            pass
    return _override


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment for each test"""
    # Clear any existing dependency overrides
    app.dependency_overrides.clear()
    
    yield
    
    # Clean up after test
    app.dependency_overrides.clear()


# Custom assertions for testing
class CustomAssertions:
    """Custom assertion methods for domain-specific testing"""
    
    @staticmethod
    def assert_cameroon_phone_number(phone_number: str):
        """Assert phone number is valid Cameroon format"""
        assert phone_number.startswith("+237"), f"Invalid Cameroon phone: {phone_number}"
        assert len(phone_number) == 13, f"Invalid length: {phone_number}"
        
        # Check prefixes
        valid_prefixes = [
            "690", "691", "692", "693", "694", "695", "696", "697", "698", "699",  # MTN
            "650", "651", "652", "653", "654", "655", "656", "657", "658", "659",  # Orange
            "670", "671", "672", "673", "674", "675", "676", "677", "678", "679"   # Others
        ]
        prefix = phone_number[4:7]
        assert prefix in valid_prefixes, f"Invalid prefix: {prefix}"
    
    @staticmethod
    def assert_service_request_valid(request):
        """Assert service request is valid"""
        assert request.service_type in ["plomberie", "électricité", "réparation électroménager"]
        assert request.location is not None
        assert len(request.description) > 0
        assert request.urgency in ["normal", "urgent", "très urgent"]
    
    @staticmethod
    def assert_transaction_amounts_valid(transaction):
        """Assert transaction amounts are valid"""
        assert transaction.amount > 0
        assert transaction.commission == transaction.amount * 0.15
        assert transaction.provider_payout == transaction.amount - transaction.commission
        assert transaction.amount == transaction.commission + transaction.provider_payout


# Make custom assertions available as pytest fixture
@pytest.fixture
def assert_custom():
    """Custom assertion methods"""
    return CustomAssertions