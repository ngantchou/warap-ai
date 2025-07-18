#!/usr/bin/env python3
"""Test script to validate all Analytics API endpoints"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def get_auth_token():
    """Get authentication token"""
    login_data = {
        "email": "admin@djobea.ai",
        "password": "Admin2025!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'accessToken' in data['data']:
                return data['data']['accessToken']
            else:
                print(f"Login response format error: {data}")
                return None
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def test_endpoint(endpoint, token, description):
    """Test a single endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/api/analytics/{endpoint}", headers=headers)
        status = "✓" if response.status_code == 200 else "✗"
        print(f"{status} {description}: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   Error: {response.text}")
            return False
        return True
    except Exception as e:
        print(f"✗ {description}: Error - {e}")
        return False

def main():
    print("Testing Analytics API Endpoints")
    print("=" * 40)
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        sys.exit(1)
    
    print("✓ Authentication successful")
    print()
    
    # Test all analytics endpoints
    endpoints = [
        ("kpis", "KPIs Analytics"),
        ("performance", "Performance Analytics"),
        ("services", "Services Analytics"),
        ("geographic", "Geographic Analytics"),
        ("insights", "AI Insights"),
        ("leaderboard", "Leaderboard"),
        ("export", "Export Analytics"),
        ("shares", "Share Analytics")
    ]
    
    success_count = 0
    total_count = len(endpoints)
    
    for endpoint, description in endpoints:
        if test_endpoint(endpoint, token, description):
            success_count += 1
    
    print()
    print(f"Results: {success_count}/{total_count} endpoints working")
    print(f"Success rate: {(success_count/total_count)*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 All Analytics API endpoints are operational!")
    else:
        print("⚠️  Some endpoints need attention")

if __name__ == "__main__":
    main()