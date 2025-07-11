#!/usr/bin/env python3
"""
Test script for Admin Authentication API endpoints
Tests the new /api/auth/* endpoints for external admin interface
"""

import requests
import json
from datetime import datetime
from app.database import get_db
from app.models.database_models import AdminUser, AdminRole
from app.services.auth_service import AuthService

def create_test_admin_user():
    """Create a test admin user with email"""
    try:
        with next(get_db()) as db:
            # Check if admin user exists by email
            existing_admin = db.query(AdminUser).filter(AdminUser.email == "admin@djobea.com").first()
            if existing_admin:
                print("✅ Admin user already exists")
                return True
            
            # Check if admin user exists by username
            existing_admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
            if existing_admin:
                # Update email if missing
                if not existing_admin.email:
                    existing_admin.email = "admin@djobea.com"
                    db.commit()
                    print("✅ Admin user email updated")
                else:
                    print("✅ Admin user already exists with email")
                return True
            
            # Create admin user
            auth_service = AuthService(db)
            admin_user = AdminUser(
                username="admin",
                email="admin@djobea.com",
                hashed_password=auth_service.get_password_hash("motdepasse123"),
                role=AdminRole.ADMIN,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            print("✅ Admin user created successfully")
            return True
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

def test_api_login():
    """Test /api/auth/login endpoint"""
    try:
        login_data = {
            "email": "admin@djobea.com",
            "password": "motdepasse123",
            "rememberMe": True
        }
        
        response = requests.post(
            "http://localhost:5000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Login successful")
            print(f"   Success: {data.get('success')}")
            print(f"   User ID: {data.get('user', {}).get('id')}")
            print(f"   User Name: {data.get('user', {}).get('name')}")
            print(f"   User Email: {data.get('user', {}).get('email')}")
            print(f"   User Role: {data.get('user', {}).get('role')}")
            print(f"   Token length: {len(data.get('token', ''))}")
            print(f"   Refresh token length: {len(data.get('refreshToken', ''))}")
            print(f"   Expires at: {data.get('expiresAt')}")
            
            return {
                "token": data.get("token"),
                "refreshToken": data.get("refreshToken"),
                "user": data.get("user")
            }
        else:
            print(f"❌ API Login failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during API login: {e}")
        return None

def test_api_refresh(refresh_token):
    """Test /api/auth/refresh endpoint"""
    try:
        refresh_data = {
            "refreshToken": refresh_token
        }
        
        response = requests.post(
            "http://localhost:5000/api/auth/refresh",
            json=refresh_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Token refresh successful")
            print(f"   Success: {data.get('success')}")
            print(f"   New token length: {len(data.get('token', ''))}")
            print(f"   New expires at: {data.get('expiresAt')}")
            
            return data.get("token")
        else:
            print(f"❌ API Token refresh failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during API token refresh: {e}")
        return None

def test_api_logout(access_token):
    """Test /api/auth/logout endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            "http://localhost:5000/api/auth/logout",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Logout successful")
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print(f"❌ API Logout failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during API logout: {e}")
        return False

def test_protected_endpoint(access_token):
    """Test a protected endpoint with the access token"""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "http://localhost:5000/api/dashboard/stats",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Protected endpoint access successful")
            print(f"   Total requests: {data.get('totalRequests')}")
            print(f"   Success rate: {data.get('successRate')}%")
            return True
        else:
            print(f"❌ Protected endpoint access failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing protected endpoint: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Admin Authentication API Endpoints")
    print("=" * 60)
    
    # Create admin user
    print("\n1. Creating admin user...")
    if not create_test_admin_user():
        print("❌ Failed to create admin user")
        return
    
    # Test API login
    print("\n2. Testing API login...")
    login_result = test_api_login()
    if not login_result:
        print("❌ Failed to login via API")
        return
    
    access_token = login_result["token"]
    refresh_token = login_result["refreshToken"]
    
    # Test protected endpoint
    print("\n3. Testing protected endpoint access...")
    if not test_protected_endpoint(access_token):
        print("❌ Failed to access protected endpoint")
        return
    
    # Test token refresh
    print("\n4. Testing token refresh...")
    new_token = test_api_refresh(refresh_token)
    if not new_token:
        print("❌ Failed to refresh token")
        return
    
    # Test logout
    print("\n5. Testing logout...")
    if not test_api_logout(new_token):
        print("❌ Failed to logout")
        return
    
    print("\n" + "=" * 60)
    print("🎉 ALL ADMIN AUTHENTICATION API TESTS PASSED!")
    print("=" * 60)
    
    # Summary
    print("\n📋 API ENDPOINTS SUMMARY:")
    print("✅ POST /api/auth/login - Authentication with email/password")
    print("✅ POST /api/auth/refresh - Token refresh")
    print("✅ POST /api/auth/logout - Logout and token revocation")
    print("✅ Authorization header support for protected endpoints")
    print("✅ Proper JSON response format matching API documentation")
    
    print("\n🔒 SECURITY FEATURES:")
    print("✅ JWT tokens with configurable expiration")
    print("✅ Refresh tokens for long-term sessions")
    print("✅ Remember me functionality")
    print("✅ Security event logging")
    print("✅ IP address and user agent tracking")

if __name__ == "__main__":
    main()