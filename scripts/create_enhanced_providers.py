"""
Script to create enhanced provider profiles with trust-building features
Run this to populate the database with comprehensive provider data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import (
    Provider, ProviderReview, ProviderPhoto, ProviderCertification, 
    ProviderSpecialization, User
)

def create_enhanced_providers():
    """Create comprehensive provider profiles with trust indicators"""
    
    db = next(get_db())
    
    try:
        # Get or create sample users for reviews
        users = []
        for i in range(1, 6):
            whatsapp_id = f"237690000{i:03d}"
            user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
            if not user:
                user = User(
                    whatsapp_id=whatsapp_id,
                    name=f"Client Test {i}",
                    phone_number=f"+237690000{i:03d}"
                )
                db.add(user)
            users.append(user)
        
        db.commit()
        
        # Enhanced Provider 1: Expert Plumber - Update existing or create new
        provider1 = db.query(Provider).filter(Provider.whatsapp_id == "237677123456").first()
        if not provider1:
            provider1 = Provider(
                name="Jean-Claude Mbida",
                whatsapp_id="237677123456",
                phone_number="+237677123456",
                services=["plomberie"],
                coverage_areas=["Bonamoussadi", "Bonapriso", "Deido"],
                rating=4.8,
                total_jobs=156,
                is_available=True,
                is_active=True
            )
            db.add(provider1)
        
        # Update with enhanced profile data
        provider1.years_experience = 8
        provider1.specialties = ["Installations sanitaires", "Réparation fuites", "Débouchage canalisations"]
        provider1.profile_photo_url = "/static/images/providers/jean_claude.jpg"
        provider1.bio = "Plombier expert avec 8 ans d'expérience. Spécialisé dans les installations sanitaires et les urgences."
        provider1.certifications = ["Certificat professionnel plomberie", "Formation sécurité"]
        provider1.response_time_avg = 7.5
        provider1.acceptance_rate = 92.0
        provider1.completion_rate = 98.5
        provider1.last_active = datetime.utcnow() - timedelta(minutes=5)
        provider1.verification_status = "verified"
        provider1.id_verified = True
        provider1.insurance_verified = True
        provider1.emergency_availability = True
        provider1.preferred_hours = {"start": "07:00", "end": "19:00", "weekend": True}
        provider1.minimum_job_value = 3000.0
        
        db.commit()
        
        # Enhanced Provider 2: Experienced Electrician - Update existing or create new
        provider2 = db.query(Provider).filter(Provider.whatsapp_id == "237681234567").first()
        if not provider2:
            provider2 = Provider(
                name="Marie Fotso",
                whatsapp_id="237681234567",
                phone_number="+237681234567",
                services=["électricité"],
                coverage_areas=["Bonamoussadi", "Akwa", "Makepe"],
                rating=4.7,
                total_jobs=203,
                is_available=True,
                is_active=True
            )
            db.add(provider2)
        
        # Update with enhanced profile data
        provider2.years_experience = 12
        provider2.specialties = ["Installation électrique", "Dépannage urgence", "Éclairage LED"]
        provider2.profile_photo_url = "/static/images/providers/marie_fotso.jpg"
        provider2.bio = "Électricienne certifiée avec 12 ans d'expérience. Experte en installations résidentielles et commerciales."
        provider2.certifications = ["Habilitation électrique B2V", "Formation sécurité électrique"]
        provider2.response_time_avg = 5.2
        provider2.acceptance_rate = 89.0
        provider2.completion_rate = 96.8
        provider2.last_active = datetime.utcnow() - timedelta(minutes=12)
        provider2.verification_status = "verified"
        provider2.id_verified = True
        provider2.insurance_verified = True
        provider2.emergency_availability = True
        provider2.preferred_hours = {"start": "06:00", "end": "20:00", "weekend": True}
        provider2.minimum_job_value = 2500.0
        
        db.commit()
        
        # Enhanced Provider 3: Appliance Repair Specialist - Update existing or create new
        provider3 = db.query(Provider).filter(Provider.whatsapp_id == "237692345678").first()
        if not provider3:
            provider3 = Provider(
                name="Paul Nguema",
                whatsapp_id="237692345678",
                phone_number="+237692345678",
                services=["réparation électroménager"],
                coverage_areas=["Bonamoussadi", "Logpom", "Bali"],
                rating=4.5,
                total_jobs=89,
                is_available=True,
                is_active=True
            )
            db.add(provider3)
        
        # Update with enhanced profile data
        provider3.years_experience = 6
        provider3.specialties = ["Réfrigérateurs", "Machines à laver", "Climatiseurs"]
        provider3.profile_photo_url = "/static/images/providers/paul_nguema.jpg"
        provider3.bio = "Spécialiste en réparation d'électroménager. Formation technique et pièces d'origine garanties."
        provider3.certifications = ["Certificat technique électroménager", "Formation réfrigération"]
        provider3.response_time_avg = 12.3
        provider3.acceptance_rate = 85.0
        provider3.completion_rate = 94.2
        provider3.last_active = datetime.utcnow() - timedelta(minutes=25)
        provider3.verification_status = "verified"
        provider3.id_verified = True
        provider3.insurance_verified = False
        provider3.emergency_availability = False
        provider3.preferred_hours = {"start": "08:00", "end": "18:00", "weekend": False}
        provider3.minimum_job_value = 2000.0
        
        db.commit()
        
        # Create reviews for providers
        reviews_data = [
            # Reviews for Jean-Claude (Provider 1)
            {
                "provider_id": provider1.id,
                "user_id": users[0].id,
                "rating": 5,
                "comment": "Excellent travail ! Jean-Claude a réparé ma fuite d'eau rapidement et proprement. Très professionnel.",
                "service_quality": 5,
                "punctuality": 5,
                "professionalism": 5,
                "value_for_money": 4,
                "is_featured": True
            },
            {
                "provider_id": provider1.id,
                "user_id": users[1].id,
                "rating": 5,
                "comment": "Intervention rapide et efficace. Prix raisonnable. Je recommande vivement.",
                "service_quality": 5,
                "punctuality": 4,
                "professionalism": 5,
                "value_for_money": 5,
                "helpful_count": 3
            },
            {
                "provider_id": provider1.id,
                "user_id": users[2].id,
                "rating": 4,
                "comment": "Bon plombier, travail soigné. Juste un peu cher mais qualité au rendez-vous.",
                "service_quality": 4,
                "punctuality": 5,
                "professionalism": 4,
                "value_for_money": 3
            },
            # Reviews for Marie (Provider 2)
            {
                "provider_id": provider2.id,
                "user_id": users[3].id,
                "rating": 5,
                "comment": "Marie est une vraie professionnelle ! Installation électrique parfaite.",
                "service_quality": 5,
                "punctuality": 5,
                "professionalism": 5,
                "value_for_money": 4,
                "is_featured": True
            },
            {
                "provider_id": provider2.id,
                "user_id": users[4].id,
                "rating": 4,
                "comment": "Très compétente et rapide. Explique bien ce qu'elle fait.",
                "service_quality": 5,
                "punctuality": 4,
                "professionalism": 5,
                "value_for_money": 4,
                "helpful_count": 2
            },
            # Reviews for Paul (Provider 3)
            {
                "provider_id": provider3.id,
                "user_id": users[0].id,
                "rating": 4,
                "comment": "A bien réparé mon frigo. Pièces de qualité et garantie respectée.",
                "service_quality": 4,
                "punctuality": 4,
                "professionalism": 4,
                "value_for_money": 4
            }
        ]
        
        for review_data in reviews_data:
            review = ProviderReview(**review_data)
            db.add(review)
        
        # Create certifications
        certifications = [
            {
                "provider_id": provider1.id,
                "name": "Certificat Professionnel de Plomberie",
                "issuing_authority": "Centre de Formation Professionnelle de Douala",
                "certificate_number": "CPP-2018-0456",
                "issue_date": date(2018, 6, 15),
                "expiry_date": date(2023, 6, 15),
                "is_verified": True,
                "verification_date": datetime(2023, 1, 10),
                "display_order": 1
            },
            {
                "provider_id": provider2.id,
                "name": "Habilitation Électrique B2V",
                "issuing_authority": "Institut National de Formation Technique",
                "certificate_number": "HE-B2V-2019-0789",
                "issue_date": date(2019, 3, 20),
                "expiry_date": date(2024, 3, 20),
                "is_verified": True,
                "verification_date": datetime(2023, 2, 5),
                "display_order": 1
            },
            {
                "provider_id": provider3.id,
                "name": "Certificat Technique Électroménager",
                "issuing_authority": "École Technique de Douala",
                "certificate_number": "CTE-2020-0123",
                "issue_date": date(2020, 9, 10),
                "is_verified": True,
                "verification_date": datetime(2023, 1, 15),
                "display_order": 1
            }
        ]
        
        for cert_data in certifications:
            cert = ProviderCertification(**cert_data)
            db.add(cert)
        
        # Create specializations
        specializations = [
            # Jean-Claude specializations
            {
                "provider_id": provider1.id,
                "service_type": "plomberie",
                "specialization": "Installation sanitaire complète",
                "skill_level": "expert",
                "years_experience": 8,
                "min_rate": 5000.0,
                "max_rate": 15000.0,
                "rate_type": "negotiable"
            },
            {
                "provider_id": provider1.id,
                "service_type": "plomberie",
                "specialization": "Réparation fuites urgences",
                "skill_level": "expert",
                "years_experience": 8,
                "min_rate": 3000.0,
                "max_rate": 8000.0,
                "rate_type": "fixed"
            },
            # Marie specializations
            {
                "provider_id": provider2.id,
                "service_type": "électricité",
                "specialization": "Installation électrique résidentielle",
                "skill_level": "expert",
                "years_experience": 12,
                "min_rate": 4000.0,
                "max_rate": 12000.0,
                "rate_type": "negotiable"
            },
            {
                "provider_id": provider2.id,
                "service_type": "électricité",
                "specialization": "Dépannage électrique urgent",
                "skill_level": "expert",
                "years_experience": 12,
                "min_rate": 3000.0,
                "max_rate": 7000.0,
                "rate_type": "fixed"
            },
            # Paul specializations
            {
                "provider_id": provider3.id,
                "service_type": "réparation électroménager",
                "specialization": "Réparation réfrigérateurs",
                "skill_level": "expert",
                "years_experience": 6,
                "min_rate": 2500.0,
                "max_rate": 6000.0,
                "rate_type": "fixed"
            },
            {
                "provider_id": provider3.id,
                "service_type": "réparation électroménager",
                "specialization": "Réparation machines à laver",
                "skill_level": "intermediate",
                "years_experience": 4,
                "min_rate": 2000.0,
                "max_rate": 5000.0,
                "rate_type": "fixed"
            }
        ]
        
        for spec_data in specializations:
            spec = ProviderSpecialization(**spec_data)
            db.add(spec)
        
        # Create portfolio photos
        photos = [
            # Jean-Claude photos
            {
                "provider_id": provider1.id,
                "photo_url": "/static/images/portfolio/plumbing_1.jpg",
                "photo_type": "work",
                "title": "Installation complète salle de bain",
                "description": "Installation sanitaire moderne avec robinetterie haut de gamme",
                "service_type": "plomberie",
                "is_featured": True,
                "display_order": 1
            },
            {
                "provider_id": provider1.id,
                "photo_url": "/static/images/portfolio/plumbing_2.jpg",
                "photo_type": "before",
                "title": "Avant réparation fuite",
                "description": "État avant intervention sur fuite majeure",
                "service_type": "plomberie",
                "display_order": 2
            },
            # Marie photos
            {
                "provider_id": provider2.id,
                "photo_url": "/static/images/portfolio/electrical_1.jpg",
                "photo_type": "work",
                "title": "Installation électrique cuisine",
                "description": "Rénovation complète installation électrique cuisine moderne",
                "service_type": "électricité",
                "is_featured": True,
                "display_order": 1
            },
            # Paul photos
            {
                "provider_id": provider3.id,
                "photo_url": "/static/images/portfolio/appliance_1.jpg",
                "photo_type": "work",
                "title": "Réparation réfrigérateur",
                "description": "Remplacement compresseur réfrigérateur Samsung",
                "service_type": "réparation électroménager",
                "is_featured": True,
                "display_order": 1
            }
        ]
        
        for photo_data in photos:
            photo = ProviderPhoto(**photo_data)
            db.add(photo)
        
        db.commit()
        
        print("✅ Enhanced providers created successfully!")
        print(f"Created {len([provider1, provider2, provider3])} providers with:")
        print(f"- {len(reviews_data)} reviews")
        print(f"- {len(certifications)} certifications")
        print(f"- {len(specializations)} specializations")
        print(f"- {len(photos)} portfolio photos")
        
        # Display provider trust scores
        db.refresh(provider1)
        db.refresh(provider2)
        db.refresh(provider3)
        
        print("\n📊 Provider Trust Scores:")
        print(f"- {provider1.name}: {provider1.trust_score:.1f}/100")
        print(f"- {provider2.name}: {provider2.trust_score:.1f}/100")
        print(f"- {provider3.name}: {provider3.trust_score:.1f}/100")
        
    except Exception as e:
        print(f"❌ Error creating enhanced providers: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_enhanced_providers()