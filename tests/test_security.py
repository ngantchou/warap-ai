"""
Security test suite for Djobea AI
Tests authentication, authorization, rate limiting, input validation, and security headers
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from app.main import app
from app.database import get_db, Base
from app.models.database_models import AdminUser, SecurityLog, AdminRole
from app.services.auth_service import AuthService
from app.middleware.security import SecurityHeadersMiddleware, InputValidationMiddleware


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_security.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def test_db():
    """Create a test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_admin_user(test_db):
    """Create a test admin user"""
    auth_service = AuthService(test_db)
    user = auth_service.create_admin_user(
        username="testadmin",
        email="test@example.com",
        password="TestPassword123!",
        role=AdminRole.ADMIN
    )
    return user


@pytest.fixture
def test_super_admin_user(test_db):
    """Create a test super admin user"""
    auth_service = AuthService(test_db)
    user = auth_service.create_admin_user(
        username="superadmin",
        email="super@example.com",
        password="SuperPassword123!",
        role=AdminRole.SUPER_ADMIN
    )
    return user


@pytest.fixture
def auth_headers(test_admin_user, test_db):
    """Create authentication headers for testing"""
    auth_service = AuthService(test_db)
    token_data = {
        "sub": str(test_admin_user.id),
        "username": test_admin_user.username,
        "role": test_admin_user.role
    }
    access_token = auth_service.create_access_token(data=token_data)
    return {"Authorization": f"Bearer {access_token}"}


class TestAuthentication:
    """Test authentication functionality"""
    
    def test_login_success(self, test_admin_user):
        """Test successful login"""
        response = client.post("/auth/api/login", json={
            "username": "testadmin",
            "password": "TestPassword123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post("/auth/api/login", json={
            "username": "testadmin",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        response = client.post("/auth/api/login", json={
            "username": "nonexistent",
            "password": "password"
        })
        
        assert response.status_code == 401
    
    def test_get_current_user(self, auth_headers):
        """Test getting current user info"""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testadmin"
        assert data["role"] == "admin"
    
    def test_unauthorized_access(self):
        """Test access without authentication"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_invalid_token(self):
        """Test access with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_token_refresh(self, test_admin_user, test_db):
        """Test token refresh functionality"""
        auth_service = AuthService(test_db)
        token_data = {
            "sub": str(test_admin_user.id),
            "username": test_admin_user.username,
            "role": test_admin_user.role
        }
        refresh_token = auth_service.create_refresh_token(data=token_data)
        
        response = client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_change_password(self, auth_headers):
        """Test password change"""
        response = client.post("/auth/change-password", 
                              headers=auth_headers,
                              json={
                                  "current_password": "TestPassword123!",
                                  "new_password": "NewPassword123!"
                              })
        
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
    
    def test_change_password_wrong_current(self, auth_headers):
        """Test password change with wrong current password"""
        response = client.post("/auth/change-password",
                              headers=auth_headers,
                              json={
                                  "current_password": "wrongpassword",
                                  "new_password": "NewPassword123!"
                              })
        
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]


class TestAuthorization:
    """Test role-based authorization"""
    
    def test_admin_access_admin_endpoints(self, auth_headers):
        """Test admin access to admin endpoints"""
        response = client.get("/admin/", headers=auth_headers)
        assert response.status_code == 200
    
    def test_super_admin_create_user(self, test_super_admin_user, test_db):
        """Test super admin can create users"""
        auth_service = AuthService(test_db)
        token_data = {
            "sub": str(test_super_admin_user.id),
            "username": test_super_admin_user.username,
            "role": test_super_admin_user.role
        }
        access_token = auth_service.create_access_token(data=token_data)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = client.post("/auth/users",
                              headers=headers,
                              json={
                                  "username": "newuser",
                                  "email": "new@example.com",
                                  "password": "Password123!",
                                  "role": "admin"
                              })
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
    
    def test_admin_cannot_create_user(self, auth_headers):
        """Test regular admin cannot create users"""
        response = client.post("/auth/users",
                              headers=auth_headers,
                              json={
                                  "username": "newuser",
                                  "email": "new@example.com",
                                  "password": "Password123!",
                                  "role": "admin"
                              })
        
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]


class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_xss_prevention(self, auth_headers):
        """Test XSS attack prevention"""
        malicious_input = "<script>alert('xss')</script>"
        
        response = client.post("/admin/providers",
                              headers=auth_headers,
                              data={
                                  "name": malicious_input,
                                  "whatsapp_id": "+237123456789",
                                  "phone_number": "+237123456789",
                                  "services": "plomberie",
                                  "coverage_areas": "Bonamoussadi"
                              })
        
        # Should reject malicious input
        assert response.status_code == 400
        assert "Invalid input detected" in response.json()["detail"]
    
    def test_sql_injection_prevention(self, auth_headers):
        """Test SQL injection prevention"""
        malicious_input = "'; DROP TABLE users; --"
        
        response = client.post("/admin/providers",
                              headers=auth_headers,
                              data={
                                  "name": "Test Provider",
                                  "whatsapp_id": malicious_input,
                                  "phone_number": "+237123456789",
                                  "services": "plomberie",
                                  "coverage_areas": "Bonamoussadi"
                              })
        
        # Should reject malicious input
        assert response.status_code == 400
        assert "Invalid input detected" in response.json()["detail"]
    
    def test_content_length_limit(self):
        """Test request size limits"""
        large_content = "x" * (11 * 1024 * 1024)  # 11MB (over the 10MB limit)
        
        response = client.post("/auth/api/login", json={
            "username": "test",
            "password": large_content
        })
        
        assert response.status_code == 413  # Request Entity Too Large


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_login_rate_limiting(self):
        """Test rate limiting on login attempts"""
        # Make multiple failed login attempts
        for i in range(6):  # Exceed the 5 attempt limit
            response = client.post("/auth/api/login", json={
                "username": "testuser",
                "password": "wrongpassword"
            })
            
            if i < 5:
                assert response.status_code == 401  # Unauthorized
            else:
                assert response.status_code == 429  # Rate limited
    
    def test_rate_limit_headers(self):
        """Test rate limit headers are present"""
        response = client.get("/")
        
        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


class TestSecurityHeaders:
    """Test security headers"""
    
    def test_security_headers_present(self):
        """Test that security headers are present"""
        response = client.get("/")
        
        # Check for security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
    
    def test_server_header_removed(self):
        """Test that server information is not disclosed"""
        response = client.get("/")
        
        # Server header should be removed or not contain sensitive info
        server_header = response.headers.get("server", "")
        assert "uvicorn" not in server_header.lower()
        assert "python" not in server_header.lower()


class TestSecurityLogging:
    """Test security event logging"""
    
    def test_failed_login_logged(self, test_db):
        """Test that failed login attempts are logged"""
        initial_logs = test_db.query(SecurityLog).count()
        
        client.post("/auth/api/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        final_logs = test_db.query(SecurityLog).count()
        assert final_logs > initial_logs
        
        # Check the latest log entry
        latest_log = test_db.query(SecurityLog).order_by(SecurityLog.created_at.desc()).first()
        assert latest_log.event_type in ["failed_login_invalid_user", "failed_login_wrong_password"]
    
    def test_successful_login_logged(self, test_admin_user, test_db):
        """Test that successful logins are logged"""
        initial_logs = test_db.query(SecurityLog).count()
        
        client.post("/auth/api/login", json={
            "username": "testadmin",
            "password": "TestPassword123!"
        })
        
        final_logs = test_db.query(SecurityLog).count()
        assert final_logs > initial_logs
        
        # Check the latest log entry
        latest_log = test_db.query(SecurityLog).order_by(SecurityLog.created_at.desc()).first()
        assert latest_log.event_type == "successful_login"
        assert latest_log.user_id == test_admin_user.id


class TestPasswordSecurity:
    """Test password security features"""
    
    def test_password_hashing(self, test_db):
        """Test that passwords are properly hashed"""
        auth_service = AuthService(test_db)
        plain_password = "TestPassword123!"
        hashed = auth_service.get_password_hash(plain_password)
        
        # Hash should not be the same as plain password
        assert hashed != plain_password
        # Hash should be verifiable
        assert auth_service.verify_password(plain_password, hashed)
        # Wrong password should not verify
        assert not auth_service.verify_password("wrongpassword", hashed)
    
    def test_account_lockout(self, test_admin_user, test_db):
        """Test account lockout after failed attempts"""
        auth_service = AuthService(test_db)
        
        # Simulate multiple failed attempts
        for i in range(6):
            auth_service.authenticate_user(
                "testadmin", "wrongpassword", "127.0.0.1", "test-agent"
            )
        
        # User should be locked
        assert auth_service.is_user_locked(test_admin_user)
        
        # Even correct password should fail when locked
        result = auth_service.authenticate_user(
            "testadmin", "TestPassword123!", "127.0.0.1", "test-agent"
        )
        assert result is None


class TestWebhookSecurity:
    """Test webhook security features"""
    
    @patch('app.services.auth_service.AuthService.validate_twilio_signature')
    def test_webhook_signature_validation(self, mock_validate):
        """Test Twilio webhook signature validation"""
        mock_validate.return_value = True
        
        response = client.post("/webhook/whatsapp", 
                              data={
                                  "From": "+237123456789",
                                  "To": "+237987654321",
                                  "Body": "Test message",
                                  "MessageSid": "SM123",
                                  "AccountSid": "AC123"
                              },
                              headers={"X-Twilio-Signature": "valid_signature"})
        
        # Should process webhook when signature is valid
        assert response.status_code == 200
        mock_validate.assert_called_once()
    
    @patch('app.services.auth_service.AuthService.validate_twilio_signature')
    def test_webhook_invalid_signature(self, mock_validate):
        """Test webhook rejection with invalid signature"""
        mock_validate.return_value = False
        
        response = client.post("/webhook/whatsapp",
                              data={
                                  "From": "+237123456789",
                                  "To": "+237987654321",
                                  "Body": "Test message",
                                  "MessageSid": "SM123",
                                  "AccountSid": "AC123"
                              },
                              headers={"X-Twilio-Signature": "invalid_signature"})
        
        # Should reject webhook with invalid signature
        assert response.status_code == 403
        assert "Invalid webhook signature" in response.json()["detail"]


class TestPhoneNumberValidation:
    """Test phone number validation and normalization"""
    
    def test_valid_cameroon_phone_numbers(self, test_db):
        """Test validation of valid Cameroon phone numbers"""
        auth_service = AuthService(test_db)
        
        valid_numbers = [
            "690123456",
            "237690123456",
            "+237690123456",
            "6 90 12 34 56",
            "+237 6 90 12 34 56"
        ]
        
        for number in valid_numbers:
            normalized = auth_service.validate_phone_number(number)
            assert normalized == "+237690123456"
    
    def test_invalid_phone_numbers(self, test_db):
        """Test rejection of invalid phone numbers"""
        auth_service = AuthService(test_db)
        
        invalid_numbers = [
            "123456789",     # Too short
            "12345678901234",  # Too long
            "590123456",     # Wrong prefix
            "abc123456",     # Non-numeric
            ""               # Empty
        ]
        
        for number in invalid_numbers:
            with pytest.raises(ValueError):
                auth_service.validate_phone_number(number)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])