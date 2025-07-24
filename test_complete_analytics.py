#!/usr/bin/env python3
"""
Complete Analytics API Test Suite
Tests all analytics endpoints: KPIs, Performance, and Services
"""

import requests
import json
import time

def get_auth_token():
    """Get authentication token for API calls"""
    try:
        response = requests.post(
            'http://localhost:5000/api/auth/login',
            json={'email': 'admin@djobea.ai', 'password': 'Admin2025!'},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()['data']['token']
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def test_analytics_endpoints():
    """Test all analytics endpoints"""
    
    print("=== Djobea AI - Complete Analytics API Test Suite ===")
    print()
    
    # Get authentication token
    print("1. Getting authentication token...")
    token = get_auth_token()
    if not token:
        print("❌ Failed to get authentication token")
        return False
    
    print("✅ Authentication successful")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test cases for all analytics endpoints
    test_cases = [
        # Analytics KPIs API
        {
            "name": "Analytics KPIs (30 days)",
            "url": "http://localhost:5000/api/analytics/kpis",
            "params": {"period": "30d"},
            "expected_fields": ["totalRequests", "activeProviders", "completedRequests", "revenue", "averageResponseTime", "customerSatisfaction"]
        },
        {
            "name": "Analytics KPIs (7 days)",
            "url": "http://localhost:5000/api/analytics/kpis",
            "params": {"period": "7d"},
            "expected_fields": ["totalRequests", "activeProviders", "completedRequests", "revenue", "averageResponseTime", "customerSatisfaction"]
        },
        
        # Analytics Performance API
        {
            "name": "Analytics Performance (daily)",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {"period": "7d", "granularity": "day"},
            "expected_fields": ["labels", "datasets"]
        },
        {
            "name": "Analytics Performance (hourly)",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {"period": "24h", "granularity": "hour"},
            "expected_fields": ["labels", "datasets"]
        },
        
        # Analytics Services API
        {
            "name": "Analytics Services (30 days)",
            "url": "http://localhost:5000/api/analytics/services",
            "params": {"period": "30d"},
            "expected_fields": ["labels", "datasets", "totals", "details"]
        },
        {
            "name": "Analytics Services (sorted by revenue)",
            "url": "http://localhost:5000/api/analytics/services",
            "params": {"period": "30d", "sort": "revenue"},
            "expected_fields": ["labels", "datasets", "totals", "details"]
        },
        {
            "name": "Service Categories",
            "url": "http://localhost:5000/api/analytics/services/categories",
            "params": {},
            "expected_fields": ["name", "key", "description"]
        },
        {
            "name": "Services Comparison",
            "url": "http://localhost:5000/api/analytics/services/comparison",
            "params": {"period": "30d", "services": ["plomberie", "electricite"]},
            "expected_fields": ["plomberie", "electricite"]
        },
        
        # Analytics Geographic API
        {
            "name": "Geographic Analytics (30 days)",
            "url": "http://localhost:5000/api/analytics/geographic",
            "params": {"period": "30d", "level": "city"},
            "expected_fields": ["region", "requests", "providers", "revenue", "satisfaction", "responseTime", "coordinates", "growth", "marketShare"]
        },
        {
            "name": "Geographic Analytics (filtered by region)",
            "url": "http://localhost:5000/api/analytics/geographic",
            "params": {"period": "30d", "region": "Douala"},
            "expected_fields": ["region", "requests", "providers", "revenue", "satisfaction", "responseTime", "coordinates", "growth", "marketShare"]
        },
        {
            "name": "Available Regions",
            "url": "http://localhost:5000/api/analytics/geographic/regions",
            "params": {},
            "expected_fields": ["name", "requestCount", "key"]
        },
        {
            "name": "Geographic Heatmap",
            "url": "http://localhost:5000/api/analytics/geographic/heatmap",
            "params": {"period": "30d", "metric": "requests"},
            "expected_fields": ["lat", "lng", "value", "location"]
        },
        
        # Analytics Insights API
        {
            "name": "Analytics Insights (7 days)",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"period": "7d"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        },
        {
            "name": "High Priority Insights",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"priority": "high"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        },
        {
            "name": "Performance Category Insights",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"category": "performance"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        }
    ]
    
    print()
    print("2. Testing analytics endpoints...")
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}/{total_tests}: {test_case['name']}")
        
        try:
            # Add small delay to prevent overwhelming the server
            time.sleep(0.1)
            
            response = requests.get(
                test_case['url'],
                headers=headers,
                params=test_case['params'],
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check if response has expected structure
                    if 'data' in data:
                        api_data = data['data']
                        
                        # Validate expected fields
                        if test_case['name'] == "Service Categories":
                            # Categories should be a list
                            if isinstance(api_data, list) and len(api_data) > 0:
                                first_category = api_data[0]
                                has_fields = all(field in first_category for field in test_case['expected_fields'])
                                if has_fields:
                                    print(f"✅ Success - {len(api_data)} categories found")
                                    success_count += 1
                                else:
                                    print(f"❌ Missing expected fields: {test_case['expected_fields']}")
                            else:
                                print(f"❌ Invalid categories data structure")
                        
                        elif test_case['name'] == "Services Comparison":
                            # Comparison should have service keys
                            has_services = all(service in api_data for service in test_case['expected_fields'])
                            if has_services:
                                print(f"✅ Success - Comparison for {len(api_data)} services")
                                success_count += 1
                            else:
                                print(f"❌ Missing services in comparison: {test_case['expected_fields']}")
                        
                        elif test_case['name'] == "Available Regions":
                            # Regions should be a list
                            if isinstance(api_data, list):
                                if len(api_data) > 0:
                                    first_region = api_data[0]
                                    has_fields = all(field in first_region for field in test_case['expected_fields'])
                                    if has_fields:
                                        print(f"✅ Success - {len(api_data)} regions found")
                                        success_count += 1
                                    else:
                                        print(f"❌ Missing expected fields in regions: {test_case['expected_fields']}")
                                else:
                                    print(f"✅ Success - No regions found (empty list)")
                                    success_count += 1
                            else:
                                print(f"❌ Invalid regions data structure")
                        
                        elif test_case['name'] == "Geographic Heatmap":
                            # Heatmap should be a list
                            if isinstance(api_data, list):
                                if len(api_data) > 0:
                                    first_point = api_data[0]
                                    has_fields = all(field in first_point for field in test_case['expected_fields'])
                                    if has_fields:
                                        print(f"✅ Success - {len(api_data)} heatmap points found")
                                        success_count += 1
                                    else:
                                        print(f"❌ Missing expected fields in heatmap: {test_case['expected_fields']}")
                                else:
                                    print(f"✅ Success - No heatmap data found (empty list)")
                                    success_count += 1
                            else:
                                print(f"❌ Invalid heatmap data structure")
                        
                        elif "Geographic Analytics" in test_case['name']:
                            # Geographic analytics should be a list
                            if isinstance(api_data, list):
                                if len(api_data) > 0:
                                    first_region = api_data[0]
                                    has_fields = all(field in first_region for field in test_case['expected_fields'])
                                    if has_fields:
                                        print(f"✅ Success - {len(api_data)} geographic regions found")
                                        # Show some insights
                                        print(f"   Top Region: {first_region.get('region', 'N/A')}")
                                        print(f"   Requests: {first_region.get('requests', 0)}")
                                        print(f"   Market Share: {first_region.get('marketShare', 0)}%")
                                        success_count += 1
                                    else:
                                        print(f"❌ Missing expected fields in geographic data: {test_case['expected_fields']}")
                                else:
                                    print(f"✅ Success - No geographic data found (empty list)")
                                    success_count += 1
                            else:
                                print(f"❌ Invalid geographic data structure")
                        
                        elif "Analytics Insights" in test_case['name'] or "Priority Insights" in test_case['name'] or "Category Insights" in test_case['name']:
                            # Insights should be a list
                            if isinstance(api_data, list):
                                if len(api_data) > 0:
                                    first_insight = api_data[0]
                                    has_fields = all(field in first_insight for field in test_case['expected_fields'])
                                    if has_fields:
                                        print(f"✅ Success - {len(api_data)} insights found")
                                        # Show insight details
                                        print(f"   Title: {first_insight.get('title', 'N/A')}")
                                        print(f"   Type: {first_insight.get('type', 'N/A')}, Priority: {first_insight.get('priority', 'N/A')}")
                                        print(f"   Category: {first_insight.get('category', 'N/A')}")
                                        print(f"   Confidence: {first_insight.get('confidence', 'N/A')}")
                                        success_count += 1
                                    else:
                                        print(f"❌ Missing expected fields in insights: {test_case['expected_fields']}")
                                else:
                                    print(f"✅ Success - No insights found (empty list)")
                                    success_count += 1
                            else:
                                print(f"❌ Invalid insights data structure")
                        
                        else:
                            # Regular endpoints should have expected fields
                            has_fields = all(field in api_data for field in test_case['expected_fields'])
                            if has_fields:
                                print(f"✅ Success - All expected fields present")
                                
                                # Show some data insights
                                if 'totalRequests' in api_data:
                                    print(f"   Total Requests: {api_data.get('totalRequests', 0)}")
                                if 'revenue' in api_data:
                                    print(f"   Revenue: {api_data.get('revenue', 0)} XAF")
                                if 'labels' in api_data:
                                    print(f"   Data Points: {len(api_data.get('labels', []))}")
                                if 'totals' in api_data:
                                    totals = api_data['totals']
                                    print(f"   Total Requests: {totals.get('totalRequests', 0)}")
                                    print(f"   Total Revenue: {totals.get('totalRevenue', 0)} XAF")
                                
                                success_count += 1
                            else:
                                print(f"❌ Missing expected fields: {test_case['expected_fields']}")
                                print(f"   Available fields: {list(api_data.keys())}")
                    else:
                        print(f"❌ Response missing 'data' field")
                        print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                        
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON response")
                    print(f"   Response: {response.text[:200]}...")
                    
            else:
                print(f"❌ HTTP {response.status_code}")
                print(f"   Error: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print(f"❌ Request timeout")
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error")
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
    
    print()
    print("=== Test Results ===")
    print(f"Successful tests: {success_count}/{total_tests}")
    print(f"Success rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 All analytics endpoints are working perfectly!")
        return True
    else:
        print("⚠️  Some endpoints need attention")
        return False

if __name__ == "__main__":
    success = test_analytics_endpoints()
    exit(0 if success else 1)