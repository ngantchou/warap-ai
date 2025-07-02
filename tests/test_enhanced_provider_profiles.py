"""
Tests for enhanced provider profiles and trust-building features

Tests the provider profile service, trust scoring, and enhanced communication
"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import Mock, AsyncMock, patch

from app.services.provider_profile_service import ProviderProfileService
from app.services.communication_service import CommunicationService
from app.models.database_models import (
    Provider, User, ServiceRequest, ProviderReview, ProviderPhoto,
    ProviderCertification, ProviderSpecialization, RequestStatus
)


class TestProviderProfileService:
    """Test comprehensive provider profile functionality"""
    
    def test_calculate_trust_score_basic_provider(self, test_db):
        """Test trust score calculation for basic provider"""
        provider = Provider(
            name="Test Provider",
            whatsapp_id="237600000000",
            phone_number="+237600000000",
            services=["plomberie"],
            coverage_areas=["Bonamoussadi"],
            rating=4.5,
            total_jobs=50,
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        test_db.commit()
        
        service = ProviderProfileService(test_db)
        score = service.calculate_trust_score(provider.id)
        
        # Basic provider should have moderate trust score
        assert 40 <= score <= 70
        assert isinstance(score, float)
    
    def test_calculate_trust_score_enhanced_provider(self, test_db):
        """Test trust score calculation for provider with enhanced profile"""
        provider = Provider(
            name="Enhanced Provider",
            whatsapp_id="237600000001",
            phone_number="+237600000001",
            services=["électricité"],
            coverage_areas=["Bonamoussadi"],
            rating=4.8,
            total_jobs=100,
            years_experience=10,
            verification_status="verified",
            id_verified=True,
            insurance_verified=True,
            response_time_avg=5.0,
            acceptance_rate=95.0,
            completion_rate=98.0,
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        test_db.commit()
        
        # Add certifications
        certification = ProviderCertification(
            provider_id=provider.id,
            name="Professional Certification",
            issuing_authority="Technical Institute",
            is_verified=True,
            verification_date=datetime.utcnow()
        )
        test_db.add(certification)
        
        # Add positive reviews
        user = User(
            whatsapp_id="237690000001",
            name="Test Client",
            phone_number="+237690000001"
        )
        test_db.add(user)
        test_db.commit()
        
        review = ProviderReview(
            provider_id=provider.id,
            user_id=user.id,
            rating=5,
            comment="Excellent work!",
            service_quality=5,
            punctuality=5,
            professionalism=5,
            value_for_money=5
        )
        test_db.add(review)
        test_db.commit()
        
        service = ProviderProfileService(test_db)
        score = service.calculate_trust_score(provider.id)
        
        # Enhanced provider should have high trust score
        assert score >= 80
        assert isinstance(score, float)
    
    def test_generate_provider_introduction(self, test_db):
        """Test provider introduction generation"""
        provider = Provider(
            name="Marie Electricienne",
            whatsapp_id="237600000002",
            phone_number="+237600000002",
            services=["électricité"],
            coverage_areas=["Bonamoussadi"],
            rating=4.7,
            total_jobs=75,
            years_experience=8,
            bio="Électricienne expérimentée spécialisée en installations résidentielles",
            specialties=["Installation électrique", "Dépannage"],
            verification_status="verified",
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        test_db.commit()
        
        service = ProviderProfileService(test_db)
        intro = service.generate_provider_introduction(provider.id)
        
        assert isinstance(intro, dict)
        assert "message" in intro
        assert "trust_score" in intro
        assert "provider_id" in intro
        
        message = intro["message"]
        assert "Marie Electricienne" in message
        assert "Score de confiance" in message
        assert "Contact" in message
        assert provider.phone_number in message
    
    def test_generate_trust_explanation(self, test_db):
        """Test trust explanation generation"""
        provider = Provider(
            name="Paul Technicien",
            whatsapp_id="237600000003",
            phone_number="+237600000003",
            services=["réparation électroménager"],
            coverage_areas=["Bonamoussadi"],
            rating=4.6,
            total_jobs=60,
            years_experience=6,
            verification_status="verified",
            id_verified=True,
            emergency_availability=True,
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        test_db.commit()
        
        service = ProviderProfileService(test_db)
        explanation = service.generate_trust_explanation(provider.id, "réparation électroménager")
        
        assert isinstance(explanation, str)
        assert "Pourquoi Paul Technicien?" in explanation
        assert "✅" in explanation
        # Should mention verification or other trust factors
        assert any(keyword in explanation.lower() for keyword in [
            "vérifié", "expérience", "note", "disponible", "urgence"
        ])
    
    def test_get_provider_specializations(self, test_db):
        """Test retrieving provider specializations"""
        provider = Provider(
            name="Specialist Provider",
            whatsapp_id="237600000004",
            phone_number="+237600000004",
            services=["plomberie"],
            coverage_areas=["Bonamoussadi"],
            rating=4.5,
            total_jobs=40,
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        test_db.commit()
        
        # Add specializations
        spec1 = ProviderSpecialization(
            provider_id=provider.id,
            service_type="plomberie",
            specialization="Installation sanitaire",
            skill_level="expert",
            years_experience=5,
            min_rate=3000.0,
            max_rate=8000.0
        )
        spec2 = ProviderSpecialization(
            provider_id=provider.id,
            service_type="plomberie",
            specialization="Réparation fuites",
            skill_level="expert",
            years_experience=5,
            min_rate=2000.0,
            max_rate=5000.0
        )
        test_db.add_all([spec1, spec2])
        test_db.commit()
        
        service = ProviderProfileService(test_db)
        specializations = service.get_provider_specializations(provider.id, "plomberie")
        
        assert len(specializations) == 2
        assert all(spec.service_type == "plomberie" for spec in specializations)
        assert "Installation sanitaire" in [spec.specialization for spec in specializations]
        assert "Réparation fuites" in [spec.specialization for spec in specializations]
    
    def test_get_provider_reviews_summary(self, test_db):
        """Test provider reviews summary generation"""
        provider = Provider(
            name="Reviewed Provider",
            whatsapp_id="237600000005",
            phone_number="+237600000005",
            services=["électricité"],
            coverage_areas=["Bonamoussadi"],
            rating=4.5,
            total_jobs=30,
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        test_db.commit()
        
        # Add test users
        users = []
        for i in range(3):
            user = User(
                whatsapp_id=f"23769000000{i+10}",
                name=f"Client {i+1}",
                phone_number=f"+23769000000{i+10}"
            )
            test_db.add(user)
            users.append(user)
        test_db.commit()
        
        # Add reviews
        reviews_data = [
            {"rating": 5, "comment": "Excellent travail, très professionnel", "is_featured": True},
            {"rating": 4, "comment": "Bon service, recommandé", "is_featured": False},
            {"rating": 5, "comment": "Rapide et efficace", "is_featured": True}
        ]
        
        for i, review_data in enumerate(reviews_data):
            review = ProviderReview(
                provider_id=provider.id,
                user_id=users[i].id,
                **review_data,
                service_quality=review_data["rating"],
                punctuality=review_data["rating"],
                professionalism=review_data["rating"],
                value_for_money=review_data["rating"] - 1 if review_data["rating"] > 1 else 5
            )
            test_db.add(review)
        test_db.commit()
        
        service = ProviderProfileService(test_db)
        summary = service.get_provider_reviews_summary(provider.id)
        
        assert isinstance(summary, dict)
        assert "total_reviews" in summary
        assert "average_rating" in summary
        assert "featured_reviews" in summary
        assert "rating_breakdown" in summary
        
        assert summary["total_reviews"] == 3
        assert summary["average_rating"] > 4.0
        assert len(summary["featured_reviews"]) == 2  # Two featured reviews


class TestEnhancedCommunicationFlow:
    """Test enhanced communication with provider profiles"""
    
    @pytest.mark.asyncio
    async def test_enhanced_provider_acceptance_message(self, test_db):
        """Test enhanced provider acceptance notification with profile data"""
        # Create enhanced provider
        provider = Provider(
            name="Expert Plombier",
            whatsapp_id="237600000010",
            phone_number="+237600000010",
            services=["plomberie"],
            coverage_areas=["Bonamoussadi"],
            rating=4.8,
            total_jobs=120,
            years_experience=10,
            bio="Plombier expert avec 10 ans d'expérience",
            specialties=["Installation", "Réparation urgence"],
            verification_status="verified",
            id_verified=True,
            insurance_verified=True,
            is_available=True,
            is_active=True
        )
        test_db.add(provider)
        
        user = User(
            whatsapp_id="237690000020",
            name="Test Client",
            phone_number="+237690000020"
        )
        test_db.add(user)
        test_db.commit()
        
        request = ServiceRequest(
            user_id=user.id,
            service_type="plomberie",
            description="Fuite dans la cuisine",
            location="Bonamoussadi",
            status=RequestStatus.PENDING,
            estimated_price=5000.0
        )
        test_db.add(request)
        test_db.commit()
        
        # Mock WhatsApp service
        mock_whatsapp = AsyncMock()
        mock_whatsapp.send_message.return_value = True
        
        # Create communication service with mocked WhatsApp
        with patch('app.services.communication_service.WhatsAppService', return_value=mock_whatsapp):
            comm_service = CommunicationService()
            
            success = await comm_service.send_provider_acceptance(
                request.id, provider.id, test_db
            )
            
            assert success is True
            mock_whatsapp.send_message.assert_called_once()
            
            # Verify message content includes enhanced profile information
            call_args = mock_whatsapp.send_message.call_args
            message = call_args[0][1]  # Second argument is the message
            
            assert "Expert Plombier" in message
            assert "Score de confiance" in message
            assert "Pourquoi Expert Plombier?" in message
            assert "Prochaines étapes" in message
            assert "Paiement sécurisé" in message
    
    @pytest.mark.asyncio
    async def test_provider_introduction_generation(self, test_db):
        """Test provider introduction generation for different provider types"""
        # Test with basic provider
        basic_provider = Provider(
            name="Basic Provider",
            whatsapp_id="237600000020",
            phone_number="+237600000020",
            services=["plomberie"],
            coverage_areas=["Bonamoussadi"],
            rating=4.0,
            total_jobs=20,
            is_available=True,
            is_active=True
        )
        test_db.add(basic_provider)
        test_db.commit()
        
        service = ProviderProfileService(test_db)
        basic_intro = service.generate_provider_introduction(basic_provider.id)
        
        # Should contain basic information
        assert "Basic Provider" in basic_intro["message"]
        assert "Score de confiance" in basic_intro["message"]
        assert basic_intro["trust_score"] < 80  # Basic provider has lower score
        
        # Test with enhanced provider
        enhanced_provider = Provider(
            name="Enhanced Provider",
            whatsapp_id="237600000021",
            phone_number="+237600000021",
            services=["électricité"],
            coverage_areas=["Bonamoussadi"],
            rating=4.9,
            total_jobs=150,
            years_experience=12,
            bio="Expert électricien certifié",
            verification_status="verified",
            id_verified=True,
            insurance_verified=True,
            response_time_avg=3.0,
            acceptance_rate=98.0,
            completion_rate=99.0,
            is_available=True,
            is_active=True
        )
        test_db.add(enhanced_provider)
        test_db.commit()
        
        enhanced_intro = service.generate_provider_introduction(enhanced_provider.id)
        
        # Should contain enhanced information and higher trust score
        assert "Enhanced Provider" in enhanced_intro["message"]
        assert enhanced_intro["trust_score"] > basic_intro["trust_score"]
        assert enhanced_intro["trust_score"] >= 80  # Enhanced provider has higher score


@pytest.fixture
def test_db():
    """Create test database session"""
    from app.database import get_db
    return next(get_db())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])