"""
Unit tests for main application endpoints
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "djobea-ai"


def test_root_redirect():
    """Test root endpoint redirects to admin"""
    response = client.get("/", allow_redirects=False)
    assert response.status_code == 303
    assert "/admin" in response.headers["location"]


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection is working"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")