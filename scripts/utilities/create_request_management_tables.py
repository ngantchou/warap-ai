#!/usr/bin/env python3
"""
Script pour créer les tables de gestion des demandes avec données de test
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")

# Créer le moteur de base de données
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base déclarative
Base = declarative_base()

# Modèles SQLAlchemy (réplication des modèles du système)
class UserRequest(Base):
    __tablename__ = "user_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255), index=True)
    title = Column(String(255))
    description = Column(Text)
    service_type = Column(String(100))
    location = Column(String(255))
    priority = Column(String(20), default='normale')
    status = Column(String(20), default='brouillon')
    estimated_price = Column(Float)
    estimated_duration = Column(Integer)
    materials_needed = Column(Text)
    special_requirements = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    scheduled_for = Column(DateTime)
    deadline = Column(DateTime)
    assigned_provider_id = Column(String(255))
    assigned_at = Column(DateTime)
    conversation_context = Column(Text)
    modification_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

class RequestValidationRule(Base):
    __tablename__ = "request_validation_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(255), unique=True, index=True)
    rule_name = Column(String(255))
    applicable_status = Column(String(50))
    field_name = Column(String(100))
    modification_type = Column(String(50))
    validation_logic = Column(Text)
    error_message = Column(Text)
    is_blocking = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

def create_tables():
    """Créer toutes les tables"""
    print("Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables créées avec succès")

def insert_sample_data():
    """Insérer des données de test"""
    db = SessionLocal()
    
    try:
        # Insérer des demandes de test
        test_requests = [
            {
                "request_id": f"req_{uuid.uuid4().hex[:12]}",
                "user_id": "237691924172",
                "title": "Réparation de fuite d'eau",
                "description": "Fuite d'eau importante dans la cuisine, urgent",
                "service_type": "plomberie",
                "location": "Bonamoussadi, Douala",
                "priority": "haute",
                "status": "en_attente",
                "estimated_price": 15000.0,
                "estimated_duration": 120,
                "materials_needed": '["joints", "tuyaux", "colle PVC"]',
                "special_requirements": "Accès facile, outils fournis"
            },
            {
                "request_id": f"req_{uuid.uuid4().hex[:12]}",
                "user_id": "237691924172",
                "title": "Installation prise électrique",
                "description": "Besoin d'installer une nouvelle prise dans le salon",
                "service_type": "électricité",
                "location": "Bonamoussadi, Douala",
                "priority": "normale",
                "status": "brouillon",
                "estimated_price": 8000.0,
                "estimated_duration": 60,
                "materials_needed": '["prise", "câbles", "disjoncteur"]',
                "special_requirements": "Travail en journée uniquement"
            },
            {
                "request_id": f"req_{uuid.uuid4().hex[:12]}",
                "user_id": "237691924172",
                "title": "Réparation réfrigérateur",
                "description": "Le réfrigérateur ne refroidit plus correctement",
                "service_type": "électroménager",
                "location": "Bonamoussadi, Douala",
                "priority": "normale",
                "status": "assignée",
                "estimated_price": 12000.0,
                "estimated_duration": 90,
                "materials_needed": '["gaz réfrigérant", "joints"]',
                "special_requirements": "Garantie 3 mois",
                "assigned_provider_id": "prov_001",
                "assigned_at": datetime.utcnow()
            }
        ]
        
        # Insérer les demandes
        for req_data in test_requests:
            request = UserRequest(**req_data)
            db.add(request)
        
        # Insérer des règles de validation
        validation_rules = [
            {
                "rule_id": f"rule_{uuid.uuid4().hex[:12]}",
                "rule_name": "Titre requis",
                "applicable_status": "brouillon",
                "field_name": "title",
                "modification_type": "modification",
                "validation_logic": '{"type": "required"}',
                "error_message": "Le titre est obligatoire",
                "is_blocking": True
            },
            {
                "rule_id": f"rule_{uuid.uuid4().hex[:12]}",
                "rule_name": "Description minimale",
                "applicable_status": "brouillon",
                "field_name": "description",
                "modification_type": "modification",
                "validation_logic": '{"type": "min_length", "min_length": 10}',
                "error_message": "La description doit contenir au moins 10 caractères",
                "is_blocking": True
            },
            {
                "rule_id": f"rule_{uuid.uuid4().hex[:12]}",
                "rule_name": "Modification limitée en cours",
                "applicable_status": "en_cours",
                "field_name": "service_type",
                "modification_type": "modification",
                "validation_logic": '{"type": "status_dependent", "allowed_statuses": ["brouillon", "en_attente"]}',
                "error_message": "Impossible de modifier le type de service en cours d'exécution",
                "is_blocking": True
            }
        ]
        
        # Insérer les règles
        for rule_data in validation_rules:
            rule = RequestValidationRule(**rule_data)
            db.add(rule)
        
        db.commit()
        print("Données de test insérées avec succès")
        
        # Afficher les données créées
        requests = db.query(UserRequest).all()
        print(f"\nDemandes créées: {len(requests)}")
        for req in requests:
            print(f"- {req.request_id}: {req.title} ({req.status})")
        
        rules = db.query(RequestValidationRule).all()
        print(f"\nRègles de validation créées: {len(rules)}")
        for rule in rules:
            print(f"- {rule.rule_id}: {rule.rule_name}")
        
    except Exception as e:
        print(f"Erreur lors de l'insertion des données: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Initialisation du système de gestion des demandes")
    print("=" * 50)
    
    create_tables()
    insert_sample_data()
    
    print("\n✅ Système de gestion des demandes prêt !")
    print("📋 Vous pouvez maintenant utiliser l'API pour gérer les demandes")
    print("🔗 Endpoints disponibles:")
    print("   - POST /api/v1/requests/create")
    print("   - GET /api/v1/requests/list")
    print("   - GET /api/v1/requests/{request_id}")
    print("   - PUT /api/v1/requests/{request_id}/modify")
    print("   - POST /api/v1/requests/conversation")
    print("   - GET /api/v1/requests/analytics/summary")