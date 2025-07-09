#!/usr/bin/env python3
"""
Script d'initialisation de la base de données pour Djobea AI
Ce script crée les tables et seed les données initiales
"""

import os
import sys
import asyncio
from typing import Dict, Any

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_session, init_db
from app.models.database_models import *
from app.services.cultural_data_service import CulturalDataService
from loguru import logger


async def create_admin_user():
    """Créer un utilisateur admin par défaut"""
    try:
        with get_db_session() as db:
            # Vérifier si l'admin existe déjà
            admin_exists = db.query(User).filter(User.phone_number == "237600000000").first()
            
            if not admin_exists:
                admin_user = User(
                    phone_number="237600000000",
                    name="Admin",
                    email="admin@djobea.ai",
                    is_admin=True,
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                logger.info("Utilisateur admin créé avec succès")
            else:
                logger.info("Utilisateur admin déjà existant")
                
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'admin: {e}")


async def seed_default_providers():
    """Seed des prestataires par défaut"""
    try:
        with get_db_session() as db:
            # Vérifier si des prestataires existent déjà
            provider_count = db.query(Provider).count()
            
            if provider_count == 0:
                default_providers = [
                    {
                        "name": "Jean Plombier",
                        "phone_number": "237655001122",
                        "email": "jean.plombier@djobea.ai",
                        "service_type": "plomberie",
                        "location": "Bonamoussadi",
                        "is_active": True,
                        "rating": 4.5,
                        "years_experience": 8,
                        "bio": "Spécialiste en plomberie avec 8 ans d'expérience",
                        "is_verified": True
                    },
                    {
                        "name": "Marie Électricienne",
                        "phone_number": "237655002233",
                        "email": "marie.electricienne@djobea.ai",
                        "service_type": "électricité",
                        "location": "Bonamoussadi",
                        "is_active": True,
                        "rating": 4.7,
                        "years_experience": 6,
                        "bio": "Électricienne certifiée, interventions rapides",
                        "is_verified": True
                    },
                    {
                        "name": "Paul Réparateur",
                        "phone_number": "237655003344",
                        "email": "paul.reparateur@djobea.ai",
                        "service_type": "réparation électroménager",
                        "location": "Bonamoussadi",
                        "is_active": True,
                        "rating": 4.3,
                        "years_experience": 5,
                        "bio": "Réparation d'électroménager toutes marques",
                        "is_verified": True
                    }
                ]
                
                for provider_data in default_providers:
                    provider = Provider(**provider_data)
                    db.add(provider)
                
                db.commit()
                logger.info(f"Seeded {len(default_providers)} prestataires par défaut")
            else:
                logger.info(f"{provider_count} prestataires déjà existants")
                
    except Exception as e:
        logger.error(f"Erreur lors du seed des prestataires: {e}")


async def seed_cultural_data():
    """Seed des données culturelles"""
    try:
        with get_db_session() as db:
            cultural_service = CulturalDataService(db)
            await cultural_service.seed_all_cultural_data()
            logger.info("Données culturelles seedées avec succès")
            
    except Exception as e:
        logger.error(f"Erreur lors du seed des données culturelles: {e}")


async def run_migrations():
    """Exécuter les migrations de base de données"""
    try:
        logger.info("Initialisation de la base de données...")
        init_db()
        logger.info("Base de données initialisée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
        raise


async def main():
    """Fonction principale d'initialisation"""
    logger.info("Démarrage de l'initialisation de la base de données...")
    
    try:
        # Attendre que la base de données soit prête
        await asyncio.sleep(5)
        
        # Exécuter les migrations
        await run_migrations()
        
        # Créer l'utilisateur admin
        await create_admin_user()
        
        # Seed des prestataires par défaut
        await seed_default_providers()
        
        # Seed des données culturelles
        await seed_cultural_data()
        
        logger.info("Initialisation de la base de données terminée avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())