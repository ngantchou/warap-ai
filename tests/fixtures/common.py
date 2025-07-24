"""
Common test fixtures and utilities for Djobea AI
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Common test data
SAMPLE_PHONE_NUMBERS = [
    "237691924172",
    "237691924173", 
    "237691924174",
    "237691924175"
]

SAMPLE_SERVICES = [
    {"name": "Plomberie", "type": "plomberie", "price_min": 5000, "price_max": 15000},
    {"name": "Électricité", "type": "electricite", "price_min": 3000, "price_max": 10000},
    {"name": "Électroménager", "type": "electromenager", "price_min": 2000, "price_max": 8000}
]

SAMPLE_LOCATIONS = [
    "Bonamoussadi",
    "Douala",
    "Makepe",
    "Akwa"
]

def create_test_user(phone_number: str = None) -> Dict[str, Any]:
    """Create a test user object"""
    return {
        "phone_number": phone_number or SAMPLE_PHONE_NUMBERS[0],
        "name": f"Test User {phone_number or '001'}",
        "created_at": datetime.utcnow(),
        "is_active": True
    }

def create_test_service_request(
    service_type: str = "plomberie",
    location: str = "Bonamoussadi",
    status: str = "pending"
) -> Dict[str, Any]:
    """Create a test service request"""
    return {
        "service_type": service_type,
        "location": location,
        "description": f"Test {service_type} request",
        "status": status,
        "created_at": datetime.utcnow(),
        "urgency": "normale"
    }

def create_test_provider(
    service_type: str = "plomberie",
    location: str = "Bonamoussadi"
) -> Dict[str, Any]:
    """Create a test provider"""
    return {
        "name": f"Test Provider {service_type}",
        "service_type": service_type,
        "location": location,
        "phone_number": f"237{service_type[:3]}123456",
        "rating": 4.5,
        "is_available": True
    }

@pytest.fixture
def sample_conversation_context():
    """Sample conversation context for testing"""
    return {
        "user_id": "test_user_001",
        "phone_number": SAMPLE_PHONE_NUMBERS[0],
        "conversation_state": "information_gathering",
        "accumulated_data": {
            "service_type": "plomberie",
            "location": "Bonamoussadi",
            "description": "Fuite d'eau dans la cuisine"
        }
    }

@pytest.fixture
def auth_headers():
    """Authentication headers for API testing"""
    return {
        "Authorization": "Bearer test_token_123",
        "Content-Type": "application/json"
    }

class TestUtils:
    """Utility class for testing"""
    
    @staticmethod
    def wait_for_condition(condition_func, timeout: int = 30, interval: float = 0.5):
        """Wait for a condition to be true"""
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            if condition_func():
                return True
            asyncio.sleep(interval)
        return False
    
    @staticmethod
    def assert_response_format(response: Dict[str, Any], expected_keys: list):
        """Assert that response has expected format"""
        assert isinstance(response, dict), "Response should be a dictionary"
        for key in expected_keys:
            assert key in response, f"Response missing key: {key}"