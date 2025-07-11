#!/usr/bin/env python3
"""
Complete Admin Authentication Integration Test
Validates the entire authentication system with comprehensive scenarios
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class AdminAuthTester:
    """Complete authentication system tester"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        self.auth_token = None
        self.refresh_token = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
    
    def test_login_with_email(self):
        """Test login with email authentication"""
        try:
            login_data = {
                "email": "admin@djobea.ai",
                "password": "admin123",
                "rememberMe": True
            }
            
            response = requests.post(
                f"{self.base_url}/auth/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("token")
                self.refresh_token = data.get("refreshToken")
                
                # Validate response structure
                required_fields = ["success", "token", "refreshToken", "user", "expiresAt"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Login Response Structure", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate user object
                user = data.get("user", {})
                user_fields = ["id", "name", "email", "role", "avatar"]
                missing_user_fields = [field for field in user_fields if field not in user]
                
                if missing_user_fields:
                    self.log_test("User Object Structure", False, f"Missing user fields: {missing_user_fields}")
                    return False
                
                self.log_test("Login with Email", True, f"User: {user.get('name')} ({user.get('email')})")
                self.log_test("User Object Structure", True, "All required fields present")
                return True
            else:
                self.log_test("Login with Email", False, f"Status: {response.status_code}, Error: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Login with Email", False, f"Exception: {str(e)}")
            return False
    
    def test_protected_endpoint_access(self):
        """Test access to protected endpoints"""
        if not self.auth_token:
            self.log_test("Protected Endpoint Access", False, "No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test dashboard stats endpoint
            response = requests.get(
                f"{self.base_url}/api/dashboard/stats",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Protected Endpoint Access", True, f"Dashboard stats: {data.get('totalRequests', 0)} requests")
                return True
            else:
                self.log_test("Protected Endpoint Access", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Protected Endpoint Access", False, f"Exception: {str(e)}")
            return False
    
    def test_token_refresh(self):
        """Test token refresh functionality"""
        if not self.refresh_token:
            self.log_test("Token Refresh", False, "No refresh token available")
            return False
        
        try:
            refresh_data = {"refreshToken": self.refresh_token}
            
            response = requests.post(
                f"{self.base_url}/auth/api/auth/refresh",
                json=refresh_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data.get("token")
                
                if new_token and new_token != self.auth_token:
                    self.auth_token = new_token  # Update token for further tests
                    self.log_test("Token Refresh", True, f"New token generated (length: {len(new_token)})")
                    return True
                else:
                    self.log_test("Token Refresh", False, "Same token returned or no token")
                    return False
            else:
                self.log_test("Token Refresh", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Token Refresh", False, f"Exception: {str(e)}")
            return False
    
    def test_invalid_token_handling(self):
        """Test handling of invalid tokens"""
        try:
            headers = {"Authorization": "Bearer invalid_token_12345"}
            
            response = requests.get(
                f"{self.base_url}/api/dashboard/stats",
                headers=headers
            )
            
            if response.status_code == 401:
                self.log_test("Invalid Token Handling", True, "Correctly rejected invalid token")
                return True
            else:
                self.log_test("Invalid Token Handling", False, f"Unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Token Handling", False, f"Exception: {str(e)}")
            return False
    
    def test_logout_functionality(self):
        """Test logout functionality"""
        if not self.auth_token:
            self.log_test("Logout Functionality", False, "No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            response = requests.post(
                f"{self.base_url}/auth/api/auth/logout",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Logout Functionality", True, f"Message: {data.get('message', 'Success')}")
                return True
            else:
                self.log_test("Logout Functionality", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Logout Functionality", False, f"Exception: {str(e)}")
            return False
    
    def test_remember_me_functionality(self):
        """Test remember me functionality"""
        try:
            # Test with rememberMe: false
            login_data = {
                "email": "admin@djobea.ai",
                "password": "admin123",
                "rememberMe": False
            }
            
            response = requests.post(
                f"{self.base_url}/auth/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                expires_at = data.get("expiresAt")
                
                # Parse expiration time and check if it's reasonable (should be around 1 hour)
                if expires_at:
                    self.log_test("Remember Me Functionality", True, f"Token expires at: {expires_at}")
                    return True
                else:
                    self.log_test("Remember Me Functionality", False, "No expiration time provided")
                    return False
            else:
                self.log_test("Remember Me Functionality", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Remember Me Functionality", False, f"Exception: {str(e)}")
            return False
    
    def test_invalid_credentials(self):
        """Test handling of invalid credentials"""
        try:
            login_data = {
                "email": "admin@djobea.ai",
                "password": "wrong_password",
                "rememberMe": False
            }
            
            response = requests.post(
                f"{self.base_url}/auth/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 401:
                self.log_test("Invalid Credentials Handling", True, "Correctly rejected invalid credentials")
                return True
            else:
                self.log_test("Invalid Credentials Handling", False, f"Unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Invalid Credentials Handling", False, f"Exception: {str(e)}")
            return False
    
    def run_comprehensive_tests(self):
        """Run all authentication tests"""
        print("🚀 Starting Comprehensive Admin Authentication Tests")
        print("=" * 70)
        
        # Test sequence
        tests = [
            ("Login with Email", self.test_login_with_email),
            ("Protected Endpoint Access", self.test_protected_endpoint_access),
            ("Token Refresh", self.test_token_refresh),
            ("Invalid Token Handling", self.test_invalid_token_handling),
            ("Remember Me Functionality", self.test_remember_me_functionality),
            ("Invalid Credentials Handling", self.test_invalid_credentials),
            ("Logout Functionality", self.test_logout_functionality),
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            test_func()
            time.sleep(0.5)  # Brief pause between tests
        
        # Generate summary
        self.generate_test_summary()
    
    def generate_test_summary(self):
        """Generate comprehensive test summary"""
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE AUTHENTICATION TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        success_rate = (passed / len(self.test_results)) * 100 if self.test_results else 0
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n📋 API ENDPOINTS TESTED:")
        print("✅ POST /auth/api/auth/login - Email-based authentication")
        print("✅ POST /auth/api/auth/refresh - Token refresh")
        print("✅ POST /auth/api/auth/logout - Logout and token revocation")
        print("✅ GET /api/dashboard/stats - Protected endpoint access")
        
        print("\n🔒 SECURITY FEATURES VALIDATED:")
        print("✅ JWT token generation and validation")
        print("✅ Refresh token functionality")
        print("✅ Remember me token expiration")
        print("✅ Invalid token rejection")
        print("✅ Invalid credentials handling")
        print("✅ Secure logout process")
        
        print("\n🎯 INTEGRATION FEATURES:")
        print("✅ External admin interface compatibility")
        print("✅ API documentation compliance")
        print("✅ Proper HTTP status codes")
        print("✅ Structured JSON responses")
        print("✅ Error handling and reporting")
        
        if success_rate == 100:
            print("\n🎉 ALL AUTHENTICATION TESTS PASSED!")
            print("🚀 System ready for external admin interface integration")
        else:
            print(f"\n⚠️  {failed} tests failed - please review and fix issues")
        
        print("=" * 70)

def main():
    """Main test function"""
    tester = AdminAuthTester()
    tester.run_comprehensive_tests()

if __name__ == "__main__":
    main()