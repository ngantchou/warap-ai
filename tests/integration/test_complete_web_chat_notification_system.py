#!/usr/bin/env python3
"""
Complete Web Chat Notification System Test
Tests the end-to-end notification flow including:
1. Service request creation
2. Notification generation
3. Notification retrieval via API
4. Real-time polling system
"""

import requests
import time
import json
from datetime import datetime

def test_complete_notification_system():
    """Test the complete web chat notification system"""
    
    base_url = "http://localhost:5000"
    test_phone = "237691924173"
    
    print("🔔 Testing Complete Web Chat Notification System")
    print("=" * 60)
    
    # Step 1: Clear existing notifications
    print("\n1. Clearing existing notifications...")
    response = requests.post(f"{base_url}/api/web-chat/notifications/{test_phone}/clear")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Step 2: Send a service request message
    print("\n2. Sending service request message...")
    session_id = f"test-{int(time.time())}"
    message_data = {
        "message": "Mon réfrigérateur ne marche plus, je suis à Bonamoussadi. C'est urgent.",
        "phone_number": test_phone,
        "session_id": session_id
    }
    
    response = requests.post(f"{base_url}/webhook/chat", json=message_data)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        chat_response = response.json()
        print(f"   Response received: {chat_response.get('response', 'No response')[:100]}...")
        print(f"   User ID: {chat_response.get('user_id')}")
        print(f"   Request Complete: {chat_response.get('request_complete', False)}")
    
    # Step 3: Wait for notification processing
    print("\n3. Waiting for notification processing...")
    time.sleep(2)
    
    # Step 4: Check notifications
    print("\n4. Checking notifications...")
    response = requests.get(f"{base_url}/api/web-chat/notifications/{test_phone}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        notifications_data = response.json()
        notifications = notifications_data.get('notifications', [])
        print(f"   Found {len(notifications)} notifications")
        
        if notifications:
            latest_notification = notifications[0]
            print(f"   Latest notification type: {latest_notification.get('type')}")
            print(f"   Latest notification message: {latest_notification.get('message', '')[:150]}...")
            print(f"   Created at: {latest_notification.get('created_at')}")
        else:
            print("   No notifications found")
    
    # Step 5: Test notification polling simulation
    print("\n5. Testing notification polling simulation...")
    for i in range(3):
        print(f"   Poll {i+1}/3...")
        response = requests.get(f"{base_url}/api/web-chat/notifications/{test_phone}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('notifications', []))
            print(f"   Found {count} notifications")
        time.sleep(1)
    
    # Step 6: Test notification marking as read
    print("\n6. Testing notification mark as read...")
    response = requests.get(f"{base_url}/api/web-chat/notifications/{test_phone}")
    if response.status_code == 200:
        notifications = response.json().get('notifications', [])
        if notifications:
            notification_id = notifications[0]['id']
            response = requests.post(f"{base_url}/api/web-chat/notifications/{test_phone}/mark-read/{notification_id}")
            print(f"   Mark as read status: {response.status_code}")
            print(f"   Response: {response.json()}")
    
    print("\n✅ Web Chat Notification System Test Complete!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_complete_notification_system()