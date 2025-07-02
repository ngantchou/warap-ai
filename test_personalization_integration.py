"""
Djobea AI Personalization Integration Test
Comprehensive test for personalization system integration with conversation manager
"""

import asyncio
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.conversation_manager import ConversationManager
from app.services.personalization_service import PersonalizationService
from app.services.emotional_intelligence_service import EmotionalIntelligenceService
from app.database import get_db, engine
from app.models.database_models import Base, User
from sqlalchemy.orm import sessionmaker


class TestPersonalizationIntegration:
    """Integration tests for personalization system with conversation manager"""
    
    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def sample_user(self, db_session):
        """Create test user"""
        user = User(phone_number="+237123456789", name="Test User")
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def conversation_manager(self):
        """Create conversation manager with personalization"""
        return ConversationManager(
            emotional_intelligence_service=EmotionalIntelligenceService()
        )
    
    @pytest.mark.asyncio
    async def test_personalization_in_conversation_flow(self, conversation_manager, db_session, sample_user):
        """Test personalization integration in conversation flow"""
        
        # Mock AI responses
        with patch.object(conversation_manager, 'client') as mock_client:
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "Bonjour! Comment puis-je vous aider aujourd'hui?"
            mock_client.messages.create.return_value = mock_response
            
            # Process message with personalization
            response, request_info, emotion = await conversation_manager.process_message_with_emotions(
                db=db_session,
                user_id=str(sample_user.id),
                message="Bonjour, j'ai besoin d'un plombier",
                conversation_id=1
            )
            
            # Verify response was generated
            assert response is not None
            assert len(response) > 0
            assert "bonjour" in response.lower()
    
    @pytest.mark.asyncio 
    async def test_personalization_learning_from_conversation(self, conversation_manager, db_session, sample_user):
        """Test that personalization learns from conversations"""
        
        # Mock AI responses for consistent testing
        with patch.object(conversation_manager, 'client') as mock_client:
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "Je vais vous aider à trouver un plombier"
            mock_client.messages.create.return_value = mock_response
            
            # Simulate multiple formal French conversations
            conversations = [
                "Bonjour, j'ai besoin d'un plombier pour une fuite",
                "Bonsoir, pourriez-vous m'aider avec l'électricité?", 
                "Bonjour, j'aimerais réparer mon électroménager"
            ]
            
            for i, message in enumerate(conversations):
                await conversation_manager.process_message_with_emotions(
                    db=db_session,
                    user_id=str(sample_user.id),
                    message=message,
                    conversation_id=i + 1
                )
            
            # Check if preferences were learned
            personalization_service = PersonalizationService()
            preferences = await personalization_service.get_user_preferences(db_session, sample_user.id)
            
            assert preferences is not None
            assert preferences.user_id == sample_user.id
            assert preferences.interaction_count >= 3
    
    @pytest.mark.asyncio
    async def test_message_personalization_application(self, conversation_manager, db_session, sample_user):
        """Test that messages are personalized based on user preferences"""
        
        # Initialize user preferences
        personalization_service = PersonalizationService()
        preferences = await personalization_service.initialize_user_preferences(db_session, sample_user.id)
        preferences.communication_style = "friendly"
        preferences.emoji_usage_preference = "moderate"
        preferences.preferred_language = "français"
        db_session.commit()
        
        # Mock AI responses
        with patch.object(conversation_manager, 'client') as mock_client:
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "Votre demande a été reçue"
            mock_client.messages.create.return_value = mock_response
            
            # Mock personalization
            with patch.object(personalization_service, 'personalize_message') as mock_personalize:
                mock_personalize.return_value = "Salut! 😊 Votre demande a bien été reçue!"
                
                response, _, _ = await conversation_manager.process_message_with_emotions(
                    db=db_session,
                    user_id=str(sample_user.id),
                    message="J'ai besoin d'aide",
                    conversation_id=1
                )
                
                # Verify personalization was applied
                mock_personalize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_conversation_manager_personalization_service_integration(self, conversation_manager):
        """Test that conversation manager has personalization service properly integrated"""
        
        assert hasattr(conversation_manager, 'personalization_service')
        assert conversation_manager.personalization_service is not None
        assert isinstance(conversation_manager.personalization_service, PersonalizationService)
    
    @pytest.mark.asyncio
    async def test_emergency_detection_with_personalization(self, conversation_manager, db_session, sample_user):
        """Test emergency detection doesn't interfere with personalization"""
        
        # Mock emotional intelligence for emergency
        with patch.object(conversation_manager.emotional_intelligence, 'analyze_emotional_context') as mock_emotion:
            mock_emotion.return_value = Mock(
                dominant_emotion="stress",
                stress_level=0.9,
                requires_immediate_attention=True
            )
            
            with patch.object(conversation_manager.emotional_intelligence, 'detect_emergency_situation') as mock_emergency:
                mock_emergency.return_value = True
                
                with patch.object(conversation_manager.emotional_intelligence, 'generate_emotionally_aware_response') as mock_response:
                    mock_response.return_value = "Situation d'urgence détectée. Je vous aide immédiatement!"
                    
                    response, request_info, emotion = await conversation_manager.process_message_with_emotions(
                        db=db_session,
                        user_id=str(sample_user.id),
                        message="URGENT! Gros problème d'eau chez moi!",
                        conversation_id=1
                    )
                    
                    # Emergency response should still be generated
                    assert "urgence" in response.lower()
                    mock_emergency.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_personalization_with_cultural_intelligence(self, conversation_manager, db_session, sample_user):
        """Test personalization works with cultural intelligence features"""
        
        # Mock cultural and emotional responses
        with patch.object(conversation_manager.emotional_intelligence, 'analyze_emotional_context') as mock_emotion:
            mock_emotion.return_value = Mock(
                dominant_emotion="neutral",
                stress_level=0.2,
                requires_immediate_attention=False
            )
            
            with patch.object(conversation_manager.emotional_intelligence, 'generate_emotionally_aware_response') as mock_response:
                mock_response.return_value = "Bonsoir! Comment allez-vous ce soir?"
                
                response, request_info, emotion = await conversation_manager.process_message_with_emotions(
                    db=db_session,
                    user_id=str(sample_user.id),
                    message="Bonsoir, j'ai un petit problème d'électricité",
                    conversation_id=1
                )
                
                # Should generate culturally appropriate response
                assert response is not None
                assert len(response) > 0
    
    def test_personalization_service_initialization(self, conversation_manager):
        """Test personalization service is properly initialized"""
        
        assert conversation_manager.personalization_service is not None
        
        # Test personalization service has AI service integration
        personalization_service = conversation_manager.personalization_service
        assert hasattr(personalization_service, 'ai_service')


async def test_full_conversation_with_personalization():
    """Integration test simulating full conversation with personalization learning"""
    
    # Create test database session
    Session = sessionmaker(bind=engine)
    db_session = Session()
    
    try:
        # Create test user
        user = User(phone_number="+237654321987", name="Integration Test User")
        db_session.add(user)
        db_session.commit()
        
        # Initialize conversation manager
        conversation_manager = ConversationManager(
            emotional_intelligence_service=EmotionalIntelligenceService()
        )
        
        # Mock AI responses for full conversation
        with patch.object(conversation_manager, 'client') as mock_client:
            mock_response = Mock()
            mock_response.content = [Mock()]
            
            # Simulate conversation sequence
            conversation_sequence = [
                ("Bonjour, j'ai une fuite d'eau", "Bonjour! Je comprends votre problème de plomberie"),
                ("C'est urgent", "Je vais vous trouver un plombier immédiatement"),
                ("Merci beaucoup", "De rien! Je reste à votre service")
            ]
            
            for i, (user_message, bot_response) in enumerate(conversation_sequence):
                mock_response.content[0].text = bot_response
                mock_client.messages.create.return_value = mock_response
                
                response, request_info, emotion = await conversation_manager.process_message_with_emotions(
                    db=db_session,
                    user_id=str(user.id),
                    message=user_message,
                    conversation_id=i + 1
                )
                
                # Verify responses are generated
                assert response is not None
                assert len(response) > 0
                
                print(f"✓ Conversation turn {i + 1}: '{user_message}' -> '{response}'")
        
        # Check personalization was applied
        personalization_service = PersonalizationService()
        preferences = await personalization_service.get_user_preferences(db_session, user.id)
        
        assert preferences is not None
        assert preferences.interaction_count >= 3
        print(f"✓ User preferences learned: {preferences.interaction_count} interactions")
        
        print("✓ Full conversation with personalization completed successfully")
        
    finally:
        db_session.close()


if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_full_conversation_with_personalization())