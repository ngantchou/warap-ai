#!/usr/bin/env python3
"""
Script to create knowledge base tables and seed initial data
"""
import os
import sys
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models.knowledge_base import (
    Base, KnowledgeCategory, KnowledgeArticle, FAQ, PricingInformation,
    ServiceProcess, UserQuestion, ArticleFeedback, SupportSession, SupportEscalation
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/djobea_ai")

def create_tables():
    """Create all knowledge base tables"""
    try:
        engine = create_engine(DATABASE_URL)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("✅ Knowledge base tables created successfully")
        
        return engine
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return None

def seed_initial_data(engine):
    """Seed initial knowledge base data"""
    try:
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Create categories
        categories = [
            {
                'category_id': 'general',
                'name': 'Général',
                'description': 'Questions générales sur la plateforme',
                'service_type': None,
                'zone': None,
                'display_order': 1
            },
            {
                'category_id': 'plomberie',
                'name': 'Plomberie',
                'description': 'Questions relatives aux services de plomberie',
                'service_type': 'plomberie',
                'zone': None,
                'display_order': 2
            },
            {
                'category_id': 'electricite',
                'name': 'Électricité',
                'description': 'Questions relatives aux services électriques',
                'service_type': 'électricité',
                'zone': None,
                'display_order': 3
            },
            {
                'category_id': 'electromenager',
                'name': 'Électroménager',
                'description': 'Questions relatives à la réparation d\'électroménager',
                'service_type': 'électroménager',
                'zone': None,
                'display_order': 4
            },
            {
                'category_id': 'bonamoussadi',
                'name': 'Bonamoussadi',
                'description': 'Questions spécifiques à la zone de Bonamoussadi',
                'service_type': None,
                'zone': 'Bonamoussadi',
                'display_order': 5
            }
        ]
        
        for cat_data in categories:
            existing = db.query(KnowledgeCategory).filter(
                KnowledgeCategory.category_id == cat_data['category_id']
            ).first()
            
            if not existing:
                category = KnowledgeCategory(**cat_data)
                db.add(category)
        
        # Create pricing information
        pricing_data = [
            {
                'pricing_id': f"price_{uuid.uuid4().hex[:12]}",
                'service_type': 'plomberie',
                'zone': 'Bonamoussadi',
                'min_price': 5000,
                'max_price': 15000,
                'average_price': 8000,
                'currency': 'XAF',
                'unit': 'service',
                'factors': {
                    'urgency': 'Prix majoré de 20% pour urgences',
                    'complexity': 'Prix variable selon complexité',
                    'materials': 'Matériaux en sus selon besoin'
                }
            },
            {
                'pricing_id': f"price_{uuid.uuid4().hex[:12]}",
                'service_type': 'électricité',
                'zone': 'Bonamoussadi',
                'min_price': 3000,
                'max_price': 12000,
                'average_price': 6000,
                'currency': 'XAF',
                'unit': 'service',
                'factors': {
                    'urgency': 'Prix majoré de 25% pour urgences',
                    'complexity': 'Prix variable selon type d\'installation',
                    'materials': 'Matériaux électriques en sus'
                }
            },
            {
                'pricing_id': f"price_{uuid.uuid4().hex[:12]}",
                'service_type': 'électroménager',
                'zone': 'Bonamoussadi',
                'min_price': 2000,
                'max_price': 10000,
                'average_price': 5000,
                'currency': 'XAF',
                'unit': 'service',
                'factors': {
                    'type': 'Prix selon type d\'appareil',
                    'brand': 'Marque influence le prix',
                    'parts': 'Pièces de rechange en sus'
                }
            }
        ]
        
        for pricing in pricing_data:
            existing = db.query(PricingInformation).filter(
                PricingInformation.service_type == pricing['service_type'],
                PricingInformation.zone == pricing['zone']
            ).first()
            
            if not existing:
                price_info = PricingInformation(**pricing)
                db.add(price_info)
        
        # Create FAQs
        faqs = [
            {
                'faq_id': f"faq_{uuid.uuid4().hex[:12]}",
                'question': 'Comment réserver un service sur Djobea AI?',
                'answer': 'Envoyez simplement un message WhatsApp décrivant votre problème. Notre IA analysera votre demande et vous mettra en contact avec un prestataire qualifié.',
                'category_id': 'general',
                'service_type': None,
                'zone': None,
                'keywords': ['réservation', 'service', 'WhatsApp', 'IA'],
                'priority': 100
            },
            {
                'faq_id': f"faq_{uuid.uuid4().hex[:12]}",
                'question': 'Combien coûte un service de plomberie?',
                'answer': 'Les tarifs de plomberie varient entre 5,000 et 15,000 XAF selon la complexité. Le prix peut être majoré de 20% en cas d\'urgence.',
                'category_id': 'plomberie',
                'service_type': 'plomberie',
                'zone': 'Bonamoussadi',
                'keywords': ['prix', 'tarif', 'plomberie', 'coût'],
                'priority': 90
            },
            {
                'faq_id': f"faq_{uuid.uuid4().hex[:12]}",
                'question': 'Que faire en cas de panne électrique?',
                'answer': 'Vérifiez d\'abord vos disjoncteurs et fusibles. Si le problème persiste, contactez notre service via WhatsApp pour un électricien qualifié.',
                'category_id': 'electricite',
                'service_type': 'électricité',
                'zone': None,
                'keywords': ['panne', 'électricité', 'disjoncteur', 'fusible'],
                'priority': 85
            },
            {
                'faq_id': f"faq_{uuid.uuid4().hex[:12]}",
                'question': 'Mon réfrigérateur ne refroidit plus, que faire?',
                'answer': 'Vérifiez que l\'appareil est bien branché et que la température est correctement réglée. Si le problème persiste, contactez notre service de réparation d\'électroménager.',
                'category_id': 'electromenager',
                'service_type': 'électroménager',
                'zone': None,
                'keywords': ['réfrigérateur', 'refroidissement', 'température', 'réparation'],
                'priority': 80
            },
            {
                'faq_id': f"faq_{uuid.uuid4().hex[:12]}",
                'question': 'Combien de temps pour avoir un prestataire à Bonamoussadi?',
                'answer': 'En moyenne, un prestataire peut intervenir dans les 30 minutes à 2 heures selon la disponibilité et le type de service demandé.',
                'category_id': 'bonamoussadi',
                'service_type': None,
                'zone': 'Bonamoussadi',
                'keywords': ['délai', 'temps', 'prestataire', 'Bonamoussadi'],
                'priority': 75
            }
        ]
        
        for faq_data in faqs:
            existing = db.query(FAQ).filter(
                FAQ.question == faq_data['question']
            ).first()
            
            if not existing:
                faq = FAQ(**faq_data)
                db.add(faq)
        
        # Create service processes
        processes = [
            {
                'process_id': f"proc_{uuid.uuid4().hex[:12]}",
                'service_type': 'plomberie',
                'process_name': 'Réparation fuite d\'eau',
                'description': 'Processus standard pour réparer une fuite d\'eau',
                'steps': [
                    {'step': 1, 'title': 'Diagnostic', 'description': 'Localiser la source de la fuite'},
                    {'step': 2, 'title': 'Arrêt d\'eau', 'description': 'Couper l\'arrivée d\'eau principale'},
                    {'step': 3, 'title': 'Réparation', 'description': 'Réparer ou remplacer la partie défaillante'},
                    {'step': 4, 'title': 'Test', 'description': 'Vérifier l\'étanchéité après réparation'},
                    {'step': 5, 'title': 'Nettoyage', 'description': 'Nettoyer la zone de travail'}
                ],
                'estimated_duration': 120,
                'required_materials': ['Joints', 'Tuyaux', 'Outils de plomberie'],
                'preparation_tips': 'Préparez un seau et des serviettes pour récupérer l\'eau.',
                'difficulty_level': 'medium'
            },
            {
                'process_id': f"proc_{uuid.uuid4().hex[:12]}",
                'service_type': 'électricité',
                'process_name': 'Installation prise électrique',
                'description': 'Processus pour installer une nouvelle prise électrique',
                'steps': [
                    {'step': 1, 'title': 'Sécurité', 'description': 'Couper le courant au disjoncteur'},
                    {'step': 2, 'title': 'Perçage', 'description': 'Percer le mur pour la prise'},
                    {'step': 3, 'title': 'Câblage', 'description': 'Connecter les câbles électriques'},
                    {'step': 4, 'title': 'Fixation', 'description': 'Fixer la prise au mur'},
                    {'step': 5, 'title': 'Test', 'description': 'Tester le fonctionnement'}
                ],
                'estimated_duration': 90,
                'required_materials': ['Prise électrique', 'Câbles', 'Disjoncteur', 'Outils électriques'],
                'preparation_tips': 'Assurez-vous que le courant est coupé avant intervention.',
                'difficulty_level': 'high'
            }
        ]
        
        for proc_data in processes:
            existing = db.query(ServiceProcess).filter(
                ServiceProcess.process_name == proc_data['process_name']
            ).first()
            
            if not existing:
                process = ServiceProcess(**proc_data)
                db.add(process)
        
        # Create knowledge articles
        articles = [
            {
                'article_id': f"art_{uuid.uuid4().hex[:12]}",
                'title': 'Guide complet de la plomberie domestique',
                'content': """
# Guide complet de la plomberie domestique

## Introduction
La plomberie domestique nécessite des connaissances techniques et des outils appropriés. Ce guide vous aidera à comprendre les bases.

## Problèmes courants
- Fuites d'eau
- Bouchons dans les canalisations
- Problèmes de pression
- Dysfonctionnements de WC

## Maintenance préventive
- Vérifier régulièrement les joints
- Nettoyer les siphons
- Contrôler la pression
- Entretenir les robinets

## Quand faire appel à un professionnel
N'hésitez pas à contacter un plombier professionnel pour :
- Fuites importantes
- Problèmes de canalisation principale
- Installations nouvelles
- Réparations complexes
                """,
                'summary': 'Guide complet pour comprendre et maintenir la plomberie domestique',
                'category_id': 'plomberie',
                'service_type': 'plomberie',
                'zone': None,
                'tags': ['plomberie', 'maintenance', 'guide', 'domestique'],
                'difficulty_level': 'intermediate',
                'estimated_read_time': 8,
                'usefulness_score': 4.2
            },
            {
                'article_id': f"art_{uuid.uuid4().hex[:12]}",
                'title': 'Sécurité électrique : les bonnes pratiques',
                'content': """
# Sécurité électrique : les bonnes pratiques

## Règles de base
La sécurité électrique est primordiale dans toute intervention.

## Précautions essentielles
- Toujours couper le courant avant intervention
- Vérifier l'absence de tension
- Utiliser des outils isolés
- Porter des équipements de protection

## Signaux d'alerte
- Étincelles
- Odeurs de brûlé
- Disjoncteurs qui sautent fréquemment
- Prises qui chauffent

## Intervention professionnelle
Contactez immédiatement un électricien pour :
- Problèmes de tableau électrique
- Installations nouvelles
- Réparations complexes
- Mise aux normes
                """,
                'summary': 'Conseils de sécurité pour les interventions électriques',
                'category_id': 'electricite',
                'service_type': 'électricité',
                'zone': None,
                'tags': ['sécurité', 'électricité', 'précautions', 'normes'],
                'difficulty_level': 'beginner',
                'estimated_read_time': 5,
                'usefulness_score': 4.5
            }
        ]
        
        for art_data in articles:
            existing = db.query(KnowledgeArticle).filter(
                KnowledgeArticle.title == art_data['title']
            ).first()
            
            if not existing:
                article = KnowledgeArticle(**art_data)
                db.add(article)
        
        # Create sample user questions for testing
        sample_questions = [
            {
                'question_id': f"q_{uuid.uuid4().hex[:12]}",
                'user_id': '237691924172',
                'question_text': 'Comment réparer une fuite sous l\'évier?',
                'service_type': 'plomberie',
                'zone': 'Bonamoussadi',
                'was_answered': False
            },
            {
                'question_id': f"q_{uuid.uuid4().hex[:12]}",
                'user_id': '237691924172',
                'question_text': 'Pourquoi mes lumières clignotent?',
                'service_type': 'électricité',
                'zone': 'Bonamoussadi',
                'was_answered': False
            },
            {
                'question_id': f"q_{uuid.uuid4().hex[:12]}",
                'user_id': '237691924172',
                'question_text': 'Mon frigo fait du bruit, c\'est normal?',
                'service_type': 'électroménager',
                'zone': 'Bonamoussadi',
                'was_answered': False
            }
        ]
        
        for q_data in sample_questions:
            existing = db.query(UserQuestion).filter(
                UserQuestion.question_text == q_data['question_text']
            ).first()
            
            if not existing:
                question = UserQuestion(**q_data)
                db.add(question)
        
        db.commit()
        db.close()
        
        print("✅ Initial knowledge base data seeded successfully")
        print(f"   - {len(categories)} categories created")
        print(f"   - {len(pricing_data)} pricing entries created")
        print(f"   - {len(faqs)} FAQs created")
        print(f"   - {len(processes)} service processes created")
        print(f"   - {len(articles)} knowledge articles created")
        print(f"   - {len(sample_questions)} sample questions created")
        
        return True
    except Exception as e:
        print(f"❌ Error seeding data: {str(e)}")
        return False

def main():
    """Main function to create tables and seed data"""
    print("🚀 Creating Knowledge Base Tables and Seeding Data")
    print("=" * 60)
    
    # Create tables
    engine = create_tables()
    if not engine:
        return
    
    # Seed initial data
    if seed_initial_data(engine):
        print("\n🎉 Knowledge Base setup completed successfully!")
        print("\n📋 Available endpoints:")
        print("   - GET /api/v1/knowledge/search")
        print("   - GET /api/v1/knowledge/faq/category/{category_id}")
        print("   - GET /api/v1/knowledge/pricing/{service_type}/{zone}")
        print("   - GET /api/v1/knowledge/processes/{service_type}")
        print("   - POST /api/v1/knowledge/support/detect")
        print("   - POST /api/v1/knowledge/feedback")
        print("   - GET /api/v1/knowledge/analytics/support")
        print("   - POST /api/v1/knowledge/maintenance/update-pricing")
        print("   - POST /api/v1/knowledge/maintenance/analyze-questions")
        print("   - GET /api/v1/knowledge/maintenance/analytics")
    else:
        print("\n❌ Failed to seed initial data")

if __name__ == "__main__":
    main()