"""
Sprint 3 - Provider seed data for testing matching system
Creates sample providers with realistic data for Douala/Bonamoussadi area
"""

from sqlalchemy.orm import Session
from app.models.database_models import Provider
from app.database import get_db
import json


def seed_providers(db: Session):
    """Seed database with sample providers for testing"""
    
    providers_data = [
        {
            "name": "Jean-Baptiste Plombier",
            "whatsapp_id": "whatsapp:+237690111111",
            "phone_number": "+237690111111",
            "services": ["plomberie"],
            "coverage_areas": ["bonamoussadi", "makepe", "station_shell"],
            "is_available": True,
            "is_active": True,
            "rating": 4.7,
            "total_jobs": 35
        },
        {
            "name": "Marie Électricienne Pro",
            "whatsapp_id": "whatsapp:+237690222222", 
            "phone_number": "+237690222222",
            "services": ["électricité"],
            "coverage_areas": ["bonamoussadi", "akwa", "bonapriso"],
            "is_available": True,
            "is_active": True,
            "rating": 4.5,
            "total_jobs": 42
        },
        {
            "name": "Paul Réparateur Multi-services",
            "whatsapp_id": "whatsapp:+237690333333",
            "phone_number": "+237690333333", 
            "services": ["réparation électroménager", "électricité"],
            "coverage_areas": ["makepe", "station_total", "carrefour"],
            "is_available": True,
            "is_active": True,
            "rating": 4.3,
            "total_jobs": 28
        },
        {
            "name": "Amélie Plombière Experte",
            "whatsapp_id": "whatsapp:+237690444444",
            "phone_number": "+237690444444",
            "services": ["plomberie"],
            "coverage_areas": ["bonamoussadi", "deido", "marché"],
            "is_available": True,
            "is_active": True,
            "rating": 4.9,
            "total_jobs": 67
        },
        {
            "name": "David Électricien Urgence",
            "whatsapp_id": "whatsapp:+237690555555",
            "phone_number": "+237690555555",
            "services": ["électricité"],
            "coverage_areas": ["akwa", "bonanjo", "deido"],
            "is_available": False,  # Currently busy
            "is_active": True,
            "rating": 4.1,
            "total_jobs": 19
        },
        {
            "name": "Sophie Service Électroménager",
            "whatsapp_id": "whatsapp:+237690666666",
            "phone_number": "+237690666666",
            "services": ["réparation électroménager"],
            "coverage_areas": ["bonamoussadi", "makepe", "cite_sic"],
            "is_available": True,
            "is_active": True,
            "rating": 4.6,
            "total_jobs": 51
        },
        {
            "name": "André Multi-Technique",
            "whatsapp_id": "whatsapp:+237690777777",
            "phone_number": "+237690777777",
            "services": ["plomberie", "électricité", "réparation électroménager"],
            "coverage_areas": ["makepe", "logbaba", "pk8"],
            "is_available": True,
            "is_active": True,
            "rating": 3.8,  # Lower rating due to being generalist
            "total_jobs": 73
        },
        {
            "name": "Christine Plomberie Spécialisée",
            "whatsapp_id": "whatsapp:+237690888888",
            "phone_number": "+237690888888",
            "services": ["plomberie"],
            "coverage_areas": ["bonamoussadi", "bonapriso"],
            "is_available": True,
            "is_active": True,
            "rating": 4.8,
            "total_jobs": 29
        }
    ]
    
    # Check if providers already exist
    existing_count = db.query(Provider).count()
    if existing_count > 0:
        print(f"Database already has {existing_count} providers. Skipping seed.")
        return
    
    # Create providers
    for provider_data in providers_data:
        provider = Provider(**provider_data)
        db.add(provider)
    
    db.commit()
    print(f"Successfully seeded {len(providers_data)} providers to database")


def reset_providers(db: Session):
    """Reset all providers - for testing only"""
    db.query(Provider).delete()
    db.commit()
    seed_providers(db)
    print("Providers reset and reseeded")


if __name__ == "__main__":
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        seed_providers(db)
    finally:
        db.close()