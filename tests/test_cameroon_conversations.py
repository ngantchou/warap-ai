"""
Sprint 2 - Real-world Cameroon conversation testing
Tests conversation manager with authentic Cameroonian expressions and scenarios
"""

import pytest
from unittest.mock import Mock, patch
import json
from app.services.conversation_manager import conversation_manager, RequestInfo


class TestCameroonConversations:
    """Test real Cameroon conversation scenarios"""
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_electricity_problem_pidgin_english(self, mock_anthropic):
        """Test electricity problem in Pidgin English"""
        # Mock Claude response for electricity problem
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "service_type": "électricité",
            "location": None,
            "description": "panne électrique dans la maison",
            "urgency": "urgent",
            "confidence_score": 0.8
        })
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        conversation_manager.client = mock_client
        
        # Test message in Pidgin English
        user_id = "237690123456"
        message = "Eeeh massa, light don go for my house since morning. No current at all!"
        
        response, request_info = conversation_manager.process_message(user_id, message)
        
        # Verify extraction
        assert request_info.service_type == "électricité"
        assert request_info.urgency == "urgent"
        assert request_info.description == "panne électrique dans la maison"
        assert request_info.location is None  # Missing location
        
        # Verify response asks for location
        assert "adresse" in response.lower() or "localisation" in response.lower()
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_plumbing_problem_french_slang(self, mock_anthropic):
        """Test plumbing problem with French slang"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "service_type": "plomberie",
            "location": "Bonamoussadi carrefour Shell",
            "description": "fuite d'eau sous évier",
            "urgency": None,
            "confidence_score": 0.85
        })
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        conversation_manager.client = mock_client
        
        # Test with French slang
        user_id = "237677654321"
        message = "Bonjour, j'ai un pb grave! Mon robinet coule-coule sans arrêt à Bonamoussadi carrefour Shell"
        
        response, request_info = conversation_manager.process_message(user_id, message)
        
        # Verify extraction
        assert request_info.service_type == "plomberie"
        assert "Bonamoussadi" in request_info.location
        assert "fuite" in request_info.description
        assert request_info.urgency is None  # Missing urgency
        
        # Verify response asks for timing
        assert "quand" in response.lower() or "délai" in response.lower()
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_appliance_repair_mixed_languages(self, mock_anthropic):
        """Test appliance repair in mixed French/English"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "service_type": "réparation électroménager",
            "location": "Bonamoussadi derrière Total",
            "description": "climatiseur ne refroidit plus",
            "urgency": "cet après-midi",
            "confidence_score": 0.9
        })
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        conversation_manager.client = mock_client
        
        # Test with mixed languages
        user_id = "237682987654"
        message = "Hello, my air conditioner is not cooling bien, je suis à Bonamoussadi derrière Total. I need help cet après-midi svp"
        
        response, request_info = conversation_manager.process_message(user_id, message)
        
        # Verify complete extraction
        assert request_info.service_type == "réparation électroménager"
        assert "Bonamoussadi" in request_info.location
        assert "climatiseur" in request_info.description
        assert request_info.urgency == "cet après-midi"
        assert request_info.is_complete()
        
        # Verify confirmation response
        assert "parfait" in response.lower() or "compris" in response.lower()
        assert "climatiseur" in response.lower() or "électroménager" in response.lower()
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_multi_turn_conversation(self, mock_anthropic):
        """Test multi-turn conversation building complete request"""
        user_id = "237655443322"
        
        # Mock responses for multi-turn conversation
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        conversation_manager.client = mock_client
        
        # Turn 1: Initial greeting
        mock_client.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps({
                "service_type": None,
                "location": None,
                "description": None,
                "urgency": None,
                "confidence_score": 0.1
            }))]
        )
        
        response1, info1 = conversation_manager.process_message(user_id, "Bonsoir")
        assert not info1.is_complete()
        
        # Turn 2: Service type mentioned
        mock_client.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps({
                "service_type": "électricité",
                "location": None,
                "description": "prise électrique ne fonctionne plus",
                "urgency": None,
                "confidence_score": 0.6
            }))]
        )
        
        response2, info2 = conversation_manager.process_message(user_id, "Ma prise ne marche plus")
        assert info2.service_type == "électricité"
        assert not info2.is_complete()
        
        # Turn 3: Location added
        mock_client.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps({
                "service_type": "électricité",
                "location": "Bonamoussadi quartier Makepe",
                "description": "prise électrique ne fonctionne plus dans chambre",
                "urgency": None,
                "confidence_score": 0.8
            }))]
        )
        
        response3, info3 = conversation_manager.process_message(user_id, "Je suis à Bonamoussadi quartier Makepe")
        assert "Bonamoussadi" in info3.location
        assert not info3.is_complete()
        
        # Turn 4: Complete with urgency
        mock_client.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps({
                "service_type": "électricité",
                "location": "Bonamoussadi quartier Makepe",
                "description": "prise électrique ne fonctionne plus dans chambre",
                "urgency": "demain matin",
                "confidence_score": 0.95
            }))]
        )
        
        response4, info4 = conversation_manager.process_message(user_id, "Demain matin si possible")
        assert info4.is_complete()
        assert info4.urgency == "demain matin"
        
        # Verify conversation memory
        history = conversation_manager.get_conversation_history(user_id)
        assert len(history) == 8  # 4 user messages + 4 bot responses
    
    def test_local_expressions_normalization(self):
        """Test normalization of Cameroon-specific expressions"""
        test_cases = [
            # Electrical issues
            ("Le courant a jump ce matin", "panne électrique"),
            ("Light don go depuis hier", "coupure électricité"),
            ("No current for house", "pas d'électricité"),
            
            # Water issues  
            ("Mon robinet coule-coule trop", "fuite d'eau"),
            ("Wata no dey comot", "pas d'eau"),
            ("Pipe don burst for kitchen", "canalisation cassée"),
            
            # WhatsApp abbreviations
            ("Slt, j'ai un pb urgent pr demain", "salut", "problème", "pour"),
            ("Bjr massa, qd est-ce que tu peux venir?", "bonjour", "quand"),
        ]
        
        for original, *expected_words in test_cases:
            normalized = conversation_manager._normalize_message(original)
            for expected in expected_words:
                assert expected in normalized, f"Expected '{expected}' in normalized '{normalized}' from '{original}'"
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_error_handling_incomplete_claude_response(self, mock_anthropic):
        """Test error handling when Claude response is malformed"""
        # Mock malformed JSON response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Invalid JSON response"
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        conversation_manager.client = mock_client
        
        user_id = "237698765432"
        message = "J'ai un problème"
        
        response, request_info = conversation_manager.process_message(user_id, message)
        
        # Should return fallback response and empty RequestInfo
        assert "problème technique" in response.lower()
        assert not request_info.is_complete()
        assert request_info.confidence_score == 0.0
    
    def test_conversation_memory_limit(self):
        """Test conversation memory keeps only last 10 messages"""
        user_id = "237612345678"
        
        # Add 15 messages
        for i in range(15):
            conversation_manager.conversation_memory[user_id] = conversation_manager.conversation_memory.get(user_id, [])
            conversation_manager.conversation_memory[user_id].append({
                "role": "user",
                "content": f"Message {i}",
                "timestamp": f"2025-07-01T10:{i:02d}:00"
            })
        
        # Should keep only last 10
        history = conversation_manager.get_conversation_history(user_id)
        assert len(history) <= 10
        assert history[-1]["content"] == "Message 14"
    
    @patch('app.services.conversation_manager.Anthropic')
    def test_high_confidence_complete_request(self, mock_anthropic):
        """Test complete request with high confidence score"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps({
            "service_type": "plomberie",
            "location": "Bonamoussadi carrefour Shell, rue des palmiers, immeuble bleu",
            "description": "fuite d'eau importante sous évier de cuisine, eau partout",
            "urgency": "urgent",
            "confidence_score": 0.95
        })
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        conversation_manager.client = mock_client
        
        user_id = "237687654321"
        message = "Urgence! Grosse fuite sous mon évier à Bonamoussadi carrefour Shell, rue des palmiers, immeuble bleu. Il y a de l'eau partout dans ma cuisine!"
        
        response, request_info = conversation_manager.process_message(user_id, message)
        
        # Verify complete extraction
        assert request_info.is_complete()
        assert request_info.confidence_score == 0.95
        assert request_info.service_type == "plomberie"
        assert "Shell" in request_info.location
        assert "fuite" in request_info.description
        assert request_info.urgency == "urgent"
        
        # Verify confirmation response with all details
        assert "plomberie" in response
        assert "Shell" in response
        assert "urgent" in response
        assert "15%" in response  # Commission mentioned
        assert "30 minutes" in response  # Response time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])