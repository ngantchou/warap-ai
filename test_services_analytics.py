#!/usr/bin/env python3
"""Test script for Services Analytics API"""

import requests
import json
import sys

def test_services_analytics():
    """Test the Services Analytics API with authentication"""
    
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
    
    # Test Services Analytics API
    print("\nTesting Services Analytics API...")
    
    test_cases = [
        # Test 1: Basic Services Analytics
        {
            "name": "Basic Services Analytics (30d)",
            "url": "http://localhost:5000/api/analytics/services",
            "params": {"period": "30d"}
        },
        # Test 2: Services Analytics with Revenue Sort
        {
            "name": "Services Analytics (sorted by revenue)",
            "url": "http://localhost:5000/api/analytics/services",
            "params": {"period": "30d", "sort": "revenue"}
        },
        # Test 3: Services Analytics with Satisfaction Sort
        {
            "name": "Services Analytics (sorted by satisfaction)",
            "url": "http://localhost:5000/api/analytics/services",
            "params": {"period": "7d", "sort": "satisfaction"}
        },
        # Test 4: Services Analytics with Category Filter
        {
            "name": "Services Analytics (filtered by plomberie)",
            "url": "http://localhost:5000/api/analytics/services",
            "params": {"period": "30d", "category": "plomberie"}
        },
        # Test 5: Services Comparison
        {
            "name": "Services Comparison",
            "url": "http://localhost:5000/api/analytics/services/comparison",
            "params": {
                "period": "30d",
                "services": ["plomberie", "electricite"]
            }
        },
        # Test 6: Service Categories
        {
            "name": "Service Categories",
            "url": "http://localhost:5000/api/analytics/services/categories",
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
                
                # Show specific data based on endpoint
                if "/services" in test_case['url'] and "comparison" not in test_case['url'] and "categories" not in test_case['url']:
                    # Main services analytics
                    if 'data' in data:
                        services_data = data['data']
                        print(f"Services found: {len(services_data.get('labels', []))}")
                        print(f"Labels: {services_data.get('labels', [])}")
                        
                        # Show totals
                        totals = services_data.get('totals', {})
                        print(f"Total Requests: {totals.get('totalRequests', 0)}")
                        print(f"Total Revenue: {totals.get('totalRevenue', 0)} XAF")
                        print(f"Avg Satisfaction: {totals.get('averageSatisfaction', 0)}")
                        print(f"Avg Response Time: {totals.get('averageResponseTime', 0)} min")
                        
                        # Show sample service detail
                        details = services_data.get('details', [])
                        if details:
                            first_service = details[0]
                            print(f"Top Service: {first_service.get('service', 'N/A')}")
                            print(f"  - Requests: {first_service.get('requests', 0)}")
                            print(f"  - Revenue: {first_service.get('revenue', 0)} XAF")
                            print(f"  - Satisfaction: {first_service.get('satisfaction', 0)}")
                            print(f"  - Growth: {first_service.get('growth', 0)}%")
                
                elif "comparison" in test_case['url']:
                    # Services comparison
                    if 'data' in data:
                        comparison_data = data['data']
                        print(f"Services compared: {len(comparison_data)}")
                        for service, metrics in comparison_data.items():
                            print(f"  {service}: {metrics.get('requests', 0)} requests, {metrics.get('revenue', 0)} XAF")
                
                elif "categories" in test_case['url']:
                    # Service categories
                    if 'data' in data:
                        categories = data['data']
                        print(f"Categories available: {len(categories)}")
                        for category in categories[:3]:  # Show first 3
                            print(f"  - {category.get('name', 'N/A')} ({category.get('key', 'N/A')})")
                
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
    success = test_services_analytics()
    sys.exit(0 if success else 1)