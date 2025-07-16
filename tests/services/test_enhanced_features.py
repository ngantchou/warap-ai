#!/usr/bin/env python3
"""
Test script for enhanced scheduling and location features
Tests the integration of scheduling service with communication flow
"""

import asyncio
import sys
import os
from datetime import datetime

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db, engine
from app.models.database_models import User, ServiceRequest, RequestStatus, Base
from app.services.conversation_manager import conversation_manager
from app.services.scheduling_service import SchedulingService
from app.services.communication_service import CommunicationService
from sqlalchemy.orm import Session

def setup_test_data(db: Session):
    """Create test user and basic data"""
    # Create test user
    test_user = User(
        whatsapp_id="+237677123456",
        first_name="Test",
        last_name="User",
        phone_number="+237677123456"
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    
    print(f"✓ Created test user: {test_user.id}")
    return test_user

def test_enhanced_conversation():
    """Test enhanced conversation with scheduling preferences"""
    print("\n📞 Testing Enhanced Conversation with Scheduling...")
    
    # Test urgent plumbing request with landmarks
    test_message = "Bonjour, j'ai une urgence plomberie chez moi près du supermarché Mahima à Bonamoussadi. L'eau coule partout, il faut intervenir dans l'heure!"
    
    try:
        response, request_info = conversation_manager.process_message("test_user_urgent", test_message)
        
        print(f"✓ Message processed")
        print(f"✓ Service type: {request_info.service_type}")
        print(f"✓ Location: {request_info.location}")
        print(f"✓ Scheduling preference: {request_info.scheduling_preference}")
        print(f"✓ Landmark references: {request_info.landmark_references}")
        print(f"✓ Location confidence: {request_info.location_confidence}")
        print(f"✓ Response: {response[:100]}...")
        
        return request_info
        
    except Exception as e:
        print(f"❌ Error in conversation test: {e}")
        return None

def test_scheduling_service():
    """Test scheduling service functionality"""
    print("\n⏰ Testing Scheduling Service...")
    
    with next(get_db()) as db:
        try:
            scheduling_service = SchedulingService(db)
            
            # Test scheduling options
            options = scheduling_service.get_scheduling_options("plomberie", "Bonamoussadi")
            print(f"✓ Got {len(options['time_slots'])} scheduling options")
            
            # Test landmark matching
            landmarks = scheduling_service.find_landmark_matches("près du supermarché Mahima")
            print(f"✓ Found {len(landmarks)} landmark matches")
            
            if landmarks:
                top_match = landmarks[0]
                print(f"✓ Top match: {top_match['name']} (confidence: {top_match['confidence']:.2f})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in scheduling test: {e}")
            return False

async def test_enhanced_communication():
    """Test enhanced communication with scheduling details"""
    print("\n💬 Testing Enhanced Communication...")
    
    with next(get_db()) as db:
        try:
            # Create test service request with scheduling data
            test_request = ServiceRequest(
                user_id=1,  # Assume user exists
                service_type="plomberie",
                description="Fuite d'eau urgente",
                location="Bonamoussadi, près supermarché Mahima",
                urgency="urgent",
                scheduling_preference="URGENT",
                urgency_supplement=2000.0,
                landmark_references="Supermarché Mahima",
                location_confidence=0.85,
                location_confirmed=True,
                status=RequestStatus.PENDING
            )
            
            db.add(test_request)
            db.commit()
            db.refresh(test_request)
            
            # Test enhanced confirmation message
            comm_service = CommunicationService()
            message = comm_service._generate_enhanced_confirmation_message(
                test_request, 
                "5 000 - 15 000 XAF", 
                "Intervention de base, matériel simple"
            )
            
            print(f"✓ Generated enhanced confirmation message")
            print(f"✓ Message length: {len(message)} characters")
            print("✓ Message preview:")
            print(message[:200] + "..." if len(message) > 200 else message)
            
            return True
            
        except Exception as e:
            print(f"❌ Error in communication test: {e}")
            return False

def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Features Test")
    print("=" * 50)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Test conversation manager
    request_info = test_enhanced_conversation()
    
    # Test scheduling service
    scheduling_ok = test_scheduling_service()
    
    # Test enhanced communication
    communication_ok = asyncio.run(test_enhanced_communication())
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"✓ Conversation Manager: {'PASS' if request_info else 'FAIL'}")
    print(f"✓ Scheduling Service: {'PASS' if scheduling_ok else 'FAIL'}")
    print(f"✓ Enhanced Communication: {'PASS' if communication_ok else 'FAIL'}")
    
    if all([request_info, scheduling_ok, communication_ok]):
        print("\n🎉 All enhanced features are working!")
        return True
    else:
        print("\n⚠️ Some features need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)