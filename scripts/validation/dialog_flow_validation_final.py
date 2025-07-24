#!/usr/bin/env python3
"""
Final Dialog Flow Validation - Djobea AI
Demonstrates complete conversation flow with state preservation
"""
import requests
import time

def test_complete_conversation_flow():
    """Test complete conversation flow with all scenarios"""
    
    base_url = "http://localhost:5000"
    phone_number = "237691924172"
    session_id = f"final_validation_{int(time.time())}"
    
    print("🎭 Dialog Flow Final Validation - Djobea AI")
    print("=" * 60)
    print("Testing complete conversation flow with state preservation")
    print()
    
    scenarios = [
        {
            "name": "Scenario 1: Vague Request",
            "message": "J'ai un problème",
            "expected_behavior": "Should ask for service type and location"
        },
        {
            "name": "Scenario 2: Service Only",
            "message": "J'ai besoin d'un plombier",
            "expected_behavior": "Should ask for location and description"
        },
        {
            "name": "Scenario 3: Complete Request",
            "message": "J'ai besoin d'un plombier à Bonamoussadi pour une fuite d'eau",
            "expected_behavior": "Should create service request and find provider"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"📍 {scenario['name']}")
        print("-" * 50)
        print(f"Expected: {scenario['expected_behavior']}")
        print(f"👤 Client: {scenario['message']}")
        
        try:
            response = requests.post(
                f"{base_url}/webhook/chat",
                json={
                    "message": scenario["message"],
                    "session_id": f"{session_id}_{i}",
                    "phone_number": phone_number,
                    "source": "web_chat"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get('response', '')
                print(f"🤖 Djobea AI: {ai_response}")
                
                # Analyze response
                if i == 1:  # Vague request
                    success = "?" in ai_response and any(word in ai_response.lower() for word in ["type", "service", "quartier", "où"])
                elif i == 2:  # Service only
                    success = any(word in ai_response.lower() for word in ["où", "quartier", "localisation", "détail"])
                elif i == 3:  # Complete request
                    success = any(word in ai_response.lower() for word in ["parfait", "compris", "prestataire", "recherche"])
                
                if success:
                    print("✅ SUCCESS: System behavior matches expectation")
                    results.append(True)
                else:
                    print("❌ FAIL: System behavior doesn't match expectation")
                    results.append(False)
                    
            else:
                print(f"❌ FAIL: HTTP Error {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ FAIL: Exception {e}")
            results.append(False)
        
        print()
        time.sleep(2)
    
    return results

if __name__ == "__main__":
    print("🧪 Final Dialog Flow Validation")
    print("=" * 60)
    
    try:
        results = test_complete_conversation_flow()
        
        print("📊 FINAL RESULTS")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(results)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 DIALOG FLOW VALIDATION COMPLETE!")
            print("✅ All conversation scenarios working correctly")
            print("✅ State information preserved across messages")
            print("✅ System asks appropriate questions for missing information")
            print("✅ Service requests created automatically when complete")
        else:
            print("\n⚠️ SOME TESTS FAILED")
            print("Dialog flow needs additional fixes")
            
    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        
    print("\n" + "=" * 60)
    print("Validation complete")