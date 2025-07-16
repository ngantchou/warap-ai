#!/usr/bin/env python3
"""
Create Escalation Detection Tables for Djobea AI
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models
from app.models.escalation_detection_models import (
    EscalationDetector, EscalationDetectionLog, EscalationBusinessRule, EscalationExecution,
    ComplexityScoring, EscalationAnalytics, EscalationPattern, EscalationFeedback
)
from app.models.database_models import Base

# Get database URL from environment
import os
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set")
    import sys
    sys.exit(1)

def create_tables():
    """Create all escalation detection tables"""
    print("🚀 Creating Escalation Detection Tables")
    print("=" * 60)
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create tables
        Base.metadata.create_all(engine)
        
        print("✅ Escalation detection tables created successfully")
        print("📊 Seeding initial escalation detection data...")
        
        # Seed initial data
        seed_initial_data(engine)
        
        print("✅ Initial escalation detection data seeded successfully")
        
        # Print table summary
        print_table_summary()
        
        print("\n🎉 Escalation Detection System setup completed successfully!")
        print("\n📋 Available endpoints:")
        print("   - POST /api/v1/escalation/detect")
        print("   - POST /api/v1/escalation/detectors")
        print("   - GET /api/v1/escalation/detectors")
        print("   - PUT /api/v1/escalation/detectors/{detector_id}")
        print("   - POST /api/v1/escalation/rules")
        print("   - GET /api/v1/escalation/rules")
        print("   - GET /api/v1/escalation/logs")
        print("   - POST /api/v1/escalation/complexity/analyze")
        print("   - GET /api/v1/escalation/complexity/analytics")
        print("   - GET /api/v1/escalation/analytics")
        print("   - GET /api/v1/escalation/analytics/dashboard")
        print("   - GET /api/v1/escalation/health")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def seed_initial_data(engine):
    """Seed initial escalation detection data"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create default escalation detectors
        detectors = [
            {
                'detector_id': f'detector_{uuid.uuid4().hex[:12]}',
                'detector_name': 'Compteur d\'Échecs',
                'detector_type': 'failure_counter',
                'is_active': True,
                'priority_level': 3,
                'escalation_threshold': 0.7,
                'failure_count_threshold': 3,
                'configuration_data': {
                    'description': 'Détecte les échecs de compréhension répétés',
                    'weight': 0.3
                }
            },
            {
                'detector_id': f'detector_{uuid.uuid4().hex[:12]}',
                'detector_name': 'Analyse de Sentiment',
                'detector_type': 'sentiment_analysis',
                'is_active': True,
                'priority_level': 3,
                'escalation_threshold': 0.6,
                'sentiment_threshold': -0.5,
                'configuration_data': {
                    'description': 'Analyse le sentiment négatif et la frustration',
                    'weight': 0.3
                }
            },
            {
                'detector_id': f'detector_{uuid.uuid4().hex[:12]}',
                'detector_name': 'Durée de Conversation',
                'detector_type': 'duration_based',
                'is_active': True,
                'priority_level': 2,
                'escalation_threshold': 0.8,
                'duration_threshold_minutes': 15,
                'configuration_data': {
                    'description': 'Détecte les conversations trop longues',
                    'weight': 0.2
                }
            },
            {
                'detector_id': f'detector_{uuid.uuid4().hex[:12]}',
                'detector_name': 'Scoring de Complexité',
                'detector_type': 'complexity_scoring',
                'is_active': True,
                'priority_level': 2,
                'escalation_threshold': 0.8,
                'complexity_threshold': 0.8,
                'configuration_data': {
                    'description': 'Analyse la complexité technique et comportementale',
                    'weight': 0.2
                }
            }
        ]
        
        for detector_data in detectors:
            detector = EscalationDetector(**detector_data)
            session.add(detector)
        
        # Create default escalation rules
        rules = [
            {
                'rule_id': f'rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Escalade Générale',
                'description': 'Escalade basée sur le score global',
                'condition_type': 'combined_score',
                'escalation_threshold': 0.7,
                'minimum_confidence': 0.6,
                'escalation_action': 'human_handoff',
                'escalation_target': 'support_agent',
                'notification_channels': ['whatsapp', 'email'],
                'is_active': True,
                'priority_order': 1,
                'max_escalations_per_day': 20,
                'cooldown_minutes': 60
            },
            {
                'rule_id': f'rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Escalade Urgente',
                'description': 'Escalade immédiate pour cas urgents',
                'condition_type': 'individual_threshold',
                'escalation_threshold': 0.9,
                'minimum_confidence': 0.8,
                'escalation_action': 'supervisor_alert',
                'escalation_target': 'supervisor',
                'notification_channels': ['whatsapp', 'email', 'sms'],
                'is_active': True,
                'priority_order': 0,
                'max_escalations_per_day': 5,
                'cooldown_minutes': 30
            },
            {
                'rule_id': f'rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Escalade Technique',
                'description': 'Escalade pour problèmes techniques complexes',
                'condition_type': 'pattern_match',
                'escalation_threshold': 0.75,
                'minimum_confidence': 0.7,
                'escalation_action': 'technical_support',
                'escalation_target': 'technical_team',
                'notification_channels': ['email'],
                'service_type_filter': 'électricité',
                'is_active': True,
                'priority_order': 2,
                'max_escalations_per_day': 10,
                'cooldown_minutes': 45
            }
        ]
        
        for rule_data in rules:
            rule = EscalationBusinessRule(**rule_data)
            session.add(rule)
        
        # Create sample escalation patterns
        patterns = [
            {
                'pattern_id': f'pattern_{uuid.uuid4().hex[:12]}',
                'pattern_name': 'Frustration Linguistique',
                'pattern_type': 'linguistic',
                'pattern_rules': {
                    'keywords': ['frustré', 'énervé', 'marre', 'impossible'],
                    'sentiment_threshold': -0.6,
                    'frequency_threshold': 2
                },
                'pattern_strength': 0.8,
                'pattern_frequency': 0.15,
                'accuracy_score': 0.75,
                'service_types': ['plomberie', 'électricité', 'électroménager'],
                'is_active': True,
                'validation_status': 'validated'
            },
            {
                'pattern_id': f'pattern_{uuid.uuid4().hex[:12]}',
                'pattern_name': 'Complexité Technique',
                'pattern_type': 'technical',
                'pattern_rules': {
                    'technical_terms_threshold': 3,
                    'service_complexity': 0.8,
                    'clarification_requests': 2
                },
                'pattern_strength': 0.7,
                'pattern_frequency': 0.12,
                'accuracy_score': 0.82,
                'service_types': ['électricité'],
                'is_active': True,
                'validation_status': 'validated'
            }
        ]
        
        for pattern_data in patterns:
            pattern = EscalationPattern(**pattern_data)
            session.add(pattern)
        
        # Create sample complexity scoring records
        complexity_records = [
            {
                'score_id': f'complexity_{uuid.uuid4().hex[:12]}',
                'user_id': '237691924172',
                'session_id': f'session_{uuid.uuid4().hex[:8]}',
                'request_id': f'req_{uuid.uuid4().hex[:8]}',
                'conversation_length': 8,
                'service_type': 'plomberie',
                'overall_complexity': 0.65,
                'escalation_probability': 0.35,
                'predicted_resolution_time': 25,
                'predicted_escalation_type': 'none',
                'suggested_action': 'continue_conversation',
                'confidence_score': 0.7,
                'scoring_metadata': {
                    'complexity_components': {
                        'linguistic': 0.4,
                        'technical': 0.7,
                        'behavioral': 0.5,
                        'emotional': 0.6,
                        'contextual': 0.5
                    }
                }
            },
            {
                'score_id': f'complexity_{uuid.uuid4().hex[:12]}',
                'user_id': '237655443322',
                'session_id': f'session_{uuid.uuid4().hex[:8]}',
                'request_id': f'req_{uuid.uuid4().hex[:8]}',
                'conversation_length': 15,
                'service_type': 'électricité',
                'overall_complexity': 0.85,
                'escalation_probability': 0.75,
                'predicted_resolution_time': 45,
                'predicted_escalation_type': 'technical',
                'suggested_action': 'consider_escalation',
                'confidence_score': 0.8,
                'scoring_metadata': {
                    'complexity_components': {
                        'linguistic': 0.7,
                        'technical': 0.9,
                        'behavioral': 0.8,
                        'emotional': 0.8,
                        'contextual': 0.7
                    }
                }
            }
        ]
        
        for record_data in complexity_records:
            record = ComplexityScoring(**record_data)
            session.add(record)
        
        # Create sample detection logs
        detection_logs = [
            {
                'log_id': f'detection_{uuid.uuid4().hex[:12]}',
                'user_id': '237691924172',
                'session_id': f'session_{uuid.uuid4().hex[:8]}',
                'request_id': f'req_{uuid.uuid4().hex[:8]}',
                'escalation_triggered': False,
                'escalation_score': 0.45,
                'escalation_reason': 'Score below threshold',
                'escalation_type': 'none',
                'failure_count': 1,
                'sentiment_score': -0.2,
                'duration_minutes': 8.5,
                'complexity_score': 0.4,
                'message_content': 'J\'ai un problème avec mon robinet qui fuit',
                'message_sentiment': 'neutral',
                'service_type': 'plomberie',
                'zone': 'Bonamoussadi',
                'user_type': 'regular',
                'urgency_level': 'normal'
            },
            {
                'log_id': f'detection_{uuid.uuid4().hex[:12]}',
                'user_id': '237655443322',
                'session_id': f'session_{uuid.uuid4().hex[:8]}',
                'request_id': f'req_{uuid.uuid4().hex[:8]}',
                'escalation_triggered': True,
                'escalation_score': 0.82,
                'escalation_reason': 'Combined score above threshold',
                'escalation_type': 'technical',
                'failure_count': 4,
                'sentiment_score': -0.7,
                'duration_minutes': 18.2,
                'complexity_score': 0.85,
                'message_content': 'Je suis vraiment frustré, ça fait 3 fois que je explique le même problème électrique complexe',
                'message_sentiment': 'negative',
                'service_type': 'électricité',
                'zone': 'Bonamoussadi',
                'user_type': 'regular',
                'urgency_level': 'high'
            }
        ]
        
        for log_data in detection_logs:
            log = EscalationDetectionLog(**log_data)
            session.add(log)
        
        session.commit()
        print("✅ Initial escalation detection data seeded successfully")
        print(f"   - 4 escalation detectors created")
        print(f"   - 3 escalation rules created")
        print(f"   - 2 escalation patterns created")
        print(f"   - 2 complexity scoring records created")
        print(f"   - 2 detection logs created")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def print_table_summary():
    """Print summary of created tables"""
    print("\n📊 Tables Created:")
    print("   - escalation_detectors: Configuration des détecteurs d'escalade")
    print("   - escalation_detection_logs: Logs des détections d'escalade")
    print("   - escalation_rules: Règles métier d'escalade")
    print("   - escalation_executions: Exécutions d'escalade")
    print("   - complexity_scoring: Scoring de complexité ML")
    print("   - escalation_analytics: Analytics d'escalade")
    print("   - escalation_patterns: Patterns appris")
    print("   - escalation_feedback: Feedback utilisateur")

if __name__ == "__main__":
    create_tables()