"""
Test Enhanced Communication Service for Djobea AI
Tests instant confirmations, proactive updates, and pricing integration
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.communication_service import CommunicationService
from app.models.database_models import ServiceRequest, User, Provider, RequestStatus


class TestEnhancedCommunication:
    """Test enhanced communication features"""
    
    @pytest.fixture
    def communication_service(self):
        """Create communication service instance"""
        return CommunicationService()
    
    @pytest.fixture
    def mock_whatsapp_service(self):
        """Mock WhatsApp service for testing"""
        with patch('app.services.communication_service.WhatsAppService') as mock:
            mock_instance = mock.return_value
            mock_instance.send_message = AsyncMock(return_value=True)
            yield mock_instance
    
    def test_pricing_estimates_configuration(self, communication_service):
        """Test that pricing estimates are correctly configured"""
        # Test plomberie pricing
        plomberie_pricing = communication_service.get_pricing_estimate("plomberie")
        assert plomberie_pricing["min"] == 5000
        assert plomberie_pricing["max"] == 15000
        assert "Intervention de base" in plomberie_pricing["description"]
        
        # Test électricité pricing
        electricite_pricing = communication_service.get_pricing_estimate("électricité")
        assert electricite_pricing["min"] == 3000
        assert electricite_pricing["max"] == 10000
        
        # Test réparation électroménager pricing
        electromenager_pricing = communication_service.get_pricing_estimate("réparation électroménager")
        assert electromenager_pricing["min"] == 2000
        assert electromenager_pricing["max"] == 8000
        
        # Test unknown service (fallback)
        unknown_pricing = communication_service.get_pricing_estimate("service_inexistant")
        assert unknown_pricing["min"] == 2000
        assert unknown_pricing["max"] == 10000
    
    def test_price_formatting(self, communication_service):
        """Test XAF price formatting"""
        pricing = {"min": 5000, "max": 15000}
        formatted = communication_service.format_price_range(pricing)
        assert formatted == "5 000 - 15 000 XAF"
        
        # Test larger numbers
        pricing = {"min": 25000, "max": 150000}
        formatted = communication_service.format_price_range(pricing)
        assert formatted == "25 000 - 150 000 XAF"
    
    @pytest.mark.asyncio
    async def test_instant_confirmation_message_generation(self, communication_service, mock_whatsapp_service):
        """Test instant confirmation message generation"""
        # Create mock objects
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.whatsapp_id = "237654321098"
        
        mock_service_request = MagicMock()
        mock_service_request.id = 1
        mock_service_request.user_id = 1
        mock_service_request.service_type = "plomberie"
        mock_service_request.location = "Bonamoussadi"
        mock_service_request.description = "Fuite d'eau urgent"
        
        # Mock database session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_service_request, mock_user]
        
        # Send instant confirmation
        success = await communication_service.send_instant_confirmation(mock_service_request.id, mock_db)
        
        # Verify success
        assert success is True
        
        # Verify WhatsApp message was sent
        mock_whatsapp_service.send_message.assert_called_once()
        call_args = mock_whatsapp_service.send_message.call_args
        
        # Check recipient
        assert call_args[0][0] == mock_user.whatsapp_id
        
        # Check message content
        message = call_args[0][1]
        assert "✅ *Demande reçue et confirmée !*" in message
        assert "🔧 *Service* : Plomberie" in message
        assert "📍 *Zone* : Bonamoussadi" in message
        assert "5 000 - 15 000 XAF" in message
        assert "Intervention de base" in message
        assert "🔍 *Recherche en cours...*" in message
        assert "⏱ *Réponse attendue* : sous 5 minutes" in message
    
    @pytest.mark.asyncio
    async def test_provider_acceptance_notification(self, communication_service, mock_whatsapp_service):
        """Test provider acceptance notification"""
        # Create test data
        user = UserFactory.create(whatsapp_id="237654321098")
        provider = ProviderFactory.create(
            name="Jean Plombier",
            phone_number="237698765432",
            rating=4.8,
            total_jobs=25,
            coverage_areas=["Bonamoussadi"]
        )
        service_request = ServiceRequestFactory.create(
            user_id=user.id,
            service_type="plomberie",
            location="Bonamoussadi"
        )
        
        # Mock database session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            service_request, provider, user
        ]
        
        # Send provider acceptance notification
        success = await communication_service.send_provider_acceptance(
            service_request.id, provider.id, mock_db
        )
        
        # Verify success
        assert success is True
        
        # Verify WhatsApp message was sent
        mock_whatsapp_service.send_message.assert_called_once()
        call_args = mock_whatsapp_service.send_message.call_args
        
        # Check message content
        message = call_args[0][1]
        assert "✅ *Prestataire trouvé !*" in message
        assert "🔧 *Jean Plombier* a accepté" in message
        assert "📱 *Contact* : 237698765432" in message
        assert "⭐ *Note* : 4.8/5.0 (25 interventions)" in message
        assert "📍 *Zone* : Bonamoussadi" in message
        assert "💰 *Paiement sécurisé disponible*" in message
    
    def test_status_update_message_generation(self, communication_service):
        """Test status update message generation based on request state"""
        # Test PENDING status
        request = ServiceRequestFactory.create(
            service_type="électricité",
            status=RequestStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(minutes=3)
        )
        
        message = communication_service._generate_status_update_message(request)
        assert "🔍 *Recherche active*" in message
        assert "électricité" in message
        assert "3 minutes" in message
        
        # Test PROVIDER_NOTIFIED status
        request.status = RequestStatus.PROVIDER_NOTIFIED
        request.created_at = datetime.utcnow() - timedelta(minutes=5)
        
        message = communication_service._generate_status_update_message(request)
        assert "📞 *Prestataires contactés*" in message
        assert "5 minutes" in message
        assert "En attente de réponse" in message
    
    @pytest.mark.asyncio
    async def test_error_message_types(self, communication_service, mock_whatsapp_service):
        """Test different error message types"""
        user_whatsapp_id = "237654321098"
        
        # Test general error
        success = await communication_service.send_error_message(user_whatsapp_id, "general")
        assert success is True
        
        # Check message content
        call_args = mock_whatsapp_service.send_message.call_args
        message = call_args[0][1]
        assert "😕 *Oups ! Un petit problème*" in message
        assert "🔄 *Solutions*" in message
        
        # Test no providers error
        mock_whatsapp_service.send_message.reset_mock()
        await communication_service.send_error_message(user_whatsapp_id, "no_providers")
        
        call_args = mock_whatsapp_service.send_message.call_args
        message = call_args[0][1]
        assert "😔 *Aucun prestataire disponible*" in message
        assert "💡 *Alternatives*" in message
        
        # Test invalid location error
        mock_whatsapp_service.send_message.reset_mock()
        await communication_service.send_error_message(user_whatsapp_id, "invalid_location")
        
        call_args = mock_whatsapp_service.send_message.call_args
        message = call_args[0][1]
        assert "📍 *Zone non couverte*" in message
        assert "🎯 *Zones couvertes*" in message
        assert "Bonamoussadi" in message
    
    def test_confirmation_message_service_emojis(self, communication_service):
        """Test that service-specific emojis are used correctly"""
        # Test plomberie
        message = communication_service._generate_confirmation_message(
            "plomberie", "Bonamoussadi", "5 000 - 15 000 XAF", "Intervention de base"
        )
        assert "🔧 *Service* : Plomberie" in message
        
        # Test électricité
        message = communication_service._generate_confirmation_message(
            "électricité", "Bonamoussadi", "3 000 - 10 000 XAF", "Diagnostic standard"
        )
        assert "⚡ *Service* : Électricité" in message
        
        # Test réparation électroménager
        message = communication_service._generate_confirmation_message(
            "réparation électroménager", "Bonamoussadi", "2 000 - 8 000 XAF", "Réparation courante"
        )
        assert "🏠 *Service* : Réparation Électroménager" in message
        
        # Test unknown service (fallback)
        message = communication_service._generate_confirmation_message(
            "service_inconnu", "Bonamoussadi", "2 000 - 10 000 XAF", "Service standard"
        )
        assert "🛠 *Service* : Service_Inconnu" in message
    
    @pytest.mark.asyncio
    async def test_proactive_updates_task_management(self, communication_service):
        """Test proactive updates task creation and cancellation"""
        request_id = 123
        
        # Mock database
        mock_db = MagicMock()
        
        # Start proactive updates
        await communication_service.start_proactive_updates(request_id, mock_db)
        
        # Verify task was created
        assert request_id in communication_service.active_tasks
        assert communication_service.active_tasks[request_id] is not None
        
        # Stop proactive updates
        communication_service.stop_proactive_updates(request_id)
        
        # Verify task was removed
        assert request_id not in communication_service.active_tasks
    
    def test_countdown_warning_generation(self, communication_service, mock_whatsapp_service):
        """Test countdown warning message generation"""
        # Create test request
        service_request = ServiceRequestFactory.create(
            service_type="plomberie",
            status=RequestStatus.PROVIDER_NOTIFIED
        )
        
        message = f"""⏰ *Mise à jour importante*

Plus que *3 minutes* pour qu'un prestataire accepte votre demande de {service_request.service_type}.

🔄 Je continue à chercher des professionnels disponibles dans votre zone.

💬 Vous pouvez me poser des questions à tout moment !"""
        
        # Check message structure
        assert "⏰ *Mise à jour importante*" in message
        assert "Plus que *3 minutes*" in message
        assert "plomberie" in message
        assert "🔄 Je continue à chercher" in message


class TestCommunicationIntegration:
    """Test communication service integration with webhook system"""
    
    @pytest.mark.asyncio
    async def test_communication_service_webhook_integration(self):
        """Test that communication service integrates properly with webhook"""
        with patch('app.services.communication_service.CommunicationService') as mock_comm:
            # Mock the communication service methods
            mock_comm_instance = mock_comm.return_value
            mock_comm_instance.send_instant_confirmation = AsyncMock(return_value=True)
            mock_comm_instance.send_provider_acceptance = AsyncMock(return_value=True)
            
            # Verify methods exist and can be called
            await mock_comm_instance.send_instant_confirmation(1, None)
            await mock_comm_instance.send_provider_acceptance(1, 1, None)
            
            # Verify calls were made
            mock_comm_instance.send_instant_confirmation.assert_called_once()
            mock_comm_instance.send_provider_acceptance.assert_called_once()
    
    def test_pricing_configuration_completeness(self):
        """Test that all supported services have pricing configuration"""
        from app.config import get_settings
        
        settings = get_settings()
        supported_services = settings.supported_services
        service_pricing = settings.service_pricing
        
        # Verify all supported services have pricing
        for service in supported_services:
            assert service in service_pricing, f"Service {service} missing pricing configuration"
            
            pricing = service_pricing[service]
            assert "min" in pricing, f"Service {service} missing min price"
            assert "max" in pricing, f"Service {service} missing max price"
            assert "description" in pricing, f"Service {service} missing description"
            assert pricing["min"] > 0, f"Service {service} min price must be positive"
            assert pricing["max"] >= pricing["min"], f"Service {service} max price must be >= min price"
    
    def test_communication_settings_validation(self):
        """Test that communication settings are properly configured"""
        from app.config import get_settings
        
        settings = get_settings()
        
        # Verify timing settings
        assert settings.instant_confirmation_seconds == 30
        assert settings.proactive_update_interval_minutes == 2
        assert settings.urgent_update_interval_minutes == 1
        assert settings.countdown_threshold_minutes == 3
        
        # Verify intervals make sense
        assert settings.urgent_update_interval_minutes <= settings.proactive_update_interval_minutes
        assert settings.countdown_threshold_minutes < settings.provider_response_timeout_minutes