#!/usr/bin/env python3
"""
Test script for Dashboard API endpoints
Creates admin user and tests all dashboard endpoints
"""

import requests
import json
from datetime import datetime
from app.database import get_db
from app.models.database_models import AdminUser, AdminRole
from app.services.auth_service import AuthService

def create_admin_user():
    """Create a test admin user"""
    try:
        with next(get_db()) as db:
            # Check if admin user exists
            existing_admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
            if existing_admin:
                print("Admin user already exists")
                return True
            
            # Create admin user
            auth_service = AuthService(db)
            admin_user = AdminUser(
                username="admin",
                email="admin@djobea.ai",
                hashed_password=auth_service.get_password_hash("admin123"),
                role=AdminRole.ADMIN,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            print("Admin user created successfully")
            return True
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False

def login_admin():
    """Login as admin and get token"""
    try:
        response = requests.post(
            "http://localhost:5000/auth/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print("Login successful")
            return token
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error during login: {e}")
        return None

def test_dashboard_endpoints(token):
    """Test all dashboard endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        ("GET /api/dashboard/", "http://localhost:5000/api/dashboard/"),
        ("GET /api/dashboard/stats", "http://localhost:5000/api/dashboard/stats"),
        ("GET /api/dashboard/stats?period=24h", "http://localhost:5000/api/dashboard/stats?period=24h"),
        ("GET /api/dashboard/stats?period=30d", "http://localhost:5000/api/dashboard/stats?period=30d"),
        ("GET /api/dashboard/activity", "http://localhost:5000/api/dashboard/activity"),
        ("GET /api/dashboard/activity?limit=5", "http://localhost:5000/api/dashboard/activity?limit=5"),
        ("GET /api/dashboard/metrics", "http://localhost:5000/api/dashboard/metrics"),
        ("GET /api/dashboard/charts/activity", "http://localhost:5000/api/dashboard/charts/activity"),
        ("GET /api/dashboard/charts/services", "http://localhost:5000/api/dashboard/charts/services"),
        ("GET /api/dashboard/charts/providers", "http://localhost:5000/api/dashboard/charts/providers"),
        ("GET /api/dashboard/charts/geographic", "http://localhost:5000/api/dashboard/charts/geographic"),
    ]
    
    results = []
    
    for description, url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {description}: SUCCESS")
                print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Non-dict response'}")
                results.append((description, "SUCCESS", response.status_code))
            else:
                print(f"❌ {description}: FAILED - {response.status_code}")
                print(f"   Error: {response.text}")
                results.append((description, "FAILED", response.status_code))
                
        except Exception as e:
            print(f"❌ {description}: ERROR - {e}")
            results.append((description, "ERROR", str(e)))
    
    return results

def main():
    """Main test function"""
    print("🚀 Testing Dashboard API Endpoints")
    print("=" * 50)
    
    # Create admin user
    print("\n1. Creating admin user...")
    if not create_admin_user():
        print("Failed to create admin user")
        return
    
    # Login
    print("\n2. Logging in...")
    token = login_admin()
    if not token:
        print("Failed to login")
        return
    
    # Test endpoints
    print("\n3. Testing dashboard endpoints...")
    results = test_dashboard_endpoints(token)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    success_count = sum(1 for _, status, _ in results if status == "SUCCESS")
    total_count = len(results)
    
    print(f"Total endpoints tested: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    print(f"Success rate: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed. Check logs above.")

if __name__ == "__main__":
    main()