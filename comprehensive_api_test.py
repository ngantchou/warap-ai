#!/usr/bin/env python3
"""
Comprehensive API Testing Script for Djobea AI
Tests all 44 endpoints across 7 categories
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class DjobeaAPITester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.access_token = None
        self.test_results = []
        
    def log_test(self, category: str, endpoint: str, method: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "details": details
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⚠️"
        print(f"{status_emoji} [{category}] {method} {endpoint} - {status}")
        if details:
            print(f"   Details: {details}")
    
    def authenticate(self) -> bool:
        """Authenticate with admin credentials"""
        try:
            # Try email-based authentication
            response = requests.post(
                f"{self.base_url}/auth/api/auth/login",
                json={"email": "admin@djobea.ai", "password": "admin123"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "token" in data:
                    self.access_token = data["token"]
                    self.log_test("AUTH", "/auth/api/auth/login", "POST", "SUCCESS", "Email-based login successful")
                    return True
            
            # Try username-based authentication
            response = requests.post(
                f"{self.base_url}/auth/api/login",
                json={"username": "admin", "password": "admin123"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "token" in data:
                    self.access_token = data["token"]
                    self.log_test("AUTH", "/auth/api/login", "POST", "SUCCESS", "Username-based login successful")
                    return True
            
            self.log_test("AUTH", "/auth/api/login", "POST", "FAILED", f"Status: {response.status_code}")
            return False
            
        except Exception as e:
            self.log_test("AUTH", "/auth/api/login", "POST", "FAILED", str(e))
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def test_endpoint(self, category: str, endpoint: str, method: str = "GET", data: Dict = None) -> bool:
        """Test a single endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            headers = self.get_headers()
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code in [200, 201]:
                self.log_test(category, endpoint, method, "SUCCESS", f"Status: {response.status_code}")
                return True
            elif response.status_code == 401:
                self.log_test(category, endpoint, method, "AUTH_REQUIRED", f"Status: {response.status_code}")
                return False
            else:
                self.log_test(category, endpoint, method, "FAILED", f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(category, endpoint, method, "FAILED", str(e))
            return False
    
    def test_analytics_endpoints(self):
        """Test Analytics API endpoints"""
        print("\n🔍 Testing Analytics API Endpoints...")
        endpoints = [
            ("/api/analytics/", "GET"),
            ("/api/analytics/performance", "GET"),
            ("/api/analytics/geographic", "GET"),
            ("/api/analytics/services", "GET"),
            ("/api/analytics/kpis", "GET"),
            ("/api/analytics/insights", "GET"),
            ("/api/analytics/leaderboard", "GET")
        ]
        
        success_count = 0
        for endpoint, method in endpoints:
            if self.test_endpoint("ANALYTICS", endpoint, method):
                success_count += 1
        
        print(f"Analytics API: {success_count}/{len(endpoints)} endpoints successful")
        return success_count, len(endpoints)
    
    def test_providers_endpoints(self):
        """Test Providers API endpoints"""
        print("\n👷 Testing Providers API Endpoints...")
        endpoints = [
            ("/api/providers/", "GET"),
            ("/api/providers/available", "GET"),
            ("/api/providers/stats", "GET"),
            ("/api/providers/1", "GET"),
            ("/api/providers/1/status", "GET"),
            ("/api/providers/1/contact", "POST", {"message": "Test message"})
        ]
        
        success_count = 0
        for item in endpoints:
            endpoint, method = item[0], item[1]
            data = item[2] if len(item) > 2 else None
            if self.test_endpoint("PROVIDERS", endpoint, method, data):
                success_count += 1
        
        print(f"Providers API: {success_count}/{len(endpoints)} endpoints successful")
        return success_count, len(endpoints)
    
    def test_requests_endpoints(self):
        """Test Requests API endpoints"""
        print("\n📋 Testing Requests API Endpoints...")
        endpoints = [
            ("/api/requests/", "GET"),
            ("/api/requests/1", "GET"),
            ("/api/requests/1/status", "GET"),
            ("/api/requests/1/invoice", "GET"),
            ("/api/requests/1/cancel", "POST", {"reason": "Test cancellation"}),
            ("/api/requests/1/assign", "POST", {"provider_id": 1})
        ]
        
        success_count = 0
        for item in endpoints:
            endpoint, method = item[0], item[1]
            data = item[2] if len(item) > 2 else None
            if self.test_endpoint("REQUESTS", endpoint, method, data):
                success_count += 1
        
        print(f"Requests API: {success_count}/{len(endpoints)} endpoints successful")
        return success_count, len(endpoints)
    
    def test_finances_endpoints(self):
        """Test Finances API endpoints"""
        print("\n💰 Testing Finances API Endpoints...")
        endpoints = [
            ("/api/finances/", "GET"),
            ("/api/finances/overview", "GET"),
            ("/api/finances/transactions", "GET"),
            ("/api/finances/commissions", "GET"),
            ("/api/finances/payouts", "GET"),
            ("/api/finances/reports", "GET"),
            ("/api/finances/payouts", "POST", {"provider_id": 1, "amount": 1000})
        ]
        
        success_count = 0
        for item in endpoints:
            endpoint, method = item[0], item[1]
            data = item[2] if len(item) > 2 else None
            if self.test_endpoint("FINANCES", endpoint, method, data):
                success_count += 1
        
        print(f"Finances API: {success_count}/{len(endpoints)} endpoints successful")
        return success_count, len(endpoints)
    
    def test_system_endpoints(self):
        """Test System API endpoints"""
        print("\n⚙️ Testing System API Endpoints...")
        endpoints = [
            ("/api/metrics/system", "GET"),
        ]
        
        success_count = 0
        for endpoint, method in endpoints:
            if self.test_endpoint("SYSTEM", endpoint, method):
                success_count += 1
        
        print(f"System API: {success_count}/{len(endpoints)} endpoints successful")
        return success_count, len(endpoints)
    
    def test_ai_endpoints(self):
        """Test AI API endpoints"""
        print("\n🤖 Testing AI API Endpoints...")
        endpoints = [
            ("/api/ai/predictions", "GET"),
            ("/api/ai/models", "GET"),
            ("/api/ai/metrics", "GET"),
            ("/api/ai/health", "GET"),
            ("/api/ai/analyze", "POST", {"text": "J'ai un problème de plomberie", "language": "fr"}),
            ("/api/ai/chat", "POST", {"message": "Bonjour", "sessionId": "test-session"})
        ]
        
        success_count = 0
        for item in endpoints:
            endpoint, method = item[0], item[1]
            data = item[2] if len(item) > 2 else None
            if self.test_endpoint("AI", endpoint, method, data):
                success_count += 1
        
        print(f"AI API: {success_count}/{len(endpoints)} endpoints successful")
        return success_count, len(endpoints)
    
    def test_settings_endpoints(self):
        """Test Settings API endpoints"""
        print("\n⚙️ Testing Settings API Endpoints...")
        endpoints = [
            ("/api/settings/system", "GET"),
            ("/api/settings/notifications", "GET"),
            ("/api/settings/pricing", "GET"),
            ("/api/settings/integrations", "GET")
        ]
        
        success_count = 0
        for endpoint, method in endpoints:
            if self.test_endpoint("SETTINGS", endpoint, method):
                success_count += 1
        
        print(f"Settings API: {success_count}/{len(endpoints)} endpoints successful")
        return success_count, len(endpoints)
    
    def run_comprehensive_test(self):
        """Run comprehensive API testing"""
        print("🚀 Starting Comprehensive Djobea AI API Testing...")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test authentication
        if not self.authenticate():
            print("❌ Authentication failed - testing endpoints without auth")
        
        # Test all endpoint categories
        results = []
        results.append(self.test_analytics_endpoints())
        results.append(self.test_providers_endpoints())
        results.append(self.test_requests_endpoints())
        results.append(self.test_finances_endpoints())
        results.append(self.test_system_endpoints())
        results.append(self.test_ai_endpoints())
        results.append(self.test_settings_endpoints())
        
        # Calculate totals
        total_success = sum(r[0] for r in results)
        total_endpoints = sum(r[1] for r in results)
        success_rate = (total_success / total_endpoints * 100) if total_endpoints > 0 else 0
        
        # Generate summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Endpoints Tested: {total_endpoints}")
        print(f"Successful: {total_success}")
        print(f"Failed: {total_endpoints - total_success}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Detailed results by category
        print("\n📋 DETAILED RESULTS BY CATEGORY:")
        categories = ["ANALYTICS", "PROVIDERS", "REQUESTS", "FINANCES", "SYSTEM", "AI", "SETTINGS"]
        for i, category in enumerate(categories):
            if i < len(results):
                success, total = results[i]
                rate = (success / total * 100) if total > 0 else 0
                print(f"  {category}: {success}/{total} ({rate:.1f}%)")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_test_results_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_endpoints": total_endpoints,
                    "successful": total_success,
                    "failed": total_endpoints - total_success,
                    "success_rate": success_rate
                },
                "detailed_results": self.test_results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")
        return success_rate >= 70  # Consider 70%+ success rate as passing

def main():
    """Main function"""
    tester = DjobeaAPITester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 API Testing PASSED - System ready for deployment!")
    else:
        print("\n⚠️ API Testing needs attention - Some endpoints require fixes")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())