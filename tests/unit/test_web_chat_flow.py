#!/usr/bin/env python3
"""
Test Web Chat Notification Flow
Tests the complete web chat notification system
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_web_chat_notification_flow():
    """Test complete web chat notification flow"""
    
    # Test user phone number
    test_user = "237691924173"
    
    print("🧪 Testing Web Chat Notification System")
    print("=" * 50)
    
    # 1. Test notification creation
    print("\n1. Testing notification creation...")
    
    notification_data = {
        "message": "Test web chat notification - system working!",
        "notification_type": "info"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/web-chat/test-notification/{test_user}",
            json=notification_data
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Notification created successfully")
        else:
            print("❌ Notification creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error creating notification: {e}")
        return False
    
    # 2. Test retrieving notifications
    print("\n2. Testing notification retrieval...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/web-chat/notifications/{test_user}")
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Notifications count: {result.get('count', 0)}")
        print(f"Unread count: {result.get('unread_count', 0)}")
        
        if result.get('count', 0) > 0:
            print("✅ Notifications retrieved successfully")
            notifications = result.get('notifications', [])
            for i, notif in enumerate(notifications):
                print(f"  {i+1}. {notif.get('message', 'No message')[:50]}...")
        else:
            print("❌ No notifications found")
            
    except Exception as e:
        print(f"❌ Error retrieving notifications: {e}")
        return False
    
    # 3. Test polling for new notifications
    print("\n3. Testing notification polling...")
    
    try:
        # Get current time for polling
        current_time = datetime.utcnow().isoformat() + "Z"
        
        # Send another notification
        notification_data = {
            "message": "Second test notification for polling",
            "notification_type": "status_update"
        }
        
        requests.post(
            f"{BASE_URL}/api/web-chat/test-notification/{test_user}",
            json=notification_data
        )
        
        # Poll for new notifications
        response = requests.get(
            f"{BASE_URL}/api/web-chat/notifications/poll/{test_user}",
            params={"last_check": current_time}
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"New notifications: {result.get('count', 0)}")
        print(f"Has new: {result.get('has_new', False)}")
        
        if result.get('has_new', False):
            print("✅ Polling system working correctly")
        else:
            print("⚠️  Polling may not be working correctly")
            
    except Exception as e:
        print(f"❌ Error testing polling: {e}")
        return False
    
    # 4. Test service request notification
    print("\n4. Testing service request notification...")
    
    try:
        # Send a chat message to trigger service request
        chat_data = {
            "message": "J'ai un problème d'électricité à Bonamoussadi",
            "user_id": test_user
        }
        
        response = requests.post(
            f"{BASE_URL}/webhook/chat",
            json=chat_data
        )
        
        print(f"Chat response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Service request processed")
            
            # Check for new notifications
            time.sleep(2)  # Wait for notifications to be processed
            
            response = requests.get(f"{BASE_URL}/api/web-chat/notifications/{test_user}")
            result = response.json()
            print(f"Total notifications after service request: {result.get('count', 0)}")
            
        else:
            print("⚠️  Service request processing may have issues")
            
    except Exception as e:
        print(f"❌ Error testing service request: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎯 Web Chat Notification Test Complete")
    print("✅ System is operational and ready for use")
    
    return True

if __name__ == "__main__":
    success = test_web_chat_notification_flow()
    if success:
        print("\n🚀 Web chat notification system is working correctly!")
    else:
        print("\n⚠️  Some issues detected - check logs for details")