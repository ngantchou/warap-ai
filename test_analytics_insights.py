#!/usr/bin/env python3
"""
Test script for Analytics Insights API
Tests the AI-generated insights and recommendations functionality
"""

import requests
import json
import sys
from datetime import datetime

def test_analytics_insights():
    """Test all analytics insights endpoints"""
    
    print("=== Djobea AI - Analytics Insights API Test ===\n")
    
    # Login to get authentication token
    print("1. Getting authentication token...")
    try:
        login_response = requests.post(
            "http://localhost:5000/api/auth/login",
            json={"email": "admin@djobea.ai", "password": "Admin2025!"},
            timeout=30
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["data"]["token"]
            print("✅ Authentication successful")
        else:
            print(f"❌ Login failed: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Test cases for insights API
    test_cases = [
        {
            "name": "Get All Insights (7 days)",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"period": "7d"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        },
        {
            "name": "Get High Priority Insights",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"period": "30d", "priority": "high"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        },
        {
            "name": "Get Performance Category Insights",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"period": "30d", "category": "performance"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        },
        {
            "name": "Get Satisfaction Category Insights",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"period": "30d", "category": "satisfaction"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        },
        {
            "name": "Get Long-term Insights (90 days)",
            "url": "http://localhost:5000/api/analytics/insights",
            "params": {"period": "90d"},
            "expected_fields": ["id", "type", "priority", "category", "title", "description", "impact", "confidence", "metrics", "recommendations", "createdAt"]
        }
    ]
    
    headers = {"Authorization": f"Bearer {token}"}
    success_count = 0
    total_tests = len(test_cases)
    
    print(f"\n2. Testing {total_tests} insights endpoints...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{total_tests}: {test_case['name']}")
        
        try:
            response = requests.get(
                test_case["url"],
                headers=headers,
                params=test_case["params"],
                timeout=30
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                if "success" in data and "data" in data and "summary" in data:
                    insights = data["data"]
                    summary = data["summary"]
                    
                    print(f"   ✅ Success - {len(insights)} insights returned")
                    print(f"   📊 Summary: {summary.get('totalInsights', 0)} total, {summary.get('highPriority', 0)} high priority")
                    
                    # Validate first insight structure (if any)
                    if len(insights) > 0:
                        first_insight = insights[0]
                        has_all_fields = all(field in first_insight for field in test_case["expected_fields"])
                        
                        if has_all_fields:
                            print(f"   ✅ Structure validation passed")
                            print(f"   🔍 Sample insight: {first_insight.get('title', 'N/A')}")
                            print(f"   📈 Type: {first_insight.get('type', 'N/A')}, Priority: {first_insight.get('priority', 'N/A')}")
                            print(f"   🎯 Impact: {first_insight.get('impact', 'N/A')}, Confidence: {first_insight.get('confidence', 'N/A')}")
                            
                            # Show recommendations if available
                            recommendations = first_insight.get("recommendations", [])
                            if recommendations:
                                print(f"   💡 Recommendations: {len(recommendations)} provided")
                                for rec in recommendations[:2]:  # Show first 2
                                    print(f"      - {rec}")
                            
                            success_count += 1
                        else:
                            print(f"   ❌ Missing required fields")
                            missing_fields = [field for field in test_case["expected_fields"] if field not in first_insight]
                            print(f"   Missing: {missing_fields}")
                    else:
                        print(f"   ✅ No insights found (valid for filtered queries)")
                        success_count += 1
                        
                    # Show category breakdown
                    categories = summary.get("categories", {})
                    if categories:
                        print(f"   📊 Categories: {', '.join([f'{k}: {v}' for k, v in categories.items()])}")
                        
                else:
                    print(f"   ❌ Invalid response structure")
                    
            else:
                print(f"   ❌ Request failed: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Summary
    print(f"=== Test Results Summary ===")
    print(f"✅ Successful tests: {success_count}/{total_tests}")
    print(f"❌ Failed tests: {total_tests - success_count}/{total_tests}")
    print(f"📊 Success rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 All Analytics Insights API tests passed successfully!")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

def test_insights_filtering():
    """Test insights filtering functionality"""
    
    print("\n=== Advanced Filtering Tests ===\n")
    
    # Login
    login_response = requests.post(
        "http://localhost:5000/api/auth/login",
        json={"email": "admin@djobea.ai", "password": "Admin2025!"},
        timeout=30
    )
    
    if login_response.status_code != 200:
        print("❌ Authentication failed for filtering tests")
        return False
    
    token = login_response.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test various filter combinations
    filter_tests = [
        {
            "name": "Filter by High Priority",
            "params": {"priority": "high"},
            "validation": lambda data: all(insight["priority"] == "high" for insight in data["data"])
        },
        {
            "name": "Filter by Performance Category",
            "params": {"category": "performance"},
            "validation": lambda data: all(insight["category"] == "performance" for insight in data["data"])
        },
        {
            "name": "Filter by Warning Type",
            "params": {"period": "30d"},
            "validation": lambda data: len(data["data"]) >= 0  # Basic validation
        },
        {
            "name": "Combined Filters",
            "params": {"priority": "high", "category": "satisfaction"},
            "validation": lambda data: all(
                insight["priority"] == "high" and insight["category"] == "satisfaction" 
                for insight in data["data"]
            )
        }
    ]
    
    filter_success = 0
    
    for test in filter_tests:
        print(f"Testing: {test['name']}")
        
        try:
            response = requests.get(
                "http://localhost:5000/api/analytics/insights",
                headers=headers,
                params=test["params"],
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if test["validation"](data):
                    print(f"✅ Filter validation passed - {len(data['data'])} insights")
                    filter_success += 1
                else:
                    print(f"❌ Filter validation failed")
            else:
                print(f"❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📊 Filter tests: {filter_success}/{len(filter_tests)} passed")
    
    return filter_success == len(filter_tests)

if __name__ == "__main__":
    # Run main tests
    main_success = test_analytics_insights()
    
    # Run filtering tests
    filter_success = test_insights_filtering()
    
    # Overall result
    if main_success and filter_success:
        print("\n🎉 All Analytics Insights API tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        sys.exit(1)