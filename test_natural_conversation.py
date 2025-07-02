"""
Test script for natural conversation engine
Tests the complete natural conversation flow without exposing database operations
"""

import asyncio
from app.database import get_db_session
from app.services.natural_conversation_engine import NaturalConversationEngine

async def test_natural_conversation():
    """Test the natural conversation engine"""
    
    # Get database session
    db = next(get_db_session())
    
    # Initialize conversation engine
    engine = NaturalConversationEngine(db)
    
    print("🚀 Testing Natural Conversation Engine")
    print("=" * 50)
    
    # Test user identifier
    user_id = "test_web_session_001"
    
    # Test conversation flows
    test_messages = [
        "Bonjour",
        "J'ai un problème de plomberie",
        "Il y a une fuite d'eau dans ma cuisine",
        "Je suis à Bonamoussadi",
        "C'est assez urgent"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n💬 Message {i}: '{message}'")
        
        try:
            # Process message through natural conversation engine
            result = await engine.process_natural_conversation(user_id, message)
            
            print(f"🤖 Response: {result.response_message}")
            print(f"📊 Confidence: {result.confidence_score:.2f}")
            print(f"🔄 Phase: {result.conversation_state.current_phase.value}")
            
            if result.system_actions:
                print(f"⚙️  System Actions: {len(result.system_actions)} actions triggered")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Natural conversation test completed")

if __name__ == "__main__":
    asyncio.run(test_natural_conversation())