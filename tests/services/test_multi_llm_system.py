#!/usr/bin/env python3
"""
Comprehensive Multi-LLM System Test
Tests all aspects of the multi-LLM fallback system implementation
"""

import requests
import json
import time
from datetime import datetime

class MultiLLMSystemTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_time: float = 0):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_time_ms": int(response_time * 1000),
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"     {details}")
        if response_time > 0:
            print(f"     Response time: {int(response_time * 1000)}ms")
        print()

    def test_llm_status_endpoint(self):
        """Test LLM status monitoring endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/llm/status")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                total_providers = data.get("total_providers", 0)
                active_providers = data.get("active_providers", 0)
                recommended = data.get("recommended_provider", "unknown")
                
                success = total_providers >= 3 and active_providers >= 1
                details = f"Total: {total_providers}, Active: {active_providers}, Recommended: {recommended}"
                
                self.log_test("LLM Status Endpoint", success, details, response_time)
                return data
            else:
                self.log_test("LLM Status Endpoint", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("LLM Status Endpoint", False, f"Error: {str(e)}")
            return None

    def test_llm_health_check(self):
        """Test LLM health check endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/llm/health")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                service_operational = data.get("service_operational", False)
                active_providers = data.get("active_providers", [])
                
                success = service_operational and len(active_providers) >= 1
                details = f"Operational: {service_operational}, Active: {active_providers}"
                
                self.log_test("LLM Health Check", success, details, response_time)
                return data
            else:
                self.log_test("LLM Health Check", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("LLM Health Check", False, f"Error: {str(e)}")
            return None

    def test_individual_providers(self):
        """Test individual LLM providers"""
        providers = ["claude", "gemini", "openai"]
        test_message = "Bonjour, comment puis-je vous aider?"
        
        provider_results = {}
        
        for provider in providers:
            start_time = time.time()
            try:
                response = requests.post(f"{self.base_url}/api/llm/test", json={
                    "provider": provider,
                    "test_message": test_message
                })
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False)
                    error_msg = data.get("error_message", "")
                    
                    if success:
                        details = f"Response generated successfully"
                    else:
                        details = f"Failed: {error_msg}"
                    
                    provider_results[provider] = success
                    self.log_test(f"Provider Test: {provider.upper()}", success, details, response_time)
                else:
                    provider_results[provider] = False
                    self.log_test(f"Provider Test: {provider.upper()}", False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                provider_results[provider] = False
                self.log_test(f"Provider Test: {provider.upper()}", False, f"Error: {str(e)}")
        
        return provider_results

    def test_ai_suggestions_fallback(self):
        """Test AI suggestions with multi-LLM fallback"""
        start_time = time.time()
        try:
            response = requests.post(f"{self.base_url}/api/ai-suggestions/generate", json={
                "current_message": "J'ai un problème de plomberie urgent à Bonamoussadi",
                "ai_response": "Je comprends votre problème. Pouvez-vous me donner plus de détails?",
                "user_id": "test_multi_llm_fallback",
                "conversation_context": {
                    "extracted_info": {
                        "service_type": "plomberie",
                        "urgency": "urgent",
                        "location": "Bonamoussadi"
                    }
                },
                "conversation_phase": "information_gathering"
            })
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                suggestions = data.get("suggestions", [])
                fallback_used = data.get("fallback_used", False)
                generation_time = data.get("generation_time_ms", 0)
                
                details = f"Suggestions: {len(suggestions)}, Fallback: {fallback_used}, Gen time: {generation_time}ms"
                
                self.log_test("AI Suggestions Fallback", success, details, response_time)
                return data
            else:
                self.log_test("AI Suggestions Fallback", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("AI Suggestions Fallback", False, f"Error: {str(e)}")
            return None

    def test_conversation_engine_fallback(self):
        """Test conversation engine with multi-LLM fallback"""
        start_time = time.time()
        try:
            # Send a message to the chat endpoint
            response = requests.post(f"{self.base_url}/webhook/chat", json={
                "message": "J'ai besoin d'un plombier à Bonamoussadi pour une urgence",
                "phone": "+237691924177",
                "user_id": "test_multi_llm_conversation"
            })
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                response_text = data.get("response", "")
                
                # Check if we got a meaningful response
                meaningful_response = len(response_text) > 10 and "erreur" not in response_text.lower()
                
                details = f"Response generated: {len(response_text)} chars, Meaningful: {meaningful_response}"
                
                self.log_test("Conversation Engine Fallback", success and meaningful_response, details, response_time)
                return data
            else:
                self.log_test("Conversation Engine Fallback", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("Conversation Engine Fallback", False, f"Error: {str(e)}")
            return None

    def test_provider_availability_recovery(self):
        """Test system recovery when providers become available again"""
        start_time = time.time()
        try:
            # Reset failed providers
            response = requests.post(f"{self.base_url}/api/llm/reset-failures")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                message = data.get("message", "")
                
                details = f"Reset successful: {success}, Message: {message}"
                
                self.log_test("Provider Recovery Reset", success, details, response_time)
                return data
            else:
                self.log_test("Provider Recovery Reset", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("Provider Recovery Reset", False, f"Error: {str(e)}")
            return None

    def generate_summary_report(self):
        """Generate comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        avg_response_time = sum(result["response_time_ms"] for result in self.test_results) / total_tests
        
        print("="*60)
        print("MULTI-LLM SYSTEM TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Average Response Time: {avg_response_time:.0f}ms")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test_name']}: {result['details']}")
        else:
            print("🎉 ALL TESTS PASSED!")
        
        print("="*60)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "test_results": self.test_results
        }

    def run_comprehensive_test(self):
        """Run all multi-LLM system tests"""
        print("🚀 Starting Multi-LLM System Comprehensive Test")
        print("="*60)
        
        # Test 1: LLM Status Monitoring
        self.test_llm_status_endpoint()
        
        # Test 2: Health Check
        self.test_llm_health_check()
        
        # Test 3: Individual Provider Tests
        self.test_individual_providers()
        
        # Test 4: AI Suggestions Fallback
        self.test_ai_suggestions_fallback()
        
        # Test 5: Conversation Engine Fallback
        self.test_conversation_engine_fallback()
        
        # Test 6: Provider Recovery
        self.test_provider_availability_recovery()
        
        # Generate summary report
        summary = self.generate_summary_report()
        
        return summary

def main():
    """Main function"""
    tester = MultiLLMSystemTester()
    summary = tester.run_comprehensive_test()
    
    # Save results to file
    with open("multi_llm_test_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nTest results saved to: multi_llm_test_results.json")
    
    # Return success code based on test results
    return 0 if summary["failed_tests"] == 0 else 1

if __name__ == "__main__":
    exit(main())