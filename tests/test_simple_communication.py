"""
Simple test for Enhanced Communication Service
Tests core functionality without complex dependencies
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.communication_service import CommunicationService


class TestCommunicationBasics:
    """Test basic communication service functionality"""
    
    def test_pricing_estimates_configuration(self):
        """Test that pricing estimates are correctly configured"""
        service = CommunicationService()
        
        # Test plomberie pricing
        plomberie_pricing = service.get_pricing_estimate("plomberie")
        assert plomberie_pricing["min"] == 5000
        assert plomberie_pricing["max"] == 15000
        assert "Intervention de base" in plomberie_pricing["description"]
        
        # Test électricité pricing
        electricite_pricing = service.get_pricing_estimate("électricité")
        assert electricite_pricing["min"] == 3000
        assert electricite_pricing["max"] == 10000
        
        # Test réparation électroménager pricing
        electromenager_pricing = service.get_pricing_estimate("réparation électroménager")
        assert electromenager_pricing["min"] == 2000
        assert electromenager_pricing["max"] == 8000
    
    def test_price_formatting(self):
        """Test XAF price formatting"""
        service = CommunicationService()
        
        pricing = {"min": 5000, "max": 15000}
        formatted = service.format_price_range(pricing)
        assert formatted == "5 000 - 15 000 XAF"
        
        # Test larger numbers
        pricing = {"min": 25000, "max": 150000}
        formatted = service.format_price_range(pricing)
        assert formatted == "25 000 - 150 000 XAF"
    
    def test_confirmation_message_generation(self):
        """Test confirmation message generation"""
        service = CommunicationService()
        
        message = service._generate_confirmation_message(
            "plomberie", "Bonamoussadi", "5 000 - 15 000 XAF", "Intervention de base"
        )
        
        assert "✅ *Demande reçue et confirmée !*" in message
        assert "🔧 *Service* : Plomberie" in message
        assert "📍 *Zone* : Bonamoussadi" in message
        assert "5 000 - 15 000 XAF" in message
        assert "Intervention de base" in message
        assert "🔍 *Recherche en cours...*" in message
        assert "⏱ *Réponse attendue* : sous 5 minutes" in message
    
    def test_service_emojis(self):
        """Test that service-specific emojis are used correctly"""
        service = CommunicationService()
        
        # Test plomberie
        message = service._generate_confirmation_message(
            "plomberie", "Bonamoussadi", "5 000 - 15 000 XAF", "Intervention de base"
        )
        assert "🔧 *Service* : Plomberie" in message
        
        # Test électricité
        message = service._generate_confirmation_message(
            "électricité", "Bonamoussadi", "3 000 - 10 000 XAF", "Diagnostic standard"
        )
        assert "⚡ *Service* : Électricité" in message
        
        # Test réparation électroménager
        message = service._generate_confirmation_message(
            "réparation électroménager", "Bonamoussadi", "2 000 - 8 000 XAF", "Réparation courante"
        )
        assert "🏠 *Service* : Réparation Électroménager" in message
    
    def test_configuration_validation(self):
        """Test that communication settings are properly configured"""
        from app.config import get_settings
        
        settings = get_settings()
        
        # Verify timing settings exist
        assert hasattr(settings, 'instant_confirmation_seconds')
        assert hasattr(settings, 'proactive_update_interval_minutes')
        assert hasattr(settings, 'urgent_update_interval_minutes')
        assert hasattr(settings, 'countdown_threshold_minutes')
        
        # Verify pricing configuration exists
        assert hasattr(settings, 'service_pricing')
        service_pricing = settings.service_pricing
        
        # Verify all supported services have pricing
        supported_services = settings.supported_services
        for service in supported_services:
            assert service in service_pricing, f"Service {service} missing pricing configuration"
            
            pricing = service_pricing[service]
            assert "min" in pricing, f"Service {service} missing min price"
            assert "max" in pricing, f"Service {service} missing max price"
            assert "description" in pricing, f"Service {service} missing description"
            assert pricing["min"] > 0, f"Service {service} min price must be positive"
            assert pricing["max"] >= pricing["min"], f"Service {service} max price must be >= min price"
    
    def test_communication_service_import(self):
        """Test that communication service can be imported in webhook"""
        try:
            from app.services.communication_service import CommunicationService
            service = CommunicationService()
            assert service is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CommunicationService: {e}")
    
    def test_task_management_methods(self):
        """Test that task management methods exist"""
        service = CommunicationService()
        
        # Verify methods exist
        assert hasattr(service, 'start_proactive_updates')
        assert hasattr(service, 'stop_proactive_updates')
        assert hasattr(service, 'send_instant_confirmation')
        assert hasattr(service, 'send_provider_acceptance')
        assert hasattr(service, 'send_error_message')
        
        # Verify active_tasks dict exists
        assert hasattr(service, 'active_tasks')
        assert isinstance(service.active_tasks, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])