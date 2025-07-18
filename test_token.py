#!/usr/bin/env python3
import sys
sys.path.append('.')
from app.services.auth_service import auth_service
import json

# Test token generation
data = {"user_id": "test-user", "permissions": ["PROVIDERS_VIEW", "PROVIDERS_MANAGE"]}
token = auth_service.create_access_token(data)

print(f"Generated token: {token}")
print(f"Token length: {len(token)}")
print(f"Token segments: {token.count('.') + 1}")

# Test token verification
try:
    payload = auth_service.verify_token(token)
    print(f"Token verification successful: {payload}")
except Exception as e:
    print(f"Token verification failed: {e}")

# Test with actual API call
import requests
try:
    response = requests.post('http://localhost:5000/api/auth/login',
                            json={'email': 'admin@djobea.ai', 'password': 'Admin2025!'})
    print(f"API Response status: {response.status_code}")
    print(f"API Response headers: {response.headers}")
    data = response.json()
    print(f"API Response data keys: {list(data.keys())}")
    
    if 'data' in data:
        print(f"Data keys: {list(data['data'].keys())}")
        if 'token' in data['data']:
            api_token = data['data']['token']
            print(f"API Token: {api_token[:50]}...")
            print(f"API Token length: {len(api_token)}")
            print(f"API Token segments: {api_token.count('.') + 1}")
            
            # Test verification of API token
            try:
                payload = auth_service.verify_token(api_token)
                print(f"API Token verification successful: {payload}")
            except Exception as e:
                print(f"API Token verification failed: {e}")
        else:
            print("No accessToken in data")
    else:
        print("No data in response")
        
except Exception as e:
    print(f"API call failed: {e}")
    import traceback
    traceback.print_exc()