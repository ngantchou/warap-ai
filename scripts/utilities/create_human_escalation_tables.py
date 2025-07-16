#!/usr/bin/env python3
"""
Create Human Escalation Tables for Djobea AI
"""
import os
import sys
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models
from app.models.human_escalation_models import (
    HumanAgent, EscalationCase, HandoverSession, CaseAction, 
    EscalationFeedback, EscalationWorkflow, EscalationMetrics
)
from app.models.database_models import Base

def create_tables():
    """Create all human escalation tables"""
    try:
        # Get database URL
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("✅ Human escalation tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def seed_initial_data():
    """Seed initial data for human escalation system"""
    try:
        # Get database URL
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        # Create engine and session
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Create sample human agents
        agents = [
            {
                'agent_id': f'agent_{uuid.uuid4().hex[:12]}',
                'name': 'Jean-Baptiste Nkomo',
                'email': 'jean.nkomo@djobea.ai',
                'phone': '+237677889900',
                'department': 'support',
                'status': 'online',
                'availability_status': 'available',
                'max_concurrent_cases': 5,
                'current_case_count': 0,
                'specializations': ['plomberie', 'électricité'],
                'service_types': ['plomberie', 'électricité', 'électroménager'],
                'languages': ['français', 'anglais'],
                'customer_satisfaction_score': 4.5,
                'escalation_success_rate': 0.85,
                'notification_channels': ['email', 'whatsapp'],
                'working_hours': {
                    'monday': {'start': '08:00', 'end': '18:00'},
                    'tuesday': {'start': '08:00', 'end': '18:00'},
                    'wednesday': {'start': '08:00', 'end': '18:00'},
                    'thursday': {'start': '08:00', 'end': '18:00'},
                    'friday': {'start': '08:00', 'end': '18:00'},
                    'saturday': {'start': '09:00', 'end': '15:00'},
                    'sunday': {'start': '09:00', 'end': '15:00'}
                },
                'timezone': 'Africa/Douala'
            },
            {
                'agent_id': f'agent_{uuid.uuid4().hex[:12]}',
                'name': 'Marie Douala',
                'email': 'marie.douala@djobea.ai',
                'phone': '+237655443322',
                'department': 'technical',
                'status': 'online',
                'availability_status': 'available',
                'max_concurrent_cases': 3,
                'current_case_count': 0,
                'specializations': ['électricité', 'électroménager'],
                'service_types': ['électricité', 'électroménager'],
                'languages': ['français', 'anglais'],
                'customer_satisfaction_score': 4.8,
                'escalation_success_rate': 0.92,
                'notification_channels': ['email', 'sms'],
                'working_hours': {
                    'monday': {'start': '09:00', 'end': '17:00'},
                    'tuesday': {'start': '09:00', 'end': '17:00'},
                    'wednesday': {'start': '09:00', 'end': '17:00'},
                    'thursday': {'start': '09:00', 'end': '17:00'},
                    'friday': {'start': '09:00', 'end': '17:00'},
                    'saturday': {'start': '10:00', 'end': '14:00'},
                    'sunday': 'off'
                },
                'timezone': 'Africa/Douala'
            },
            {
                'agent_id': f'agent_{uuid.uuid4().hex[:12]}',
                'name': 'Paul Bonamoussadi',
                'email': 'paul.bonamoussadi@djobea.ai',
                'phone': '+237699887755',
                'department': 'supervisor',
                'status': 'online',
                'availability_status': 'available',
                'max_concurrent_cases': 8,
                'current_case_count': 0,
                'specializations': ['plomberie', 'électricité', 'électroménager'],
                'service_types': ['plomberie', 'électricité', 'électroménager'],
                'languages': ['français', 'anglais'],
                'customer_satisfaction_score': 4.7,
                'escalation_success_rate': 0.88,
                'notification_channels': ['email', 'whatsapp', 'sms'],
                'working_hours': {
                    'monday': {'start': '07:00', 'end': '19:00'},
                    'tuesday': {'start': '07:00', 'end': '19:00'},
                    'wednesday': {'start': '07:00', 'end': '19:00'},
                    'thursday': {'start': '07:00', 'end': '19:00'},
                    'friday': {'start': '07:00', 'end': '19:00'},
                    'saturday': {'start': '08:00', 'end': '16:00'},
                    'sunday': {'start': '08:00', 'end': '16:00'}
                },
                'timezone': 'Africa/Douala'
            }
        ]
        
        for agent_data in agents:
            agent = HumanAgent(**agent_data)
            session.add(agent)
        
        # Create sample escalation workflows
        workflows = [
            {
                'workflow_id': f'workflow_{uuid.uuid4().hex[:12]}',
                'workflow_name': 'Escalation Standard',
                'workflow_description': 'Workflow standard pour les escalations de niveau normal',
                'workflow_type': 'standard',
                'trigger_conditions': {
                    'escalation_score': {'min': 0.6, 'max': 0.8},
                    'urgency_levels': ['medium', 'high']
                },
                'escalation_thresholds': {
                    'sentiment_threshold': -0.5,
                    'complexity_threshold': 0.7,
                    'duration_threshold': 15
                },
                'service_type_filters': ['plomberie', 'électricité', 'électroménager'],
                'workflow_steps': [
                    {'step': 1, 'action': 'create_case', 'required': True},
                    {'step': 2, 'action': 'assign_agent', 'required': True},
                    {'step': 3, 'action': 'create_handover', 'required': True},
                    {'step': 4, 'action': 'notify_agent', 'required': True},
                    {'step': 5, 'action': 'monitor_response', 'required': True}
                ],
                'required_actions': ['contact_customer', 'update_status'],
                'optional_actions': ['escalate_further', 'request_specialist'],
                'auto_assignment_rules': {
                    'criteria': ['specialization', 'workload', 'performance'],
                    'fallback_to_supervisor': True
                },
                'notification_rules': {
                    'immediate': ['email', 'whatsapp'],
                    'reminder_after_minutes': 5,
                    'escalate_after_minutes': 15
                },
                'target_response_time': 10,
                'target_resolution_time': 120,
                'escalation_sla': {
                    'response_time_minutes': 10,
                    'resolution_time_minutes': 120,
                    'customer_satisfaction_target': 4.0
                },
                'is_active': True,
                'priority_order': 1
            },
            {
                'workflow_id': f'workflow_{uuid.uuid4().hex[:12]}',
                'workflow_name': 'Escalation Urgente',
                'workflow_description': 'Workflow pour les escalations urgentes et critiques',
                'workflow_type': 'urgent',
                'trigger_conditions': {
                    'escalation_score': {'min': 0.8, 'max': 1.0},
                    'urgency_levels': ['high', 'critical']
                },
                'escalation_thresholds': {
                    'sentiment_threshold': -0.7,
                    'complexity_threshold': 0.8,
                    'duration_threshold': 10
                },
                'service_type_filters': ['électricité', 'plomberie'],
                'workflow_steps': [
                    {'step': 1, 'action': 'create_case', 'required': True},
                    {'step': 2, 'action': 'assign_supervisor', 'required': True},
                    {'step': 3, 'action': 'immediate_handover', 'required': True},
                    {'step': 4, 'action': 'priority_notification', 'required': True},
                    {'step': 5, 'action': 'continuous_monitoring', 'required': True}
                ],
                'required_actions': ['immediate_contact', 'status_update', 'escalate_if_needed'],
                'optional_actions': ['send_specialist', 'manager_notification'],
                'auto_assignment_rules': {
                    'criteria': ['supervisor_available', 'specialization', 'experience'],
                    'fallback_to_manager': True
                },
                'notification_rules': {
                    'immediate': ['email', 'whatsapp', 'sms'],
                    'reminder_after_minutes': 2,
                    'escalate_after_minutes': 5
                },
                'target_response_time': 5,
                'target_resolution_time': 60,
                'escalation_sla': {
                    'response_time_minutes': 5,
                    'resolution_time_minutes': 60,
                    'customer_satisfaction_target': 4.5
                },
                'is_active': True,
                'priority_order': 0
            }
        ]
        
        for workflow_data in workflows:
            workflow = EscalationWorkflow(**workflow_data)
            session.add(workflow)
        
        # Create sample escalation cases
        cases = [
            {
                'case_id': f'case_{uuid.uuid4().hex[:12]}',
                'user_id': '237691924172',
                'session_id': 'session_demo_1',
                'original_request_id': 'req_12345',
                'escalation_trigger': 'frustration',
                'escalation_score': 0.75,
                'escalation_reason': 'Client exprime de la frustration après plusieurs tentatives',
                'urgency_level': 'high',
                'service_type': 'plomberie',
                'problem_category': 'fuite_eau',
                'problem_description': 'Fuite d\'eau importante au niveau du robinet de cuisine',
                'customer_context': {
                    'previous_requests': 2,
                    'service_history': 'Nouveau client',
                    'location': 'Bonamoussadi'
                },
                'status': 'pending',
                'priority': 'high',
                'case_metadata': {
                    'source': 'ai_detection',
                    'detection_confidence': 0.85
                }
            },
            {
                'case_id': f'case_{uuid.uuid4().hex[:12]}',
                'user_id': '237655443322',
                'session_id': 'session_demo_2',
                'original_request_id': 'req_67890',
                'escalation_trigger': 'complexity',
                'escalation_score': 0.68,
                'escalation_reason': 'Problème technique complexe nécessitant expertise spécialisée',
                'urgency_level': 'medium',
                'service_type': 'électricité',
                'problem_category': 'panne_electrique',
                'problem_description': 'Problème de disjoncteur qui saute répétitivement',
                'customer_context': {
                    'previous_requests': 0,
                    'service_history': 'Client fidèle',
                    'location': 'Bonamoussadi'
                },
                'status': 'pending',
                'priority': 'medium',
                'case_metadata': {
                    'source': 'ai_detection',
                    'detection_confidence': 0.78
                }
            }
        ]
        
        for case_data in cases:
            case = EscalationCase(**case_data)
            session.add(case)
        
        # Commit all changes
        session.commit()
        session.close()
        
        print("✅ Initial human escalation data seeded successfully")
        print(f"   - {len(agents)} agents created")
        print(f"   - {len(workflows)} workflows created")
        print(f"   - {len(cases)} sample cases created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Creating Human Escalation Tables")
    print("=" * 60)
    
    # Create tables
    if create_tables():
        print("📊 Seeding initial human escalation data...")
        
        if seed_initial_data():
            print("✅ Initial human escalation data seeded successfully")
            
            print("\n📊 Tables Created:")
            print("   - human_agents: Agents du support client")
            print("   - escalation_cases: Cas d'escalation")
            print("   - handover_sessions: Sessions de handover")
            print("   - case_actions: Actions sur les cas")
            print("   - escalation_feedback: Feedback des agents")
            print("   - escalation_workflows: Workflows d'escalation")
            print("   - escalation_metrics: Métriques d'escalation")
            
            print("\n🎉 Human Escalation System setup completed successfully!")
            
            print("\n📋 Available endpoints:")
            print("   - POST /api/v1/escalation/cases")
            print("   - GET /api/v1/escalation/cases")
            print("   - GET /api/v1/escalation/cases/{case_id}")
            print("   - PUT /api/v1/escalation/cases/{case_id}/status")
            print("   - GET /api/v1/escalation/agents")
            print("   - GET /api/v1/escalation/agents/{agent_id}/dashboard")
            print("   - PUT /api/v1/escalation/agents/{agent_id}/status")
            print("   - POST /api/v1/escalation/cases/{case_id}/actions")
            print("   - GET /api/v1/escalation/cases/{case_id}/actions")
            print("   - POST /api/v1/escalation/feedback")
            print("   - GET /api/v1/escalation/feedback")
            print("   - GET /api/v1/escalation/analytics/human")
            print("   - GET /api/v1/escalation/analytics/dashboard")
            print("   - GET /api/v1/escalation/human/health")
            
        else:
            print("❌ Failed to seed initial data")
            sys.exit(1)
    else:
        print("❌ Failed to create tables")
        sys.exit(1)

if __name__ == "__main__":
    main()