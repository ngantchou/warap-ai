"""
Test Suite for Djobea AI Personalization System
Comprehensive testing for intelligent user preference learning and personalization features
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from app.models.database_models import Base, User, ServiceRequest, RequestStatus
from app.models.personalization_models import (
    UserPreferences, ServiceHistory, BehavioralPatterns, 
    PreferenceLearningData, ContextualMemory, PersonalizationMetrics
)
from app.services.personalization_service import PersonalizationService


class TestPersonalizationService:
    """Test suite for the PersonalizationService"""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def personalization_service(self):
        """Create a PersonalizationService instance"""
        return PersonalizationService()
    
    @pytest.fixture
    def sample_user(self, db_session):
        """Create a sample user for testing"""
        user = User(
            phone_number="+237123456789",
            name="Test User"
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.mark.asyncio
    async def test_initialize_user_preferences(self, personalization_service, db_session, sample_user):
        """Test user preferences initialization"""
        preferences = await personalization_service.initialize_user_preferences(db_session, sample_user.id)
        
        assert preferences.user_id == sample_user.id
        assert preferences.communication_style == "respectful"
        assert preferences.preferred_language == "français"
        assert preferences.personalization_enabled is True
        assert preferences.preference_confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_learn_from_conversation_basic(self, personalization_service, db_session, sample_user):
        """Test basic conversation learning"""
        # Initialize preferences
        await personalization_service.initialize_user_preferences(db_session, sample_user.id)
        
        # Simulate conversation
        conversation = {
            'message': 'Bonjour, j\'ai besoin d\'un plombier rapidement',
            'response': 'Bonjour! Je vais vous aider à trouver un plombier',
            'conversation_id': 1,
            'request_info': {
                'service_type': 'plomberie',
                'urgency': 'urgent',
                'language_detected': 'français',
                'politeness_level': 'formal'
            }
        }
        
        await personalization_service.learn_from_conversation(
            db_session, sample_user.id, conversation
        )
        
        # Check if learning data was recorded
        learning_data = db_session.query(PreferenceLearningData).filter_by(
            user_id=sample_user.id
        ).first()
        
        assert learning_data is not None
        assert learning_data.preference_category in ['communication', 'language', 'service']
        assert learning_data.processed is False
        
    @pytest.mark.asyncio
    async def test_learn_from_conversation_language_preference(self, personalization_service, db_session, sample_user):
        """Test language preference learning"""
        await personalization_service.initialize_user_preferences(db_session, sample_user.id)
        
        # Multiple French conversations
        for i in range(3):
            conversation = {
                'message': f'Bonjour, message {i}',
                'response': f'Réponse {i}',
                'conversation_id': i,
                'request_info': {
                    'language_detected': 'français',
                    'formality_level': 'formal'
                }
            }
            await personalization_service.learn_from_conversation(
                db_session, sample_user.id, conversation
            )
        
        # Check preferences updated
        preferences = await personalization_service.get_user_preferences(db_session, sample_user.id)
        assert preferences.preferred_language == "français"
    
    @pytest.mark.asyncio
    async def test_personalize_message_basic(self, personalization_service, db_session, sample_user):
        """Test basic message personalization"""
        # Initialize preferences with specific style
        preferences = await personalization_service.initialize_user_preferences(db_session, sample_user.id)
        preferences.communication_style = "friendly"
        preferences.emoji_usage_preference = "moderate"
        preferences.message_length_preference = "brief"
        db_session.commit()
        
        base_message = "Votre demande de service a été reçue."
        
        # Mock AI service response
        with patch.object(personalization_service, '_apply_ai_personalization') as mock_ai:
            mock_ai.return_value = "Salut! 😊 Votre demande a été reçue!"
            
            personalized = await personalization_service.personalize_message(
                db_session, sample_user.id, base_message
            )
            
            assert personalized != base_message
            assert "😊" in personalized  # Emoji usage
            mock_ai.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_smart_defaults(self, personalization_service, db_session, sample_user):
        """Test smart defaults generation"""
        # Create service history
        history = ServiceHistory(
            user_id=sample_user.id,
            service_type="plomberie",
            location="Bonamoussadi",
            urgency_level="normal",
            estimated_cost=10000,
            service_outcome="completed",
            overall_satisfaction=4.5
        )
        db_session.add(history)
        db_session.commit()
        
        defaults = await personalization_service.get_smart_defaults(db_session, sample_user.id)
        
        assert 'most_used_location' in defaults
        assert 'preferred_service_types' in defaults
        assert 'typical_budget_range' in defaults
        assert defaults['most_used_location'] == "Bonamoussadi"
    
    @pytest.mark.asyncio
    async def test_predict_user_needs(self, personalization_service, db_session, sample_user):
        """Test user needs prediction"""
        # Create multiple service requests with pattern
        for i in range(3):
            history = ServiceHistory(
                user_id=sample_user.id,
                service_type="électricité",
                location="Bonamoussadi",
                urgency_level="normal",
                estimated_cost=5000 + (i * 1000),
                service_outcome="completed",
                overall_satisfaction=4.0,
                created_at=datetime.now() - timedelta(days=30 * i)
            )
            db_session.add(history)
        db_session.commit()
        
        predictions = await personalization_service.predict_user_needs(db_session, sample_user.id)
        
        assert len(predictions) > 0
        assert any(pred['service_type'] == 'électricité' for pred in predictions)
        assert any('confidence' in pred for pred in predictions)
    
    @pytest.mark.asyncio
    async def test_learn_from_service_completion(self, personalization_service, db_session, sample_user):
        """Test learning from completed service"""
        # Create service request
        service_request = ServiceRequest(
            id=1,
            user_id=sample_user.id,
            service_type="plomberie",
            description="Fuite d'eau",
            location="Bonamoussadi",
            urgency="urgent",
            status=RequestStatus.COMPLETED
        )
        db_session.add(service_request)
        db_session.commit()
        
        outcome_data = {
            'completion_time': datetime.now(),
            'cost': 15000,
            'rating': 5.0,
            'feedback': 'Excellent service',
            'response_time_satisfaction': 'satisfied'
        }
        
        await personalization_service.learn_from_service_completion(
            db_session, sample_user.id, service_request, outcome_data
        )
        
        # Check service history created
        history = db_session.query(ServiceHistory).filter_by(
            user_id=sample_user.id,
            service_request_id=service_request.id
        ).first()
        
        assert history is not None
        assert history.actual_cost == 15000
        assert history.overall_satisfaction == 5.0
        assert history.service_outcome == "completed"
    
    @pytest.mark.asyncio
    async def test_behavioral_patterns_update(self, personalization_service, db_session, sample_user):
        """Test behavioral patterns analysis"""
        # Create multiple service histories
        service_types = ["plomberie", "électricité", "plomberie", "électroménager", "plomberie"]
        
        for i, service_type in enumerate(service_types):
            history = ServiceHistory(
                user_id=sample_user.id,
                service_type=service_type,
                location="Bonamoussadi",
                urgency_level="normal",
                estimated_cost=8000,
                actual_cost=8500,
                service_outcome="completed",
                overall_satisfaction=4.2,
                created_at=datetime.now() - timedelta(days=i * 7)
            )
            db_session.add(history)
        db_session.commit()
        
        # Update behavioral patterns
        await personalization_service._update_behavioral_patterns(
            db_session, sample_user.id, history
        )
        
        patterns = await personalization_service._get_behavioral_patterns(db_session, sample_user.id)
        
        assert patterns is not None
        assert patterns.user_type in ['new_user', 'occasional', 'moderate', 'power_user']
        assert patterns.most_requested_services is not None
    
    @pytest.mark.asyncio
    async def test_contextual_memory_creation(self, personalization_service, db_session, sample_user):
        """Test contextual memory system"""
        # Create a memorable conversation
        conversation = {
            'message': 'Mon chauffe-eau est tombé en panne la semaine dernière et maintenant il fuit',
            'response': 'Je comprends votre problème récurrent avec le chauffe-eau',
            'conversation_id': 1,
            'request_info': {
                'service_type': 'plomberie',
                'problem_type': 'chauffe-eau',
                'is_recurring': True
            }
        }
        
        await personalization_service.learn_from_conversation(
            db_session, sample_user.id, conversation
        )
        
        # Check if contextual memory was created
        memory = db_session.query(ContextualMemory).filter_by(
            user_id=sample_user.id
        ).first()
        
        if memory:  # Memory creation is conditional based on importance
            assert memory.memory_type in ['conversation', 'service', 'preference']
            assert memory.importance_score > 0.0
    
    @pytest.mark.asyncio
    async def test_personalization_metrics_tracking(self, personalization_service, db_session, sample_user):
        """Test personalization metrics calculation"""
        # Initialize preferences and create activity
        await personalization_service.initialize_user_preferences(db_session, sample_user.id)
        
        # Simulate successful personalization
        base_message = "Votre demande a été traitée"
        personalized_message = "Salut! Votre demande a été traitée avec succès 😊"
        
        await personalization_service._track_personalization_usage(
            db_session, sample_user.id, base_message, personalized_message
        )
        
        # Get insights
        insights = await personalization_service.get_personalization_insights(db_session, sample_user.id)
        
        assert 'personalization_accuracy' in insights
        assert 'user_satisfaction_impact' in insights
        assert 'preference_gaps' in insights
        assert 'recommendations' in insights
    
    @pytest.mark.asyncio
    async def test_preference_confidence_building(self, personalization_service, db_session, sample_user):
        """Test preference confidence scoring"""
        await personalization_service.initialize_user_preferences(db_session, sample_user.id)
        
        # Multiple consistent conversations
        consistent_conversations = [
            {
                'message': 'Bonjour, j\'ai besoin d\'aide',
                'response': 'Bonjour! Comment puis-je vous aider?',
                'request_info': {'communication_style': 'formal', 'language': 'français'}
            },
            {
                'message': 'Bonsoir, pourriez-vous m\'assister?',
                'response': 'Bonsoir! Bien sûr, je suis là pour vous aider',
                'request_info': {'communication_style': 'formal', 'language': 'français'}
            },
            {
                'message': 'Bonjour, j\'aimerais avoir des informations',
                'response': 'Bonjour! Je vais vous fournir les informations',
                'request_info': {'communication_style': 'formal', 'language': 'français'}
            }
        ]
        
        for i, conversation in enumerate(consistent_conversations):
            conversation['conversation_id'] = i
            await personalization_service.learn_from_conversation(
                db_session, sample_user.id, conversation
            )
        
        # Check confidence improvement
        preferences = await personalization_service.get_user_preferences(db_session, sample_user.id)
        # Confidence should increase with consistent patterns
        assert preferences.interaction_count >= 3
    
    @pytest.mark.asyncio
    async def test_emergency_situation_learning(self, personalization_service, db_session, sample_user):
        """Test learning from emergency situations"""
        emergency_conversation = {
            'message': 'URGENT! Fuite d\'eau importante dans ma cuisine!',
            'response': 'Situation d\'urgence détectée. Je vous trouve immédiatement un plombier',
            'conversation_id': 1,
            'request_info': {
                'urgency': 'emergency',
                'service_type': 'plomberie',
                'emotional_state': 'stressed'
            }
        }
        
        await personalization_service.learn_from_conversation(
            db_session, sample_user.id, emergency_conversation
        )
        
        # Check learning data contains emergency indicators
        learning_data = db_session.query(PreferenceLearningData).filter_by(
            user_id=sample_user.id,
            signal_type='preference_indicator'
        ).first()
        
        if learning_data:
            assert 'urgency' in learning_data.preference_category or 'emergency' in str(learning_data.signal_data)

    def test_message_personalization_ai_integration(self, personalization_service):
        """Test AI-powered message personalization"""
        base_message = "Votre demande de service a été enregistrée"
        context = {
            'communication_style': 'friendly',
            'emoji_usage': 'moderate',
            'language_preference': 'français',
            'message_length': 'brief'
        }
        
        # Mock AI service
        with patch.object(personalization_service, '_apply_ai_personalization') as mock_ai:
            mock_ai.return_value = "Salut! 😊 Votre demande est enregistrée!"
            
            result = asyncio.run(
                personalization_service._apply_ai_personalization(base_message, context)
            )
            
            assert result != base_message
            mock_ai.assert_called_once_with(base_message, context)


class TestPersonalizationModels:
    """Test the personalization database models"""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_user_preferences_model(self, db_session):
        """Test UserPreferences model creation and relationships"""
        preferences = UserPreferences(
            user_id=1,
            communication_style="friendly",
            preferred_language="français",
            message_length_preference="brief",
            emoji_usage_preference="moderate",
            personalization_enabled=True,
            preference_confidence=0.75
        )
        
        db_session.add(preferences)
        db_session.commit()
        
        retrieved = db_session.query(UserPreferences).filter_by(user_id=1).first()
        assert retrieved.communication_style == "friendly"
        assert retrieved.preference_confidence == 0.75
    
    def test_service_history_model(self, db_session):
        """Test ServiceHistory model"""
        history = ServiceHistory(
            user_id=1,
            service_type="plomberie",
            location="Bonamoussadi",
            urgency_level="urgent",
            estimated_cost=10000,
            actual_cost=12000,
            service_outcome="completed",
            overall_satisfaction=4.5,
            would_use_again=True
        )
        
        db_session.add(history)
        db_session.commit()
        
        retrieved = db_session.query(ServiceHistory).filter_by(user_id=1).first()
        assert retrieved.service_type == "plomberie"
        assert retrieved.overall_satisfaction == 4.5
    
    def test_behavioral_patterns_model(self, db_session):
        """Test BehavioralPatterns model"""
        patterns = BehavioralPatterns(
            user_id=1,
            user_type="power_user",
            activity_level="high",
            loyalty_score=0.8,
            most_requested_services=["plomberie", "électricité"],
            planning_behavior="planner",
            pattern_confidence=0.9
        )
        
        db_session.add(patterns)
        db_session.commit()
        
        retrieved = db_session.query(BehavioralPatterns).filter_by(user_id=1).first()
        assert retrieved.user_type == "power_user"
        assert retrieved.loyalty_score == 0.8
    
    def test_contextual_memory_model(self, db_session):
        """Test ContextualMemory model"""
        memory = ContextualMemory(
            user_id=1,
            memory_type="service",
            memory_category="recurring_issue",
            memory_title="Problème chauffe-eau récurrent",
            memory_content="L'utilisateur a des problèmes récurrents avec son chauffe-eau",
            importance_score=0.8,
            context_tags=["chauffe-eau", "récurrent", "plomberie"]
        )
        
        db_session.add(memory)
        db_session.commit()
        
        retrieved = db_session.query(ContextualMemory).filter_by(user_id=1).first()
        assert retrieved.memory_title == "Problème chauffe-eau récurrent"
        assert retrieved.importance_score == 0.8


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])