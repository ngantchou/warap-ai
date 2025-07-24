#!/usr/bin/env python3
"""
Test Provider Notification System
Verify that provider notifications are working after service request creation
"""

import asyncio
import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.natural_conversation_engine import NaturalConversationEngine
from app.models.database_models import ServiceRequest, RequestStatus, User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

async def test_provider_notification():
    """Test complete provider notification flow"""
    
    print("🔍 Testing Provider Notification System")
    print("=" * 50)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize conversation engine
        conversation_engine = NaturalConversationEngine(db)
        
        # Test user identifier
        user_identifier = "237691924177"  # Test phone number
        
        # Test message that should create a service request
        test_message = "J'ai un problème de plomberie à Bonamoussadi. Mon robinet fuit beaucoup."
        
        print(f"📱 Testing message: {test_message}")
        print(f"👤 User: {user_identifier}")
        print("")
        
        # Process the message through natural conversation engine
        result = await conversation_engine.process_natural_conversation(
            user_identifier, 
            test_message
        )
        
        print("✅ Conversation Processing Results:")
        print(f"Response: {result.response_message}")
        print(f"Phase: {result.conversation_state.current_phase}")
        print(f"Active Request ID: {result.conversation_state.active_request_id}")
        print(f"System Actions: {result.system_actions}")
        print("")
        
        # Check if service request was created
        if result.conversation_state.active_request_id:
            request = db.query(ServiceRequest).filter(
                ServiceRequest.id == result.conversation_state.active_request_id
            ).first()
            
            if request:
                print("🎯 Service Request Created Successfully:")
                print(f"  ID: {request.id}")
                print(f"  Service Type: {request.service_type}")
                print(f"  Location: {request.location}")
                print(f"  Description: {request.description}")
                print(f"  Status: {request.status}")
                print(f"  Created At: {request.created_at}")
                print("")
                
                # Check provider notification status
                if request.status == RequestStatus.PROVIDER_NOTIFIED:
                    print("✅ Provider Notification Status: NOTIFIED")
                    print("🔔 Providers should have received WhatsApp notifications!")
                else:
                    print(f"❌ Provider Notification Status: {request.status}")
                    print("⚠️  Providers may not have been notified yet")
                    
            else:
                print("❌ Service request not found in database")
        else:
            print("❌ No service request was created")
        
        # Check for any active background tasks
        print("\n📊 System Status:")
        print(f"Active conversations: {len(conversation_engine.active_conversations)}")
        print(f"Conversation data cache: {len(conversation_engine.conversation_data)}")
        
        # Show provider status
        from app.models.database_models import Provider
        providers = db.query(Provider).filter(Provider.is_active == True).all()
        print(f"Active providers: {len(providers)}")
        
        for provider in providers:
            print(f"  - {provider.name} ({provider.whatsapp_id})")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        logger.error(f"Test error: {e}")
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_provider_notification())