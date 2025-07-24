#!/usr/bin/env python3
"""
Test Script for AI-Based Suggestions System
Validates the new intelligent, contextual suggestions functionality
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any, List

class AISuggestionsSystemTester:
    """Test suite for AI-based suggestions system"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        self.success_count = 0
        self.total_tests = 0
    
    def log_test_result(self, test_name: str, success: bool, details: str = "", suggestions: List[str] = None):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "suggestions": suggestions or [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        self.total_tests += 1
        if success:
            self.success_count += 1
        
        # Print result
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if suggestions:
            print(f"   Suggestions: {suggestions}")
        print()
    
    def test_chat_widget_ai_suggestions(self):
        """Test AI suggestions in chat widget"""
        print("="*60)
        print("TESTING AI SUGGESTIONS IN CHAT WIDGET")
        print("="*60)
        
        # Test scenarios
        scenarios = [
            {
                "name": "Plomberie Service Request",
                "message": "J'ai un problème de plomberie",
                "expected_context": "plomberie",
                "phone_number": "237691924190"
            },
            {
                "name": "Électricité with Location",
                "message": "Problème électrique à Bonamoussadi",
                "expected_context": "électricité",
                "phone_number": "237691924191"
            },
            {
                "name": "Urgency Request",
                "message": "C'est urgent! Le disjoncteur a sauté",
                "expected_context": "urgence",
                "phone_number": "237691924192"
            },
            {
                "name": "Incomplete Information",
                "message": "J'ai besoin d'aide",
                "expected_context": "information_gathering",
                "phone_number": "237691924193"
            }
        ]
        
        for scenario in scenarios:
            try:
                # Send message to chat widget
                response = requests.post(
                    f"{self.base_url}/webhook/chat",
                    json={
                        "message": scenario["message"],
                        "session_id": f"test_{scenario['name'].lower().replace(' ', '_')}",
                        "phone_number": scenario["phone_number"]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    suggestions = result.get("suggestions", [])
                    
                    # Check if suggestions are provided
                    if suggestions:
                        # Check if suggestions are contextual (not generic)
                        generic_suggestions = ["Oui", "Non", "Merci"]
                        is_contextual = not all(s in generic_suggestions for s in suggestions)
                        
                        if is_contextual:
                            self.log_test_result(
                                f"Chat Widget - {scenario['name']}",
                                True,
                                f"Generated {len(suggestions)} contextual suggestions",
                                suggestions
                            )
                        else:
                            self.log_test_result(
                                f"Chat Widget - {scenario['name']}",
                                False,
                                "Generated only generic suggestions",
                                suggestions
                            )
                    else:
                        # Check if this is a completed request (no suggestions expected)
                        phase = result.get("request_info", {}).get("phase", "unknown")
                        if phase == "request_processing":
                            self.log_test_result(
                                f"Chat Widget - {scenario['name']}",
                                True,
                                "Correctly hidden suggestions after request completion"
                            )
                        else:
                            self.log_test_result(
                                f"Chat Widget - {scenario['name']}",
                                False,
                                "No suggestions generated"
                            )
                else:
                    self.log_test_result(
                        f"Chat Widget - {scenario['name']}",
                        False,
                        f"HTTP {response.status_code}: {response.text}"
                    )
                    
            except Exception as e:
                self.log_test_result(
                    f"Chat Widget - {scenario['name']}",
                    False,
                    f"Error: {str(e)}"
                )
    
    def test_ai_suggestions_api(self):
        """Test the AI suggestions API endpoints"""
        print("="*60)
        print("TESTING AI SUGGESTIONS API ENDPOINTS")
        print("="*60)
        
        # Test health check
        try:
            response = requests.get(f"{self.base_url}/api/ai-suggestions/health")
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log_test_result(
                        "AI Suggestions API Health Check",
                        True,
                        f"Service healthy, generated {result.get('test_suggestions_generated', 0)} test suggestions"
                    )
                else:
                    self.log_test_result(
                        "AI Suggestions API Health Check",
                        False,
                        f"Service unhealthy: {result.get('error', 'Unknown error')}"
                    )
            else:
                self.log_test_result(
                    "AI Suggestions API Health Check",
                    False,
                    f"HTTP {response.status_code}"
                )
        except Exception as e:
            self.log_test_result(
                "AI Suggestions API Health Check",
                False,
                f"Error: {str(e)}"
            )
        
        # Test direct suggestion generation
        try:
            test_request = {
                "current_message": "J'ai un problème de plomberie urgent",
                "ai_response": "Je comprends votre problème de plomberie. Pouvez-vous me dire dans quel quartier vous vous trouvez?",
                "user_id": "test_user_api",
                "conversation_context": {
                    "extracted_info": {
                        "service_type": "plomberie",
                        "urgency": "élevée"
                    }
                },
                "conversation_phase": "information_gathering"
            }
            
            response = requests.post(
                f"{self.base_url}/api/ai-suggestions/generate",
                json=test_request
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    suggestions = result.get("suggestions", [])
                    generation_time = result.get("generation_time_ms", 0)
                    
                    self.log_test_result(
                        "Direct AI Suggestions Generation",
                        True,
                        f"Generated {len(suggestions)} suggestions in {generation_time}ms",
                        suggestions
                    )
                else:
                    self.log_test_result(
                        "Direct AI Suggestions Generation",
                        False,
                        "API returned success=False"
                    )
            else:
                self.log_test_result(
                    "Direct AI Suggestions Generation",
                    False,
                    f"HTTP {response.status_code}"
                )
        except Exception as e:
            self.log_test_result(
                "Direct AI Suggestions Generation",
                False,
                f"Error: {str(e)}"
            )
    
    def test_suggestion_quality(self):
        """Test the quality and relevance of AI suggestions"""
        print("="*60)
        print("TESTING AI SUGGESTION QUALITY")
        print("="*60)
        
        # Test different conversation contexts
        quality_tests = [
            {
                "context": "Plomberie + Location Missing",
                "message": "Fuite d'eau",
                "ai_response": "Je comprends que vous avez une fuite d'eau. Dans quel quartier êtes-vous?",
                "expected_themes": ["location", "quartier", "zone"]
            },
            {
                "context": "Électricité + Description Missing",
                "message": "Problème électrique à Bonamoussadi",
                "ai_response": "Pouvez-vous me décrire le problème électrique en détail?",
                "expected_themes": ["disjoncteur", "panne", "coupure"]
            },
            {
                "context": "Urgency Assessment",
                "message": "C'est urgent",
                "ai_response": "Je comprends que c'est urgent. Pouvez-vous me dire de quel type de problème il s'agit?",
                "expected_themes": ["oui", "urgent", "rapidement"]
            }
        ]
        
        for test in quality_tests:
            try:
                # Generate suggestions via API
                response = requests.post(
                    f"{self.base_url}/api/ai-suggestions/generate",
                    json={
                        "current_message": test["message"],
                        "ai_response": test["ai_response"],
                        "user_id": "quality_test",
                        "conversation_context": {},
                        "conversation_phase": "information_gathering"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    suggestions = result.get("suggestions", [])
                    
                    # Check if suggestions are relevant to expected themes
                    relevant_suggestions = []
                    for suggestion in suggestions:
                        suggestion_lower = suggestion.lower()
                        for theme in test["expected_themes"]:
                            if theme.lower() in suggestion_lower:
                                relevant_suggestions.append(suggestion)
                                break
                    
                    if relevant_suggestions:
                        self.log_test_result(
                            f"Quality Test - {test['context']}",
                            True,
                            f"Found {len(relevant_suggestions)} relevant suggestions",
                            relevant_suggestions
                        )
                    else:
                        self.log_test_result(
                            f"Quality Test - {test['context']}",
                            False,
                            "No relevant suggestions found",
                            suggestions
                        )
                else:
                    self.log_test_result(
                        f"Quality Test - {test['context']}",
                        False,
                        f"HTTP {response.status_code}"
                    )
            except Exception as e:
                self.log_test_result(
                    f"Quality Test - {test['context']}",
                    False,
                    f"Error: {str(e)}"
                )
    
    def test_performance_metrics(self):
        """Test performance of AI suggestions system"""
        print("="*60)
        print("TESTING AI SUGGESTIONS PERFORMANCE")
        print("="*60)
        
        # Test multiple requests to measure performance
        performance_tests = []
        
        for i in range(5):
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.base_url}/api/ai-suggestions/generate",
                    json={
                        "current_message": f"Test message {i}",
                        "ai_response": f"Test response {i}",
                        "user_id": f"perf_test_{i}",
                        "conversation_context": {},
                        "conversation_phase": "information_gathering"
                    }
                )
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                if response.status_code == 200:
                    result = response.json()
                    generation_time = result.get("generation_time_ms", 0)
                    
                    performance_tests.append({
                        "success": True,
                        "total_time_ms": response_time,
                        "generation_time_ms": generation_time,
                        "suggestions_count": len(result.get("suggestions", []))
                    })
                else:
                    performance_tests.append({
                        "success": False,
                        "total_time_ms": response_time,
                        "generation_time_ms": 0,
                        "suggestions_count": 0
                    })
                    
            except Exception as e:
                performance_tests.append({
                    "success": False,
                    "total_time_ms": 0,
                    "generation_time_ms": 0,
                    "suggestions_count": 0
                })
        
        # Calculate performance metrics
        successful_tests = [t for t in performance_tests if t["success"]]
        
        if successful_tests:
            avg_total_time = sum(t["total_time_ms"] for t in successful_tests) / len(successful_tests)
            avg_generation_time = sum(t["generation_time_ms"] for t in successful_tests) / len(successful_tests)
            avg_suggestions = sum(t["suggestions_count"] for t in successful_tests) / len(successful_tests)
            
            self.log_test_result(
                "Performance Metrics",
                True,
                f"Avg total time: {avg_total_time:.0f}ms, Avg generation: {avg_generation_time:.0f}ms, Avg suggestions: {avg_suggestions:.1f}"
            )
        else:
            self.log_test_result(
                "Performance Metrics",
                False,
                "All performance tests failed"
            )
    
    def run_all_tests(self):
        """Run all AI suggestions tests"""
        print("🚀 STARTING AI SUGGESTIONS SYSTEM TESTS")
        print("="*60)
        
        # Run all test suites
        self.test_chat_widget_ai_suggestions()
        self.test_ai_suggestions_api()
        self.test_suggestion_quality()
        self.test_performance_metrics()
        
        # Print final results
        print("="*60)
        print("🎯 FINAL TEST RESULTS")
        print("="*60)
        
        success_rate = (self.success_count / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        print(f"Total Tests: {self.total_tests}")
        print(f"Successful: {self.success_count}")
        print(f"Failed: {self.total_tests - self.success_count}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("✅ AI SUGGESTIONS SYSTEM - EXCELLENT PERFORMANCE")
        elif success_rate >= 60:
            print("⚠️  AI SUGGESTIONS SYSTEM - GOOD PERFORMANCE")
        else:
            print("❌ AI SUGGESTIONS SYSTEM - NEEDS IMPROVEMENT")
        
        # Print detailed results
        print("\n" + "="*60)
        print("📊 DETAILED TEST RESULTS")
        print("="*60)
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test_name']}")
            if result["details"]:
                print(f"   {result['details']}")
            if result["suggestions"]:
                print(f"   Suggestions: {result['suggestions']}")
        
        return success_rate >= 80

def main():
    """Main function"""
    print("🤖 AI SUGGESTIONS SYSTEM COMPREHENSIVE TEST")
    print("Testing intelligent, contextual suggestions functionality")
    print("="*60)
    
    # Initialize tester
    tester = AISuggestionsSystemTester()
    
    # Run all tests
    success = tester.run_all_tests()
    
    # Return appropriate exit code
    exit(0 if success else 1)

if __name__ == "__main__":
    main()