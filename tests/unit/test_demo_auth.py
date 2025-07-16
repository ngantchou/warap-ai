#!/usr/bin/env python3
"""
Test script for demo provider authentication system
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_demo_auth():
    """Test the complete demo authentication flow"""
    
    # Test 1: Send OTP with demo phone number
    print("=== Testing Demo OTP Send ===")
    
    phone_numbers = ["+237690000003", "237690000003", "+237677123456"]
    
    for phone in phone_numbers:
        print(f"\n🔸 Testing with phone: {phone}")
        
        otp_response = requests.post(
            f"{BASE_URL}/api/provider/auth/send-otp",
            headers={"Content-Type": "application/json"},
            json={"phone_number": phone}
        )
        
        print(f"Status: {otp_response.status_code}")
        print(f"Response: {otp_response.text}")
        
        if otp_response.status_code == 200:
            otp_data = otp_response.json()
            if otp_data.get("success"):
                # Get demo OTP from response if available
                demo_otp = otp_data.get("demo_note", "").replace("Demo OTP: ", "")
                if demo_otp:
                    print(f"✅ Demo OTP found: {demo_otp}")
                    
                    # Test 2: Verify OTP
                    print(f"\n=== Testing Demo OTP Verification ===")
                    verify_response = requests.post(
                        f"{BASE_URL}/api/provider/auth/verify-otp",
                        headers={"Content-Type": "application/json"},
                        json={
                            "session_token": otp_data["session_token"],
                            "otp_code": demo_otp,
                            "otp_hash": otp_data["otp_hash"]
                        }
                    )
                    
                    print(f"Verify Status: {verify_response.status_code}")
                    print(f"Verify Response: {verify_response.text}")
                    
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        if verify_data.get("success"):
                            auth_token = verify_data["auth_token"]
                            print(f"✅ Authentication successful! Token: {auth_token[:20]}...")
                            
                            # Test 3: Test dashboard access
                            print(f"\n=== Testing Dashboard Access ===")
                            dashboard_response = requests.get(
                                f"{BASE_URL}/api/provider/dashboard/stats",
                                headers={"Authorization": f"Bearer {auth_token}"}
                            )
                            
                            print(f"Dashboard Status: {dashboard_response.status_code}")
                            print(f"Dashboard Response: {dashboard_response.text[:200]}...")
                            
                            if dashboard_response.status_code == 200:
                                print("✅ Dashboard access successful!")
                                return True
                break
    
    print("❌ Demo authentication test failed")
    return False

if __name__ == "__main__":
    success = test_demo_auth()
    if success:
        print("\n🎉 Demo provider authentication system is working!")
    else:
        print("\n💥 Demo provider authentication system needs fixing")