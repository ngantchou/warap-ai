#!/usr/bin/env python3
"""
Quick API test to validate authentication and dashboard endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_auth_and_dashboard():
    """Test authentication and dashboard endpoints"""
    
    # Step 1: Login
    print("1. Testing authentication...")
    login_data = {
        "email": "admin@djobea.ai",
        "password": "admin123",
        "rememberMe": False
    }
    
    response = requests.post(f"{BASE_URL}/api/api/auth/login", json=login_data)
    print(f"Login response: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("token"):
            token = data["token"]
            print(f"✓ Authentication successful - Token: {token[:50]}...")
            
            # Step 2: Test dashboard endpoints
            headers = {"Authorization": f"Bearer {token}"}
            
            print("\n2. Testing dashboard endpoints...")
            
            # Test stats endpoint
            stats_response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
            print(f"Stats endpoint: {stats_response.status_code}")
            if stats_response.status_code == 200:
                print(f"✓ Stats data: {stats_response.json()}")
            else:
                print(f"✗ Stats failed: {stats_response.text}")
            
            # Test dashboard endpoint
            dashboard_response = requests.get(f"{BASE_URL}/api/dashboard/dashboard", headers=headers)
            print(f"Dashboard endpoint: {dashboard_response.status_code}")
            if dashboard_response.status_code == 200:
                print(f"✓ Dashboard data available")
            else:
                print(f"✗ Dashboard failed: {dashboard_response.text}")
            
            # Test profile endpoint
            profile_response = requests.get(f"{BASE_URL}/api/api/auth/profile", headers=headers)
            print(f"Profile endpoint: {profile_response.status_code}")
            if profile_response.status_code == 200:
                print(f"✓ Profile data: {profile_response.json()}")
            else:
                print(f"✗ Profile failed: {profile_response.text}")
                
        else:
            print(f"✗ Login failed: {data}")
    else:
        print(f"✗ Login request failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_auth_and_dashboard()