#!/usr/bin/env python3
"""
Test Complete Notification Flow
Simulates the complete user experience from service request to notifications
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_complete_notification_flow():
    """Test the complete notification flow"""
    
    print("🧪 Testing Complete Notification Flow")
    print("=" * 60)
    
    # Test user phone number (from database)
    test_user_phone = "237691924173"
    
    # Step 1: Clear existing notifications
    print("\n1. Clearing existing notifications...")
    try:
        response = requests.post(f"{BASE_URL}/api/web-chat/notifications/{test_user_phone}/clear")
        print(f"Clear status: {response.status_code}")
    except Exception as e:
        print(f"Clear error (non-critical): {e}")
    
    # Step 2: Create a service request through the chat system
    print("\n2. Creating service request through chat...")
    
    # First, send a complete service request message
    chat_data = {
        "message": "J'ai un problème de plomberie urgente à Bonamoussadi, ma canalisation fuit dans la cuisine",
        "phone_number": test_user_phone,
        "session_id": "test-flow-" + str(int(time.time()))
    }
    
    try:
        response = requests.post(f"{BASE_URL}/webhook/chat", json=chat_data)
        print(f"Chat response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')[:100]}...")
            if result.get('request_complete'):
                print(f"✅ Service request created: {result.get('request_id')}")
                request_id = result.get('request_id')
            else:
                print("⚠️  Request may need more information")
                request_id = None
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"Response: {response.text}")
            request_id = None
            
    except Exception as e:
        print(f"❌ Error in chat request: {e}")
        request_id = None
    
    # Step 3: Wait a moment for notifications to be processed
    print("\n3. Waiting for notifications to be processed...")
    time.sleep(3)
    
    # Step 4: Check for notifications
    print("\n4. Checking for notifications...")
    try:
        response = requests.get(f"{BASE_URL}/api/web-chat/notifications/{test_user_phone}")
        print(f"Notifications status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Notifications count: {result.get('count', 0)}")
            print(f"Unread count: {result.get('unread_count', 0)}")
            
            if result.get('count', 0) > 0:
                print("✅ Notifications found!")
                for i, notif in enumerate(result.get('notifications', [])):
                    print(f"  {i+1}. [{notif.get('type', 'unknown')}] {notif.get('message', 'No message')[:80]}...")
                return True
            else:
                print("❌ No notifications found")
                return False
        else:
            print(f"❌ Failed to get notifications: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking notifications: {e}")
        return False
    
    # Step 5: Test manual notification
    print("\n5. Testing manual notification...")
    try:
        manual_notif = {
            "message": "✅ Manual test notification - system is working!",
            "notification_type": "test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/web-chat/test-notification/{test_user_phone}",
            json=manual_notif
        )
        
        if response.status_code == 200:
            print("✅ Manual notification sent successfully")
            
            # Check if it appears in notifications
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/web-chat/notifications/{test_user_phone}")
            if response.status_code == 200:
                result = response.json()
                print(f"Total notifications after manual test: {result.get('count', 0)}")
        else:
            print(f"❌ Manual notification failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error in manual notification: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Complete Notification Flow Test Complete")
    
    return True

if __name__ == "__main__":
    success = test_complete_notification_flow()
    if success:
        print("\n🚀 Notification system is operational!")
    else:
        print("\n⚠️  Some issues detected in notification flow")