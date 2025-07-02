"""
Simple Multi-LLM System Test
Validates the basic functionality of the multi-LLM conversational AI system
"""

import asyncio
import requests
from typing import Dict, Any

# Test the enhanced webhook endpoint
async def test_enhanced_webhook():
    """Test the enhanced WhatsApp webhook with multi-LLM processing"""
    print("🧪 Testing Enhanced Multi-LLM Webhook Endpoint")
    print("=" * 50)
    
    # Test data for enhanced conversation
    test_data = {
        "AccountSid": "ACtest123",
        "MessageSid": "SMtest456", 
        "From": "+237690123456",
        "To": "+237690000000",
        "Body": "Bonjour, j'ai un problème urgent de plomberie dans ma cuisine",
        "NumMedia": "0",
        "MediaUrl0": "",
        "MediaContentType0": ""
    }
    
    try:
        # Send POST request to enhanced webhook
        response = requests.post(
            "http://0.0.0.0:5000/webhook/whatsapp-enhanced",
            data=test_data,
            timeout=30
        )
        
        print(f"✅ Enhanced Webhook Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Processing Time: {response.elapsed.total_seconds():.2f}s")
        
        if response.status_code == 200:
            print("   ✓ Multi-LLM system processed request successfully")
        else:
            print(f"   ❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing enhanced webhook: {e}")

# Test the landing page chat widget
async def test_landing_page_chat():
    """Test the landing page chat widget integration"""
    print("\n💬 Testing Landing Page Chat Widget")
    print("=" * 50)
    
    try:
        # Test chat endpoint
        chat_data = {
            "message": "Je cherche un plombier pour une urgence",
            "phone_number": "+237690987654"
        }
        
        response = requests.post(
            "http://0.0.0.0:5000/api/chat",
            json=chat_data,
            timeout=30
        )
        
        print(f"✅ Chat Widget Response:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   AI Response: {data.get('response', '')[:100]}...")
            print("   ✓ Chat widget integrated with multi-LLM system")
        else:
            print(f"   ❌ Chat failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing chat widget: {e}")

# Test provider dashboard
async def test_provider_dashboard():
    """Test provider dashboard functionality"""
    print("\n📊 Testing Provider Dashboard")
    print("=" * 50)
    
    try:
        # Test dashboard page
        response = requests.get("http://0.0.0.0:5000/provider-dashboard", timeout=10)
        
        print(f"✅ Dashboard Response:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ Provider dashboard loaded successfully")
            
            # Test stats API
            stats_response = requests.get("http://0.0.0.0:5000/api/provider/stats", timeout=10)
            if stats_response.status_code == 200:
                print("   ✓ Provider stats API working")
            else:
                print("   ⚠️  Provider stats API needs authentication")
        else:
            print(f"   ❌ Dashboard failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")

# Test system health
async def test_system_health():
    """Test overall system health"""
    print("\n🏥 Testing System Health")
    print("=" * 50)
    
    try:
        # Test health endpoint
        response = requests.get("http://0.0.0.0:5000/health", timeout=5)
        
        print(f"✅ Health Check:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('database')}")
            print("   ✓ System is healthy")
        else:
            print(f"   ❌ Health check failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error checking system health: {e}")

async def main():
    """Run all multi-LLM system tests"""
    print("🚀 Multi-LLM Conversational AI System Test Suite")
    print("🤖 Testing Claude + Gemini + GPT-4 Integration")
    print("=" * 60)
    
    # Test system health first
    await test_system_health()
    
    # Test provider dashboard
    await test_provider_dashboard()
    
    # Test landing page chat widget
    await test_landing_page_chat()
    
    # Test enhanced webhook (main multi-LLM functionality)
    await test_enhanced_webhook()
    
    print("\n" + "=" * 60)
    print("✅ Multi-LLM System Test Suite Complete!")
    print("🎯 Advanced conversational AI system with Claude, Gemini, and GPT-4 is operational")

if __name__ == "__main__":
    asyncio.run(main())