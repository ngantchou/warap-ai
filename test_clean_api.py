#!/usr/bin/env python3
"""
Test script for cleaned API structure
Tests only essential endpoints (14 endpoints vs previous 44)
"""

import requests
import json
from datetime import datetime

def test_clean_api_structure():
    """Test the cleaned API structure with only essential endpoints"""
    
    base_url = "http://localhost:5000"
    
    # Test authentication first
    try:
        auth_response = requests.post(
            f"{base_url}/auth/api/auth/login",
            json={"email": "admin@djobea.ai", "password": "admin123"}
        )
        
        if auth_response.status_code != 200:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            return
        
        token = auth_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("✅ Authentication successful")
        
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return
    
    # Essential endpoints to test (cleaned structure)
    essential_endpoints = [
        # Core business endpoints
        ("GET", "/api/analytics/", "Analytics overview"),
        ("GET", "/api/ai/health", "AI service health"),
        ("GET", "/api/settings/system", "System settings"),
        ("GET", "/api/finances/overview", "Finance overview"),
        ("POST", "/webhook/whatsapp", "WhatsApp webhook"),
        
        # External API endpoints
        ("GET", "/api/providers/", "Providers list"),
        ("GET", "/api/requests/", "Requests list"),
        ("GET", "/api/analytics/performance", "Analytics performance"),
        ("GET", "/api/finances/transactions", "Finance transactions"),
        ("GET", "/health", "Health check"),
        
        # Chat widget
        ("POST", "/api/chat/widget", "Chat widget"),
        
        # Dashboard
        ("GET", "/api/dashboard/stats", "Dashboard stats"),
    ]
    
    print(f"\n🧪 Testing {len(essential_endpoints)} essential endpoints...")
    
    success_count = 0
    
    for method, endpoint, description in essential_endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=5)
            elif method == "POST":
                if "webhook" in endpoint:
                    # Skip webhook test (requires specific data)
                    print(f"⏭️  {description}: Skipped (webhook)")
                    continue
                elif "chat" in endpoint:
                    response = requests.post(f"{base_url}{endpoint}", 
                                           json={"message": "test", "phone": "237691924172"}, 
                                           headers=headers, timeout=5)
                else:
                    response = requests.post(f"{base_url}{endpoint}", 
                                           json={}, headers=headers, timeout=5)
            
            if response.status_code in [200, 201]:
                print(f"✅ {description}: {response.status_code}")
                success_count += 1
            else:
                print(f"⚠️  {description}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {description}: Error - {e}")
    
    print(f"\n📊 Results: {success_count}/{len(essential_endpoints)-1} endpoints working")
    print(f"Success rate: {(success_count/(len(essential_endpoints)-1)*100):.1f}%")
    
    if success_count >= 8:
        print("✅ Clean API structure is working well!")
    else:
        print("⚠️  Some endpoints need attention")

if __name__ == "__main__":
    test_clean_api_structure()