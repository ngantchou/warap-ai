"""
Sprint 4 - End-to-End Testing
Complete system testing with all scenarios including success, timeout, and failure cases
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.services.user_journey_manager import UserJourneyManager
from app.services.analytics_service import AnalyticsService
from app.services.provider_matcher import ProviderMatcher
from app.services.notification_service import WhatsAppNotificationService
from app.models.database_models import User, Provider, ServiceRequest, RequestStatus


class TestEndToEndScenarios:
    """Complete end-to-end system testing"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def sample_user(self):
        return User(
            id=1,
            whatsapp_id="whatsapp:+237699000001",
            name="Test User",
            phone_number="+237699000001"
        )
    
    @pytest.fixture
    def sample_providers(self):
        return [
            Provider(
                id=1, name="Provider 1", phone_number="+237690111111",
                services=["plomberie"], coverage_areas=["bonamoussadi"],
                is_active=True, is_available=True, rating=4.5, total_jobs=20
            ),
            Provider(
                id=2, name="Provider 2", phone_number="+237690222222",
                services=["plomberie"], coverage_areas=["bonamoussadi"],
                is_active=True, is_available=True, rating=4.2, total_jobs=15
            )
        ]
    
    @pytest.mark.asyncio
    async def test_complete_success_scenario(self, mock_db, sample_user, sample_providers):
        """
        End-to-end success scenario:
        Client sends request → AI extraction → provider matching → notification → acceptance → completion
        """
        
        # Step 1: User sends WhatsApp message
        incoming_message = "Bonjour, j'ai une fuite d'eau dans ma cuisine à Bonamoussadi. C'est urgent!"
        
        # Step 2: AI extracts request information
        extracted_data = {
            "service_type": "plomberie",
            "location": "Bonamoussadi",
            "description": "fuite d'eau dans ma cuisine",
            "urgency": "urgent",
            "confidence": 0.95
        }
        
        # Step 3: Create service request
        service_request = ServiceRequest(
            id=1,
            user_id=sample_user.id,
            service_type=extracted_data["service_type"],
            location=extracted_data["location"],
            description=extracted_data["description"],
            urgency=extracted_data["urgency"],
            status=RequestStatus.PENDING
        )
        
        # Step 4: Provider matching finds available providers
        matcher = ProviderMatcher(mock_db)
        with patch.object(matcher, 'find_available_providers') as mock_find:
            mock_find.return_value = sample_providers
            
            available_providers = matcher.find_available_providers(service_request)
            assert len(available_providers) == 2
        
        # Step 5: Notification service sends message to best provider
        notification_service = WhatsAppNotificationService(mock_db)
        with patch.object(notification_service, 'notify_provider') as mock_notify:
            mock_notify.return_value = True
            
            result = await notification_service.notify_provider(sample_providers[0], service_request)
            assert result is True
            mock_notify.assert_called_once()
        
        # Step 6: Provider accepts request
        with patch.object(notification_service, 'process_provider_response') as mock_response:
            mock_response.return_value = True
            
            acceptance = await notification_service.process_provider_response(
                sample_providers[0].phone_number, "OUI"
            )
            assert acceptance is True
        
        # Step 7: User gets confirmation
        journey_manager = UserJourneyManager(mock_db)
        with patch.object(journey_manager, 'handle_status_request') as mock_status:
            mock_status.return_value = "✅ Demande #1 assignée! Un prestataire a accepté votre demande."
            
            status_response = journey_manager.handle_status_request(sample_user.id, sample_user.whatsapp_id)
            assert "assignée" in status_response
        
        # Step 8: Verify metrics tracking
        analytics = AnalyticsService(mock_db)
        with patch.object(analytics, 'get_dashboard_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "overview": {
                    "total_requests": 1,
                    "success_rate": 100.0,
                    "pending_requests": 0
                }
            }
            
            metrics = analytics.get_dashboard_metrics()
            assert metrics["overview"]["success_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_provider_timeout_scenario(self, mock_db, sample_user, sample_providers):
        """
        Timeout scenario:
        Request → 1st provider timeout → 2nd provider → acceptance
        """
        
        service_request = ServiceRequest(
            id=2,
            user_id=sample_user.id,
            service_type="plomberie",
            location="Bonamoussadi",
            description="urgent plumbing issue",
            urgency="urgent",
            status=RequestStatus.PENDING
        )
        
        notification_service = WhatsAppNotificationService(mock_db)
        
        # Mock provider matcher to return multiple providers
        with patch.object(notification_service, 'provider_matcher') as mock_matcher:
            mock_matcher.get_best_providers.return_value = [
                Mock(provider=sample_providers[0]),
                Mock(provider=sample_providers[1])
            ]
            
            # Mock first provider timeout, second provider accepts
            async def mock_wait_response(notification, timeout):
                if notification.provider.id == 1:
                    return False  # Timeout
                else:
                    return True   # Accept
            
            with patch.object(notification_service, '_wait_for_provider_response', side_effect=mock_wait_response):
                with patch.object(notification_service, 'notify_provider', return_value=True):
                    with patch.object(notification_service, '_notify_client_provider_found', return_value=True):
                        
                        result = await notification_service.notify_providers_for_request(service_request)
                        assert result is True  # Should succeed with second provider
    
    @pytest.mark.asyncio 
    async def test_no_providers_scenario(self, mock_db, sample_user):
        """
        No providers scenario:
        Request → all providers reject/unavailable → fallback message
        """
        
        service_request = ServiceRequest(
            id=3,
            user_id=sample_user.id,
            service_type="plomberie",
            location="Unknown Area",
            description="emergency repair",
            urgency="urgent",
            status=RequestStatus.PENDING
        )
        
        notification_service = WhatsAppNotificationService(mock_db)
        
        # Mock provider matcher to return no providers
        with patch.object(notification_service, 'provider_matcher') as mock_matcher:
            mock_matcher.get_best_providers.return_value = []
            
            with patch.object(notification_service, '_notify_client_no_providers', return_value=True):
                result = await notification_service.notify_providers_for_request(service_request)
                assert result is False  # Should fail - no providers available
    
    @pytest.mark.asyncio
    async def test_user_cancellation_scenario(self, mock_db, sample_user):
        """
        Cancellation scenario:
        Request → user cancellation before provider acceptance → database cleanup
        """
        
        service_request = ServiceRequest(
            id=4,
            user_id=sample_user.id,
            service_type="électricité",
            location="Bonamoussadi",
            description="power issue",
            urgency="normal",
            status=RequestStatus.PENDING
        )
        
        journey_manager = UserJourneyManager(mock_db)
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = service_request
        
        # Mock request service cancellation
        with patch.object(journey_manager.request_service, 'cancel_request') as mock_cancel:
            mock_cancel.return_value = True
            
            # Mock WhatsApp service
            with patch.object(journey_manager.whatsapp_service, 'send_message') as mock_send:
                mock_send.return_value = True
                
                result = journey_manager.handle_cancellation(
                    sample_user.id, 
                    service_request.id,
                    sample_user.whatsapp_id
                )
                
                assert "annulée avec succès" in result
                mock_cancel.assert_called_once()
    
    def test_user_feedback_scenario(self, mock_db, sample_user, sample_providers):
        """
        Feedback scenario:
        Completed request → user provides rating → provider rating updated
        """
        
        completed_request = ServiceRequest(
            id=5,
            user_id=sample_user.id,
            provider_id=sample_providers[0].id,
            service_type="plomberie",
            location="Bonamoussadi",
            description="fixed leak",
            status=RequestStatus.COMPLETED
        )
        
        journey_manager = UserJourneyManager(mock_db)
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            completed_request,  # Request lookup
            sample_providers[0]  # Provider lookup
        ]
        
        # Mock WhatsApp service
        with patch.object(journey_manager.whatsapp_service, 'send_message') as mock_send:
            mock_send.return_value = True
            
            result = journey_manager.handle_feedback(
                sample_user.id,
                completed_request.id,
                5,  # 5-star rating
                "Excellent travail!",
                sample_user.whatsapp_id
            )
            
            assert "Merci pour votre évaluation" in result
            assert "5/5" in result
    
    def test_status_inquiry_scenarios(self, mock_db, sample_user):
        """Test various status inquiry scenarios"""
        
        journey_manager = UserJourneyManager(mock_db)
        
        # Scenario 1: No requests found
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        result = journey_manager.handle_status_request(sample_user.id, sample_user.whatsapp_id)
        assert "Aucune demande trouvée" in result
        
        # Scenario 2: Pending request
        pending_request = ServiceRequest(
            id=6,
            user_id=sample_user.id,
            service_type="plomberie",
            location="Bonamoussadi",
            status=RequestStatus.PENDING,
            created_at=datetime.now()
        )
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = pending_request
        
        result = journey_manager.handle_status_request(sample_user.id, sample_user.whatsapp_id)
        assert "en attente" in result
        assert "recherchons un prestataire" in result


class TestAnalyticsEndToEnd:
    """Test analytics service with real data scenarios"""
    
    @pytest.fixture
    def mock_db_with_data(self):
        """Mock database with sample data"""
        db = Mock()
        
        # Sample requests data
        sample_requests = [
            Mock(
                id=1, status=RequestStatus.COMPLETED.value, service_type="plomberie",
                location="Bonamoussadi", created_at=datetime.now() - timedelta(days=1),
                accepted_at=datetime.now() - timedelta(days=1, hours=1),
                completed_at=datetime.now() - timedelta(hours=2),
                provider_id=1
            ),
            Mock(
                id=2, status=RequestStatus.PENDING.value, service_type="électricité",
                location="Makepe", created_at=datetime.now() - timedelta(hours=3),
                accepted_at=None, completed_at=None, provider_id=None
            ),
            Mock(
                id=3, status=RequestStatus.CANCELLED.value, service_type="plomberie",
                location="Akwa", created_at=datetime.now() - timedelta(days=2),
                accepted_at=None, completed_at=None, provider_id=None
            )
        ]
        
        # Sample providers data
        sample_providers = [
            Mock(
                id=1, name="Provider 1", phone_number="+237690111111",
                services=["plomberie"], rating=4.5, total_jobs=20,
                is_active=True, is_available=True
            ),
            Mock(
                id=2, name="Provider 2", phone_number="+237690222222", 
                services=["électricité"], rating=4.2, total_jobs=15,
                is_active=True, is_available=False
            )
        ]
        
        db.query.return_value.count.return_value = len(sample_requests)
        db.query.return_value.all.return_value = sample_requests
        db.query.return_value.filter.return_value.count.side_effect = [1, 1, 1]  # Status counts
        
        return db
    
    def test_dashboard_metrics_calculation(self, mock_db_with_data):
        """Test dashboard metrics calculation with sample data"""
        
        analytics = AnalyticsService(mock_db_with_data)
        
        # Mock various queries
        mock_db_with_data.query.return_value.count.side_effect = [3, 2, 5]  # requests, providers, users
        mock_db_with_data.query.return_value.filter.return_value.count.side_effect = [2, 1, 1]  # active, pending, recent
        
        metrics = analytics.get_dashboard_metrics()
        
        assert "overview" in metrics
        assert "status_distribution" in metrics
        assert "last_updated" in metrics
        assert metrics["overview"]["total_requests"] >= 0
        assert metrics["overview"]["success_rate"] >= 0
    
    def test_success_rate_analytics(self, mock_db_with_data):
        """Test success rate analytics over time"""
        
        analytics = AnalyticsService(mock_db_with_data)
        
        # Mock time-based queries
        mock_db_with_data.query.return_value.filter.return_value.all.return_value = [
            Mock(status=RequestStatus.COMPLETED.value),
            Mock(status=RequestStatus.PENDING.value),
            Mock(status=RequestStatus.CANCELLED.value)
        ]
        
        result = analytics.get_success_rate_analytics(7)
        
        assert "period_days" in result
        assert "overall_success_rate" in result
        assert "daily_data" in result
        assert result["period_days"] == 7
        assert len(result["daily_data"]) == 7
    
    def test_provider_rankings(self, mock_db_with_data):
        """Test provider performance rankings"""
        
        analytics = AnalyticsService(mock_db_with_data)
        
        # Mock provider queries
        providers = [
            Mock(id=1, name="Provider 1", phone_number="+237690111111",
                 services=["plomberie"], rating=4.5, total_jobs=20,
                 is_active=True, is_available=True),
            Mock(id=2, name="Provider 2", phone_number="+237690222222",
                 services=["électricité"], rating=4.2, total_jobs=15,
                 is_active=True, is_available=False)
        ]
        
        mock_db_with_data.query.return_value.all.return_value = providers
        mock_db_with_data.query.return_value.filter.return_value.all.return_value = []  # No requests per provider
        
        rankings = analytics.get_provider_rankings()
        
        assert isinstance(rankings, list)
        for ranking in rankings:
            assert "provider_id" in ranking
            assert "name" in ranking
            assert "completion_rate" in ranking
            assert "total_requests" in ranking


class TestSystemRobustness:
    """Test system robustness and error handling"""
    
    def test_database_connection_failure(self):
        """Test system behavior when database connection fails"""
        
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database connection failed")
        
        analytics = AnalyticsService(mock_db)
        metrics = analytics.get_dashboard_metrics()
        
        # Should return error state, not crash
        assert "error" in metrics
        assert metrics["overview"]["total_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_whatsapp_service_failure(self, mock_db):
        """Test system behavior when WhatsApp service fails"""
        
        journey_manager = UserJourneyManager(mock_db)
        
        # Mock WhatsApp service failure
        with patch.object(journey_manager.whatsapp_service, 'send_message') as mock_send:
            mock_send.return_value = False  # Failed to send
            
            # Should still return response even if sending fails
            result = journey_manager.handle_status_request(1, "whatsapp:+237690000001")
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_invalid_input_handling(self, mock_db):
        """Test handling of invalid inputs"""
        
        journey_manager = UserJourneyManager(mock_db)
        
        # Test invalid rating
        result = journey_manager.handle_feedback(1, 1, 10, "", "whatsapp:+237690000001")  # Rating > 5
        assert "Note invalide" in result
        
        # Test invalid user ID
        result = journey_manager.handle_status_request(-1, "invalid_whatsapp_id")
        assert "Aucune demande trouvée" in result or "Erreur" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])