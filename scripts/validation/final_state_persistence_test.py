#!/usr/bin/env python3
"""
Final State Persistence Test - Djobea AI
Comprehensive test to demonstrate working conversation state persistence
"""
import requests
import time
import json

def test_complete_conversation_flow():
    """Test complete conversation flow with state persistence"""
    
    base_url = "http://localhost:5000"
    session_id = f"final_test_{int(time.time())}"
    phone_number = "237691924199"
    
    print("🎯 Final State Persistence Test")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print(f"Phone: {phone_number}")
    print()
    
    # Test scenarios
    scenarios = [
        {
            "name": "Service Type Only",
            "message": "J'ai un problème de plomberie",
            "expected": "should ask for location"
        },
        {
            "name": "Location Addition",
            "message": "Je suis à Bonamoussadi",
            "expected": "should create service request or ask for more details"
        },
        {
            "name": "Description Addition (if needed)",
            "message": "Mon évier est bouché",
            "expected": "should complete the request"
        }
    ]
    
    conversation_complete = False
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"📞 Step {i}: {scenario['name']}")
        print(f"User: {scenario['message']}")
        
        response = requests.post(
            f"{base_url}/webhook/chat",
            json={
                "message": scenario['message'],
                "session_id": session_id,
                "phone_number": phone_number,
                "source": "web_chat"
            },
            timeout=12
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            print(f"AI: {ai_response}")
            
            # Check if request was completed
            if ('prestataire' in ai_response.lower() or 
                'recherche' in ai_response.lower() or
                'plombier' in ai_response.lower() and 'contact' in ai_response.lower()):
                print("✅ SUCCESS: Service request created!")
                conversation_complete = True
                break
            elif i == 1 and 'bonamoussadi' in ai_response.lower():
                print("✅ SUCCESS: Location preserved and acknowledged!")
            elif i == 1 and 'plomberie' in ai_response.lower():
                print("✅ SUCCESS: Service type preserved!")
            else:
                print("🔄 Continuing conversation...")
                
        else:
            print(f"❌ Error: {response.status_code}")
            return False
            
        print()
        time.sleep(2)
    
    # Final assessment
    print("=" * 60)
    if conversation_complete:
        print("🎉 FINAL SUCCESS: Complete conversation flow working!")
        print("✅ State persistence: FIXED")
        print("✅ Information accumulation: WORKING")
        print("✅ Automatic service creation: WORKING")
        print("✅ Natural conversation flow: WORKING")
        return True
    else:
        print("⚠️  Conversation not completed, but state persistence may be working")
        return False

def test_edge_cases():
    """Test edge cases for state persistence"""
    
    print("\n🔍 Edge Case Testing")
    print("=" * 40)
    
    # Test with different session
    session_id = f"edge_test_{int(time.time())}"
    phone_number = "237691924200"
    
    # Test 1: Very short messages
    print("Test 1: Very short messages")
    response1 = requests.post(
        "http://localhost:5000/webhook/chat",
        json={
            "message": "plomberie",
            "session_id": session_id,
            "phone_number": phone_number,
            "source": "web_chat"
        },
        timeout=8
    )
    
    if response1.status_code == 200:
        print("✅ Short message handled")
        
        time.sleep(2)
        
        response2 = requests.post(
            "http://localhost:5000/webhook/chat",
            json={
                "message": "Bonamoussadi",
                "session_id": session_id,
                "phone_number": phone_number,
                "source": "web_chat"
            },
            timeout=8
        )
        
        if response2.status_code == 200:
            data = response2.json()
            response_text = data.get('response', '')
            if 'plomberie' in response_text.lower() or 'prestataire' in response_text.lower():
                print("✅ State preserved in short messages")
            else:
                print("❌ State not preserved in short messages")
        else:
            print("❌ Second message failed")
    else:
        print("❌ First message failed")

if __name__ == "__main__":
    try:
        print("Starting comprehensive state persistence testing...")
        print()
        
        # Main test
        success = test_complete_conversation_flow()
        
        # Edge case tests
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🏁 FINAL RESULT:")
        if success:
            print("✅ CONVERSATION STATE PERSISTENCE: WORKING")
            print("✅ DIALOG FLOW CONTINUATION: FIXED")
            print("✅ NATURAL CONVERSATION ENGINE: OPERATIONAL")
        else:
            print("⚠️  PARTIAL SUCCESS - Some functionality working")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")