"""
Comprehensive Test Suite for Multi-LLM Conversational AI System
Tests the integration of Claude, Gemini, and GPT-4 with advanced state management
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List
from datetime import datetime
import logging

from app.services.multi_llm_orchestrator import (
    MultiLLMOrchestrator, ConversationContext, ProcessingResult, LLMProvider
)
from app.services.conversation_state_machine import (
    ConversationStateMachine, ConversationState, TriggerEvent
)
from app.services.proactive_engagement_service import (
    ProactiveEngagementService, EngagementTrigger
)
from app.services.enhanced_conversation_manager import EnhancedConversationManager
from app.database import get_db
from app.models.database_models import User, ServiceRequest, Conversation

logger = logging.getLogger(__name__)

class MultiLLMConversationalTestSuite:
    """Comprehensive test suite for multi-LLM conversational AI system"""
    
    def __init__(self):
        self.orchestrator = MultiLLMOrchestrator()
        self.state_machine = ConversationStateMachine()
        self.proactive_service = ProactiveEngagementService()
        self.enhanced_manager = EnhancedConversationManager()
        
    async def run_complete_test_suite(self):
        """Run comprehensive multi-LLM conversational AI tests"""
        try:
            print("🚀 Starting Multi-LLM Conversational AI Test Suite")
            print("=" * 60)
            
            # Test 1: Multi-LLM Orchestrator
            await self.test_multi_llm_orchestrator()
            
            # Test 2: Intelligent Task Routing
            await self.test_intelligent_task_routing()
            
            # Test 3: State Machine Transitions
            await self.test_state_machine_transitions()
            
            # Test 4: Proactive Engagement System
            await self.test_proactive_engagement_system()
            
            # Test 5: Enhanced Conversation Manager
            await self.test_enhanced_conversation_manager()
            
            # Test 6: Multi-LLM Conversation Scenarios
            await self.test_multi_llm_conversation_scenarios()
            
            # Test 7: Complex Problem Solving Pipeline
            await self.test_complex_problem_solving_pipeline()
            
            # Test 8: Integration with Provider Matching
            await self.test_provider_matching_integration()
            
            print("\n" + "=" * 60)
            print("✅ Multi-LLM Conversational AI Test Suite Completed Successfully!")
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            logger.error(f"Test suite error: {e}")
            
    async def test_multi_llm_orchestrator(self):
        """Test multi-LLM orchestration capabilities"""
        print("\n📋 Testing Multi-LLM Orchestrator...")
        
        # Test Claude for conversation analysis
        context = ConversationContext(
            user_id="test_user_1",
            phone_number="+237690000001",
            message="Bonjour, j'ai un problème de plomberie urgent dans ma cuisine",
            conversation_history=[],
            current_state="INITIAL"
        )
        
        result = await self.orchestrator.process_conversation(context)
        
        print(f"✓ Claude Analysis:")
        print(f"  - Response: {result.response[:100]}...")
        print(f"  - Confidence: {result.confidence}")
        print(f"  - LLM Provider: {result.provider.value}")
        print(f"  - Extracted Data: {result.extracted_data}")
        
        assert result.response, "Claude should generate a response"
        assert result.confidence > 0.5, "Confidence should be reasonable"
        assert result.provider == LLMProvider.CLAUDE, "Should use Claude for conversation analysis"
        
        # Test complex scenario requiring multiple LLMs
        complex_context = ConversationContext(
            user_id="test_user_2",
            phone_number="+237690000002",
            message="Je veux négocier le prix et j'ai aussi des photos du problème électrique",
            conversation_history=[],
            current_state="INITIAL",
            requires_multimodal=True
        )
        
        complex_result = await self.orchestrator.process_conversation(complex_context)
        
        print(f"✓ Complex Multi-LLM Processing:")
        print(f"  - Response: {complex_result.response[:100]}...")
        print(f"  - Complexity Score: {complex_context.complexity_score}")
        print(f"  - Provider: {complex_result.provider.value}")
        
        assert complex_result.response, "Should handle complex requests"
        assert complex_result.confidence > 0.6, "Complex processing should be confident"
        
    async def test_intelligent_task_routing(self):
        """Test intelligent routing of tasks to appropriate LLMs"""
        print("\n🔀 Testing Intelligent Task Routing...")
        
        test_scenarios = [
            {
                "message": "Je suis très frustré, ça ne marche toujours pas!",
                "expected_intention": "plainte",
                "expected_provider": LLMProvider.CLAUDE,
                "description": "Emotional handling"
            },
            {
                "message": "J'ai besoin d'un plombier pour demain matin",
                "expected_intention": "nouvelle_demande", 
                "expected_provider": LLMProvider.GEMINI,
                "description": "Provider matching prediction"
            },
            {
                "message": "Pouvez-vous m'expliquer pourquoi le prix est si élevé?",
                "expected_intention": "question_info",
                "expected_provider": LLMProvider.GPT4,
                "description": "Complex explanation"
            }
        ]
        
        for scenario in test_scenarios:
            context = ConversationContext(
                user_id="test_routing",
                phone_number="+237690000003",
                message=scenario["message"],
                conversation_history=[],
                current_state="INITIAL"
            )
            
            result = await self.orchestrator.process_conversation(context)
            
            print(f"✓ {scenario['description']}:")
            print(f"  - Message: {scenario['message']}")
            print(f"  - Provider Used: {result.provider.value}")
            print(f"  - Confidence: {result.confidence}")
            
            # Verify intelligent routing worked
            extracted_data = result.extracted_data or {}
            intention = extracted_data.get("intention_primaire", "")
            
            if intention == scenario["expected_intention"]:
                print(f"  - ✅ Correct intention detected: {intention}")
            else:
                print(f"  - ⚠️  Expected {scenario['expected_intention']}, got {intention}")
            
    async def test_state_machine_transitions(self):
        """Test conversation state machine transitions"""
        print("\n⚙️ Testing State Machine Transitions...")
        
        # Mock database session
        db = next(get_db())
        
        # Test transition from INITIAL to COLLECTING_INFO
        current_state = ConversationState.INITIAL
        trigger = TriggerEvent.NEW_MESSAGE
        context = {
            "user_id": "test_state",
            "phone_number": "+237690000004",
            "extracted_entities": {"service_type": "plomberie"},
            "confidence": 0.8
        }
        
        new_state, messages = await self.state_machine.handle_state_transition(
            current_state, trigger, context, db
        )
        
        print(f"✓ State Transition Test:")
        print(f"  - From: {current_state.value}")
        print(f"  - Trigger: {trigger.value}")
        print(f"  - To: {new_state.value}")
        print(f"  - System Messages: {len(messages)}")
        
        assert new_state == ConversationState.COLLECTING_INFO, "Should transition to COLLECTING_INFO"
        
        # Test complete information trigger
        complete_context = {
            "user_id": "test_state",
            "phone_number": "+237690000004",
            "extracted_entities": {
                "service_type": "plomberie",
                "location": "Bonamoussadi",
                "description": "Fuite dans la cuisine",
                "urgency": "urgent"
            },
            "confidence": 0.9
        }
        
        final_state, final_messages = await self.state_machine.handle_state_transition(
            ConversationState.COLLECTING_INFO,
            TriggerEvent.INFO_COMPLETE,
            complete_context,
            db
        )
        
        print(f"✓ Complete Info Transition:")
        print(f"  - To: {final_state.value}")
        print(f"  - Messages: {len(final_messages)}")
        
        assert final_state == ConversationState.CONFIRMING_REQUEST, "Should move to confirming request"
        
    async def test_proactive_engagement_system(self):
        """Test proactive engagement and follow-up system"""
        print("\n📢 Testing Proactive Engagement System...")
        
        # Schedule proactive engagement
        await self.proactive_service.schedule_engagement(
            user_id="test_proactive",
            phone_number="+237690000005",
            trigger=EngagementTrigger.REQUEST_CREATED,
            context={
                "service_type": "électricité",
                "location": "Bonamoussadi",
                "urgency": "normal"
            },
            custom_delay=1  # 1 second for testing
        )
        
        print("✓ Proactive engagement scheduled")
        
        # Test engagement generation
        engagement_message = await self.proactive_service._generate_engagement_message(
            engagement=self.proactive_service.scheduled_engagements[0] if self.proactive_service.scheduled_engagements else None,
            rule=self.proactive_service.engagement_rules[EngagementTrigger.REQUEST_CREATED]
        )
        
        print(f"✓ Generated Engagement Message:")
        print(f"  - Length: {len(engagement_message)} characters")
        print(f"  - Contains service info: {'électricité' in engagement_message}")
        
        assert engagement_message, "Should generate engagement message"
        assert len(engagement_message) > 50, "Message should be substantial"
        
        # Test engagement status
        status = self.proactive_service.get_engagement_status("test_proactive")
        print(f"✓ Engagement Status: {len(status)} active engagements")
        
    async def test_enhanced_conversation_manager(self):
        """Test enhanced conversation manager integration"""
        print("\n🧠 Testing Enhanced Conversation Manager...")
        
        # Test message processing
        result = await self.enhanced_manager.process_message(
            phone_number="+237690000006",
            message="J'ai une urgence de plomberie, il y a de l'eau partout!",
            media_url=None,
            db=next(get_db())
        )
        
        print(f"✓ Enhanced Message Processing:")
        print(f"  - Response: {result['response'][:100]}...")
        print(f"  - State: {result['state']}")
        print(f"  - Confidence: {result['confidence']}")
        print(f"  - LLM Provider: {result['llm_provider']}")
        print(f"  - System Actions: {result['system_actions']}")
        
        assert result["response"], "Should generate response"
        assert result["state"], "Should determine conversation state"
        assert result["confidence"] > 0.5, "Should have reasonable confidence"
        
        # Test conversation status
        status = await self.enhanced_manager.get_conversation_status(
            phone_number="+237690000006",
            db=next(get_db())
        )
        
        print(f"✓ Conversation Status:")
        print(f"  - Status: {status['status']}")
        print(f"  - State: {status['state']}")
        print(f"  - Turns: {status['conversation_turns']}")
        
        assert status["status"] == "active", "Conversation should be active"
        
    async def test_multi_llm_conversation_scenarios(self):
        """Test complete conversation scenarios using multiple LLMs"""
        print("\n💬 Testing Multi-LLM Conversation Scenarios...")
        
        scenarios = [
            {
                "name": "Emotional Support + Technical Solution",
                "messages": [
                    "Je suis désespéré, ma climatisation est cassée depuis 3 jours!",
                    "Oui, je veux bien que vous m'aidiez rapidement"
                ],
                "expected_llms": [LLMProvider.CLAUDE, LLMProvider.GEMINI]
            },
            {
                "name": "Complex Problem + Creative Solution",
                "messages": [
                    "J'ai un problème électrique très compliqué avec plusieurs pannes",
                    "Pouvez-vous m'expliquer toutes les options possibles?"
                ],
                "expected_llms": [LLMProvider.CLAUDE, LLMProvider.GPT4]
            }
        ]
        
        for scenario in scenarios:
            print(f"\n  📝 Scenario: {scenario['name']}")
            
            phone_number = f"+23769000{len(scenarios):04d}"
            
            for i, message in enumerate(scenario["messages"]):
                result = await self.enhanced_manager.process_message(
                    phone_number=phone_number,
                    message=message,
                    media_url=None,
                    db=next(get_db())
                )
                
                print(f"    Turn {i+1}:")
                print(f"    - Message: {message}")
                print(f"    - Response: {result['response'][:80]}...")
                print(f"    - LLM: {result['llm_provider']}")
                print(f"    - State: {result['state']}")
                
                assert result["response"], f"Turn {i+1} should generate response"
                
    async def test_complex_problem_solving_pipeline(self):
        """Test complex problem solving with multi-LLM coordination"""
        print("\n🔧 Testing Complex Problem Solving Pipeline...")
        
        # Simulate complex negotiation scenario
        complex_message = """
        Bonjour, j'ai plusieurs problèmes:
        1. Fuite d'eau dans la salle de bain
        2. Panne électrique dans la cuisine  
        3. Budget limité à 20,000 XAF
        4. Disponible seulement le weekend
        
        Pouvez-vous me proposer une solution complète et économique?
        """
        
        result = await self.enhanced_manager.process_message(
            phone_number="+237690000999",
            message=complex_message,
            media_url=None,
            db=next(get_db())
        )
        
        print(f"✓ Complex Problem Solving:")
        print(f"  - Response Length: {len(result['response'])} characters")
        print(f"  - Confidence: {result['confidence']}")
        print(f"  - LLM Provider: {result['llm_provider']}")
        print(f"  - Contains Budget: {'20,000' in result['response'] or '20000' in result['response']}")
        print(f"  - Contains Weekend: {'weekend' in result['response'].lower()}")
        print(f"  - Multi-problem Handling: {len([x for x in ['fuite', 'électrique', 'plomberie'] if x in result['response'].lower()])}")
        
        assert result["response"], "Should handle complex multi-problem request"
        assert result["confidence"] > 0.6, "Should be confident in complex handling"
        assert len(result["response"]) > 200, "Complex problems need detailed responses"
        
    async def test_provider_matching_integration(self):
        """Test integration with provider matching using Gemini predictions"""
        print("\n👥 Testing Provider Matching Integration...")
        
        # Test provider matching scenario
        matching_message = "Je cherche le meilleur plombier disponible aujourd'hui à Bonamoussadi"
        
        context = ConversationContext(
            user_id="test_matching",
            phone_number="+237690000888",
            message=matching_message,
            conversation_history=[],
            current_state="SEARCHING_PROVIDERS"
        )
        
        # Process with Gemini for provider matching
        result = await self.orchestrator.enhance_with_gemini(context, {
            "intention_primaire": "nouvelle_demande",
            "entities": {
                "service_type": "plomberie",
                "location": "Bonamoussadi",
                "urgency": "aujourd'hui"
            }
        })
        
        print(f"✓ Provider Matching Enhancement:")
        print(f"  - Provider Matching: {result.get('provider_matching', {})}")
        print(f"  - User Predictions: {result.get('user_predictions', {})}")
        print(f"  - System Recommendations: {result.get('system_recommendations', {})}")
        print(f"  - Enhancement Confidence: {result.get('enhancement_confidence', 0)}")
        
        assert result.get("provider_matching"), "Should provide provider matching insights"
        assert result.get("user_predictions"), "Should predict user preferences"
        
        # Test full integration
        full_result = await self.enhanced_manager.process_message(
            phone_number="+237690000888",
            message=matching_message,
            media_url=None,
            db=next(get_db())
        )
        
        print(f"✓ Full Integration:")
        print(f"  - Response: {full_result['response'][:100]}...")
        print(f"  - State: {full_result['state']}")
        print(f"  - Provider Integration: {'prestataire' in full_result['response'].lower()}")
        
        assert "prestataire" in full_result["response"].lower(), "Should mention providers"

async def main():
    """Run the multi-LLM conversational AI test suite"""
    test_suite = MultiLLMConversationalTestSuite()
    await test_suite.run_complete_test_suite()

if __name__ == "__main__":
    import sys
    import os
    
    # Add project root to Python path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Run the test suite
    asyncio.run(main())