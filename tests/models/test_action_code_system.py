"""
Test Suite for Action Code System - Agent-LLM Communication
Comprehensive tests for 99% automation system
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database_models import Base, User, ServiceRequest, Conversation
from app.models.action_codes import (
    ActionCode, LLMRequest, LLMResponse, ConversationState, 
    ActionResult, ActionCodeValidator
)
from app.services.code_executor import CodeExecutor
from app.services.enhanced_conversation_manager_v2 import EnhancedConversationManagerV2
from app.database import get_db


class TestActionCodeSystem:
    """Test suite for action code system"""
    
    @pytest.fixture
    def db_session(self):
        """Create test database session"""
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def sample_user(self, db_session):
        """Create sample user for testing"""
        user = User(
            whatsapp_id="237691924172",
            phone_number="237691924172",
            name="Test User",
            created_at=datetime.now()
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.fixture
    def code_executor(self):
        """Create code executor instance"""
        return CodeExecutor()
    
    @pytest.fixture
    def conversation_manager(self):
        """Create conversation manager instance"""
        return EnhancedConversationManagerV2()
    
    # === ACTION CODE TESTS ===
    
    def test_action_code_enum_completeness(self):
        """Test that all required action codes are defined"""
        required_codes = [
            "COLLECTE_BESOIN", "COLLECTE_LOCALISATION", "COLLECTE_DESCRIPTION",
            "COLLECTE_DELAI", "COLLECTE_URGENCE", "COLLECTE_CONTACT",
            "VALIDATE_SERVICE", "VALIDATE_COMPLETE",
            "CREATE_SERVICE", "SEARCH_PROVIDERS", "NOTIFY_PROVIDERS",
            "INFO_GENERALE", "INFO_TARIFS", "INFO_SERVICES",
            "STATUS_CHECK", "CANCEL_SERVICE", "MODIFY_SERVICE",
            "CLARIFICATION", "ESCALATE_HUMAN", "ERROR_HANDLING"
        ]
        
        for code in required_codes:
            assert hasattr(ActionCode, code), f"Missing action code: {code}"
    
    def test_action_code_categories(self):
        """Test action code categorization"""
        # Test collection codes
        assert ActionCode.get_category(ActionCode.COLLECTE_BESOIN) == "COLLECTION"
        assert ActionCode.get_category(ActionCode.COLLECTE_LOCALISATION) == "COLLECTION"
        
        # Test validation codes
        assert ActionCode.get_category(ActionCode.VALIDATE_SERVICE) == "VALIDATION"
        assert ActionCode.get_category(ActionCode.VALIDATE_COMPLETE) == "VALIDATION"
        
        # Test action codes
        assert ActionCode.get_category(ActionCode.CREATE_SERVICE) == "ACTION"
        assert ActionCode.get_category(ActionCode.SEARCH_PROVIDERS) == "ACTION"
        
        # Test information codes
        assert ActionCode.get_category(ActionCode.INFO_GENERALE) == "INFORMATION"
        assert ActionCode.get_category(ActionCode.INFO_TARIFS) == "INFORMATION"
        
        # Test escalation codes
        assert ActionCode.get_category(ActionCode.ESCALATE_HUMAN) == "ESCALATION"
    
    def test_action_code_descriptions(self):
        """Test action code descriptions"""
        description = ActionCode.get_description(ActionCode.COLLECTE_BESOIN)
        assert "besoin initial" in description.lower()
        
        description = ActionCode.get_description(ActionCode.CREATE_SERVICE)
        assert "créer" in description.lower()
        assert "service" in description.lower()
    
    def test_action_code_validation(self):
        """Test action code validation"""
        # Valid codes
        assert ActionCode.is_valid_code("COLLECTE_BESOIN") == True
        assert ActionCode.is_valid_code("CREATE_SERVICE") == True
        
        # Invalid codes
        assert ActionCode.is_valid_code("INVALID_CODE") == False
        assert ActionCode.is_valid_code("") == False
        assert ActionCode.is_valid_code(None) == False
    
    def test_codes_by_category(self):
        """Test getting codes by category"""
        collection_codes = ActionCode.get_codes_by_category("COLLECTION")
        assert ActionCode.COLLECTE_BESOIN in collection_codes
        assert ActionCode.COLLECTE_LOCALISATION in collection_codes
        assert ActionCode.CREATE_SERVICE not in collection_codes
        
        validation_codes = ActionCode.get_codes_by_category("VALIDATION")
        assert ActionCode.VALIDATE_SERVICE in validation_codes
        assert ActionCode.VALIDATE_COMPLETE in validation_codes
        assert ActionCode.COLLECTE_BESOIN not in validation_codes
    
    # === LLM REQUEST/RESPONSE TESTS ===
    
    def test_llm_request_creation(self):
        """Test LLM request creation"""
        session_context = {
            "user_id": "237691924172",
            "conversation_state": ConversationState.COLLECTING,
            "session_data": {"service_type": "plomberie"}
        }
        
        llm_request = LLMRequest(
            message="J'ai une fuite d'eau",
            user_id="237691924172",
            session_context=session_context,
            dynamic_context={"current_time": datetime.now().isoformat()},
            conversation_history=[],
            current_state=ConversationState.COLLECTING,
            timestamp=datetime.now()
        )
        
        assert llm_request.message == "J'ai une fuite d'eau"
        assert llm_request.user_id == "237691924172"
        assert llm_request.current_state == ConversationState.COLLECTING
        
        # Test dict conversion
        request_dict = llm_request.to_dict()
        assert "message" in request_dict
        assert "user_id" in request_dict
        assert "session_context" in request_dict
    
    def test_llm_response_creation(self):
        """Test LLM response creation"""
        llm_response = LLMResponse(
            action_code=ActionCode.COLLECTE_LOCALISATION,
            client_message="Où se trouve le problème exactement ?",
            extracted_data={"service_type": "plomberie"},
            session_update={"collection_phase": "location"},
            next_state=ConversationState.COLLECTING,
            confidence=0.95,
            metadata={"reasoning": "Location needed for plumbing service"}
        )
        
        assert llm_response.action_code == ActionCode.COLLECTE_LOCALISATION
        assert llm_response.confidence == 0.95
        assert llm_response.next_state == ConversationState.COLLECTING
        
        # Test dict conversion
        response_dict = llm_response.to_dict()
        assert response_dict["action_code"] == "COLLECTE_LOCALISATION"
        assert response_dict["confidence"] == 0.95
        
        # Test from_dict
        recreated = LLMResponse.from_dict(response_dict)
        assert recreated.action_code == ActionCode.COLLECTE_LOCALISATION
        assert recreated.confidence == 0.95
    
    def test_llm_response_validation(self):
        """Test LLM response validation"""
        # Valid response
        valid_response = {
            "action_code": "COLLECTE_BESOIN",
            "client_message": "Quel est votre problème ?",
            "extracted_data": {},
            "session_update": {},
            "next_state": "COLLECTING",
            "confidence": 0.9,
            "metadata": {}
        }
        
        is_valid, error = ActionCodeValidator.validate_llm_response(valid_response)
        assert is_valid == True
        assert error == ""
        
        # Invalid response - missing field
        invalid_response = {
            "action_code": "COLLECTE_BESOIN",
            "client_message": "Test",
            # Missing required fields
        }
        
        is_valid, error = ActionCodeValidator.validate_llm_response(invalid_response)
        assert is_valid == False
        assert "manquant" in error.lower()
        
        # Invalid response - invalid action code
        invalid_code_response = {
            "action_code": "INVALID_CODE",
            "client_message": "Test",
            "extracted_data": {},
            "session_update": {},
            "next_state": "COLLECTING",
            "confidence": 0.9,
            "metadata": {}
        }
        
        is_valid, error = ActionCodeValidator.validate_llm_response(invalid_code_response)
        assert is_valid == False
        assert "invalide" in error.lower()
    
    def test_fallback_actions(self):
        """Test fallback action selection"""
        assert ActionCodeValidator.get_fallback_action("invalid_code") == ActionCode.ERROR_HANDLING
        assert ActionCodeValidator.get_fallback_action("validation_error") == ActionCode.ERROR_VALIDATION
        assert ActionCodeValidator.get_fallback_action("unclear_intent") == ActionCode.CLARIFICATION
        assert ActionCodeValidator.get_fallback_action("escalation") == ActionCode.ESCALATE_HUMAN
    
    # === CODE EXECUTOR TESTS ===
    
    @pytest.mark.asyncio
    async def test_code_executor_initialization(self, code_executor):
        """Test code executor initialization"""
        assert code_executor is not None
        assert hasattr(code_executor, "execution_stats")
        assert code_executor.execution_stats["total_executions"] == 0
    
    @pytest.mark.asyncio
    async def test_collect_service_need_execution(self, code_executor, db_session, sample_user):
        """Test collect service need action execution"""
        llm_response = LLMResponse(
            action_code=ActionCode.COLLECTE_BESOIN,
            client_message="Quel est votre problème ?",
            extracted_data={"service_type": "plomberie", "service_hint": "fuite"},
            session_update={"collection_phase": "service_need"},
            next_state=ConversationState.COLLECTING,
            confidence=0.9,
            metadata={}
        )
        
        session_context = {}
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, session_context, db_session
        )
        
        assert result.success == True
        assert result.action_code == ActionCode.COLLECTE_BESOIN
        assert result.result_data["message_sent"] == True
        assert result.execution_time is not None
    
    @pytest.mark.asyncio
    async def test_collect_location_execution(self, code_executor, db_session, sample_user):
        """Test collect location action execution"""
        llm_response = LLMResponse(
            action_code=ActionCode.COLLECTE_LOCALISATION,
            client_message="Où se trouve le problème ?",
            extracted_data={"location": "Bonamoussadi, Douala"},
            session_update={"collection_phase": "location"},
            next_state=ConversationState.COLLECTING,
            confidence=0.9,
            metadata={}
        )
        
        session_context = {}
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, session_context, db_session
        )
        
        assert result.success == True
        assert result.action_code == ActionCode.COLLECTE_LOCALISATION
        assert "bonamoussadi" in result.result_data["location"]
    
    @pytest.mark.asyncio
    async def test_collect_location_coverage_error(self, code_executor, db_session, sample_user):
        """Test location collection with coverage error"""
        llm_response = LLMResponse(
            action_code=ActionCode.COLLECTE_LOCALISATION,
            client_message="Où se trouve le problème ?",
            extracted_data={"location": "Yaoundé"},  # Outside coverage
            session_update={"collection_phase": "location"},
            next_state=ConversationState.COLLECTING,
            confidence=0.9,
            metadata={}
        )
        
        session_context = {}
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, session_context, db_session
        )
        
        assert result.success == False
        assert result.result_data["coverage_error"] == True
        assert "non couverte" in result.error_message
    
    @pytest.mark.asyncio
    async def test_create_service_execution(self, code_executor, db_session, sample_user):
        """Test service creation execution"""
        llm_response = LLMResponse(
            action_code=ActionCode.CREATE_SERVICE,
            client_message="Je crée votre demande...",
            extracted_data={},
            session_update={},
            next_state=ConversationState.PROCESSING,
            confidence=0.95,
            metadata={}
        )
        
        session_context = {
            "service_type": "plomberie",
            "location": "Bonamoussadi, Douala",
            "description": "Fuite d'eau sous l'évier",
            "urgency": "normal"
        }
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, session_context, db_session
        )
        
        assert result.success == True
        assert result.action_code == ActionCode.CREATE_SERVICE
        assert "service_id" in result.result_data
        assert result.result_data["status"] == "PENDING"
        
        # Verify service was created in database
        service = db_session.query(ServiceRequest).filter(
            ServiceRequest.id == result.result_data["service_id"]
        ).first()
        assert service is not None
        assert service.service_type == "plomberie"
        assert service.location == "Bonamoussadi, Douala"
    
    @pytest.mark.asyncio
    async def test_validation_execution(self, code_executor, db_session, sample_user):
        """Test validation execution"""
        llm_response = LLMResponse(
            action_code=ActionCode.VALIDATE_SERVICE,
            client_message="Je valide votre demande...",
            extracted_data={},
            session_update={},
            next_state=ConversationState.VALIDATING,
            confidence=0.9,
            metadata={}
        )
        
        # Complete session context
        session_context = {
            "service_type": "plomberie",
            "location": "Bonamoussadi, Douala",
            "description": "Fuite d'eau sous l'évier"
        }
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, session_context, db_session
        )
        
        assert result.success == True
        assert result.result_data["validation_passed"] == True
        
        # Test with missing fields
        incomplete_context = {
            "service_type": "plomberie",
            # Missing location and description
        }
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, incomplete_context, db_session
        )
        
        assert result.success == False
        assert "missing_fields" in result.result_data
        assert len(result.result_data["missing_fields"]) > 0
    
    @pytest.mark.asyncio
    async def test_information_actions(self, code_executor, db_session, sample_user):
        """Test information providing actions"""
        # Test general info
        llm_response = LLMResponse(
            action_code=ActionCode.INFO_GENERALE,
            client_message="Voici les informations...",
            extracted_data={"info_type": "general"},
            session_update={},
            next_state=ConversationState.COLLECTING,
            confidence=0.9,
            metadata={}
        )
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, {}, db_session
        )
        
        assert result.success == True
        assert "app_name" in result.result_data
        assert "services" in result.result_data
        assert "coverage_area" in result.result_data
        
        # Test pricing info
        llm_response.action_code = ActionCode.INFO_TARIFS
        llm_response.extracted_data = {"service_type": "plomberie"}
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, {}, db_session
        )
        
        assert result.success == True
        assert "min" in result.result_data or "all_pricing" in result.result_data
    
    @pytest.mark.asyncio
    async def test_error_handling_actions(self, code_executor, db_session, sample_user):
        """Test error handling actions"""
        llm_response = LLMResponse(
            action_code=ActionCode.ERROR_HANDLING,
            client_message="Une erreur s'est produite...",
            extracted_data={"error_type": "system_error"},
            session_update={},
            next_state=ConversationState.ERROR,
            confidence=0.7,
            metadata={}
        )
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, {}, db_session
        )
        
        assert result.success == True
        assert result.result_data["error_handled"] == True
        assert result.result_data["error_type"] == "system_error"
        
        # Test clarification
        llm_response.action_code = ActionCode.CLARIFICATION
        llm_response.extracted_data = {"clarification_type": "service_type"}
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, {}, db_session
        )
        
        assert result.success == True
        assert result.result_data["clarification_requested"] == True
        
        # Test escalation
        llm_response.action_code = ActionCode.ESCALATE_HUMAN
        llm_response.extracted_data = {"escalation_reason": "complex_technical_issue"}
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, {}, db_session
        )
        
        assert result.success == True
        assert result.result_data["escalated"] == True
        assert result.result_data["escalation_reason"] == "complex_technical_issue"
    
    @pytest.mark.asyncio
    async def test_invalid_action_code(self, code_executor, db_session, sample_user):
        """Test handling of invalid action codes"""
        # Create response with valid enum but no implementation
        llm_response = LLMResponse(
            action_code=ActionCode.FLOW_PAUSE,  # Valid enum but no method
            client_message="Pause...",
            extracted_data={},
            session_update={},
            next_state=ConversationState.PAUSED,
            confidence=0.8,
            metadata={}
        )
        
        result = await code_executor.execute_action(
            llm_response, sample_user.phone_number, {}, db_session
        )
        
        assert result.success == False
        assert "non implémentée" in result.error_message
    
    def test_execution_stats(self, code_executor):
        """Test execution statistics tracking"""
        stats = code_executor.get_execution_stats()
        
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        assert "success_rate" in stats
        assert "average_execution_time" in stats
    
    # === CONVERSATION MANAGER TESTS ===
    
    @pytest.mark.asyncio
    async def test_conversation_manager_initialization(self, conversation_manager):
        """Test conversation manager initialization"""
        assert conversation_manager is not None
        assert hasattr(conversation_manager, "active_sessions")
        assert hasattr(conversation_manager, "conversation_stats")
        assert conversation_manager.conversation_stats["total_conversations"] == 0
    
    @pytest.mark.asyncio
    async def test_session_creation(self, conversation_manager, db_session):
        """Test session creation and management"""
        phone_number = "237691924172"
        
        # Create session
        session = conversation_manager.get_or_create_session(phone_number, db_session)
        
        assert session is not None
        assert session["conversation_state"] == ConversationState.INITIAL
        assert session["turn_count"] == 1
        assert "session_data" in session
        
        # Verify user was created
        user = db_session.query(User).filter(User.phone_number == phone_number).first()
        assert user is not None
        assert user.phone_number == phone_number
        
        # Test existing session
        session2 = conversation_manager.get_or_create_session(phone_number, db_session)
        assert session2["turn_count"] == 2  # Should increment
    
    @pytest.mark.asyncio
    async def test_llm_request_creation(self, conversation_manager, db_session, sample_user):
        """Test LLM request creation"""
        phone_number = sample_user.phone_number
        message = "J'ai un problème de plomberie"
        
        session_context = conversation_manager.get_or_create_session(phone_number, db_session)
        
        llm_request = conversation_manager.create_llm_request(
            phone_number, message, session_context, db_session
        )
        
        assert llm_request.message == message
        assert llm_request.user_id == phone_number
        assert llm_request.current_state == ConversationState.INITIAL
        assert "available_services" in llm_request.dynamic_context
        assert "coverage_area" in llm_request.dynamic_context
    
    @pytest.mark.asyncio
    async def test_structured_prompt_creation(self, conversation_manager, db_session, sample_user):
        """Test structured prompt creation"""
        phone_number = sample_user.phone_number
        message = "J'ai une fuite d'eau"
        
        session_context = conversation_manager.get_or_create_session(phone_number, db_session)
        llm_request = conversation_manager.create_llm_request(
            phone_number, message, session_context, db_session
        )
        
        prompt = conversation_manager.create_structured_prompt(llm_request)
        
        assert "SYSTÈME DE COMMUNICATION AGENT-LLM" in prompt
        assert "COLLECTE_BESOIN" in prompt
        assert "CREATE_SERVICE" in prompt
        assert "ESCALATE_HUMAN" in prompt
        assert "FORMAT JSON" in prompt
        assert message in prompt
    
    @pytest.mark.asyncio
    async def test_response_parsing(self, conversation_manager, db_session, sample_user):
        """Test LLM response parsing"""
        phone_number = sample_user.phone_number
        session_context = conversation_manager.get_or_create_session(phone_number, db_session)
        llm_request = conversation_manager.create_llm_request(
            phone_number, "Test message", session_context, db_session
        )
        
        # Test valid JSON response
        json_response = '''
        {
            "action_code": "COLLECTE_LOCALISATION",
            "client_message": "Où se trouve le problème ?",
            "extracted_data": {"service_type": "plomberie"},
            "session_update": {"phase": "location"},
            "next_state": "COLLECTING",
            "confidence": 0.9,
            "metadata": {}
        }
        '''
        
        parsed = conversation_manager.parse_llm_response(json_response, llm_request)
        
        assert parsed.action_code == ActionCode.COLLECTE_LOCALISATION
        assert parsed.confidence == 0.9
        assert parsed.next_state == ConversationState.COLLECTING
        
        # Test invalid JSON response
        invalid_response = "Simple text response without JSON"
        
        parsed = conversation_manager.parse_llm_response(invalid_response, llm_request)
        
        assert parsed.action_code in [ActionCode.COLLECTE_BESOIN, ActionCode.CLARIFICATION]
        assert parsed.client_message == invalid_response
    
    @pytest.mark.asyncio
    async def test_fallback_response_creation(self, conversation_manager):
        """Test fallback response creation"""
        session_context = {"user_id": "test"}
        
        fallback = conversation_manager.create_fallback_response("validation_error", session_context)
        
        assert fallback.action_code == ActionCode.ERROR_VALIDATION
        assert fallback.next_state == ConversationState.ERROR
        assert fallback.confidence == 0.5
        assert fallback.metadata["fallback_response"] == True
    
    @pytest.mark.asyncio
    async def test_session_context_update(self, conversation_manager, db_session, sample_user):
        """Test session context updates"""
        phone_number = sample_user.phone_number
        
        # Create session
        conversation_manager.get_or_create_session(phone_number, db_session)
        
        llm_response = LLMResponse(
            action_code=ActionCode.COLLECTE_LOCALISATION,
            client_message="Test",
            extracted_data={"service_type": "plomberie"},
            session_update={"collection_phase": "location"},
            next_state=ConversationState.COLLECTING,
            confidence=0.9,
            metadata={}
        )
        
        action_result = ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_LOCALISATION,
            result_data={"location_validated": True}
        )
        
        conversation_manager.update_session_context(
            phone_number, llm_response, action_result, db_session
        )
        
        session = conversation_manager.active_sessions[phone_number]
        assert session["conversation_state"] == ConversationState.COLLECTING
        assert session["session_data"]["service_type"] == "plomberie"
        assert session["session_data"]["collection_phase"] == "location"
        assert session["session_data"]["location_validated"] == True
    
    @pytest.mark.asyncio
    async def test_conversation_logging(self, conversation_manager, db_session, sample_user):
        """Test conversation interaction logging"""
        phone_number = sample_user.phone_number
        message = "J'ai un problème de plomberie"
        
        llm_response = LLMResponse(
            action_code=ActionCode.COLLECTE_LOCALISATION,
            client_message="Où se trouve le problème ?",
            extracted_data={"service_type": "plomberie"},
            session_update={},
            next_state=ConversationState.COLLECTING,
            confidence=0.9,
            metadata={}
        )
        
        action_result = ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_LOCALISATION,
            result_data={"location_validated": True},
            execution_time=0.5
        )
        
        await conversation_manager.log_conversation_interaction(
            phone_number, message, llm_response, action_result, db_session
        )
        
        # Verify log was created
        conversation_log = db_session.query(Conversation).filter(
            Conversation.user_id == sample_user.id
        ).first()
        
        assert conversation_log is not None
        assert conversation_log.message_content == message
        assert conversation_log.ai_response == llm_response.client_message
        assert conversation_log.action_code == ActionCode.COLLECTE_LOCALISATION.value
        assert conversation_log.confidence_score == 0.9
        assert conversation_log.action_success == True
        assert conversation_log.execution_time == 0.5
    
    @pytest.mark.asyncio
    async def test_conversation_history_retrieval(self, conversation_manager, db_session, sample_user):
        """Test conversation history retrieval"""
        phone_number = sample_user.phone_number
        
        # Create conversation history
        conversations = [
            Conversation(
                user_id=sample_user.id,
                message_content="Premier message",
                ai_response="Première réponse",
                action_code="COLLECTE_BESOIN",
                confidence_score=0.8,
                created_at=datetime.now()
            ),
            Conversation(
                user_id=sample_user.id,
                message_content="Deuxième message",
                ai_response="Deuxième réponse",
                action_code="COLLECTE_LOCALISATION",
                confidence_score=0.9,
                created_at=datetime.now()
            )
        ]
        
        for conv in conversations:
            db_session.add(conv)
        db_session.commit()
        
        # Retrieve history
        history = conversation_manager.get_conversation_history(phone_number, db_session)
        
        assert len(history) == 2
        assert history[0]["message"] == "Premier message"
        assert history[1]["message"] == "Deuxième message"
        assert history[0]["action_code"] == "COLLECTE_BESOIN"
        assert history[1]["action_code"] == "COLLECTE_LOCALISATION"
    
    @pytest.mark.asyncio
    async def test_conversation_stats_update(self, conversation_manager):
        """Test conversation statistics updates"""
        # Test successful resolution
        llm_response = LLMResponse(
            action_code=ActionCode.CREATE_SERVICE,
            client_message="Service créé",
            extracted_data={},
            session_update={},
            next_state=ConversationState.PROCESSING,
            confidence=0.9,
            metadata={}
        )
        
        action_result = ActionResult(
            success=True,
            action_code=ActionCode.CREATE_SERVICE,
            result_data={}
        )
        
        conversation_manager.update_conversation_stats(llm_response, action_result)
        
        assert conversation_manager.conversation_stats["automated_resolutions"] == 1
        
        # Test escalation
        llm_response.action_code = ActionCode.ESCALATE_HUMAN
        action_result.action_code = ActionCode.ESCALATE_HUMAN
        
        conversation_manager.update_conversation_stats(llm_response, action_result)
        
        assert conversation_manager.conversation_stats["human_escalations"] == 1
    
    def test_session_cleanup(self, conversation_manager, db_session):
        """Test expired session cleanup"""
        phone_number = "237691924172"
        
        # Create session
        session = conversation_manager.get_or_create_session(phone_number, db_session)
        
        # Manually set old timestamp
        from datetime import timedelta
        session["last_activity"] = datetime.now() - timedelta(hours=2)
        
        # Cleanup
        conversation_manager.cleanup_expired_sessions(max_inactive_hours=1)
        
        # Session should be removed
        assert phone_number not in conversation_manager.active_sessions
    
    def test_conversation_stats_retrieval(self, conversation_manager):
        """Test conversation statistics retrieval"""
        stats = conversation_manager.get_conversation_stats()
        
        assert "total_conversations" in stats
        assert "automated_resolutions" in stats
        assert "human_escalations" in stats
        assert "automation_rate" in stats
        assert "success_rate" in stats
        assert "active_sessions" in stats
        assert "code_executor_stats" in stats
    
    # === INTEGRATION TESTS ===
    
    @pytest.mark.asyncio
    async def test_complete_service_creation_flow(self, conversation_manager, db_session):
        """Test complete service creation flow"""
        phone_number = "237691924172"
        
        # Mock AI service
        with patch.object(conversation_manager.ai_service, 'process_message_with_context') as mock_ai:
            mock_ai.return_value = '''
            {
                "action_code": "CREATE_SERVICE",
                "client_message": "Je crée votre demande de service. Un prestataire sera contacté sous peu.",
                "extracted_data": {},
                "session_update": {"status": "service_created"},
                "next_state": "PROCESSING",
                "confidence": 0.95,
                "metadata": {"ready_for_creation": true}
            }
            '''
            
            # Set up complete session context
            session = conversation_manager.get_or_create_session(phone_number, db_session)
            session["session_data"] = {
                "service_type": "plomberie",
                "location": "Bonamoussadi, Douala",
                "description": "Fuite d'eau sous l'évier",
                "urgency": "normal"
            }
            
            # Process message
            response = await conversation_manager.process_message(
                phone_number, "Je confirme ma demande", db_session
            )
            
            assert "prestataire sera contacté" in response
            
            # Verify service was created
            user = db_session.query(User).filter(User.phone_number == phone_number).first()
            service = db_session.query(ServiceRequest).filter(
                ServiceRequest.user_id == user.id
            ).first()
            
            assert service is not None
            assert service.service_type == "plomberie"
            assert service.location == "Bonamoussadi, Douala"
    
    @pytest.mark.asyncio
    async def test_escalation_flow(self, conversation_manager, db_session):
        """Test escalation to human flow"""
        phone_number = "237691924172"
        
        # Mock AI service to return escalation
        with patch.object(conversation_manager.ai_service, 'process_message_with_context') as mock_ai:
            mock_ai.return_value = '''
            {
                "action_code": "ESCALATE_HUMAN",
                "client_message": "Je vous transfère vers un agent humain qui pourra mieux vous aider.",
                "extracted_data": {"escalation_reason": "complex_technical_issue"},
                "session_update": {"escalated": true},
                "next_state": "ESCALATED",
                "confidence": 0.9,
                "metadata": {"escalation_reason": "complex_technical_issue"}
            }
            '''
            
            # Process message
            response = await conversation_manager.process_message(
                phone_number, "Je ne comprends pas votre système", db_session
            )
            
            assert "agent humain" in response
            
            # Verify escalation was logged
            user = db_session.query(User).filter(User.phone_number == phone_number).first()
            conversation_log = db_session.query(Conversation).filter(
                Conversation.user_id == user.id
            ).first()
            
            assert conversation_log.action_code == "ESCALATE_HUMAN"
            assert conversation_log.conversation_state == "ESCALATED"
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, conversation_manager, db_session):
        """Test error handling and recovery"""
        phone_number = "237691924172"
        
        # Mock AI service to raise exception
        with patch.object(conversation_manager.ai_service, 'process_message_with_context') as mock_ai:
            mock_ai.side_effect = Exception("AI service error")
            
            # Process message
            response = await conversation_manager.process_message(
                phone_number, "Test message", db_session
            )
            
            assert "erreur technique" in response.lower()
            
            # Verify error was logged
            user = db_session.query(User).filter(User.phone_number == phone_number).first()
            conversation_log = db_session.query(Conversation).filter(
                Conversation.user_id == user.id
            ).first()
            
            assert conversation_log.action_code == "ERROR_HANDLING"
    
    @pytest.mark.asyncio
    async def test_automation_rate_calculation(self, conversation_manager, db_session):
        """Test automation rate calculation"""
        phone_number = "237691924172"
        
        # Simulate multiple conversations
        for i in range(10):
            # Most should be automated
            with patch.object(conversation_manager.ai_service, 'process_message_with_context') as mock_ai:
                if i < 9:  # 9 out of 10 automated
                    mock_ai.return_value = '''
                    {
                        "action_code": "COLLECTE_BESOIN",
                        "client_message": "Quel est votre problème ?",
                        "extracted_data": {},
                        "session_update": {},
                        "next_state": "COLLECTING",
                        "confidence": 0.9,
                        "metadata": {}
                    }
                    '''
                else:  # 1 out of 10 escalated
                    mock_ai.return_value = '''
                    {
                        "action_code": "ESCALATE_HUMAN",
                        "client_message": "Je vous transfère vers un agent.",
                        "extracted_data": {},
                        "session_update": {},
                        "next_state": "ESCALATED",
                        "confidence": 0.9,
                        "metadata": {}
                    }
                    '''
                
                await conversation_manager.process_message(
                    phone_number, f"Message {i}", db_session
                )
        
        # Check automation rate
        stats = conversation_manager.get_conversation_stats()
        assert stats["automation_rate"] == 90.0  # 9/10 = 90%
        assert stats["total_conversations"] == 10
        assert stats["human_escalations"] == 1


@pytest.mark.asyncio
async def test_performance_benchmarks():
    """Test performance benchmarks for the system"""
    conversation_manager = EnhancedConversationManagerV2()
    
    # Create test database
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        # Create test user
        user = User(
            whatsapp_id="237691924172",
            phone_number="237691924172",
            name="Performance Test User"
        )
        db.add(user)
        db.commit()
        
        # Benchmark message processing
        import time
        
        start_time = time.time()
        
        # Mock AI service for consistent timing
        with patch.object(conversation_manager.ai_service, 'process_message_with_context') as mock_ai:
            mock_ai.return_value = '''
            {
                "action_code": "COLLECTE_BESOIN",
                "client_message": "Quel est votre problème ?",
                "extracted_data": {"service_type": "plomberie"},
                "session_update": {},
                "next_state": "COLLECTING",
                "confidence": 0.9,
                "metadata": {}
            }
            '''
            
            # Process 100 messages
            for i in range(100):
                await conversation_manager.process_message(
                    "237691924172", f"Message {i}", db
                )
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 100
        
        # Performance assertions
        assert avg_time < 0.1, f"Average processing time too high: {avg_time:.3f}s"
        assert total_time < 10, f"Total processing time too high: {total_time:.3f}s"
        
        print(f"Performance benchmark: {avg_time:.3f}s average per message")
        print(f"Total time for 100 messages: {total_time:.3f}s")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("Running Action Code System Tests...")
    pytest.main([__file__, "-v"])