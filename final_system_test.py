#!/usr/bin/env python3
"""
Final System Test - Comprehensive testing of Dynamic Services API
This script validates the complete functionality of the dynamic services system
"""

import requests
import json
from datetime import datetime

def run_comprehensive_tests():
    """Run comprehensive tests for the dynamic services API"""
    
    base_url = "http://localhost:5000/api/v1/dynamic-services"
    
    print("🚀 Starting Comprehensive Dynamic Services System Test")
    print("=" * 60)
    
    # Test 1: System Health Check
    print("\n1. System Health Check")
    response = requests.get(f"{base_url}/test/system")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Database connectivity: {data['test_results']['database_connectivity']}")
        print(f"   ✅ Zone count: {data['test_results']['zone_count']}")
        print(f"   ✅ Category count: {data['test_results']['category_count']}")
        print(f"   ✅ Service count: {data['test_results']['service_count']}")
    else:
        print(f"   ❌ System health check failed: {response.status_code}")
    
    # Test 2: Zone Search Functionality
    print("\n2. Zone Search Tests")
    zone_tests = [
        ("bonamoussadi", "District-level search"),
        ("douala", "City-level search"),
        ("littoral", "Region-level search"),
        ("akwa", "District-level search")
    ]
    
    for query, description in zone_tests:
        response = requests.get(f"{base_url}/zones/search?query={query}&limit=5")
        if response.status_code == 200:
            data = response.json()
            if data['success'] and data['results']:
                zone = data['results'][0]['zone']
                print(f"   ✅ {description}: {zone['name']} (Score: {data['results'][0]['relevance_score']})")
            else:
                print(f"   ❌ {description}: No results")
        else:
            print(f"   ❌ {description}: HTTP {response.status_code}")
    
    # Test 3: Service Search Functionality
    print("\n3. Service Search Tests")
    service_tests = [
        ("plomberie", "French plumbing search"),
        ("plumbing", "English plumbing search"),
        ("fuite", "Water leak search"),
        ("débouchage", "Drain cleaning search"),
        ("électricité", "Electrical services search"),
        ("réparation", "General repair search")
    ]
    
    for query, description in service_tests:
        response = requests.get(f"{base_url}/services/search?query={query}&limit=5")
        if response.status_code == 200:
            data = response.json()
            if data['success'] and data['results']:
                service = data['results'][0]['service']
                print(f"   ✅ {description}: {service['name']} (Score: {data['results'][0]['relevance_score']})")
            else:
                print(f"   ❌ {description}: No results")
        else:
            print(f"   ❌ {description}: HTTP {response.status_code}")
    
    # Test 4: Zone-Specific Service Search
    print("\n4. Zone-Specific Service Search")
    zone_service_tests = [
        ("plomberie", "bonamoussadi", "Plumbing in Bonamoussadi"),
        ("électricité", "douala", "Electrical in Douala"),
        ("réparation", "akwa", "Repair in Akwa")
    ]
    
    for query, zone_code, description in zone_service_tests:
        response = requests.get(f"{base_url}/services/search?query={query}&zone_code={zone_code}&limit=5")
        if response.status_code == 200:
            data = response.json()
            if data['success'] and data['results']:
                service = data['results'][0]['service']
                print(f"   ✅ {description}: {service['name']} (Score: {data['results'][0]['relevance_score']})")
            else:
                print(f"   ❌ {description}: No results")
        else:
            print(f"   ❌ {description}: HTTP {response.status_code}")
    
    # Test 5: Performance and Caching
    print("\n5. Performance and Caching Tests")
    
    # Test cache performance
    import time
    start_time = time.time()
    response = requests.get(f"{base_url}/services/search?query=plomberie&limit=5")
    first_request_time = time.time() - start_time
    
    start_time = time.time()
    response = requests.get(f"{base_url}/services/search?query=plomberie&limit=5")
    second_request_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        cached = data.get('cached', False)
        print(f"   ✅ First request: {first_request_time:.3f}s")
        print(f"   ✅ Second request: {second_request_time:.3f}s (Cached: {cached})")
    else:
        print(f"   ❌ Performance test failed: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("🎉 Dynamic Services System Test Complete!")
    print(f"📅 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    run_comprehensive_tests()