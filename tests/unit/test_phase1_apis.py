"""
Phase 1 API Testing - Core API endpoints validation
Tests authentication and dashboard endpoints with proper JWT tokens
"""

import requests
import json
import time
from datetime import datetime

class Phase1APITester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.token = None
        self.refresh_token = None
        self.test_results = []
        
    def log_test(self, endpoint, method, status, response_time, details=""):
        """Log test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "response_time": response_time,
            "details": details
        }
        self.test_results.append(result)
        print(f"[{status}] {method} {endpoint} - {response_time:.2f}ms - {details}")
        
    def authenticate(self):
        """Authenticate with admin credentials"""
        login_data = {
            "email": "admin@djobea.ai",
            "password": "admin123",
            "rememberMe": False
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/api/api/auth/login",
                json=login_data,
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("token"):
                    self.token = data["token"]
                    self.refresh_token = data.get("refreshToken")
                    self.log_test("/api/api/auth/login", "POST", "SUCCESS", response_time, "Authentication successful")
                    return True
                else:
                    self.log_test("/api/api/auth/login", "POST", "FAILED", response_time, f"Invalid response: {data}")
                    return False
            else:
                self.log_test("/api/api/auth/login", "POST", "FAILED", response_time, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            self.log_test("/api/api/auth/login", "POST", "ERROR", response_time, f"Request failed: {str(e)}")
            return False
            
    def test_endpoint(self, endpoint, method="GET", data=None, auth_required=True):
        """Test a single endpoint"""
        headers = {}
        if auth_required and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        start_time = time.time()
        try:
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(f"{self.base_url}{endpoint}", json=data, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(f"{self.base_url}{endpoint}", json=data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(f"{self.base_url}{endpoint}", headers=headers, timeout=10)
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        self.log_test(endpoint, method, "SUCCESS", response_time, "Valid response received")
                        return True
                    else:
                        self.log_test(endpoint, method, "PARTIAL", response_time, f"Response: {data}")
                        return True
                except json.JSONDecodeError:
                    self.log_test(endpoint, method, "SUCCESS", response_time, "Non-JSON response")
                    return True
            elif response.status_code == 401:
                self.log_test(endpoint, method, "AUTH_REQUIRED", response_time, "Authentication required")
                return False
            elif response.status_code == 404:
                self.log_test(endpoint, method, "NOT_FOUND", response_time, "Endpoint not found")
                return False
            else:
                self.log_test(endpoint, method, "FAILED", response_time, f"HTTP {response.status_code}: {response.text[:100]}")
                return False
                
        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            self.log_test(endpoint, method, "ERROR", response_time, f"Request failed: {str(e)}")
            return False
            
    def test_phase1_endpoints(self):
        """Test all Phase 1 endpoints"""
        print("=== PHASE 1 API TESTING ===")
        print("Testing Core API endpoints (Auth + Dashboard)")
        print()
        
        # Test authentication endpoints
        print("1. Testing Authentication Endpoints...")
        auth_endpoints = [
            ("/api/api/auth/login", "POST", {"email": "admin@djobea.ai", "password": "admin123"}, False),
            ("/api/api/auth/profile", "GET", None, True),
            ("/api/api/auth/refresh", "POST", {"refreshToken": "fake-token"}, False),
            ("/api/api/auth/logout", "POST", None, True)
        ]
        
        for endpoint, method, data, auth_required in auth_endpoints:
            if endpoint == "/api/api/auth/login":
                self.authenticate()
            else:
                self.test_endpoint(endpoint, method, data, auth_required)
        
        print()
        print("2. Testing Dashboard Endpoints...")
        dashboard_endpoints = [
            ("/api/dashboard/dashboard", "GET", None, True),
            ("/api/dashboard/dashboard?period=7d", "GET", None, True),
            ("/api/dashboard/dashboard?period=30d", "GET", None, True),
            ("/api/dashboard/stats", "GET", None, True),
            ("/api/dashboard/stats?period=24h", "GET", None, True),
            ("/api/dashboard/activity", "GET", None, True),
            ("/api/dashboard/activity?limit=5&offset=0", "GET", None, True),
            ("/api/dashboard/metrics", "GET", None, True),
            ("/api/dashboard/charts/activity", "GET", None, True),
            ("/api/dashboard/charts/services", "GET", None, True)
        ]
        
        for endpoint, method, data, auth_required in dashboard_endpoints:
            self.test_endpoint(endpoint, method, data, auth_required)
            
        print()
        self.generate_report()
        
    def generate_report(self):
        """Generate test report"""
        print("=== TEST REPORT ===")
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["status"] in ["SUCCESS", "PARTIAL"]])
        auth_required_tests = len([r for r in self.test_results if r["status"] == "AUTH_REQUIRED"])
        failed_tests = len([r for r in self.test_results if r["status"] in ["FAILED", "ERROR", "NOT_FOUND"]])
        
        print(f"Total tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Auth required: {auth_required_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {(successful_tests / total_tests * 100):.1f}%")
        print()
        
        # Group results by status
        status_groups = {}
        for result in self.test_results:
            status = result["status"]
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(result)
        
        for status, results in status_groups.items():
            print(f"{status} ({len(results)} tests):")
            for result in results:
                print(f"  - {result['method']} {result['endpoint']} - {result['details']}")
        
        print()
        
        # Save results to file
        with open("phase1_api_test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        
        print("Test results saved to phase1_api_test_results.json")
        
        # Recommendations
        print("\n=== RECOMMENDATIONS ===")
        if auth_required_tests > 0:
            print("✓ Authentication system is working correctly")
        if successful_tests > 0:
            print("✓ API endpoints are responding properly")
        if failed_tests > 0:
            print("⚠ Some endpoints need attention - check failed tests above")
        
        print("\n=== NEXT STEPS ===")
        print("1. Fix any failed endpoints identified above")
        print("2. Continue with Phase 2 - Providers and Requests modules")
        print("3. Test authentication flow with real admin credentials")

if __name__ == "__main__":
    tester = Phase1APITester()
    tester.test_phase1_endpoints()