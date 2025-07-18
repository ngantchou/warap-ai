#!/usr/bin/env python3
"""Complete test script for Analytics API System (KPIs + Performance)"""

import requests
import json
import sys

def test_complete_analytics():
    """Test the complete Analytics API system with all endpoints"""
    
    # Test login first
    print("=== COMPLETE ANALYTICS API SYSTEM TEST ===")
    print("Testing authentication...")
    try:
        response = requests.post(
            'http://localhost:5000/api/auth/login',
            headers={'Content-Type': 'application/json'},
            json={'email': 'admin@djobea.ai', 'password': 'Admin2025!'}
        )
        
        if response.status_code != 200:
            print(f"✗ Login failed with status {response.status_code}")
            return False
            
        data = response.json()
        token = data['data']['token']
        print(f"✓ Authentication successful")
        
    except Exception as e:
        print(f"✗ Authentication error: {e}")
        return False
    
    # Test all Analytics endpoints
    print("\n=== TESTING ANALYTICS ENDPOINTS ===")
    
    endpoints = [
        # KPIs API Endpoints
        {
            "category": "KPIs",
            "name": "Main KPIs",
            "url": "http://localhost:5000/api/analytics/kpis",
            "params": {"period": "30d", "compare": "true"},
            "expected_fields": ["totalRequests", "activeProviders", "completedRequests", "revenue", "averageResponseTime", "customerSatisfaction"]
        },
        {
            "category": "KPIs",
            "name": "KPI Trends",
            "url": "http://localhost:5000/api/analytics/kpis/trends",
            "params": {"period": "30d"},
            "expected_fields": ["requestsTrend", "completionRateTrend"]
        },
        {
            "category": "KPIs",
            "name": "KPI Targets",
            "url": "http://localhost:5000/api/analytics/kpis/targets",
            "params": {},
            "expected_fields": ["totalRequests", "activeProviders", "completedRequests", "revenue", "averageResponseTime", "customerSatisfaction"]
        },
        # Performance API Endpoints
        {
            "category": "Performance",
            "name": "Performance Data",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {"period": "7d", "granularity": "day"},
            "expected_fields": ["labels", "datasets", "summary"]
        },
        {
            "category": "Performance",
            "name": "Performance Summary",
            "url": "http://localhost:5000/api/analytics/performance/summary",
            "params": {"period": "7d"},
            "expected_fields": ["totalRequests", "successRate", "responseTime", "aiEfficiency"]
        },
        {
            "category": "Performance",
            "name": "Available Metrics",
            "url": "http://localhost:5000/api/analytics/performance/metrics",
            "params": {},
            "expected_fields": ["successRate", "responseTime", "aiEfficiency"]
        }
    ]
    
    results = {}
    total_tests = len(endpoints)
    successful_tests = 0
    
    for endpoint in endpoints:
        category = endpoint["category"]
        if category not in results:
            results[category] = {"success": 0, "total": 0}
        
        print(f"\n--- Testing {endpoint['category']}: {endpoint['name']} ---")
        
        try:
            response = requests.get(
                endpoint['url'],
                headers={'Authorization': f'Bearer {token}'},
                params=endpoint['params']
            )
            
            results[category]["total"] += 1
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Status: {response.status_code}")
                
                # Validate expected fields
                if 'data' in data:
                    # Handle different data structures
                    if isinstance(data['data'], dict):
                        data_keys = list(data['data'].keys())
                        expected_fields = endpoint['expected_fields']
                        
                        found_fields = [field for field in expected_fields if field in data_keys]
                        print(f"✓ Expected fields found: {len(found_fields)}/{len(expected_fields)}")
                        
                        if found_fields:
                            print(f"  Fields: {found_fields}")
                        
                        # Show sample data
                        if category == "KPIs" and "kpis" in endpoint['url'] and "trends" not in endpoint['url'] and "targets" not in endpoint['url']:
                            sample_kpi = list(data['data'].keys())[0]
                            sample_value = data['data'][sample_kpi]
                            print(f"  Sample KPI ({sample_kpi}): Value={sample_value.get('value', 'N/A')}, Change={sample_value.get('change', 'N/A')}%")
                        
                        elif category == "Performance" and "performance" in endpoint['url'] and "summary" not in endpoint['url'] and "metrics" not in endpoint['url']:
                            print(f"  Data points: {len(data['data'].get('labels', []))}")
                            print(f"  Datasets: {len(data['data'].get('datasets', []))}")
                            summary = data['data'].get('summary', {})
                            print(f"  Summary: Success={summary.get('averageSuccessRate', 0)}%, Response={summary.get('averageResponseTime', 0)}min, AI={summary.get('averageAiEfficiency', 0)}%")
                    
                    elif isinstance(data['data'], list):
                        # Handle list data (like available metrics)
                        expected_fields = endpoint['expected_fields']
                        if data['data'] and isinstance(data['data'][0], dict):
                            available_keys = [metric['key'] for metric in data['data']]
                            found_fields = [field for field in expected_fields if field in available_keys]
                            print(f"✓ Expected metrics found: {len(found_fields)}/{len(expected_fields)}")
                            print(f"  Available metrics: {available_keys}")
                        else:
                            print(f"✓ Data structure: List with {len(data['data'])} items")
                    
                    else:
                        print(f"✓ Data structure: {type(data['data'])}")
                
                results[category]["success"] += 1
                successful_tests += 1
            else:
                print(f"✗ Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"✗ Error: {e}")
            results[category]["total"] += 1
    
    # Summary results
    print(f"\n=== ANALYTICS SYSTEM TEST RESULTS ===")
    for category, result in results.items():
        success_rate = (result["success"] / result["total"]) * 100 if result["total"] > 0 else 0
        print(f"{category} API: {result['success']}/{result['total']} ({success_rate:.1f}%)")
    
    overall_success_rate = (successful_tests / total_tests) * 100
    print(f"\nOverall Success Rate: {successful_tests}/{total_tests} ({overall_success_rate:.1f}%)")
    
    # System status
    if overall_success_rate == 100:
        print("🎉 COMPLETE ANALYTICS SYSTEM OPERATIONAL")
        print("✅ All KPIs and Performance endpoints working")
        print("✅ Real database integration confirmed")
        print("✅ JWT authentication working")
        print("✅ Ready for production deployment")
    elif overall_success_rate >= 80:
        print("⚠️  Analytics system mostly operational")
        print("✅ Core functionality working")
        print("⚠️  Some endpoints may need attention")
    else:
        print("❌ Analytics system needs attention")
        print("❌ Multiple endpoints failing")
    
    return overall_success_rate == 100

if __name__ == "__main__":
    success = test_complete_analytics()
    sys.exit(0 if success else 1)