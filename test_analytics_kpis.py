#!/usr/bin/env python3
"""Test script for Analytics KPIs API"""

import requests
import json
import sys

def test_analytics_kpis():
    """Test the Analytics KPIs API with authentication"""
    
    # Test login first
    print("Testing login...")
    try:
        response = requests.post(
            'http://localhost:5000/api/auth/login',
            headers={'Content-Type': 'application/json'},
            json={'email': 'admin@djobea.ai', 'password': 'Admin2025!'}
        )
        
        if response.status_code != 200:
            print(f"Login failed with status {response.status_code}")
            return False
            
        data = response.json()
        token = data['data']['token']
        print(f"✓ Login successful")
        
    except Exception as e:
        print(f"Login error: {e}")
        return False
    
    # Test Analytics KPIs API
    print("\nTesting Analytics KPIs API...")
    
    test_cases = [
        # Test 1: Basic KPIs
        {
            "name": "Basic KPIs",
            "url": "http://localhost:5000/api/analytics/kpis",
            "params": {}
        },
        # Test 2: KPIs with period
        {
            "name": "KPIs with 30d period",
            "url": "http://localhost:5000/api/analytics/kpis",
            "params": {"period": "30d"}
        },
        # Test 3: KPIs with comparison
        {
            "name": "KPIs with comparison",
            "url": "http://localhost:5000/api/analytics/kpis",
            "params": {"period": "30d", "compare": "true"}
        },
        # Test 4: Specific metrics
        {
            "name": "Specific metrics",
            "url": "http://localhost:5000/api/analytics/kpis",
            "params": {
                "period": "30d",
                "compare": "true",
                "metrics": ["revenue", "customerSatisfaction"]
            }
        },
        # Test 5: KPI trends
        {
            "name": "KPI trends",
            "url": "http://localhost:5000/api/analytics/kpis/trends",
            "params": {"period": "30d"}
        },
        # Test 6: KPI targets
        {
            "name": "KPI targets",
            "url": "http://localhost:5000/api/analytics/kpis/targets",
            "params": {}
        }
    ]
    
    success_count = 0
    
    for test_case in test_cases:
        print(f"\n--- Testing {test_case['name']} ---")
        
        try:
            response = requests.get(
                test_case['url'],
                headers={'Authorization': f'Bearer {token}'},
                params=test_case['params']
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success")
                
                # Show sample data for main KPIs endpoint
                if "kpis" in test_case['url'] and "trends" not in test_case['url'] and "targets" not in test_case['url']:
                    if 'data' in data:
                        print(f"KPIs returned: {list(data['data'].keys())}")
                        # Show first KPI as example
                        if data['data']:
                            first_kpi = list(data['data'].keys())[0]
                            print(f"Sample KPI ({first_kpi}): {json.dumps(data['data'][first_kpi], indent=2)}")
                
                success_count += 1
            else:
                print(f"✗ Failed: {response.text}")
                
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Successful tests: {success_count}/{len(test_cases)}")
    print(f"Success rate: {(success_count/len(test_cases))*100:.1f}%")
    
    return success_count == len(test_cases)

if __name__ == "__main__":
    success = test_analytics_kpis()
    sys.exit(0 if success else 1)