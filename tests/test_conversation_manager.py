"""
Unit tests for Djobea AI Conversation Manager - Sprint 2
Tests intelligent conversation understanding and information extraction
"""

import pytest
import json
from unittest.mock import Mock, patch
from app.services.conversation_manager import DjobeaConversationManager, RequestInfo


class TestRequestInfo:
    """Test RequestInfo dataclass functionality"""
    
    def test_is_complete_with_all_fields(self):
        """Test complete request info"""
        request_info = RequestInfo(
            service_type="plomberie",
            location="Bonamoussadi carrefour Shell",
            description="robinet coule-coule dans cuisine",
            urgency="urgent",
            confidence_score=0.9
        )
        assert request_info.is_complete() is True
    
    def test_is_complete_with_missing_fields(self):
        """Test incomplete request info"""
        request_info = RequestInfo(
            service_type="électricité",
            location=None,
            description="prise ne marche plus",
            urgency="demain"
        )
        assert request_info.is_complete() is False
    
    def test_missing_fields_identification(self):
        """Test missing fields detection"""
        request_info = RequestInfo(
            service_type="plomberie",
            location=None,
            description=None,
            urgency="urgent"
        )
        missing = request_info.missing_fields()
        assert "location" in missing
        assert "description" in missing
        assert len(missing) == 2


class TestDjobeaConversationManager:
    """Test conversation manager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create conversation manager instance for testing"""
        return DjobeaConversationManager()
    
    def test_message_normalization(self, manager):
        """Test local expression and typo normalization"""
        # Test local expressions
        normalized = manager._normalize_message("Le courant a jump chez moi")
        assert "panne électrique" in normalized
        
        normalized = manager._normalize_message("Mon robinet coule-coule")
        assert "fuite d'eau" in normalized
        
        # Test typo corrections
        normalized = manager._normalize_message("Bjr, j'ai un pb avec tt")
        assert "bonjour" in normalized
        assert "problème" in normalized
        assert "tout" in normalized
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_extract_request_info_complete(self, mock_anthropic, manager):
        """Test extraction with complete information"""
        # Mock Claude API response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "service_type": "plomberie",
            "location": "Bonamoussadi carrefour Shell, rue des palmiers",
            "description": "fuite d'eau sous évier de cuisine",
            "urgency": "urgent",
            "confidence_score": 0.95
        })
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        manager.client = mock_client
        
        conversation = [
            {"role": "user", "content": "Bonjour, j'ai une fuite sous mon évier"},
            {"role": "user", "content": "Je suis à Bonamoussadi carrefour Shell, rue des palmiers"},
            {"role": "user", "content": "C'est urgent, l'eau coule beaucoup"}
        ]
        
        request_info = manager.extract_request_info(conversation)
        
        assert request_info.service_type == "plomberie"
        assert "Bonamoussadi" in request_info.location
        assert "fuite" in request_info.description
        assert request_info.urgency == "urgent"
        assert request_info.confidence_score == 0.95
        assert request_info.is_complete() is True
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_extract_request_info_partial(self, mock_anthropic, manager):
        """Test extraction with missing information"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "service_type": "électricité",
            "location": None,
            "description": "prise électrique ne fonctionne plus",
            "urgency": None,
            "confidence_score": 0.7
        })
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        manager.client = mock_client
        
        conversation = [
            {"role": "user", "content": "Ma prise ne marche plus"}
        ]
        
        request_info = manager.extract_request_info(conversation)
        
        assert request_info.service_type == "électricité"
        assert request_info.location is None
        assert request_info.urgency is None
        assert request_info.is_complete() is False
        assert "location" in request_info.missing_fields()
        assert "urgency" in request_info.missing_fields()
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_process_message_flow(self, mock_anthropic, manager):
        """Test complete message processing flow"""
        # Mock extraction response
        extraction_response = Mock()
        extraction_response.content = [Mock()]
        extraction_response.content[0].text = json.dumps({
            "service_type": "plomberie",
            "location": None,
            "description": "robinet fuit",
            "urgency": None,
            "confidence_score": 0.6
        })
        
        # Mock question generation response
        question_response = Mock()
        question_response.content = [Mock()]
        question_response.content[0].text = "Pouvez-vous me donner votre adresse précise à Bonamoussadi ?"
        
        mock_client = Mock()
        mock_client.messages.create.side_effect = [extraction_response, question_response]
        mock_anthropic.return_value = mock_client
        manager.client = mock_client
        
        user_id = "237123456789"
        message = "Bonjour, mon robinet fuit"
        
        response, request_info = manager.process_message(user_id, message)
        
        # Check response generation
        assert "adresse" in response.lower()
        assert "bonamoussadi" in response.lower()
        
        # Check request info extraction
        assert request_info.service_type == "plomberie"
        assert request_info.location is None
        assert request_info.description == "robinet fuit"
        
        # Check conversation memory
        history = manager.get_conversation_history(user_id)
        assert len(history) == 2  # User message + bot response
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
    
    def test_conversation_memory_management(self, manager):
        """Test conversation memory storage and retrieval"""
        user_id = "237123456789"
        
        # Initially empty
        assert len(manager.get_conversation_history(user_id)) == 0
        
        # Add to memory
        manager.conversation_memory[user_id] = [
            {"role": "user", "content": "Test message", "timestamp": "2025-07-01T10:00:00"}
        ]
        
        # Retrieve history
        history = manager.get_conversation_history(user_id)
        assert len(history) == 1
        assert history[0]["content"] == "Test message"
        
        # Clear conversation
        manager.clear_conversation(user_id)
        assert len(manager.get_conversation_history(user_id)) == 0
    
    def test_local_expressions_understanding(self, manager):
        """Test understanding of Cameroon-specific expressions"""
        test_cases = [
            ("Le courant a jump", "panne électrique"),
            ("Mon robinet coule-coule", "fuite d'eau"),
            ("No current for house", "pas d'électricité"),
            ("Wata no dey comot", "pas d'eau"),
            ("Light don go since morning", "coupure électricité")
        ]
        
        for original, expected in test_cases:
            normalized = manager._normalize_message(original)
            assert expected in normalized
    
    def test_whatsapp_abbreviations_handling(self, manager):
        """Test WhatsApp abbreviation normalization"""
        message = "Slt, j'ai un pb avec tt, qd est-ce que c'est possible svp ?"
        normalized = manager._normalize_message(message)
        
        assert "salut" in normalized
        assert "problème" in normalized
        assert "tout" in normalized
        assert "quand" in normalized
        assert "s'il vous plaît" in normalized
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_confirmation_response_generation(self, mock_anthropic, manager):
        """Test confirmation message when all info is collected"""
        complete_request = RequestInfo(
            service_type="électricité",
            location="Bonamoussadi carrefour Total, Immeuble Bleu",
            description="panne de prises électriques dans chambre",
            urgency="cet après-midi",
            confidence_score=0.9
        )
        
        response = manager._generate_confirmation_response(complete_request)
        
        assert "électricité" in response
        assert "Bonamoussadi" in response
        assert "panne de prises" in response
        assert "cet après-midi" in response
        assert "15%" in response  # Commission mentioned
        assert "30 minutes" in response  # Response time mentioned
    
    def test_error_handling(self, manager):
        """Test error response generation"""
        error_response = manager._get_error_response()
        
        assert "problème technique" in error_response
        assert "plomberie" in error_response
        assert "électricité" in error_response
        assert "réparation électroménager" in error_response
        assert "Bonamoussadi" in error_response
    
    def test_conversation_context_building(self, manager):
        """Test conversation context formatting"""
        history = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"},
            {"role": "user", "content": "J'ai un problème d'électricité"},
            {"role": "assistant", "content": "Pouvez-vous me donner plus de détails ?"},
            {"role": "user", "content": "Les prises ne marchent plus"}
        ]
        
        context = manager._build_conversation_context(history)
        
        assert "Client: Bonjour" in context
        assert "Assistant: Bonjour !" in context
        assert "Client: J'ai un problème d'électricité" in context
        assert "Client: Les prises ne marchent plus" in context


@pytest.mark.integration
class TestConversationIntegration:
    """Integration tests for complete conversation flows"""
    
    @pytest.fixture
    def manager(self):
        """Create manager for integration tests"""
        return DjobeaConversationManager()
    
    def test_complete_service_request_flow(self, manager):
        """Test complete flow from greeting to service request completion"""
        # This would be an integration test with real Claude API
        # For now, we'll mock the responses but test the flow
        user_id = "237123456789"
        
        with patch('app.services.conversation_manager.Anthropic') as mock_anthropic:
            # Mock responses for each step
            mock_client = Mock()
            mock_anthropic.return_value = mock_client
            manager.client = mock_client
            
            # Step 1: Initial greeting
            mock_client.messages.create.return_value = Mock(
                content=[Mock(text=json.dumps({
                    "service_type": None,
                    "location": None,
                    "description": None,
                    "urgency": None,
                    "confidence_score": 0.1
                }))]
            )
            
            response1, info1 = manager.process_message(user_id, "Bonjour")
            assert not info1.is_complete()
            
            # Verify conversation flow continues until complete...
            # (Additional steps would be added for complete integration test)


if __name__ == "__main__":
    pytest.main([__file__])