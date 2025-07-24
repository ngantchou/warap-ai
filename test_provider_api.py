#!/usr/bin/env python3
"""Test script for Provider API"""

import requests
import json
import sys

def test_provider_api():
    """Test the Provider API with authentication"""
    
    # Test login
    print("Testing login...")
    try:
        response = requests.post(
            'http://localhost:5000/api/auth/login',
            headers={'Content-Type': 'application/json'},
            json={'email': 'admin@djobea.ai', 'password': 'Admin2025!'}
        )
        
        if response.status_code != 200:
            print(f"Login failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        data = response.json()
        if 'data' not in data or 'token' not in data['data']:
            print("Login response missing token")
            print(f"Response: {json.dumps(data, indent=2)}")
            return False
            
        token = data['data']['token']
        print(f"✓ Login successful, token length: {len(token)}")
        
    except Exception as e:
        print(f"Login error: {e}")
        return False
    
    # Test Provider API
    print("\nTesting Provider API...")
    try:
        response = requests.get(
            'http://localhost:5000/api/providers',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        print(f"Provider API status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✓ Provider API working!")
            return True
        else:
            print(f"✗ Provider API failed")
            return False
            
    except Exception as e:
        print(f"Provider API error: {e}")
        return False

if __name__ == "__main__":
    success = test_provider_api()
    sys.exit(0 if success else 1)