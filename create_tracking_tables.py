#!/usr/bin/env python3
"""
Script to create real-time tracking tables and seed initial data
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.tracking_models import (
    RequestStatus, StatusHistory, NotificationRule, NotificationLog,
    EscalationRule, EscalationLog, TrackingUserPreference, TrackingAnalytics
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
    """Create all tracking tables"""
    print("🚀 Creating Real-time Tracking Tables")
    print("=" * 60)
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create tables
        Base.metadata.create_all(engine)
        
        print("✅ Real-time tracking tables created successfully")
        
        # Seed initial data
        seed_initial_data(engine)
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def seed_initial_data(engine):
    """Seed initial tracking data"""
    print("📊 Seeding initial tracking data...")
    
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create default notification rules
        notification_rules = [
            {
                'rule_id': f'rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Acceptation Prestataire',
                'trigger_status': 'provider_accepted',
                'trigger_delay_minutes': 0,
                'notification_channels': ['whatsapp'],
                'notification_template': 'provider_accepted',
                'notification_frequency': 'immediate',
                'max_notifications': 3,
                'priority_level': 1,
                'is_active': True
            },
            {
                'rule_id': f'rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Prestataire en Route',
                'trigger_status': 'provider_enroute',
                'trigger_delay_minutes': 0,
                'notification_channels': ['whatsapp'],
                'notification_template': 'provider_enroute',
                'notification_frequency': 'immediate',
                'max_notifications': 2,
                'priority_level': 1,
                'is_active': True
            },
            {
                'rule_id': f'rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Service Terminé',
                'trigger_status': 'service_completed',
                'trigger_delay_minutes': 0,
                'notification_channels': ['whatsapp'],
                'notification_template': 'service_completed',
                'notification_frequency': 'immediate',
                'max_notifications': 1,
                'priority_level': 1,
                'is_active': True
            },
            {
                'rule_id': f'rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Rappel Retard',
                'trigger_status': 'all',
                'trigger_delay_minutes': 30,
                'notification_channels': ['whatsapp'],
                'notification_template': 'delay_reminder',
                'notification_frequency': 'immediate',
                'max_notifications': 5,
                'priority_level': 2,
                'is_active': True
            }
        ]
        
        for rule_data in notification_rules:
            rule = NotificationRule(**rule_data)
            session.add(rule)
        
        # Create default escalation rules
        escalation_rules = [
            {
                'rule_id': f'esc_rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Retard Prestataire',
                'status_trigger': 'provider_accepted',
                'delay_threshold_minutes': 45,
                'urgency_level': 'normal',
                'escalation_type': 'provider_reminder',
                'escalation_target': 'provider',
                'escalation_message': 'Rappel: Veuillez vous rendre chez le client',
                'escalation_channels': ['whatsapp'],
                'max_escalations': 3,
                'escalation_interval_minutes': 15,
                'is_active': True
            },
            {
                'rule_id': f'esc_rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Recherche Prestataire Longue',
                'status_trigger': 'provider_search',
                'delay_threshold_minutes': 20,
                'urgency_level': 'high',
                'escalation_type': 'find_new_provider',
                'escalation_target': 'system',
                'escalation_message': 'Recherche étendue de prestataires',
                'escalation_channels': ['whatsapp'],
                'max_escalations': 2,
                'escalation_interval_minutes': 10,
                'is_active': True
            },
            {
                'rule_id': f'esc_rule_{uuid.uuid4().hex[:12]}',
                'rule_name': 'Urgence Manager',
                'status_trigger': 'all',
                'delay_threshold_minutes': 60,
                'urgency_level': 'urgent',
                'escalation_type': 'manager_alert',
                'escalation_target': 'manager',
                'escalation_message': 'Intervention manager requise',
                'escalation_channels': ['whatsapp', 'email'],
                'max_escalations': 1,
                'escalation_interval_minutes': 30,
                'is_active': True
            }
        ]
        
        for rule_data in escalation_rules:
            rule = EscalationRule(**rule_data)
            session.add(rule)
        
        # Create sample user preferences
        user_preferences = [
            {
                'user_id': '237691924172',
                'preferred_channels': ['whatsapp'],
                'notification_frequency': 'immediate',
                'quiet_hours_start': '22:00',
                'quiet_hours_end': '07:00',
                'language': 'fr',
                'communication_style': 'friendly',
                'urgency_sensitivity': 'normal',
                'max_updates_per_day': 15,
                'wants_completion_photos': True,
                'wants_cost_updates': True,
                'wants_provider_info': True,
                'share_location': True,
                'share_contact_info': True,
                'marketing_notifications': False
            },
            {
                'user_id': '237655443322',
                'preferred_channels': ['whatsapp', 'sms'],
                'notification_frequency': 'hourly',
                'quiet_hours_start': '21:00',
                'quiet_hours_end': '08:00',
                'language': 'fr',
                'communication_style': 'formal',
                'urgency_sensitivity': 'high',
                'max_updates_per_day': 8,
                'wants_completion_photos': False,
                'wants_cost_updates': True,
                'wants_provider_info': True,
                'share_location': True,
                'share_contact_info': False,
                'marketing_notifications': True
            }
        ]
        
        for pref_data in user_preferences:
            pref = TrackingUserPreference(**pref_data)
            session.add(pref)
        
        # Create sample request statuses for testing
        sample_requests = [
            {
                'status_id': f'status_{uuid.uuid4().hex[:12]}',
                'request_id': f'req_{uuid.uuid4().hex[:12]}',
                'user_id': '237691924172',
                'current_status': 'provider_accepted',
                'provider_id': 'prov_123',
                'status_reason': 'Prestataire accepté',
                'urgency_level': 'normal',
                'completion_percentage': 40.0,
                'predicted_next_step': 'provider_enroute',
                'next_step_eta': datetime.utcnow() + timedelta(minutes=30),
                'provider_eta': datetime.utcnow() + timedelta(minutes=45),
                'metadata': {
                    'service_type': 'plomberie',
                    'zone': 'Bonamoussadi',
                    'estimated_cost': 8500
                }
            },
            {
                'status_id': f'status_{uuid.uuid4().hex[:12]}',
                'request_id': f'req_{uuid.uuid4().hex[:12]}',
                'user_id': '237655443322',
                'current_status': 'service_started',
                'provider_id': 'prov_456',
                'status_reason': 'Service en cours',
                'urgency_level': 'high',
                'completion_percentage': 70.0,
                'predicted_next_step': 'service_completed',
                'next_step_eta': datetime.utcnow() + timedelta(minutes=90),
                'metadata': {
                    'service_type': 'électricité',
                    'zone': 'Bonamoussadi',
                    'estimated_cost': 12000
                }
            }
        ]
        
        for req_data in sample_requests:
            req = RequestStatus(**req_data)
            session.add(req)
        
        # Create sample tracking analytics
        sample_analytics = [
            {
                'analytics_id': f'analytics_{uuid.uuid4().hex[:12]}',
                'request_id': f'req_{uuid.uuid4().hex[:12]}',
                'user_id': '237691924172',
                'total_duration_minutes': 180,
                'status_changes_count': 6,
                'notifications_sent': 4,
                'escalations_count': 0,
                'response_time_minutes': 15,
                'resolution_time_minutes': 180,
                'completion_time_minutes': 165,
                'user_satisfaction_score': 4.2,
                'provider_rating': 4.5,
                'service_quality_score': 4.0,
                'communication_effectiveness': 4.3,
                'service_type': 'plomberie',
                'zone': 'Bonamoussadi',
                'urgency_level': 'normal',
                'completion_date': datetime.utcnow() - timedelta(hours=2),
                'status_progression': [
                    {'status': 'pending', 'timestamp': '2025-07-09T08:00:00', 'duration': 10},
                    {'status': 'provider_search', 'timestamp': '2025-07-09T08:10:00', 'duration': 15},
                    {'status': 'provider_accepted', 'timestamp': '2025-07-09T08:25:00', 'duration': 45},
                    {'status': 'service_started', 'timestamp': '2025-07-09T09:10:00', 'duration': 120},
                    {'status': 'service_completed', 'timestamp': '2025-07-09T11:10:00', 'duration': 10}
                ],
                'optimization_suggestions': [
                    {'area': 'provider_search', 'suggestion': 'Optimize matching algorithm'},
                    {'area': 'communication', 'suggestion': 'Add progress photos'}
                ],
                'success_factors': [
                    'Quick provider acceptance',
                    'Clear communication',
                    'On-time completion'
                ]
            }
        ]
        
        for analytics_data in sample_analytics:
            analytics = TrackingAnalytics(**analytics_data)
            session.add(analytics)
        
        session.commit()
        session.close()
        
        print("✅ Initial tracking data seeded successfully")
        print(f"   - {len(notification_rules)} notification rules created")
        print(f"   - {len(escalation_rules)} escalation rules created")
        print(f"   - {len(user_preferences)} user preferences created")
        print(f"   - {len(sample_requests)} sample requests created")
        print(f"   - {len(sample_analytics)} analytics entries created")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        raise

def main():
    """Main function to create tables and seed data"""
    try:
        create_tables()
        
        print("\n🎉 Real-time Tracking System setup completed successfully!")
        
        print("\n📋 Available endpoints:")
        print("   - POST /api/v1/tracking/status/update")
        print("   - GET /api/v1/tracking/request/{request_id}")
        print("   - GET /api/v1/tracking/user/{user_id}/requests")
        print("   - POST /api/v1/tracking/preferences")
        print("   - GET /api/v1/tracking/preferences/{user_id}")
        print("   - POST /api/v1/tracking/notifications/send")
        print("   - POST /api/v1/tracking/notifications/rules")
        print("   - GET /api/v1/tracking/notifications/rules")
        print("   - GET /api/v1/tracking/notifications/history")
        print("   - GET /api/v1/tracking/notifications/analytics")
        print("   - POST /api/v1/tracking/escalations/rules")
        print("   - GET /api/v1/tracking/escalations/rules")
        print("   - GET /api/v1/tracking/escalations/history")
        print("   - GET /api/v1/tracking/escalations/analytics")
        print("   - GET /api/v1/tracking/analytics/performance")
        print("   - GET /api/v1/tracking/analytics/dashboard")
        print("   - GET /api/v1/tracking/analytics/service")
        print("   - GET /api/v1/tracking/analytics/user/{user_id}")
        print("   - GET /api/v1/tracking/analytics/optimization")
        print("   - GET /api/v1/tracking/health")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()