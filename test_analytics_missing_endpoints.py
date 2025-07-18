#!/usr/bin/env python3
"""
Test script for missing analytics endpoints (leaderboard, export, share)
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:5000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
CREDENTIALS = {
    "email": "admin@djobea.ai",
    "password": "Admin2025!"
}

def get_auth_token():
    """Get authentication token"""
    response = requests.post(LOGIN_URL, json=CREDENTIALS)
    if response.status_code == 200:
        data = response.json()
        print(f"Login response keys: {list(data.keys())}")
        print(f"Login data keys: {list(data['data'].keys())}")
        
        # Try different possible token field names
        token_fields = ['accessToken', 'access_token', 'token']
        for field in token_fields:
            if field in data['data']:
                return data['data'][field]
        
        # If not found, show what's available
        print(f"Available fields in data: {data['data']}")
        return None
    else:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        return None

def test_leaderboard_endpoint(token):
    """Test leaderboard endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "category": "providers",
        "period": "30d",
        "limit": 10,
        "metric": "rating"
    }
    
    url = f"{BASE_URL}/api/analytics/leaderboard"
    response = requests.get(url, headers=headers, params=params)
    
    print(f"Leaderboard endpoint: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

def test_export_endpoint(token):
    """Test export endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "format": "json",
        "data": ["kpis", "performance"],
        "period": "30d"
    }
    
    url = f"{BASE_URL}/api/analytics/export"
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Export endpoint: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

def test_share_endpoint(token):
    """Test share endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "reportId": "test-report",
        "recipients": [
            {
                "email": "test@example.com",
                "name": "Test User",
                "permissions": ["view"]
            }
        ]
    }
    
    url = f"{BASE_URL}/api/analytics/share"
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Share endpoint: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

def main():
    """Main test function"""
    print("=== Testing Analytics Missing Endpoints ===")
    
    # Get authentication token
    print("1. Getting authentication token...")
    token = get_auth_token()
    if not token:
        print("Failed to get authentication token")
        sys.exit(1)
    
    print(f"Token obtained (length: {len(token)})")
    print()
    
    # Test endpoints
    results = {
        "leaderboard": test_leaderboard_endpoint(token),
        "export": test_export_endpoint(token),
        "share": test_share_endpoint(token)
    }
    
    print("\n=== Results Summary ===")
    for endpoint, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{endpoint}: {status}")
    
    # Overall result
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nOverall: {total_passed}/{total_tests} endpoints working")
    
    if total_passed == total_tests:
        print("🎉 All analytics endpoints are operational!")
        sys.exit(0)
    else:
        print("❌ Some endpoints need attention")
        sys.exit(1)

if __name__ == "__main__":
    main()