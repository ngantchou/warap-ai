#!/usr/bin/env python3
"""
Test Improved Dialog Flow - Djobea AI
Validates the fixes for repetitive greetings and improved suggestions
"""

import requests
import json
import time
from typing import Dict, Any

class ImprovedDialogTester:
    """Test the improved dialog flow and suggestions"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session_id = "test_session_improved_flow"
        self.phone_number = "237691924174"
        self.conversation_history = []
        
    def send_message(self, message: str) -> Dict[str, Any]:
        """Send message to chat endpoint"""
        
        url = f"{self.base_url}/webhook/chat"
        payload = {
            "message": message,
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "source": "web_chat"
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Store conversation history
            self.conversation_history.append({
                "user_message": message,
                "ai_response": result.get("response", ""),
                "suggestions": result.get("suggestions", []),
                "timestamp": time.time()
            })
            
            return result
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return {"error": str(e)}
    
    def test_improved_conversation_flow(self):
        """Test improved conversation flow without repetitive greetings"""
        
        print("\n" + "="*60)
        print("TESTING IMPROVED DIALOG FLOW")
        print("="*60)
        
        # Test 1: First message should have greeting
        print("\n1. First message test:")
        result1 = self.send_message("J'ai un problème électrique")
        print(f"User: J'ai un problème électrique")
        print(f"AI: {result1.get('response', 'ERROR')}")
        print(f"Suggestions: {result1.get('suggestions', [])}")
        
        # Check that first response contains greeting
        first_response = result1.get('response', '').lower()
        has_greeting = any(word in first_response for word in ['bonjour', 'salut', 'bienvenue'])
        print(f"✓ Has greeting: {has_greeting}")
        
        time.sleep(1)
        
        # Test 2: Second message should NOT have greeting
        print("\n2. Second message test:")
        result2 = self.send_message("court-circuit")
        print(f"User: court-circuit")
        print(f"AI: {result2.get('response', 'ERROR')}")
        print(f"Suggestions: {result2.get('suggestions', [])}")
        
        # Check that second response does NOT contain greeting
        second_response = result2.get('response', '').lower()
        has_greeting = any(word in second_response for word in ['bonjour', 'salut', 'bienvenue'])
        print(f"✓ No repeated greeting: {not has_greeting}")
        
        time.sleep(1)
        
        # Test 3: Third message should ask for location
        print("\n3. Third message test:")
        result3 = self.send_message("bonamoussadi")
        print(f"User: bonamoussadi")
        print(f"AI: {result3.get('response', 'ERROR')}")
        print(f"Suggestions: {result3.get('suggestions', [])}")
        
        # Check that third response progresses conversation
        third_response = result3.get('response', '').lower()
        has_greeting = any(word in third_response for word in ['bonjour', 'salut', 'bienvenue'])
        print(f"✓ No repeated greeting: {not has_greeting}")
        
        time.sleep(1)
        
        # Test 4: Fourth message should be specific
        print("\n4. Fourth message test:")
        result4 = self.send_message("Le courant a sauté dans la cuisine")
        print(f"User: Le courant a sauté dans la cuisine")
        print(f"AI: {result4.get('response', 'ERROR')}")
        print(f"Suggestions: {result4.get('suggestions', [])}")
        
        # Check that fourth response is contextual
        fourth_response = result4.get('response', '').lower()
        has_greeting = any(word in fourth_response for word in ['bonjour', 'salut', 'bienvenue'])
        print(f"✓ No repeated greeting: {not has_greeting}")
        
        return True
    
    def test_contextual_suggestions(self):
        """Test improved contextual suggestions"""
        
        print("\n" + "="*60)
        print("TESTING CONTEXTUAL SUGGESTIONS")
        print("="*60)
        
        # Test plomberie suggestions
        print("\n1. Plomberie suggestions test:")
        result1 = self.send_message("J'ai un problème de plomberie")
        suggestions1 = result1.get('suggestions', [])
        print(f"User: J'ai un problème de plomberie")
        print(f"Suggestions: {suggestions1}")
        
        # Check plomberie-specific suggestions
        plomberie_suggestions = any('fuite' in s.lower() or 'wc' in s.lower() or 'pression' in s.lower() 
                                   for s in suggestions1)
        print(f"✓ Plomberie-specific suggestions: {plomberie_suggestions}")
        
        time.sleep(1)
        
        # Test location suggestions
        print("\n2. Location suggestions test:")
        result2 = self.send_message("où êtes-vous")
        suggestions2 = result2.get('suggestions', [])
        print(f"User: où êtes-vous")
        print(f"Suggestions: {suggestions2}")
        
        # Check location-specific suggestions
        location_suggestions = any('bonamoussadi' in s.lower() or 'akwa' in s.lower() or 'douala' in s.lower() 
                                  for s in suggestions2)
        print(f"✓ Location-specific suggestions: {location_suggestions}")
        
        time.sleep(1)
        
        return True
    
    def test_conversation_memory(self):
        """Test conversation memory persistence"""
        
        print("\n" + "="*60)
        print("TESTING CONVERSATION MEMORY")
        print("="*60)
        
        # Start new conversation
        new_session = "test_memory_session"
        self.session_id = new_session
        
        # Send service type
        result1 = self.send_message("J'ai un problème électrique")
        print(f"1. User: J'ai un problème électrique")
        print(f"   AI: {result1.get('response', 'ERROR')}")
        
        time.sleep(1)
        
        # Send location
        result2 = self.send_message("je suis à bonamoussadi")
        print(f"2. User: je suis à bonamoussadi")
        print(f"   AI: {result2.get('response', 'ERROR')}")
        
        # Check if AI remembers the electrical problem
        response2 = result2.get('response', '').lower()
        remembers_service = 'électr' in response2
        print(f"✓ Remembers electrical problem: {remembers_service}")
        
        time.sleep(1)
        
        # Send description
        result3 = self.send_message("court-circuit dans la cuisine")
        print(f"3. User: court-circuit dans la cuisine")
        print(f"   AI: {result3.get('response', 'ERROR')}")
        
        # Check if AI remembers both service and location
        response3 = result3.get('response', '').lower()
        remembers_both = 'électr' in response3 and 'bonamoussadi' in response3
        print(f"✓ Remembers both service and location: {remembers_both}")
        
        return True
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "="*60)
        print("IMPROVED DIALOG FLOW TEST REPORT")
        print("="*60)
        
        total_messages = len(self.conversation_history)
        print(f"Total messages tested: {total_messages}")
        
        # Check for repetitive greetings
        greeting_count = 0
        for msg in self.conversation_history:
            response = msg['ai_response'].lower()
            if any(word in response for word in ['bonjour', 'salut', 'bienvenue']):
                greeting_count += 1
        
        print(f"Greeting messages: {greeting_count}/{total_messages}")
        print(f"✓ Greeting only in first message: {greeting_count <= 1}")
        
        # Check suggestion quality
        contextual_suggestions = 0
        for msg in self.conversation_history:
            suggestions = msg.get('suggestions', [])
            if suggestions and len(suggestions) > 0:
                # Check if suggestions are contextual (not generic)
                generic_suggestions = ['J\'ai un problème de plomberie', 'J\'ai un problème électrique', 'Mon électroménager ne marche pas']
                is_contextual = not all(s in generic_suggestions for s in suggestions)
                if is_contextual:
                    contextual_suggestions += 1
        
        print(f"Contextual suggestions: {contextual_suggestions}/{total_messages}")
        print(f"✓ Improved suggestions: {contextual_suggestions > 0}")
        
        # Overall assessment
        improvements_working = (
            greeting_count <= 1 and  # No repetitive greetings
            contextual_suggestions > 0  # Better suggestions
        )
        
        print(f"\n{'='*60}")
        print(f"OVERALL RESULT: {'✅ IMPROVEMENTS WORKING' if improvements_working else '❌ IMPROVEMENTS NEEDED'}")
        print(f"{'='*60}")
        
        return improvements_working

def main():
    """Main test function"""
    
    tester = ImprovedDialogTester()
    
    print("🧪 Testing Improved Dialog Flow and Suggestions")
    print("=" * 60)
    
    # Run all tests
    try:
        tester.test_improved_conversation_flow()
        tester.test_contextual_suggestions()
        tester.test_conversation_memory()
        success = tester.generate_test_report()
        
        if success:
            print("\n✅ All improvements validated successfully!")
        else:
            print("\n❌ Some improvements still need work")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()