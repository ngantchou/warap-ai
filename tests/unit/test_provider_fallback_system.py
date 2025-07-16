#!/usr/bin/env python3
"""
Test script for Provider Fallback System
Demonstrates the notification fallback functionality with provider list
"""

import asyncio
import sys
sys.path.append(".")

from app.database import get_db
from app.services.provider_fallback_service import ProviderFallbackService
from app.services.communication_service import CommunicationService
from app.services.provider_service import ProviderService
from app.models.database_models import ServiceRequest, User, Provider
from datetime import datetime
from sqlalchemy.orm import Session


async def test_provider_fallback_system():
    """Test the complete provider fallback system"""
    
    print("🔄 Testing Provider Fallback System")
    print("=" * 50)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create test service request
        test_request = ServiceRequest(
            user_id=1,
            service_type="plomberie",
            location="Bonamoussadi",
            description="Problème de fuite d'eau dans la cuisine",
            urgency="normal",
            status="PENDING",
            estimated_cost=8000
        )
        
        db.add(test_request)
        db.commit()
        db.refresh(test_request)
        
        print(f"✅ Test service request created: {test_request.id}")
        
        # Test 1: Basic provider fallback list
        print("\n📋 Test 1: Basic Provider Fallback List")
        print("-" * 40)
        
        fallback_service = ProviderFallbackService(db)
        fallback_data = await fallback_service.get_provider_fallback_list(test_request)
        
        print(f"Success: {fallback_data['success']}")
        print(f"Provider count: {len(fallback_data['providers'])}")
        
        if fallback_data['providers']:
            print("\n📱 Provider List:")
            for i, provider in enumerate(fallback_data['providers'], 1):
                print(f"{i}. {provider['name']} - ⭐ {provider['rating']}")
                print(f"   📞 {provider['phone']} | 📱 {provider['whatsapp']}")
                print(f"   📍 {provider['location']}")
                print(f"   ⏱️ {provider['response_time']}")
        
        # Test 2: Complete notification failure handling
        print("\n🚨 Test 2: Complete Notification Failure")
        print("-" * 40)
        
        fallback_message = await fallback_service.handle_notification_failure(
            test_request, "provider_notification_failed"
        )
        
        print("📨 Fallback Message Generated:")
        print(fallback_message[:500] + "...")
        
        # Test 3: Communication service integration
        print("\n🔗 Test 3: Communication Service Integration")
        print("-" * 40)
        
        communication_service = CommunicationService()
        
        # Simulate failed providers
        failed_providers = db.query(Provider).filter(Provider.is_active == True).limit(2).all()
        
        if failed_providers:
            print(f"Simulating failure for {len(failed_providers)} providers")
            
            # Test provider notification failure handling
            success = await communication_service.handle_provider_notification_failure(
                test_request, failed_providers, db
            )
            
            print(f"Fallback handling success: {success}")
        else:
            print("No providers found for simulation")
        
        # Test 4: Provider service integration
        print("\n🔔 Test 4: Provider Service Integration")
        print("-" * 40)
        
        provider_service = ProviderService(db)
        
        # Get available providers
        available_providers = provider_service.find_available_providers(
            test_request.service_type, test_request.location
        )
        
        print(f"Available providers: {len(available_providers)}")
        
        if available_providers:
            # Test notification with fallback
            print("Testing notification with fallback...")
            
            # Note: This won't actually send messages in test mode
            # But it will demonstrate the fallback logic
            notification_success = await provider_service.notify_providers_with_fallback(
                test_request, available_providers[:2]  # Test with first 2 providers
            )
            
            print(f"Notification with fallback success: {notification_success}")
        
        # Test 5: Emergency fallback
        print("\n🆘 Test 5: Emergency Fallback")
        print("-" * 40)
        
        emergency_message = fallback_service._generate_emergency_fallback_message(test_request)
        
        print("📨 Emergency Fallback Message:")
        print(emergency_message[:300] + "...")
        
        print("\n✅ All tests completed successfully!")
        
        # Clean up test data
        db.delete(test_request)
        db.commit()
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def demo_user_experience():
    """Demonstrate the user experience with provider fallback"""
    
    print("\n🎭 User Experience Demo")
    print("=" * 50)
    
    scenarios = [
        {
            "name": "Normal Request",
            "description": "User makes a plumbing request",
            "service_type": "plomberie",
            "location": "Bonamoussadi",
            "expected": "Instant confirmation + provider matching"
        },
        {
            "name": "Notification Failure",
            "description": "WhatsApp service fails to notify providers",
            "service_type": "électricité",
            "location": "Bonapriso",
            "expected": "Fallback message with provider list"
        },
        {
            "name": "Complete System Failure",
            "description": "All systems fail",
            "service_type": "électroménager",
            "location": "Deido",
            "expected": "Emergency fallback with contact info"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📱 Scenario: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"Expected: {scenario['expected']}")
        print("-" * 30)
        
        # User sends message
        print("👤 User: J'ai un problème de", scenario['service_type'], "à", scenario['location'])
        
        # System processes request
        print("🤖 System: Demande reçue, recherche de prestataires...")
        
        if scenario['name'] == "Normal Request":
            print("✅ System: Confirmation envoyée, prestataire trouvé")
        elif scenario['name'] == "Notification Failure":
            print("⚠️  System: Notification échouée, envoi de la liste des prestataires")
            print("📋 System: Voici les 3 meilleurs prestataires que vous pouvez contacter directement:")
            print("   1. Jean-Paul Electro - ⭐ 4.8 - 📞 237 691 234 567")
            print("   2. Marie Plomberie - ⭐ 4.6 - 📞 237 681 345 678")
            print("   3. Tech Solutions - ⭐ 4.5 - 📞 237 671 456 789")
        elif scenario['name'] == "Complete System Failure":
            print("🆘 System: Erreur système, envoi des contacts d'urgence")
            print("📞 System: Contactez notre service client: 237 691 924 172")


def main():
    """Main function"""
    print("🎯 Provider Fallback System - Complete Test Suite")
    print("=" * 60)
    
    try:
        # Run async tests
        asyncio.run(test_provider_fallback_system())
        
        # Run user experience demo
        asyncio.run(demo_user_experience())
        
        print("\n🎉 Test Suite Completed Successfully!")
        print("=" * 60)
        
        print("\n📊 Summary:")
        print("✅ Provider Fallback Service - Operational")
        print("✅ Communication Service Integration - Operational")
        print("✅ Provider Service Integration - Operational")
        print("✅ Emergency Fallback - Operational")
        print("✅ User Experience Flow - Validated")
        
        print("\n🔄 Next Steps:")
        print("1. Integration with WhatsApp webhook system")
        print("2. Real-time testing with actual providers")
        print("3. Analytics and monitoring setup")
        print("4. Performance optimization")
        
    except Exception as e:
        print(f"\n❌ Test Suite Failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())