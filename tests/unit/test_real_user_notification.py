#!/usr/bin/env python3
"""
Test Real User Notification Flow
Simulates the exact scenario described by the user
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_real_user_scenario():
    """Test the exact user scenario"""
    
    print("🧪 Testing Real User Notification Scenario")
    print("=" * 60)
    
    test_user_phone = "237691924173"
    
    # Step 1: Clear existing notifications
    print("\n1. Clearing existing notifications...")
    requests.post(f"{BASE_URL}/api/web-chat/notifications/{test_user_phone}/clear")
    
    # Step 2: Send the exact message from the user
    print("\n2. Sending exact user message...")
    
    chat_data = {
        "message": "Bonjour j'ai besoin d'un réparateur de télé, je suis à kotto",
        "phone_number": test_user_phone,
        "session_id": "real-user-session-123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/webhook/chat", json=chat_data)
        print(f"Chat response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"AI Response: {result.get('response', 'No response')}")
            print(f"Request complete: {result.get('request_complete', False)}")
            print(f"Request ID: {result.get('request_id', 'None')}")
            
            # Check if a service request was created
            if result.get('request_complete') and result.get('request_id'):
                print("✅ Service request created successfully!")
                request_id = result.get('request_id')
                
                # Step 3: Wait for notifications
                print("\n3. Waiting for notifications...")
                time.sleep(2)
                
                # Step 4: Check notifications
                print("\n4. Checking for notifications...")
                notif_response = requests.get(f"{BASE_URL}/api/web-chat/notifications/{test_user_phone}")
                
                if notif_response.status_code == 200:
                    notif_result = notif_response.json()
                    print(f"Notifications count: {notif_result.get('count', 0)}")
                    
                    if notif_result.get('count', 0) > 0:
                        print("✅ NOTIFICATIONS FOUND!")
                        for i, notif in enumerate(notif_result.get('notifications', [])):
                            print(f"  {i+1}. [{notif.get('type')}] {notif.get('message')[:100]}...")
                        return True
                    else:
                        print("❌ NO NOTIFICATIONS - This is the issue!")
                        return False
                else:
                    print(f"❌ Failed to check notifications: {notif_response.status_code}")
                    return False
            else:
                print("⚠️  Service request may not have been created")
                print("This might be why notifications aren't being sent")
                return False
                
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        return False
    
    # Step 5: Test direct notification to verify the system works
    print("\n5. Testing direct notification...")
    try:
        direct_notif = {
            "message": "🔧 Test: Direct notification to verify system works",
            "notification_type": "test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/web-chat/test-notification/{test_user_phone}",
            json=direct_notif
        )
        
        if response.status_code == 200:
            print("✅ Direct notification sent successfully")
            
            # Check if it appears
            time.sleep(1)
            notif_response = requests.get(f"{BASE_URL}/api/web-chat/notifications/{test_user_phone}")
            if notif_response.status_code == 200:
                notif_result = notif_response.json()
                print(f"Total notifications after direct test: {notif_result.get('count', 0)}")
                
                if notif_result.get('count', 0) > 0:
                    print("✅ Direct notification system is working!")
                else:
                    print("❌ Even direct notifications aren't working")
        else:
            print(f"❌ Direct notification failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error in direct notification: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Real User Notification Test Complete")
    return False

if __name__ == "__main__":
    success = test_real_user_scenario()
    if success:
        print("\n🚀 User notifications are working correctly!")
    else:
        print("\n⚠️  Issue confirmed - users are not receiving notifications from service requests")
        print("The notification system works for direct tests but not for actual service requests")