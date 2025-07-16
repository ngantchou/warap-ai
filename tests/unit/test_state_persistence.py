#!/usr/bin/env python3
"""
Test State Persistence - Djobea AI
Quick test to verify conversation state is preserved between messages
"""
import requests
import time
import json

def test_state_persistence():
    """Test that conversation state is preserved between messages"""
    
    base_url = "http://localhost:5000"
    session_id = f"persistence_test_{int(time.time())}"
    phone_number = "237691924176"
    
    print("🧪 Testing State Persistence")
    print("=" * 50)
    print(f"Session: {session_id}")
    print(f"Phone: {phone_number}")
    print()
    
    # Message 1: Service request with missing location
    print("📞 Message 1: Service request")
    message1 = "J'ai un problème de plomberie"
    print(f"User: {message1}")
    
    response1 = requests.post(
        f"{base_url}/webhook/chat",
        json={
            "message": message1,
            "session_id": session_id,
            "phone_number": phone_number,
            "source": "web_chat"
        },
        timeout=10
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        ai_response1 = data1.get('response', '')
        print(f"AI: {ai_response1}")
        
        # Should ask for location
        if "où" in ai_response1.lower() or "quartier" in ai_response1.lower():
            print("✅ Message 1: System correctly asks for location")
        else:
            print("❌ Message 1: System did not ask for location")
            return False
    else:
        print(f"❌ Message 1 failed: {response1.status_code}")
        return False
    
    print()
    time.sleep(3)
    
    # Message 2: Provide location
    print("📞 Message 2: Provide location")
    message2 = "Je suis à Bonamoussadi"
    print(f"User: {message2}")
    
    response2 = requests.post(
        f"{base_url}/webhook/chat",
        json={
            "message": message2,
            "session_id": session_id,
            "phone_number": phone_number,
            "source": "web_chat"
        },
        timeout=10
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        ai_response2 = data2.get('response', '')
        print(f"AI: {ai_response2}")
        
        # Should either ask for description or create request
        if ("détail" in ai_response2.lower() or "problème" in ai_response2.lower() or 
            "parfait" in ai_response2.lower() or "prestataire" in ai_response2.lower()):
            print("✅ Message 2: System preserved state and continued conversation")
            return True
        else:
            print("❌ Message 2: System did not preserve state")
            print(f"Response: {ai_response2}")
            return False
    else:
        print(f"❌ Message 2 failed: {response2.status_code}")
        return False

if __name__ == "__main__":
    try:
        success = test_state_persistence()
        print()
        print("=" * 50)
        if success:
            print("🎉 SUCCESS: State persistence working correctly!")
        else:
            print("❌ FAILED: State persistence not working")
    except Exception as e:
        print(f"❌ ERROR: {e}")