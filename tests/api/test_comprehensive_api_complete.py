#!/usr/bin/env python3
"""
Comprehensive API Test Suite for All Implemented Endpoints
Tests all 45+ endpoints across 9 API modules
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class ComprehensiveAPITester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.token = None
        self.test_results = []
        
    def log_test(self, endpoint: str, method: str, status: str, response_time: float, details: str = ""):
        """Log test result"""
        self.test_results.append({
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "response_time": response_time,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"[{status}] {method} {endpoint} - {response_time:.2f}ms {details}")
    
    def authenticate(self) -> bool:
        """Authenticate and get token"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                data={"username": "admin", "password": "admin123"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.log_test("/auth/login", "POST", "SUCCESS", 0, "Authentication successful")
                return True
            else:
                self.log_test("/auth/login", "POST", "FAILED", 0, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("/auth/login", "POST", "ERROR", 0, f"Auth error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None) -> bool:
        """Test a single endpoint"""
        start_time = time.time()
        try:
            headers = self.get_headers()
            
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(f"{self.base_url}{endpoint}", json=data, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(f"{self.base_url}{endpoint}", json=data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(f"{self.base_url}{endpoint}", headers=headers, timeout=10)
            else:
                self.log_test(endpoint, method, "UNSUPPORTED", 0, "Unsupported method")
                return False
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 201, 202]:
                self.log_test(endpoint, method, "SUCCESS", response_time, f"HTTP {response.status_code}")
                return True
            else:
                self.log_test(endpoint, method, "FAILED", response_time, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.log_test(endpoint, method, "ERROR", response_time, f"Exception: {e}")
            return False
    
    def test_analytics_api(self):
        """Test Analytics API endpoints"""
        print("\n=== Testing Analytics API ===")
        endpoints = [
            "/api/analytics/overview",
            "/api/analytics/performance",
            "/api/analytics/revenue",
            "/api/analytics/trends",
            "/api/analytics/reports",
            "/api/analytics/real-time",
            "/api/analytics/kpi"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
    
    def test_providers_api(self):
        """Test Providers API endpoints"""
        print("\n=== Testing Providers API ===")
        endpoints = [
            "/api/providers/",
            "/api/providers/stats",
            "/api/providers/performance",
            "/api/providers/availability",
            "/api/providers/search",
            "/api/providers/rankings",
            "/api/providers/verification"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
        
        # Test specific provider endpoint
        self.test_endpoint("/api/providers/1")
    
    def test_requests_api(self):
        """Test Requests API endpoints"""
        print("\n=== Testing Requests API ===")
        endpoints = [
            "/api/requests/",
            "/api/requests/stats",
            "/api/requests/analytics",
            "/api/requests/timeline",
            "/api/requests/status-distribution",
            "/api/requests/priority-analysis",
            "/api/requests/performance",
            "/api/requests/search"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
        
        # Test specific request endpoint
        self.test_endpoint("/api/requests/1")
        
        # Test POST request creation
        self.test_endpoint(
            "/api/requests/",
            method="POST",
            data={
                "clientName": "Test Client",
                "serviceType": "plomberie",
                "description": "Test request",
                "location": "Bonamoussadi",
                "phone": "237690000001",
                "urgency": "normale"
            }
        )
    
    def test_finances_api(self):
        """Test Finances API endpoints"""
        print("\n=== Testing Finances API ===")
        endpoints = [
            "/api/finances/overview",
            "/api/finances/revenue",
            "/api/finances/transactions",
            "/api/finances/analytics",
            "/api/finances/commissions",
            "/api/finances/reports",
            "/api/finances/trends"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
    
    def test_ai_api(self):
        """Test AI API endpoints"""
        print("\n=== Testing AI API ===")
        endpoints = [
            "/api/ai/metrics",
            "/api/ai/insights",
            "/api/ai/health"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
        
        # Test AI analysis
        self.test_endpoint(
            "/api/ai/analyze",
            method="POST",
            data={"message": "J'ai un problème de plomberie"}
        )
        
        # Test AI chat
        self.test_endpoint(
            "/api/ai/chat",
            method="POST",
            data={"message": "Bonjour", "sessionId": "test-session"}
        )
    
    def test_settings_api(self):
        """Test Settings API endpoints"""
        print("\n=== Testing Settings API ===")
        endpoints = [
            "/api/settings/",
            "/api/settings/general",
            "/api/settings/notifications"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
        
        # Test settings update
        self.test_endpoint(
            "/api/settings/general",
            method="PUT",
            data={"siteName": "Djobea AI Test", "language": "fr"}
        )
    
    def test_geolocation_api(self):
        """Test Geolocation API endpoints"""
        print("\n=== Testing Geolocation API ===")
        endpoints = [
            "/api/geolocation/",
            "/api/geolocation/zones",
            "/api/geolocation/zones/1",
            "/api/geolocation/zones/2"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
    
    def test_notifications_api(self):
        """Test Notifications API endpoints"""
        print("\n=== Testing Notifications API ===")
        endpoints = [
            "/api/notifications/",
            "/api/notifications/?status=unread",
            "/api/notifications/?type=system"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
        
        # Test mark as read
        self.test_endpoint("/api/notifications/1/read", method="PUT")
        self.test_endpoint("/api/notifications/read-all", method="PUT")
    
    def test_export_api(self):
        """Test Export API endpoints"""
        print("\n=== Testing Export API ===")
        
        # Test export creation
        export_response = self.test_endpoint(
            "/api/export/",
            method="POST",
            data={
                "type": "requests",
                "format": "csv",
                "dateRange": {
                    "start": "2025-01-01",
                    "end": "2025-12-31"
                }
            }
        )
        
        # Test export status (using a dummy ID)
        self.test_endpoint("/api/export/dummy-export-id")
    
    def test_auth_api(self):
        """Test Auth API endpoints"""
        print("\n=== Testing Auth API ===")
        endpoints = [
            "/auth/profile",
            "/auth/users",
            "/auth/security-logs",
            "/auth/health"
        ]
        
        for endpoint in endpoints:
            self.test_endpoint(endpoint)
    
    def run_comprehensive_test(self):
        """Run comprehensive API testing"""
        print("🚀 Starting Comprehensive API Test Suite")
        print("=" * 60)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        # Test all API modules
        self.test_analytics_api()
        self.test_providers_api()
        self.test_requests_api()
        self.test_finances_api()
        self.test_ai_api()
        self.test_settings_api()
        self.test_geolocation_api()
        self.test_notifications_api()
        self.test_export_api()
        self.test_auth_api()
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE API TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["status"] == "SUCCESS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAILED"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])
        
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Average response time
        response_times = [r["response_time"] for r in self.test_results if r["response_time"] > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        print(f"Average Response Time: {avg_response_time:.2f}ms")
        
        # Test by API module
        print("\n📋 Results by API Module:")
        modules = {}
        for result in self.test_results:
            module = result["endpoint"].split("/")[2] if len(result["endpoint"].split("/")) > 2 else "auth"
            if module not in modules:
                modules[module] = {"total": 0, "success": 0}
            modules[module]["total"] += 1
            if result["status"] == "SUCCESS":
                modules[module]["success"] += 1
        
        for module, stats in modules.items():
            success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  {module}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Failed tests details
        failed_results = [r for r in self.test_results if r["status"] in ["FAILED", "ERROR"]]
        if failed_results:
            print(f"\n❌ Failed Tests ({len(failed_results)}):")
            for result in failed_results:
                print(f"  {result['method']} {result['endpoint']} - {result['details']}")
        
        # Summary
        print("\n" + "=" * 60)
        if success_rate >= 90:
            print("✅ EXCELLENT: API suite is working perfectly!")
        elif success_rate >= 75:
            print("✅ GOOD: API suite is working well with minor issues")
        elif success_rate >= 50:
            print("⚠️ FAIR: API suite needs attention")
        else:
            print("❌ POOR: API suite requires immediate fixes")
        
        print("=" * 60)
        
        # Save results to file
        with open("api_test_results_comprehensive.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "successful": successful_tests,
                    "failed": failed_tests,
                    "errors": error_tests,
                    "success_rate": success_rate,
                    "average_response_time": avg_response_time,
                    "test_date": datetime.utcnow().isoformat()
                },
                "results": self.test_results
            }, f, indent=2)
        
        print("📄 Detailed results saved to: api_test_results_comprehensive.json")

def main():
    """Main function"""
    tester = ComprehensiveAPITester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()