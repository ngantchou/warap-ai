"""
Global test configuration for Djobea AI
"""

import pytest
import asyncio
import os
from pathlib import Path
import sys

# Add app directory to path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///test_djobea.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_app():
    """Create test app instance"""
    from app.main import app
    app.config["TESTING"] = True
    return app

@pytest.fixture(scope="function")
def test_client(test_app):
    """Create test client"""
    from fastapi.testclient import TestClient
    return TestClient(test_app)

@pytest.fixture(scope="function")
def test_db():
    """Create test database session"""
    from app.database import get_db
    # Create test database session
    # This would be implemented based on your database setup
    pass

@pytest.fixture(scope="function")
def auth_token():
    """Create test authentication token"""
    return "test_token_123456"

@pytest.fixture(scope="function")
def sample_user():
    """Create sample user for testing"""
    return {
        "id": "test_user_001",
        "phone_number": "237691924172",
        "name": "Test User",
        "created_at": "2025-01-01T00:00:00Z"
    }

@pytest.fixture(scope="function")
def sample_service_request():
    """Create sample service request"""
    return {
        "id": "req_001",
        "service_type": "plomberie",
        "location": "Bonamoussadi",
        "description": "Fuite d'eau dans la cuisine",
        "status": "pending",
        "created_at": "2025-01-01T00:00:00Z"
    }

@pytest.fixture(scope="function")
def api_headers(auth_token):
    """Create API headers with authentication"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

# Test cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test"""
    yield
    # Add cleanup logic here
    pass