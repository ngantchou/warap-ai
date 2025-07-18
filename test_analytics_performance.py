#!/usr/bin/env python3
"""Test script for Analytics Performance API"""

import requests
import json
import sys

def test_analytics_performance():
    """Test the Analytics Performance API with authentication"""
    
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
    
    # Test Analytics Performance API
    print("\nTesting Analytics Performance API...")
    
    test_cases = [
        # Test 1: Basic Performance Data
        {
            "name": "Basic Performance Data (7d, daily)",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {"period": "7d", "granularity": "day"}
        },
        # Test 2: Hourly Performance Data
        {
            "name": "Hourly Performance Data (24h)",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {"period": "24h", "granularity": "hour"}
        },
        # Test 3: Monthly Performance Data
        {
            "name": "Monthly Performance Data (1y)",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {"period": "1y", "granularity": "month"}
        },
        # Test 4: Specific Metrics
        {
            "name": "Specific Metrics (Success Rate only)",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {
                "period": "7d",
                "granularity": "day",
                "metrics": ["successRate"]
            }
        },
        # Test 5: Multiple Specific Metrics
        {
            "name": "Multiple Metrics (Success Rate + AI Efficiency)",
            "url": "http://localhost:5000/api/analytics/performance",
            "params": {
                "period": "30d",
                "granularity": "day",
                "metrics": ["successRate", "aiEfficiency"]
            }
        },
        # Test 6: Performance Summary
        {
            "name": "Performance Summary",
            "url": "http://localhost:5000/api/analytics/performance/summary",
            "params": {"period": "7d"}
        },
        # Test 7: Available Metrics
        {
            "name": "Available Metrics",
            "url": "http://localhost:5000/api/analytics/performance/metrics",
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
                
                # Show sample data for main performance endpoint
                if "/performance" in test_case['url'] and "summary" not in test_case['url'] and "metrics" not in test_case['url']:
                    if 'data' in data and 'labels' in data['data']:
                        print(f"Data points: {len(data['data']['labels'])}")
                        print(f"Datasets: {len(data['data']['datasets'])}")
                        print(f"Summary - Success Rate: {data['data']['summary']['averageSuccessRate']}%")
                        print(f"Summary - Response Time: {data['data']['summary']['averageResponseTime']} min")
                        print(f"Summary - AI Efficiency: {data['data']['summary']['averageAiEfficiency']}%")
                        
                        # Show sample dataset info
                        if data['data']['datasets']:
                            first_dataset = data['data']['datasets'][0]
                            print(f"First dataset: {first_dataset['label']}")
                            print(f"Sample data: {first_dataset['data'][:3]}...")
                
                # Show summary data
                elif "summary" in test_case['url']:
                    if 'data' in data:
                        summary = data['data']
                        print(f"Total Requests: {summary['totalRequests']}")
                        print(f"Success Rate: {summary['successRate']}%")
                        print(f"Response Time: {summary['responseTime']} min")
                        print(f"AI Efficiency: {summary['aiEfficiency']}%")
                
                # Show available metrics
                elif "metrics" in test_case['url']:
                    if 'data' in data:
                        metrics = data['data']
                        print(f"Available metrics: {len(metrics)}")
                        for metric in metrics:
                            print(f"  - {metric['name']} ({metric['key']}): {metric['description']}")
                
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
    success = test_analytics_performance()
    sys.exit(0 if success else 1)