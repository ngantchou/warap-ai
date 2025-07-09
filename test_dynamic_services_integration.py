#!/usr/bin/env python3
"""
Test d'intégration des services dynamiques avec le LLM Conversation Manager
Vérifie que les services et zones sont correctement récupérés de la base de données
"""

import asyncio
import json
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from datetime import datetime

# Ajouter le chemin de l'app au PYTHONPATH
sys.path.insert(0, '/tmp/workspace/app')
sys.path.insert(0, '/tmp/workspace')

from app.services.llm_conversation_manager import LLMConversationManager
from app.models.database_models import Base
from app.models.dynamic_services import Service, Zone, ServiceCategory

class DynamicServicesTest:
    """Test d'intégration des services dynamiques"""
    
    def __init__(self):
        """Initialisation du test"""
        self.engine = create_engine(os.environ.get('DATABASE_URL'))
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def test_dynamic_services_retrieval(self):
        """Test de récupération des services dynamiques"""
        print("=== Test de récupération des services dynamiques ===")
        
        db = self.SessionLocal()
        try:
            # Créer le manager de conversation
            manager = LLMConversationManager(db)
            
            # Test asynchrone
            async def test_async():
                # Récupérer les services dynamiques
                services = await manager._get_dynamic_services()
                print(f"Services trouvés: {len(services)}")
                
                for service in services:
                    print(f"  - {service['name']}: {service['description']}")
                    if service['min_price'] and service['max_price']:
                        print(f"    Prix: {service['min_price']} - {service['max_price']} XAF")
                
                # Récupérer les zones dynamiques
                zones = await manager._get_dynamic_zones()
                print(f"\nZones trouvées: {len(zones)}")
                
                for zone in zones:
                    print(f"  - {zone['name']} ({zone['type']})")
                
                return services, zones
            
            # Exécuter le test asynchrone
            services, zones = asyncio.run(test_async())
            
            # Vérifications
            assert len(services) > 0, "Aucun service trouvé"
            assert len(zones) > 0, "Aucune zone trouvée"
            
            print("\n✓ Test de récupération réussi")
            return True
            
        except Exception as e:
            print(f"✗ Erreur dans le test: {e}")
            return False
        finally:
            db.close()
    
    def test_faq_response_with_dynamic_data(self):
        """Test de génération de réponse FAQ avec données dynamiques"""
        print("\n=== Test de génération FAQ avec données dynamiques ===")
        
        db = self.SessionLocal()
        try:
            manager = LLMConversationManager(db)
            
            async def test_async():
                # Simuler une demande FAQ
                response = await manager.process_message(
                    user_identifier="test_user_dynamic",
                    message="services disponibles",
                    session_id="test_session"
                )
                
                print(f"Réponse générée: {response['response'][:200]}...")
                
                # Vérifier que la réponse contient des informations dynamiques
                response_text = response['response']
                
                # Vérifier la présence d'informations de services
                assert "plomberie" in response_text.lower() or "Plomberie" in response_text
                assert "électricité" in response_text.lower() or "Électricité" in response_text
                assert "électroménager" in response_text.lower() or "Électroménager" in response_text
                
                # Vérifier la présence d'informations de zones
                assert "bonamoussadi" in response_text.lower() or "Bonamoussadi" in response_text
                
                return response
            
            response = asyncio.run(test_async())
            
            print("✓ Test de génération FAQ réussi")
            return True
            
        except Exception as e:
            print(f"✗ Erreur dans le test FAQ: {e}")
            return False
        finally:
            db.close()
    
    def test_database_content(self):
        """Test du contenu de la base de données"""
        print("\n=== Test du contenu de la base de données ===")
        
        db = self.SessionLocal()
        try:
            # Compter les services
            service_count = db.query(Service).count()
            print(f"Nombre de services en base: {service_count}")
            
            # Compter les zones
            zone_count = db.query(Zone).count()
            print(f"Nombre de zones en base: {zone_count}")
            
            # Lister les services disponibles
            available_services = db.query(Service).filter(Service.status == "available").all()
            print(f"Services disponibles: {len(available_services)}")
            
            for service in available_services[:5]:  # Limiter l'affichage
                print(f"  - {service.name_fr or service.name}")
            
            # Lister les zones actives
            active_zones = db.query(Zone).filter(Zone.is_active == True).all()
            print(f"Zones actives: {len(active_zones)}")
            
            for zone in active_zones[:5]:  # Limiter l'affichage
                print(f"  - {zone.name_fr or zone.name}")
            
            print("✓ Test du contenu de la base réussi")
            return True
            
        except Exception as e:
            print(f"✗ Erreur dans le test de base: {e}")
            return False
        finally:
            db.close()
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🔧 Test d'intégration des services dynamiques - Djobea AI")
        print("=" * 60)
        
        tests = [
            ("Test de contenu de la base de données", self.test_database_content),
            ("Test de récupération des services", self.test_dynamic_services_retrieval),
            ("Test de génération FAQ", self.test_faq_response_with_dynamic_data)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}...")
            result = test_func()
            results.append((test_name, result))
        
        # Résumé des résultats
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 60)
        
        passed = 0
        for test_name, result in results:
            status = "✓ RÉUSSI" if result else "✗ ÉCHOUÉ"
            print(f"{status} - {test_name}")
            if result:
                passed += 1
        
        print(f"\nRésultat global: {passed}/{len(tests)} tests réussis")
        
        if passed == len(tests):
            print("🎉 Tous les tests sont passés avec succès !")
            print("✓ Les services dynamiques sont correctement intégrés")
        else:
            print("⚠️  Certains tests ont échoué")
        
        return passed == len(tests)

def main():
    """Fonction principale"""
    test = DynamicServicesTest()
    success = test.run_all_tests()
    
    if success:
        print("\n🚀 Intégration des services dynamiques terminée avec succès")
    else:
        print("\n❌ Problèmes détectés dans l'intégration")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())