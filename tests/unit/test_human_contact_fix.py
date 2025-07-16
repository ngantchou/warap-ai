#!/usr/bin/env python3
"""
Test simple pour valider la correction du contact humain
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import asyncio
from app.services.natural_conversation_engine import NaturalConversationEngine
from app.database import get_session

async def test_human_contact():
    """Test simple du contact humain"""
    print("🧪 Test du contact humain - Djobea AI")
    print("=" * 50)
    
    # Initialiser le moteur de conversation
    with get_session() as db:
        engine = NaturalConversationEngine(db)
        
        # Simuler une demande de contact humain
        user_id = "237691924173"
        message = "puis discuter avec un gestionnaire ?"
        
        try:
            print(f"📞 Test message: {message}")
            result = await engine.process_natural_conversation(user_id, message)
            
            print(f"✅ Résultat: {result.response_message}")
            print(f"⚙️ Actions système: {result.system_actions}")
            print(f"🎯 Confidence: {result.confidence_score}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_human_contact())
    sys.exit(0 if success else 1)