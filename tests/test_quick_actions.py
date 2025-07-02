"""
Test suite for Quick Actions Menu System
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.services.quick_actions_service import QuickActionsService
from app.services.conversation_manager import conversation_manager
from app.models.database_models import (
    User, Provider, ServiceRequest, RequestStatus, ActionType,
    UserAction, SupportTicket, SupportTicketStatus
)


class TestQuickActionsService:
    """Test QuickActionsService functionality"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)

    @pytest.fixture
    def quick_actions_service(self, mock_db):
        """Quick actions service instance"""
        return QuickActionsService(mock_db)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing"""
        return User(
            id=1,
            whatsapp_id="+237670000001",
            name="Jean Test",
            phone_number="+237670000001"
        )

    @pytest.fixture
    def sample_provider(self):
        """Sample provider for testing"""
        return Provider(
            id=1,
            name="Tech Pro Services",
            whatsapp_id="+237670000002",
            phone_number="+237670000002",
            services=["électricité", "plomberie"],
            coverage_areas=["Bonamoussadi"],
            rating=4.5,
            total_jobs=25,
            is_available=True,
            is_active=True
        )

    @pytest.fixture
    def sample_request(self, sample_user, sample_provider):
        """Sample service request for testing"""
        return ServiceRequest(
            id=1,
            user_id=sample_user.id,
            provider_id=sample_provider.id,
            service_type="électricité",
            description="Problème de courant dans la cuisine",
            location="Bonamoussadi, Douala",
            preferred_time="Dans l'après-midi",
            urgency="urgent",
            status=RequestStatus.ASSIGNED,
            created_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            user=sample_user,
            provider=sample_provider
        )

    def test_generate_actions_menu_french(self, quick_actions_service):
        """Test menu generation in French"""
        menu = quick_actions_service.generate_actions_menu(123, "french")
        
        # Check menu structure
        assert "🎯 *Menu Actions Rapides*" in menu
        assert "1️⃣ *STATUT*" in menu
        assert "2️⃣ *MODIFIER*" in menu
        assert "3️⃣ *ANNULER*" in menu
        assert "4️⃣ *AIDE*" in menu
        assert "5️⃣ *PROFIL*" in menu
        assert "6️⃣ *CONTACT*" in menu
        assert "Tapez le *NUMÉRO* ou *MOT-CLÉ*" in menu

    def test_generate_actions_menu_english(self, quick_actions_service):
        """Test menu generation in English"""
        menu = quick_actions_service.generate_actions_menu(123, "english")
        
        # Check menu structure
        assert "🎯 *Quick Actions Menu*" in menu
        assert "1️⃣ *STATUS*" in menu
        assert "2️⃣ *MODIFY*" in menu
        assert "3️⃣ *CANCEL*" in menu
        assert "4️⃣ *HELP*" in menu
        assert "5️⃣ *PROFILE*" in menu
        assert "6️⃣ *CONTACT*" in menu
        assert "Type the *NUMBER* or *KEYWORD*" in menu

    def test_detect_action_command_numbers(self, quick_actions_service):
        """Test action detection using numbers"""
        assert quick_actions_service.detect_action_command("1") == ActionType.STATUS_CHECK
        assert quick_actions_service.detect_action_command("2") == ActionType.MODIFY_REQUEST
        assert quick_actions_service.detect_action_command("3") == ActionType.CANCEL_REQUEST
        assert quick_actions_service.detect_action_command("4") == ActionType.HELP_REQUEST
        assert quick_actions_service.detect_action_command("5") == ActionType.PROVIDER_PROFILE
        assert quick_actions_service.detect_action_command("6") == ActionType.CONTACT_PROVIDER

    def test_detect_action_command_french_keywords(self, quick_actions_service):
        """Test action detection using French keywords"""
        assert quick_actions_service.detect_action_command("statut") == ActionType.STATUS_CHECK
        assert quick_actions_service.detect_action_command("modifier") == ActionType.MODIFY_REQUEST
        assert quick_actions_service.detect_action_command("annuler") == ActionType.CANCEL_REQUEST
        assert quick_actions_service.detect_action_command("aide") == ActionType.HELP_REQUEST
        assert quick_actions_service.detect_action_command("profil") == ActionType.PROVIDER_PROFILE
        assert quick_actions_service.detect_action_command("contact") == ActionType.CONTACT_PROVIDER

    def test_detect_action_command_english_keywords(self, quick_actions_service):
        """Test action detection using English keywords"""
        assert quick_actions_service.detect_action_command("status") == ActionType.STATUS_CHECK
        assert quick_actions_service.detect_action_command("modify") == ActionType.MODIFY_REQUEST
        assert quick_actions_service.detect_action_command("cancel") == ActionType.CANCEL_REQUEST
        assert quick_actions_service.detect_action_command("help") == ActionType.HELP_REQUEST
        assert quick_actions_service.detect_action_command("profile") == ActionType.PROVIDER_PROFILE
        assert quick_actions_service.detect_action_command("call") == ActionType.CONTACT_PROVIDER

    def test_detect_action_command_no_match(self, quick_actions_service):
        """Test action detection with no matches"""
        assert quick_actions_service.detect_action_command("bonjour") is None
        assert quick_actions_service.detect_action_command("je voudrais") is None
        assert quick_actions_service.detect_action_command("7") is None

    @pytest.mark.asyncio
    async def test_handle_status_check_with_provider(self, quick_actions_service, sample_request):
        """Test status check with assigned provider"""
        # Mock recent request
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.STATUS_CHECK
        )
        
        # Check response content
        assert "📊 *Statut de votre demande*" in response
        assert f"🆔 *Demande* : #{sample_request.id}" in response
        assert f"🔧 *Service* : {sample_request.service_type.title()}" in response
        assert f"📍 *Lieu* : {sample_request.location}" in response
        assert "👷 *Prestataire assigné* :" in response
        assert sample_request.provider.name in response
        assert sample_request.provider.phone_number in response

    @pytest.mark.asyncio
    async def test_handle_status_check_no_provider(self, quick_actions_service, sample_request):
        """Test status check without assigned provider"""
        # Remove provider assignment
        sample_request.provider_id = None
        sample_request.provider = None
        sample_request.status = RequestStatus.PENDING
        
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.STATUS_CHECK
        )
        
        # Check response content
        assert "📊 *Statut de votre demande*" in response
        assert "⏳" in response  # Pending status emoji
        assert "Recherche d'un prestataire en cours" in response

    @pytest.mark.asyncio
    async def test_handle_modify_request_allowed(self, quick_actions_service, sample_request):
        """Test request modification when allowed"""
        sample_request.status = RequestStatus.PENDING
        
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.MODIFY_REQUEST
        )
        
        # Check response content
        assert "✏️ *Modification de votre demande*" in response
        assert "1️⃣ *DESCRIPTION*" in response
        assert "2️⃣ *LIEU*" in response
        assert "3️⃣ *URGENCE*" in response

    @pytest.mark.asyncio
    async def test_handle_modify_request_not_allowed(self, quick_actions_service, sample_request):
        """Test request modification when not allowed"""
        sample_request.status = RequestStatus.COMPLETED
        
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.MODIFY_REQUEST
        )
        
        # Check response content
        assert "❌ *Modification impossible*" in response
        assert "terminée" in response.lower()

    @pytest.mark.asyncio
    async def test_handle_cancel_request_pending(self, quick_actions_service, sample_request):
        """Test request cancellation for pending request"""
        sample_request.status = RequestStatus.PENDING
        
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.CANCEL_REQUEST
        )
        
        # Check response content
        assert "❌ *Confirmation d'annulation*" in response
        assert "Tapez *OUI* pour confirmer" in response
        assert "Tapez *NON* pour garder" in response

    @pytest.mark.asyncio
    async def test_handle_cancel_request_in_progress(self, quick_actions_service, sample_request):
        """Test request cancellation for in-progress request"""
        sample_request.status = RequestStatus.IN_PROGRESS
        
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.CANCEL_REQUEST
        )
        
        # Check response content
        assert "⚠️ *Annulation complexe*" in response
        assert "en cours d'exécution" in response
        assert "contactez notre support" in response

    @pytest.mark.asyncio
    async def test_handle_help_request(self, quick_actions_service):
        """Test help request handling"""
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.HELP_REQUEST
        )
        
        # Check response content
        assert "🆘 *Centre d'aide Djobea AI*" in response
        assert "*Questions fréquentes :*" in response
        assert "*Comment ça marche ?*" in response
        assert "*Combien ça coûte ?*" in response
        assert "*Comment payer ?*" in response
        assert "MTN Mobile Money" in response
        assert "Orange Money" in response

    @pytest.mark.asyncio
    async def test_handle_provider_profile_with_provider(self, quick_actions_service, sample_request):
        """Test provider profile view with assigned provider"""
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.PROVIDER_PROFILE
        )
        
        # Check response content
        assert "👤 *Profil du prestataire*" in response
        assert f"Nom : {sample_request.provider.name}" in response
        assert f"Note : {'⭐' * int(sample_request.provider.rating)}" in response
        assert f"Téléphone : {sample_request.provider.phone_number}" in response

    @pytest.mark.asyncio
    async def test_handle_provider_profile_no_provider(self, quick_actions_service, sample_request):
        """Test provider profile view without assigned provider"""
        sample_request.provider_id = None
        sample_request.provider = None
        
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.PROVIDER_PROFILE
        )
        
        # Check response content
        assert "👤 *Aucun prestataire assigné*" in response
        assert "n'a pas encore de prestataire" in response

    @pytest.mark.asyncio
    async def test_handle_contact_provider_with_provider(self, quick_actions_service, sample_request):
        """Test provider contact with assigned provider"""
        quick_actions_service._get_user_recent_request = Mock(return_value=sample_request)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.CONTACT_PROVIDER
        )
        
        # Check response content
        assert "📞 *Contacter votre prestataire*" in response
        assert f"👤 *{sample_request.provider.name}*" in response
        assert f"📱 *{sample_request.provider.phone_number}*" in response
        assert "1️⃣ *Appel direct*" in response
        assert "2️⃣ *WhatsApp*" in response
        assert "3️⃣ *Message suggéré :*" in response

    @pytest.mark.asyncio
    async def test_handle_no_request_found(self, quick_actions_service):
        """Test handling when user has no requests"""
        quick_actions_service._get_user_recent_request = Mock(return_value=None)
        quick_actions_service._log_user_action = Mock()
        
        response = await quick_actions_service.handle_action_command(
            1, "+237670000001", ActionType.STATUS_CHECK
        )
        
        # Check response content
        assert "🔍 *Aucune demande trouvée*" in response
        assert "n'avez pas encore de demande" in response

    def test_create_support_ticket(self, quick_actions_service, mock_db):
        """Test support ticket creation"""
        # Mock database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        # Create a mock ticket with an id
        mock_ticket = Mock()
        mock_ticket.id = 123
        mock_db.add.side_effect = lambda obj: setattr(obj, 'id', 123)
        
        ticket_id = quick_actions_service.create_support_ticket(
            user_id=1,
            title="Problème avec prestataire",
            description="Le prestataire n'est pas venu",
            request_id=456,
            priority="high"
        )
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_track_request_modification(self, quick_actions_service, mock_db):
        """Test request modification tracking"""
        # Mock database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        quick_actions_service.track_request_modification(
            request_id=123,
            user_id=1,
            field_modified="description",
            old_value="Ancien problème",
            new_value="Nouveau problème",
            reason="Plus de détails nécessaires"
        )
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called


class TestConversationManagerQuickActions:
    """Test ConversationManager quick action detection"""

    @pytest.fixture
    def conv_manager(self):
        """Conversation manager instance"""
        return conversation_manager

    def test_detect_quick_action_status_patterns(self, conv_manager):
        """Test status check detection patterns"""
        assert conv_manager.detect_quick_action("1") == ActionType.STATUS_CHECK
        assert conv_manager.detect_quick_action("statut") == ActionType.STATUS_CHECK
        assert conv_manager.detect_quick_action("status") == ActionType.STATUS_CHECK
        assert conv_manager.detect_quick_action("où en est ma demande?") == ActionType.STATUS_CHECK
        assert conv_manager.detect_quick_action("comment ça va?") == ActionType.STATUS_CHECK

    def test_detect_quick_action_modify_patterns(self, conv_manager):
        """Test modify request detection patterns"""
        assert conv_manager.detect_quick_action("2") == ActionType.MODIFY_REQUEST
        assert conv_manager.detect_quick_action("modifier") == ActionType.MODIFY_REQUEST
        assert conv_manager.detect_quick_action("changer ma demande") == ActionType.MODIFY_REQUEST
        assert conv_manager.detect_quick_action("correction") == ActionType.MODIFY_REQUEST

    def test_detect_quick_action_cancel_patterns(self, conv_manager):
        """Test cancel request detection patterns"""
        assert conv_manager.detect_quick_action("3") == ActionType.CANCEL_REQUEST
        assert conv_manager.detect_quick_action("annuler") == ActionType.CANCEL_REQUEST
        assert conv_manager.detect_quick_action("cancel") == ActionType.CANCEL_REQUEST
        assert conv_manager.detect_quick_action("stop") == ActionType.CANCEL_REQUEST
        assert conv_manager.detect_quick_action("plus besoin") == ActionType.CANCEL_REQUEST

    def test_detect_quick_action_help_patterns(self, conv_manager):
        """Test help request detection patterns"""
        assert conv_manager.detect_quick_action("4") == ActionType.HELP_REQUEST
        assert conv_manager.detect_quick_action("aide") == ActionType.HELP_REQUEST
        assert conv_manager.detect_quick_action("help") == ActionType.HELP_REQUEST
        assert conv_manager.detect_quick_action("support") == ActionType.HELP_REQUEST
        assert conv_manager.detect_quick_action("j'ai un problème") == ActionType.HELP_REQUEST

    def test_detect_quick_action_profile_patterns(self, conv_manager):
        """Test provider profile detection patterns"""
        assert conv_manager.detect_quick_action("5") == ActionType.PROVIDER_PROFILE
        assert conv_manager.detect_quick_action("profil") == ActionType.PROVIDER_PROFILE
        assert conv_manager.detect_quick_action("prestataire") == ActionType.PROVIDER_PROFILE
        assert conv_manager.detect_quick_action("qui est mon prestataire?") == ActionType.PROVIDER_PROFILE

    def test_detect_quick_action_contact_patterns(self, conv_manager):
        """Test contact provider detection patterns"""
        assert conv_manager.detect_quick_action("6") == ActionType.CONTACT_PROVIDER
        assert conv_manager.detect_quick_action("contact") == ActionType.CONTACT_PROVIDER
        assert conv_manager.detect_quick_action("contacter") == ActionType.CONTACT_PROVIDER
        assert conv_manager.detect_quick_action("appeler") == ActionType.CONTACT_PROVIDER
        assert conv_manager.detect_quick_action("numéro de téléphone") == ActionType.CONTACT_PROVIDER

    def test_detect_quick_action_no_match(self, conv_manager):
        """Test no action detection for regular messages"""
        assert conv_manager.detect_quick_action("bonjour") is None
        assert conv_manager.detect_quick_action("j'ai une fuite d'eau") is None
        assert conv_manager.detect_quick_action("merci beaucoup") is None
        assert conv_manager.detect_quick_action("7") is None
        assert conv_manager.detect_quick_action("random text") is None


class TestQuickActionsIntegration:
    """Integration tests for quick actions system"""

    @pytest.mark.asyncio
    async def test_full_status_check_flow(self):
        """Test complete status check flow"""
        # This would test the full integration from webhook to response
        # Mock all dependencies and verify the complete flow
        pass

    @pytest.mark.asyncio
    async def test_full_cancel_request_flow(self):
        """Test complete request cancellation flow"""
        # This would test the full integration for request cancellation
        # Including confirmation handling and actual cancellation
        pass

    @pytest.mark.asyncio
    async def test_menu_display_after_confirmation(self):
        """Test that quick actions menu is displayed after service confirmation"""
        # This would test that the menu appears after a service request is created
        pass