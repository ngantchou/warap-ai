"""
Sprint 3 - Matching and Notifications System Tests
Comprehensive testing of provider matching algorithm and notification system
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio

from app.services.provider_matcher import ProviderMatcher, ProviderScore
from app.services.notification_service import WhatsAppNotificationService, NotificationStatus
from app.models.database_models import Provider, ServiceRequest, User, RequestStatus


class TestProviderMatcher:
    """Test provider matching algorithm"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def provider_matcher(self, mock_db):
        return ProviderMatcher(mock_db)
    
    @pytest.fixture
    def sample_providers(self):
        """Sample providers for testing"""
        return [
            Provider(
                id=1, name="Jean Plombier", phone_number="237690111111",
                services=["plomberie"], coverage_areas=["bonamoussadi", "makepe"],
                is_active=True, is_available=True, rating=4.5, total_jobs=25
            ),
            Provider(
                id=2, name="Paul Électricien", phone_number="237690222222", 
                services=["électricité"], coverage_areas=["bonamoussadi", "akwa"],
                is_active=True, is_available=True, rating=4.2, total_jobs=18
            ),
            Provider(
                id=3, name="Marie Réparatrice", phone_number="237690333333",
                services=["réparation électroménager"], coverage_areas=["makepe"],
                is_active=True, is_available=True, rating=4.8, total_jobs=42
            )
        ]
    
    @pytest.fixture
    def sample_request(self):
        """Sample service request"""
        return ServiceRequest(
            id=1, user_id=1, service_type="plomberie",
            description="Fuite d'eau sous évier", location="Bonamoussadi carrefour Shell",
            urgency="urgent", status=RequestStatus.PENDING
        )
    
    def test_extract_location_keywords(self, provider_matcher):
        """Test location keyword extraction"""
        test_cases = [
            ("Bonamoussadi carrefour Shell", ["bonamoussadi", "station_shell"]),
            ("Makepe Total station", ["makepe", "station_total"]), 
            ("Akwa centre ville", ["akwa"]),
            ("Deido marché central", ["deido", "marché"]),
            ("Location inconnue", ["bonamoussadi"])  # Default
        ]
        
        for location, expected_keywords in test_cases:
            keywords = provider_matcher._extract_location_keywords(location)
            for keyword in expected_keywords:
                assert keyword in keywords
    
    def test_proximity_scoring(self, provider_matcher):
        """Test geographic proximity scoring"""
        provider = Provider(coverage_areas=["bonamoussadi", "makepe"])
        
        # Perfect match
        score1 = provider_matcher._calculate_proximity_score(provider, "Bonamoussadi")
        assert score1 >= 0.8
        
        # Partial match
        score2 = provider_matcher._calculate_proximity_score(provider, "Akwa")
        assert score2 < score1
        
        # No match
        score3 = provider_matcher._calculate_proximity_score(provider, "Douala port")
        assert score3 < score2
    
    def test_rating_scoring(self, provider_matcher):
        """Test rating-based scoring"""
        high_rated = Provider(rating=4.8, total_jobs=50)
        medium_rated = Provider(rating=3.5, total_jobs=20)
        low_rated = Provider(rating=2.0, total_jobs=5)
        
        score_high = provider_matcher._calculate_rating_score(high_rated)
        score_medium = provider_matcher._calculate_rating_score(medium_rated)
        score_low = provider_matcher._calculate_rating_score(low_rated)
        
        assert score_high > score_medium > score_low
        assert 0 <= score_low <= score_medium <= score_high <= 1
    
    def test_specialization_scoring(self, provider_matcher):
        """Test service specialization scoring"""
        specialist = Provider(services=["plomberie"])
        multi_service = Provider(services=["plomberie", "électricité"])
        generalist = Provider(services=["plomberie", "électricité", "réparation électroménager", "autres"])
        
        score_specialist = provider_matcher._calculate_specialization_score(specialist, "plomberie")
        score_multi = provider_matcher._calculate_specialization_score(multi_service, "plomberie")
        score_generalist = provider_matcher._calculate_specialization_score(generalist, "plomberie")
        
        assert score_specialist > score_multi > score_generalist
        assert score_specialist == 1.0  # Perfect specialization
    
    @patch('app.services.provider_matcher.Session')
    def test_availability_scoring(self, mock_session, provider_matcher):
        """Test current availability scoring"""
        provider = Provider(id=1, is_available=True)
        
        # Mock database query for current jobs
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 0  # No current jobs
        provider_matcher.db.query.return_value = mock_query
        
        score = provider_matcher._calculate_availability_score(provider)
        assert score == 1.0  # Fully available
        
        # Test with busy provider
        mock_query.filter.return_value.count.return_value = 3  # Very busy
        score_busy = provider_matcher._calculate_availability_score(provider)
        assert score_busy < score


class TestWhatsAppNotificationService:
    """Test WhatsApp notification service"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def notification_service(self, mock_db):
        return WhatsAppNotificationService(mock_db)
    
    @pytest.fixture
    def sample_provider(self):
        return Provider(
            id=1, name="Jean Plombier", phone_number="237690111111",
            services=["plomberie"], rating=4.5, total_jobs=25
        )
    
    @pytest.fixture
    def sample_request(self):
        return ServiceRequest(
            id=1, service_type="plomberie", location="Bonamoussadi carrefour Shell",
            description="Fuite d'eau sous évier", urgency="urgent"
        )
    
    def test_format_provider_message(self, notification_service, sample_provider, sample_request):
        """Test provider notification message formatting"""
        message = notification_service._format_provider_message(sample_provider, sample_request)
        
        # Check for required elements according to spec
        assert "🔧 NOUVELLE MISSION DJOBEA" in message
        assert "Service : Plomberie" in message
        assert "Lieu : Bonamoussadi carrefour Shell" in message
        assert "Problème : Fuite d'eau sous évier" in message
        assert "Délai : urgent" in message
        assert "✅ OUI pour accepter" in message
        assert "❌ NON pour refuser" in message
        assert "⏰ Réponse attendue sous 10 min" in message
    
    @patch('app.services.notification_service.WhatsAppService')
    def test_notify_provider_success(self, mock_whatsapp, notification_service, sample_provider, sample_request):
        """Test successful provider notification"""
        # Mock WhatsApp service
        mock_whatsapp_instance = Mock()
        mock_whatsapp_instance.send_message.return_value = True
        mock_whatsapp.return_value = mock_whatsapp_instance
        notification_service.whatsapp_service = mock_whatsapp_instance
        
        result = asyncio.run(notification_service.notify_provider(sample_provider, sample_request))
        
        assert result is True
        mock_whatsapp_instance.send_message.assert_called_once()
        
        # Check message was formatted correctly
        call_args = mock_whatsapp_instance.send_message.call_args
        phone_number, message = call_args[0]
        assert phone_number == "237690111111"
        assert "🔧 NOUVELLE MISSION DJOBEA" in message
    
    def test_process_provider_response_accept(self, notification_service):
        """Test processing provider acceptance"""
        # Mock provider lookup
        mock_provider = Provider(id=1, phone_number="237690111111")
        notification_service.db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        # Mock active notification
        from app.services.notification_service import ProviderNotification, NotificationStatus
        notification = ProviderNotification(
            provider_id=1, provider=mock_provider, request_id=1, 
            status=NotificationStatus.SENT
        )
        notification_service.active_notifications = {1: [notification]}
        
        result = asyncio.run(notification_service.process_provider_response("237690111111", "OUI"))
        
        assert result is True
        assert notification.status == NotificationStatus.ACCEPTED
        assert notification.responded_at is not None
    
    def test_process_provider_response_reject(self, notification_service):
        """Test processing provider rejection"""
        mock_provider = Provider(id=1, phone_number="237690111111")
        notification_service.db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        from app.services.notification_service import ProviderNotification, NotificationStatus
        notification = ProviderNotification(
            provider_id=1, provider=mock_provider, request_id=1,
            status=NotificationStatus.SENT
        )
        notification_service.active_notifications = {1: [notification]}
        
        result = asyncio.run(notification_service.process_provider_response("237690111111", "NON"))
        
        assert result is True
        assert notification.status == NotificationStatus.REJECTED
    
    def test_process_provider_response_ambiguous(self, notification_service):
        """Test processing ambiguous provider response"""
        mock_provider = Provider(id=1, phone_number="237690111111")
        notification_service.db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        # Mock WhatsApp service for clarification message
        notification_service.whatsapp_service = Mock()
        notification_service.whatsapp_service.send_message.return_value = True
        
        result = asyncio.run(notification_service.process_provider_response("237690111111", "peut-être"))
        
        assert result is False
        notification_service.whatsapp_service.send_message.assert_called_once()
        
        # Check clarification message was sent
        call_args = notification_service.whatsapp_service.send_message.call_args[0]
        assert "✅ OUI pour accepter" in call_args[1]
        assert "❌ NON pour refuser" in call_args[1]
    
    @patch('app.services.notification_service.asyncio')
    async def test_fallback_notification_logic(self, mock_asyncio, notification_service, sample_request):
        """Test fallback notification when providers don't respond"""
        # Mock provider matcher
        mock_provider_matcher = Mock()
        
        # Create mock providers with scoring
        providers = [
            ProviderScore(provider_id=1, provider=Provider(id=1, name="Provider1"), total_score=0.9,
                         proximity_score=0.8, rating_score=0.9, response_time_score=0.8, 
                         specialization_score=1.0, availability_score=1.0),
            ProviderScore(provider_id=2, provider=Provider(id=2, name="Provider2"), total_score=0.7,
                         proximity_score=0.6, rating_score=0.8, response_time_score=0.7,
                         specialization_score=0.8, availability_score=0.9)
        ]
        
        mock_provider_matcher.get_best_providers.return_value = providers
        notification_service.provider_matcher = mock_provider_matcher
        
        # Mock notification sending
        notification_service.notify_provider = AsyncMock(return_value=True)
        notification_service._wait_for_provider_response = AsyncMock(return_value=False)  # Timeout
        notification_service._notify_client_extended_delay = AsyncMock(return_value=True)
        
        result = await notification_service.notify_providers_for_request(sample_request)
        
        # Should have tried all providers and failed
        assert result is False
        assert notification_service.notify_provider.call_count == 2  # Tried both providers
        notification_service._notify_client_extended_delay.assert_called_once()
    
    def test_notification_metrics(self, notification_service):
        """Test notification system metrics calculation"""
        from app.services.notification_service import ProviderNotification, NotificationStatus
        
        # Mock notifications with different statuses
        notifications = [
            ProviderNotification(1, Mock(), 1, NotificationStatus.ACCEPTED, 
                               datetime.now() - timedelta(minutes=5), datetime.now()),
            ProviderNotification(2, Mock(), 1, NotificationStatus.REJECTED,
                               datetime.now() - timedelta(minutes=8), datetime.now()),
            ProviderNotification(3, Mock(), 1, NotificationStatus.TIMEOUT),
            ProviderNotification(4, Mock(), 2, NotificationStatus.ACCEPTED,
                               datetime.now() - timedelta(minutes=3), datetime.now())
        ]
        
        notification_service.active_notifications = {1: notifications[:3], 2: [notifications[3]]}
        
        metrics = notification_service.get_notification_metrics()
        
        assert metrics["total_notifications"] == 4
        assert metrics["accepted"] == 2
        assert metrics["rejected"] == 1
        assert metrics["timeouts"] == 1
        assert metrics["acceptance_rate"] == 2/3  # 2 accepted out of 3 responses
        assert metrics["timeout_rate"] == 1/4     # 1 timeout out of 4 total
        assert 0 < metrics["average_response_time_minutes"] < 10


class TestIntegration:
    """Integration tests for matching + notification system"""
    
    @pytest.fixture
    def mock_db_session(self):
        session = Mock()
        session.query.return_value.filter.return_value.all.return_value = []
        return session
    
    @patch('app.services.provider_matcher.ProviderMatcher')
    @patch('app.services.notification_service.WhatsAppService')
    async def test_end_to_end_successful_matching(self, mock_whatsapp, mock_matcher, mock_db_session):
        """Test complete flow: request → matching → notification → acceptance"""
        
        # Setup mocks
        notification_service = WhatsAppNotificationService(mock_db_session)
        
        # Mock successful provider matching
        best_provider = ProviderScore(
            provider_id=1, 
            provider=Provider(id=1, name="Best Provider", phone_number="237690111111"),
            total_score=0.95, proximity_score=1.0, rating_score=0.9,
            response_time_score=1.0, specialization_score=1.0, availability_score=1.0
        )
        
        notification_service.provider_matcher.get_best_providers.return_value = [best_provider]
        
        # Mock successful notification
        notification_service.whatsapp_service.send_message.return_value = True
        
        # Mock successful provider response
        async def mock_wait_response(notification, timeout):
            notification.status = NotificationStatus.ACCEPTED
            notification.responded_at = datetime.now()
            return True
        
        notification_service._wait_for_provider_response = mock_wait_response
        notification_service._notify_client_provider_found = AsyncMock(return_value=True)
        
        # Test request
        request = ServiceRequest(
            id=1, service_type="plomberie", location="Bonamoussadi",
            description="Urgent leak", urgency="urgent"
        )
        
        result = await notification_service.notify_providers_for_request(request)
        
        assert result is True
        notification_service.whatsapp_service.send_message.assert_called()
        notification_service._notify_client_provider_found.assert_called_once()
    
    def test_status_transitions(self):
        """Test request status transitions through the system"""
        from app.models.database_models import RequestStatus
        
        # Test all required statuses exist
        assert RequestStatus.PENDING == "en attente"
        assert RequestStatus.PROVIDER_NOTIFIED == "prestataire_notifie" 
        assert RequestStatus.ASSIGNED == "assignée"
        assert RequestStatus.IN_PROGRESS == "en cours"
        assert RequestStatus.COMPLETED == "terminée"
        assert RequestStatus.CANCELLED == "annulée"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])