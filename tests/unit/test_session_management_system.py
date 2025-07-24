#!/usr/bin/env python3
"""
Test Suite for Session Management System
Comprehensive testing of conversation session management with states and persistence
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database_models import Base, User, ConversationSession as DBSession, Conversation
from app.models.conversation_session import (
    ConversationSession, ConversationState, SessionPhase, ConversationMessage,
    CollectedData, SessionMetrics, TransitionRule
)
from app.services.session_manager import SessionManager
from app.services.enhanced_conversation_manager_v3 import EnhancedConversationManagerV3


class TestSessionManagementSystem:
    """Test suite for session management system"""
    
    @pytest.fixture
    def setup_database(self):
        """Setup test database"""
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        return TestingSessionLocal
    
    @pytest.fixture
    def sample_user(self, setup_database):
        """Create sample user"""
        db = setup_database()
        user = User(
            whatsapp_id="237691924172",
            phone_number="237691924172",
            name="Test User Cameroon"
        )
        db.add(user)
        db.commit()
        return user, db
    
    @pytest.mark.asyncio
    async def test_conversation_session_creation(self, sample_user):
        """Test conversation session creation"""
        user, db = sample_user
        
        # Create session
        session = ConversationSession(
            session_id="test_session_001",
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.INITIAL
        )
        
        # Verify session properties
        assert session.session_id == "test_session_001"
        assert session.user_id == str(user.id)
        assert session.phone_number == user.phone_number
        assert session.current_state == ConversationState.INITIAL
        assert session.previous_state is None
        assert len(session.conversation_history) == 0
        assert session.collected_data.collection_progress == 0.0
        
        print("✓ Conversation session creation test passed")
    
    @pytest.mark.asyncio
    async def test_state_transitions(self, sample_user):
        """Test state transitions and validation"""
        user, db = sample_user
        
        session = ConversationSession(
            session_id="test_session_002",
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.INITIAL
        )
        
        # Test valid transitions
        assert session.transition_to(ConversationState.COLLECTING, "start_collection")
        assert session.current_state == ConversationState.COLLECTING
        assert session.previous_state == ConversationState.INITIAL
        
        assert session.transition_to(ConversationState.VALIDATING, "data_complete")
        assert session.current_state == ConversationState.VALIDATING
        
        assert session.transition_to(ConversationState.CONFIRMING, "validation_passed")
        assert session.current_state == ConversationState.CONFIRMING
        
        assert session.transition_to(ConversationState.PROCESSING, "user_confirmed")
        assert session.current_state == ConversationState.PROCESSING
        
        assert session.transition_to(ConversationState.COMPLETED, "service_completed")
        assert session.current_state == ConversationState.COMPLETED
        
        # Test invalid transition (from terminal state)
        assert not session.transition_to(ConversationState.COLLECTING, "invalid_transition")
        assert session.current_state == ConversationState.COMPLETED
        
        print("✓ State transition validation test passed")
    
    @pytest.mark.asyncio
    async def test_rollback_functionality(self, sample_user):
        """Test state rollback functionality"""
        user, db = sample_user
        
        session = ConversationSession(
            session_id="test_session_003",
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.INITIAL
        )
        
        # Transition to collecting
        session.transition_to(ConversationState.COLLECTING, "start_collection")
        
        # Transition to validating
        session.transition_to(ConversationState.VALIDATING, "data_complete")
        
        # Rollback to previous state
        assert session.rollback_state("validation_error")
        assert session.current_state == ConversationState.COLLECTING
        assert session.previous_state == ConversationState.VALIDATING
        
        # Rollback again
        assert session.rollback_state("need_more_data")
        assert session.current_state == ConversationState.VALIDATING
        
        print("✓ State rollback functionality test passed")
    
    @pytest.mark.asyncio
    async def test_data_collection(self, sample_user):
        """Test data collection and progress tracking"""
        user, db = sample_user
        
        session = ConversationSession(
            session_id="test_session_004",
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.COLLECTING
        )
        
        # Update collected data
        session.update_collected_data("service_type", "plomberie", 0.9)
        session.update_collected_data("location", "Bonamoussadi, Douala", 0.95)
        session.update_collected_data("description", "Fuite d'eau sous l'évier", 0.8)
        
        # Check data completeness
        assert session.collected_data.service_type == "plomberie"
        assert session.collected_data.location == "Bonamoussadi, Douala"
        assert session.collected_data.description == "Fuite d'eau sous l'évier"
        assert session.collected_data.service_confidence == 0.9
        assert session.collected_data.location_confidence == 0.95
        
        # Check if data is complete
        assert session.is_data_complete()
        assert session.can_proceed_to_validation()
        
        # Check missing data for incomplete session
        incomplete_session = ConversationSession(
            session_id="incomplete",
            user_id=str(user.id),
            phone_number=user.phone_number
        )
        incomplete_session.update_collected_data("service_type", "plomberie")
        
        missing_fields = incomplete_session.get_missing_data()
        assert "location" in missing_fields
        assert "description" in missing_fields
        assert not incomplete_session.is_data_complete()
        
        print("✓ Data collection and progress tracking test passed")
    
    @pytest.mark.asyncio
    async def test_conversation_history(self, sample_user):
        """Test conversation history management"""
        user, db = sample_user
        
        session = ConversationSession(
            session_id="test_session_005",
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.COLLECTING
        )
        
        # Add messages to conversation
        for i in range(15):  # Add more than max_history_size (10)
            message = ConversationMessage(
                message_type="incoming" if i % 2 == 0 else "outgoing",
                content=f"Message {i}",
                timestamp=datetime.now()
            )
            session.add_message(message)
        
        # Check history size limit
        assert len(session.conversation_history) == session.max_history_size
        
        # Check recent history
        recent_history = session.get_recent_history(limit=5)
        assert len(recent_history) == 5
        
        # Check metrics
        assert session.metrics.total_messages == 15
        assert session.metrics.user_messages == 8  # 0, 2, 4, 6, 8, 10, 12, 14
        assert session.metrics.ai_responses == 7   # 1, 3, 5, 7, 9, 11, 13
        
        print("✓ Conversation history management test passed")
    
    @pytest.mark.asyncio
    async def test_session_expiration(self, sample_user):
        """Test session expiration functionality"""
        user, db = sample_user
        
        session = ConversationSession(
            session_id="test_session_006",
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.COLLECTING
        )
        
        # Check that session is not expired initially
        assert not session.is_expired()
        
        # Manually set expiration to past
        session.expires_at = datetime.now() - timedelta(hours=1)
        assert session.is_expired()
        
        # Test expiration extension
        session.extend_expiration(minutes=120)
        assert not session.is_expired()
        assert session.expires_at > datetime.now()
        
        print("✓ Session expiration functionality test passed")
    
    @pytest.mark.asyncio
    async def test_session_manager_operations(self, sample_user):
        """Test session manager operations"""
        user, db = sample_user
        
        session_manager = SessionManager()
        
        # Test session creation
        session = await session_manager.create_session(
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.INITIAL,
            db=db
        )
        
        assert session.user_id == str(user.id)
        assert session.phone_number == user.phone_number
        assert session.current_state == ConversationState.INITIAL
        
        # Test session retrieval
        retrieved_session = await session_manager.get_session(session.session_id, db)
        assert retrieved_session is not None
        assert retrieved_session.session_id == session.session_id
        
        # Test session update
        session.update_collected_data("service_type", "plomberie", 0.9)
        success = await session_manager.update_session(session, db)
        assert success
        
        # Test state transition
        success = await session_manager.transition_session_state(
            session.session_id, ConversationState.COLLECTING, "start_collection", db
        )
        assert success
        
        # Test message addition
        message = ConversationMessage(
            message_type="incoming",
            content="J'ai un problème de plomberie",
            timestamp=datetime.now()
        )
        success = await session_manager.add_message_to_session(
            session.session_id, message, db
        )
        assert success
        
        # Test data update
        success = await session_manager.update_collected_data(
            session.session_id, "location", "Bonamoussadi", 0.95, db
        )
        assert success
        
        # Test session completion
        success = await session_manager.complete_session(session.session_id, db)
        assert success
        
        # Verify session is completed
        completed_session = await session_manager.get_session(session.session_id, db)
        assert completed_session.current_state == ConversationState.COMPLETED
        
        print("✓ Session manager operations test passed")
    
    @pytest.mark.asyncio
    async def test_session_persistence(self, sample_user):
        """Test session persistence to database"""
        user, db = sample_user
        
        session_manager = SessionManager()
        
        # Create and populate session
        session = await session_manager.create_session(
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.INITIAL,
            db=db
        )
        
        # Add data and transition states
        await session_manager.update_collected_data(
            session.session_id, "service_type", "plomberie", 0.9, db
        )
        await session_manager.update_collected_data(
            session.session_id, "location", "Bonamoussadi", 0.95, db
        )
        await session_manager.transition_session_state(
            session.session_id, ConversationState.COLLECTING, "start_collection", db
        )
        
        # Verify database persistence
        db_session = db.query(DBSession).filter(
            DBSession.session_id == session.session_id
        ).first()
        
        assert db_session is not None
        assert db_session.user_id == user.id
        assert db_session.phone_number == user.phone_number
        assert db_session.current_state == ConversationState.COLLECTING.value
        assert db_session.collected_data is not None
        assert db_session.collected_data["service_type"] == "plomberie"
        assert db_session.collected_data["location"] == "Bonamoussadi"
        
        print("✓ Session persistence test passed")
    
    @pytest.mark.asyncio
    async def test_conversation_manager_integration(self, sample_user):
        """Test conversation manager integration with session management"""
        user, db = sample_user
        
        conversation_manager = EnhancedConversationManagerV3()
        
        # Test initial message processing
        response = await conversation_manager.process_message(
            message="J'ai un problème de plomberie",
            phone_number=user.phone_number,
            user_id=str(user.id),
            db=db
        )
        
        assert response is not None
        assert response.get("response") is not None
        assert response.get("session_id") is not None
        assert response.get("conversation_state") is not None
        
        session_id = response["session_id"]
        
        # Test follow-up message
        response2 = await conversation_manager.process_message(
            message="C'est à Bonamoussadi",
            phone_number=user.phone_number,
            user_id=str(user.id),
            db=db
        )
        
        assert response2 is not None
        assert response2.get("session_id") == session_id  # Same session
        assert response2.get("conversation_state") is not None
        
        # Test session info retrieval
        session_info = await conversation_manager.get_session_info(session_id, db)
        assert session_info is not None
        assert session_info["session_id"] == session_id
        assert session_info["user_id"] == str(user.id)
        
        print("✓ Conversation manager integration test passed")
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, sample_user):
        """Test session cleanup functionality"""
        user, db = sample_user
        
        session_manager = SessionManager()
        
        # Create expired session
        expired_session = await session_manager.create_session(
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.INITIAL,
            db=db
        )
        
        # Manually expire the session
        expired_session.expires_at = datetime.now() - timedelta(hours=1)
        await session_manager.update_session(expired_session, db)
        
        # Create active session
        active_session = await session_manager.create_session(
            user_id=str(user.id),
            phone_number=user.phone_number + "2",
            initial_state=ConversationState.INITIAL,
            db=db
        )
        
        # Run cleanup
        cleaned_count = await session_manager.cleanup_expired_sessions(db)
        assert cleaned_count >= 1
        
        # Verify expired session is marked as expired
        db_expired = db.query(DBSession).filter(
            DBSession.session_id == expired_session.session_id
        ).first()
        assert db_expired.is_expired == True
        
        # Verify active session is still active
        db_active = db.query(DBSession).filter(
            DBSession.session_id == active_session.session_id
        ).first()
        assert db_active.is_expired == False
        
        print("✓ Session cleanup functionality test passed")
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, sample_user):
        """Test performance metrics tracking"""
        user, db = sample_user
        
        session = ConversationSession(
            session_id="test_session_metrics",
            user_id=str(user.id),
            phone_number=user.phone_number,
            initial_state=ConversationState.COLLECTING
        )
        
        # Record some actions
        session.metrics.record_action(success=True, execution_time=0.5)
        session.metrics.record_action(success=True, execution_time=0.3)
        session.metrics.record_action(success=False, execution_time=0.8)
        
        # Check metrics
        assert session.metrics.action_executions == 3
        assert session.metrics.successful_actions == 2
        assert session.metrics.total_response_time == 1.6
        assert session.metrics.average_response_time == 1.6 / 3
        
        # Test automation score calculation
        automation_score = session.metrics.calculate_automation_score()
        assert 0 <= automation_score <= 100
        
        # Test session duration
        session.metrics.end_time = datetime.now()
        duration = session.metrics.get_session_duration()
        assert duration.total_seconds() > 0
        
        print("✓ Performance metrics tracking test passed")
    
    async def run_all_tests(self):
        """Run all session management tests"""
        print("=== SESSION MANAGEMENT SYSTEM TESTS ===\n")
        
        # Setup test database
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = TestingSessionLocal()
        
        # Create test user
        user = User(
            whatsapp_id="237691924172",
            phone_number="237691924172",
            name="Test User Cameroon"
        )
        db.add(user)
        db.commit()
        
        try:
            # Run all tests
            await self.test_conversation_session_creation((user, db))
            await self.test_state_transitions((user, db))
            await self.test_rollback_functionality((user, db))
            await self.test_data_collection((user, db))
            await self.test_conversation_history((user, db))
            await self.test_session_expiration((user, db))
            await self.test_session_manager_operations((user, db))
            await self.test_session_persistence((user, db))
            await self.test_conversation_manager_integration((user, db))
            await self.test_session_cleanup((user, db))
            await self.test_performance_metrics((user, db))
            
            print("\n=== ALL TESTS PASSED ✓ ===")
            print("Session management system is working correctly!")
            
        except Exception as e:
            print(f"\n=== TEST FAILED ✗ ===")
            print(f"Error: {e}")
            raise
        finally:
            db.close()

async def run_session_management_tests():
    """Run comprehensive session management tests"""
    test_suite = TestSessionManagementSystem()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(run_session_management_tests())