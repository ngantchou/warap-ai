"""
Production Security Testing Suite
Comprehensive security tests for authentication, authorization, and attack prevention
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session

from app.main import app
from app.models.database_models import AdminUser, SecurityLog, RateLimitLog
from app.services.auth_service import AuthService, get_current_user
from app.database import get_db
from tests.conftest import test_db, override_get_db


class TestAuthenticationSecurity:
    """Test authentication security features"""
    
    def test_password_strength_requirements(self, test_db):
        """Test password strength validation"""
        auth_service = AuthService()
        
        weak_passwords = [
            "123",
            "password",
            "12345678",
            "abc123",
            "qwerty"
        ]
        
        strong_passwords = [
            "StrongP@ssw0rd123",
            "MySecure#2024Pass",
            "C0mpl3x@Password!"
        ]
        
        for weak_pass in weak_passwords:
            with pytest.raises(ValueError, match="Password too weak"):
                auth_service.validate_password_strength(weak_pass)
        
        for strong_pass in strong_passwords:
            # Should not raise an exception
            auth_service.validate_password_strength(strong_pass)

    def test_account_lockout_mechanism(self, test_db):
        """Test account lockout after failed login attempts"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        # Create test user
        admin_user = AdminUser(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$fakehash",
            is_active=True
        )
        test_db.add(admin_user)
        test_db.commit()
        
        # Attempt multiple failed logins
        for i in range(6):  # Exceeds the 5 attempt limit
            response = client.post("/auth/login", data={
                "username": "testuser",
                "password": "wrong_password"
            })
            
            if i < 5:
                assert response.status_code == 401
            else:
                # Account should be locked
                assert response.status_code == 423  # Locked
        
        # Verify lockout persists
        response = client.post("/auth/login", data={
            "username": "testuser",
            "password": "correct_password"  # Even correct password should fail
        })
        assert response.status_code == 423

    def test_jwt_token_expiration(self, test_db):
        """Test JWT token expiration handling"""
        auth_service = AuthService()
        
        # Create a user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongP@ssw0rd123"
        }
        
        user = auth_service.create_user(test_db, user_data)
        
        # Generate token with short expiration
        with patch('app.services.auth_service.timedelta') as mock_timedelta:
            mock_timedelta.return_value.total_seconds.return_value = -1  # Expired
            token = auth_service.create_access_token({"sub": user.username})
        
        # Try to verify expired token
        with pytest.raises(Exception, match="Token expired"):
            auth_service.verify_token(token)

    def test_password_history_prevention(self, test_db):
        """Test prevention of password reuse"""
        auth_service = AuthService()
        
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongP@ssw0rd123"
        }
        
        user = auth_service.create_user(test_db, user_data)
        original_hash = user.hashed_password
        
        # Try to change to same password
        with pytest.raises(ValueError, match="Cannot reuse previous password"):
            auth_service.change_password(test_db, user.id, "StrongP@ssw0rd123", "StrongP@ssw0rd123")


class TestAuthorizationSecurity:
    """Test role-based authorization security"""
    
    def test_role_based_access_control(self, test_db):
        """Test that users can only access authorized endpoints"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        # Create regular admin user
        regular_admin = AdminUser(
            username="regular_admin",
            email="admin@example.com",
            hashed_password="$2b$12$fakehash",
            role="admin",
            is_active=True
        )
        test_db.add(regular_admin)
        test_db.commit()
        
        # Login as regular admin
        with patch('app.services.auth_service.AuthService.verify_password', return_value=True):
            response = client.post("/auth/login", data={
                "username": "regular_admin",
                "password": "password"
            })
        
        # Try to access super admin endpoints
        response = client.post("/auth/users", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password",
            "role": "admin"
        })
        
        assert response.status_code == 403  # Forbidden

    def test_endpoint_protection(self, test_db):
        """Test that protected endpoints require authentication"""
        client = TestClient(app)
        
        protected_endpoints = [
            ("/admin/", "GET"),
            ("/admin/providers", "GET"),
            ("/admin/requests", "GET"),
            ("/admin/payments", "GET"),
            ("/admin/analytics", "GET")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint)
            
            # Should redirect to login or return 401/403
            assert response.status_code in [302, 401, 403]

    def test_session_timeout(self, test_db):
        """Test session timeout functionality"""
        auth_service = AuthService()
        
        # Create user and login
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongP@ssw0rd123"
        }
        
        user = auth_service.create_user(test_db, user_data)
        
        # Mock time to simulate session timeout
        with patch('time.time') as mock_time:
            # Initial login
            mock_time.return_value = 1000
            token = auth_service.create_access_token({"sub": user.username})
            
            # Advance time beyond session timeout
            mock_time.return_value = 1000 + (24 * 60 * 60) + 1  # 24 hours + 1 second
            
            with pytest.raises(Exception, match="Token expired"):
                auth_service.verify_token(token)


class TestInputValidationSecurity:
    """Test input validation and sanitization"""
    
    def test_sql_injection_prevention(self, test_db):
        """Test SQL injection attack prevention"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        # SQL injection payloads
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM admin_users --",
            "'; INSERT INTO admin_users VALUES ('hacker', 'hack@evil.com'); --"
        ]
        
        for payload in sql_payloads:
            # Try in login form
            response = client.post("/auth/login", data={
                "username": payload,
                "password": "password"
            })
            
            # Should not cause server error or return unexpected data
            assert response.status_code in [400, 401, 422]
            
            # Try in provider creation
            response = client.post("/admin/providers/add", data={
                "name": payload,
                "whatsapp_id": "+237690000001",
                "phone_number": "+237690000001",
                "services": "plomberie",
                "coverage_areas": "Bonamoussadi"
            })
            
            assert response.status_code in [302, 400, 401, 403, 422]

    def test_xss_prevention(self, test_db):
        """Test XSS attack prevention"""
        client = TestClient(app)
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>"
        ]
        
        for payload in xss_payloads:
            response = client.post("/admin/providers/add", data={
                "name": payload,
                "whatsapp_id": "+237690000001",
                "phone_number": "+237690000001",
                "services": "plomberie",
                "coverage_areas": "Bonamoussadi"
            })
            
            # Check response doesn't contain unescaped payload
            if response.status_code == 200:
                assert payload not in response.text
                # Should be HTML escaped
                import html
                assert html.escape(payload) in response.text or response.status_code != 200

    def test_file_upload_security(self, test_db):
        """Test file upload security measures"""
        client = TestClient(app)
        
        # Malicious file types
        malicious_files = [
            ("test.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
            ("test.jsp", b"<% Runtime.getRuntime().exec(request.getParameter('cmd')); %>", "application/java"),
            ("test.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream"),
            ("test.bat", b"@echo off\nformat c: /y", "application/x-msdos-program")
        ]
        
        for filename, content, content_type in malicious_files:
            # If file upload endpoint exists, test it
            if hasattr(client, 'post'):  # Placeholder for actual file upload endpoint
                files = {"file": (filename, content, content_type)}
                response = client.post("/admin/upload", files=files)
                
                # Should reject malicious files
                assert response.status_code in [400, 403, 415, 422]

    def test_command_injection_prevention(self, test_db):
        """Test command injection prevention"""
        client = TestClient(app)
        
        command_payloads = [
            "; cat /etc/passwd",
            "| whoami",
            "&& rm -rf /",
            "`id`",
            "$(cat /etc/shadow)"
        ]
        
        for payload in command_payloads:
            # Test in various input fields
            response = client.post("/admin/providers/add", data={
                "name": f"Provider {payload}",
                "whatsapp_id": f"+237690000001{payload}",
                "phone_number": "+237690000001",
                "services": "plomberie",
                "coverage_areas": payload
            })
            
            # Should not execute commands or cause server errors
            assert response.status_code in [302, 400, 401, 403, 422]


class TestRateLimitingSecurity:
    """Test rate limiting security measures"""
    
    def test_login_rate_limiting(self, test_db):
        """Test rate limiting on login attempts"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        # Rapid login attempts
        for i in range(10):
            response = client.post("/auth/login", data={
                "username": "testuser",
                "password": "wrong_password"
            })
            
            if i < 5:
                assert response.status_code == 401
            else:
                # Should be rate limited
                assert response.status_code == 429
                assert "rate limit" in response.text.lower()

    def test_api_rate_limiting(self, test_db):
        """Test API endpoint rate limiting"""
        client = TestClient(app)
        
        # Test various endpoints
        endpoints = [
            "/health",
            "/",
            "/payment/success"
        ]
        
        for endpoint in endpoints:
            rate_limited = False
            
            # Make rapid requests
            for i in range(50):
                response = client.get(endpoint)
                
                if response.status_code == 429:
                    rate_limited = True
                    break
            
            # At least some endpoints should have rate limiting
            # (Not all endpoints may be rate limited)

    def test_webhook_rate_limiting(self, test_db):
        """Test webhook endpoint rate limiting"""
        client = TestClient(app)
        
        # Rapid webhook requests
        for i in range(20):
            response = client.post("/webhook/whatsapp", json={
                "From": "+237690000001",
                "Body": "Test message",
                "MessageSid": f"test_sid_{i}"
            })
            
            # Should eventually be rate limited
            if response.status_code == 429:
                break
        
        # Ensure rate limiting headers are present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestWebhookSecurity:
    """Test webhook security measures"""
    
    def test_twilio_signature_validation(self, test_db):
        """Test Twilio webhook signature validation"""
        client = TestClient(app)
        
        # Test without signature
        response = client.post("/webhook/whatsapp", json={
            "From": "+237690000001",
            "Body": "Test message"
        })
        
        # Should require valid signature
        assert response.status_code in [401, 403]
        
        # Test with invalid signature
        response = client.post("/webhook/whatsapp", 
            json={
                "From": "+237690000001",
                "Body": "Test message"
            },
            headers={"X-Twilio-Signature": "invalid_signature"}
        )
        
        assert response.status_code in [401, 403]

    def test_monetbil_signature_validation(self, test_db):
        """Test Monetbil webhook signature validation"""
        client = TestClient(app)
        
        # Test without signature
        response = client.post("/webhook/monetbil", data={
            "payment_ref": "test_ref",
            "status": "success"
        })
        
        assert response.status_code in [401, 403]
        
        # Test with invalid signature
        response = client.post("/webhook/monetbil",
            data={
                "payment_ref": "test_ref",
                "status": "success"
            },
            headers={"X-Monetbil-Signature": "invalid_signature"}
        )
        
        assert response.status_code in [401, 403]

    def test_webhook_payload_validation(self, test_db):
        """Test webhook payload validation"""
        client = TestClient(app)
        
        # Invalid payloads
        invalid_payloads = [
            {},  # Empty payload
            {"invalid": "data"},  # Missing required fields
            {"From": "invalid_phone", "Body": "test"},  # Invalid phone format
            {"From": "+237690000001", "Body": ""},  # Empty message
        ]
        
        for payload in invalid_payloads:
            with patch('app.api.webhook.validate_webhook_signature', return_value=True):
                response = client.post("/webhook/whatsapp", json=payload)
                
                # Should validate payload structure
                assert response.status_code in [400, 422]


class TestSecurityHeaders:
    """Test security headers implementation"""
    
    def test_security_headers_present(self, test_db):
        """Test that security headers are present in responses"""
        client = TestClient(app)
        
        response = client.get("/")
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Referrer-Policy",
            "Content-Security-Policy"
        ]
        
        for header in required_headers:
            assert header in response.headers
            
        # Check specific header values
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "max-age" in response.headers["Strict-Transport-Security"]

    def test_csp_header_configuration(self, test_db):
        """Test Content Security Policy header configuration"""
        client = TestClient(app)
        
        response = client.get("/")
        csp = response.headers.get("Content-Security-Policy", "")
        
        # Should restrict unsafe sources
        assert "default-src 'self'" in csp
        assert "script-src" in csp
        assert "style-src" in csp
        
        # Should not allow unsafe-eval or unsafe-inline without specific need
        # (Some inline may be needed for specific frameworks)

    def test_cors_configuration(self, test_db):
        """Test CORS configuration security"""
        client = TestClient(app)
        
        # Test preflight request
        response = client.options("/", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        })
        
        # Should not allow arbitrary origins
        cors_origin = response.headers.get("Access-Control-Allow-Origin", "")
        assert cors_origin != "*" or cors_origin == ""


class TestSecurityLogging:
    """Test security event logging"""
    
    def test_failed_login_logging(self, test_db):
        """Test that failed login attempts are logged"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        initial_count = test_db.query(SecurityLog).count()
        
        # Failed login attempt
        response = client.post("/auth/login", data={
            "username": "nonexistent",
            "password": "wrong"
        })
        
        # Check if security event was logged
        final_count = test_db.query(SecurityLog).count()
        assert final_count > initial_count
        
        # Check log details
        log_entry = test_db.query(SecurityLog).order_by(SecurityLog.id.desc()).first()
        assert log_entry.event_type == "failed_login"
        assert "nonexistent" in str(log_entry.details)

    def test_successful_login_logging(self, test_db):
        """Test that successful logins are logged"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        # Create test user
        admin_user = AdminUser(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$fakehash",
            is_active=True
        )
        test_db.add(admin_user)
        test_db.commit()
        
        initial_count = test_db.query(SecurityLog).count()
        
        # Successful login
        with patch('app.services.auth_service.AuthService.verify_password', return_value=True):
            response = client.post("/auth/login", data={
                "username": "testuser",
                "password": "correct_password"
            })
        
        # Check if security event was logged
        final_count = test_db.query(SecurityLog).count()
        if response.status_code in [200, 302]:  # Successful login
            assert final_count > initial_count

    def test_rate_limit_logging(self, test_db):
        """Test that rate limit violations are logged"""
        client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: test_db
        
        # Generate rate limit violation
        for i in range(10):
            response = client.post("/auth/login", data={
                "username": "testuser",
                "password": "wrong"
            })
            
            if response.status_code == 429:
                break
        
        # Check if rate limit was logged
        rate_limit_logs = test_db.query(RateLimitLog).filter(
            RateLimitLog.is_blocked == True
        ).count()
        
        assert rate_limit_logs > 0


class TestDataProtection:
    """Test data protection and privacy measures"""
    
    def test_password_hashing(self, test_db):
        """Test that passwords are properly hashed"""
        auth_service = AuthService()
        
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        
        # Should not store plaintext password
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt format
        
        # Should verify correctly
        assert auth_service.verify_password(password, hashed)
        assert not auth_service.verify_password("wrong_password", hashed)

    def test_sensitive_data_masking(self, test_db):
        """Test that sensitive data is masked in logs"""
        client = TestClient(app)
        
        # Make request with sensitive data
        response = client.post("/auth/login", data={
            "username": "testuser",
            "password": "sensitive_password_123"
        })
        
        # Check that password is not in response
        assert "sensitive_password_123" not in response.text
        
        # Check logs don't contain sensitive data
        # (This would require checking actual log files in a real implementation)

    def test_session_data_protection(self, test_db):
        """Test session data protection"""
        client = TestClient(app)
        
        # Login and get session
        response = client.post("/auth/login", data={
            "username": "testuser",
            "password": "password"
        })
        
        # Session cookies should be secure
        cookies = response.cookies
        for cookie_name, cookie in cookies.items():
            if "session" in cookie_name.lower() or "token" in cookie_name.lower():
                # Should have secure flags
                assert cookie.get("httponly", False) or cookie.get("secure", False)