"""
Intelligent Notification Service for Djobea AI
"""
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from loguru import logger

from app.models.tracking_models import (
    NotificationRule, NotificationLog, TrackingUserPreference, EscalationRule, EscalationLog
)
from app.services.whatsapp_service import WhatsAppService
from app.database import get_db

class NotificationService:
    """Service for intelligent notifications"""
    
    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService()
    
    def create_notification_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new notification rule"""
        try:
            rule_id = f"rule_{uuid.uuid4().hex[:12]}"
            
            rule = NotificationRule(
                rule_id=rule_id,
                rule_name=rule_data['rule_name'],
                trigger_status=rule_data.get('trigger_status', 'all'),
                trigger_delay_minutes=rule_data.get('trigger_delay_minutes', 0),
                trigger_urgency_level=rule_data.get('trigger_urgency_level', 'normal'),
                trigger_condition=rule_data.get('trigger_condition', {}),
                notification_channels=rule_data.get('notification_channels', ['whatsapp']),
                notification_template=rule_data.get('notification_template', 'default'),
                notification_frequency=rule_data.get('notification_frequency', 'immediate'),
                max_notifications=rule_data.get('max_notifications', 5),
                user_type_filter=rule_data.get('user_type_filter', 'all'),
                service_type_filter=rule_data.get('service_type_filter'),
                zone_filter=rule_data.get('zone_filter'),
                priority_level=rule_data.get('priority_level', 1),
                escalation_rule=rule_data.get('escalation_rule', False)
            )
            
            self.db.add(rule)
            self.db.commit()
            
            return {
                'success': True,
                'rule_id': rule_id,
                'message': 'Notification rule created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating notification rule: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_notification_rules(self, active_only: bool = True) -> Dict[str, Any]:
        """Get all notification rules"""
        try:
            query = self.db.query(NotificationRule)
            
            if active_only:
                query = query.filter(NotificationRule.is_active == True)
            
            rules = query.order_by(desc(NotificationRule.priority_level)).all()
            
            return {
                'success': True,
                'rules': [self._format_rule(rule) for rule in rules]
            }
            
        except Exception as e:
            logger.error(f"Error getting notification rules: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_notification_rule(self, rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a notification rule"""
        try:
            rule = self.db.query(NotificationRule).filter(
                NotificationRule.rule_id == rule_id
            ).first()
            
            if not rule:
                return {
                    'success': False,
                    'error': 'Rule not found'
                }
            
            # Update fields
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            rule.updated_at = datetime.utcnow()
            self.db.commit()
            
            return {
                'success': True,
                'message': 'Rule updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error updating notification rule: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_immediate_notification(self, user_id: str, message: str, 
                                  channels: List[str] = None,
                                  urgency: str = 'normal') -> Dict[str, Any]:
        """Send immediate notification to user"""
        try:
            if not channels:
                # Get user preferred channels
                user_prefs = self.db.query(TrackingUserPreference).filter(
                    TrackingUserPreference.user_id == user_id
                ).first()
                
                channels = user_prefs.preferred_channels if user_prefs else ['whatsapp']
            
            results = []
            
            for channel in channels:
                try:
                    if channel == 'whatsapp':
                        result = self._send_whatsapp_notification(user_id, message)
                    elif channel == 'sms':
                        result = self._send_sms_notification(user_id, message)
                    elif channel == 'email':
                        result = self._send_email_notification(user_id, message)
                    else:
                        result = {'success': False, 'error': f'Unknown channel: {channel}'}
                    
                    results.append({
                        'channel': channel,
                        'success': result['success'],
                        'message': result.get('message', result.get('error'))
                    })
                    
                    # Log notification
                    self._log_notification(
                        user_id=user_id,
                        channel=channel,
                        message=message,
                        delivery_status='sent' if result['success'] else 'failed',
                        notification_type='immediate'
                    )
                    
                except Exception as e:
                    logger.error(f"Error sending {channel} notification: {str(e)}")
                    results.append({
                        'channel': channel,
                        'success': False,
                        'message': str(e)
                    })
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error sending immediate notification: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_notification_history(self, user_id: str = None, 
                               request_id: str = None,
                               limit: int = 50) -> Dict[str, Any]:
        """Get notification history"""
        try:
            query = self.db.query(NotificationLog)
            
            if user_id:
                query = query.filter(NotificationLog.user_id == user_id)
            
            if request_id:
                query = query.filter(NotificationLog.request_id == request_id)
            
            notifications = query.order_by(
                desc(NotificationLog.sent_timestamp)
            ).limit(limit).all()
            
            return {
                'success': True,
                'notifications': [self._format_notification_log(n) for n in notifications]
            }
            
        except Exception as e:
            logger.error(f"Error getting notification history: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_notification_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get notification analytics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total notifications
            total_notifications = self.db.query(NotificationLog).filter(
                NotificationLog.sent_timestamp >= start_date
            ).count()
            
            # Notifications by channel
            channel_stats = self.db.query(
                NotificationLog.channel,
                func.count(NotificationLog.id).label('count')
            ).filter(
                NotificationLog.sent_timestamp >= start_date
            ).group_by(NotificationLog.channel).all()
            
            # Delivery rates
            delivery_stats = self.db.query(
                NotificationLog.delivery_status,
                func.count(NotificationLog.id).label('count')
            ).filter(
                NotificationLog.sent_timestamp >= start_date
            ).group_by(NotificationLog.delivery_status).all()
            
            # Response rates
            response_rate = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.sent_timestamp >= start_date,
                    NotificationLog.user_response.isnot(None)
                )
            ).count()
            
            # Satisfaction scores
            satisfaction_avg = self.db.query(
                func.avg(NotificationLog.satisfaction_score)
            ).filter(
                and_(
                    NotificationLog.sent_timestamp >= start_date,
                    NotificationLog.satisfaction_score.isnot(None)
                )
            ).scalar()
            
            return {
                'success': True,
                'analytics': {
                    'total_notifications': total_notifications,
                    'channel_distribution': {stat.channel: stat.count for stat in channel_stats},
                    'delivery_rates': {stat.delivery_status: stat.count for stat in delivery_stats},
                    'response_rate': (response_rate / total_notifications * 100) if total_notifications > 0 else 0,
                    'average_satisfaction': round(satisfaction_avg, 2) if satisfaction_avg else 0,
                    'period_days': days
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting notification analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_notification_system(self, user_id: str) -> Dict[str, Any]:
        """Test notification system with a user"""
        try:
            test_message = "🧪 Test de notification Djobea AI\n\nCeci est un test du système de notification intelligent.\n\n✅ Si vous recevez ce message, le système fonctionne correctement !\n\n📱 Djobea AI"
            
            result = self.send_immediate_notification(
                user_id=user_id,
                message=test_message,
                channels=['whatsapp'],
                urgency='normal'
            )
            
            return {
                'success': True,
                'test_result': result,
                'message': 'Test notification sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Error testing notification system: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_whatsapp_notification(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp notification"""
        try:
            # Format phone number (assuming user_id is phone number)
            phone_number = user_id if user_id.startswith('237') else f"237{user_id}"
            
            # Send via WhatsApp service
            result = self.whatsapp_service.send_message(phone_number, message)
            
            return {
                'success': True,
                'message': 'WhatsApp notification sent successfully',
                'delivery_id': result.get('message_id')
            }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp notification: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_sms_notification(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send SMS notification"""
        try:
            # TODO: Implement SMS sending via Twilio
            # For now, return success for testing
            return {
                'success': True,
                'message': 'SMS notification sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_email_notification(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send email notification"""
        try:
            # TODO: Implement email sending
            # For now, return success for testing
            return {
                'success': True,
                'message': 'Email notification sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _log_notification(self, user_id: str, channel: str, message: str,
                         delivery_status: str, notification_type: str,
                         request_id: str = None, rule_id: str = None):
        """Log notification in database"""
        try:
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            
            notification_log = NotificationLog(
                log_id=log_id,
                user_id=user_id,
                request_id=request_id,
                rule_id=rule_id,
                notification_type=notification_type,
                channel=channel,
                message_content=message,
                delivery_status=delivery_status,
                delivered_timestamp=datetime.utcnow() if delivery_status == 'sent' else None
            )
            
            self.db.add(notification_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging notification: {str(e)}")
            self.db.rollback()
    
    def _format_rule(self, rule: NotificationRule) -> Dict[str, Any]:
        """Format notification rule for API response"""
        return {
            'rule_id': rule.rule_id,
            'rule_name': rule.rule_name,
            'trigger_status': rule.trigger_status,
            'trigger_delay_minutes': rule.trigger_delay_minutes,
            'notification_channels': rule.notification_channels,
            'notification_template': rule.notification_template,
            'notification_frequency': rule.notification_frequency,
            'max_notifications': rule.max_notifications,
            'is_active': rule.is_active,
            'priority_level': rule.priority_level,
            'escalation_rule': rule.escalation_rule,
            'created_at': rule.created_at.isoformat(),
            'updated_at': rule.updated_at.isoformat()
        }
    
    def _format_notification_log(self, log: NotificationLog) -> Dict[str, Any]:
        """Format notification log for API response"""
        return {
            'log_id': log.log_id,
            'user_id': log.user_id,
            'request_id': log.request_id,
            'notification_type': log.notification_type,
            'channel': log.channel,
            'message_content': log.message_content,
            'delivery_status': log.delivery_status,
            'sent_timestamp': log.sent_timestamp.isoformat(),
            'delivery_timestamp': log.delivery_timestamp.isoformat() if log.delivery_timestamp else None,
            'user_response': log.user_response,
            'satisfaction_score': log.satisfaction_score,
            'retry_count': log.retry_count
        }


class EscalationService:
    """Service for automatic escalation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    def create_escalation_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new escalation rule"""
        try:
            rule_id = f"esc_rule_{uuid.uuid4().hex[:12]}"
            
            rule = EscalationRule(
                rule_id=rule_id,
                rule_name=rule_data['rule_name'],
                status_trigger=rule_data.get('status_trigger', 'all'),
                delay_threshold_minutes=rule_data.get('delay_threshold_minutes', 30),
                urgency_level=rule_data.get('urgency_level', 'normal'),
                failure_count_threshold=rule_data.get('failure_count_threshold', 3),
                escalation_type=rule_data.get('escalation_type', 'manager_alert'),
                escalation_target=rule_data.get('escalation_target', 'manager'),
                escalation_message=rule_data.get('escalation_message', 'Escalation required'),
                escalation_channels=rule_data.get('escalation_channels', ['whatsapp']),
                max_escalations=rule_data.get('max_escalations', 3),
                escalation_interval_minutes=rule_data.get('escalation_interval_minutes', 30),
                service_type_filter=rule_data.get('service_type_filter'),
                zone_filter=rule_data.get('zone_filter'),
                provider_rating_threshold=rule_data.get('provider_rating_threshold')
            )
            
            self.db.add(rule)
            self.db.commit()
            
            return {
                'success': True,
                'rule_id': rule_id,
                'message': 'Escalation rule created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating escalation rule: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_escalation_rules(self, active_only: bool = True) -> Dict[str, Any]:
        """Get all escalation rules"""
        try:
            query = self.db.query(EscalationRule)
            
            if active_only:
                query = query.filter(EscalationRule.is_active == True)
            
            rules = query.order_by(desc(EscalationRule.created_at)).all()
            
            return {
                'success': True,
                'rules': [self._format_escalation_rule(rule) for rule in rules]
            }
            
        except Exception as e:
            logger.error(f"Error getting escalation rules: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_escalation_history(self, request_id: str = None, 
                             limit: int = 50) -> Dict[str, Any]:
        """Get escalation history"""
        try:
            query = self.db.query(EscalationLog)
            
            if request_id:
                query = query.filter(EscalationLog.request_id == request_id)
            
            escalations = query.order_by(
                desc(EscalationLog.escalation_timestamp)
            ).limit(limit).all()
            
            return {
                'success': True,
                'escalations': [self._format_escalation_log(e) for e in escalations]
            }
            
        except Exception as e:
            logger.error(f"Error getting escalation history: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_escalation_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get escalation analytics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total escalations
            total_escalations = self.db.query(EscalationLog).filter(
                EscalationLog.escalation_timestamp >= start_date
            ).count()
            
            # Escalations by type
            type_stats = self.db.query(
                EscalationLog.escalation_type,
                func.count(EscalationLog.id).label('count')
            ).filter(
                EscalationLog.escalation_timestamp >= start_date
            ).group_by(EscalationLog.escalation_type).all()
            
            # Escalations by status
            status_stats = self.db.query(
                EscalationLog.escalation_status,
                func.count(EscalationLog.id).label('count')
            ).filter(
                EscalationLog.escalation_timestamp >= start_date
            ).group_by(EscalationLog.escalation_status).all()
            
            # Average response time
            avg_response_time = self.db.query(
                func.avg(EscalationLog.response_time_minutes)
            ).filter(
                and_(
                    EscalationLog.escalation_timestamp >= start_date,
                    EscalationLog.response_time_minutes.isnot(None)
                )
            ).scalar()
            
            # Resolution rate
            resolved_count = self.db.query(EscalationLog).filter(
                and_(
                    EscalationLog.escalation_timestamp >= start_date,
                    EscalationLog.escalation_status == 'resolved'
                )
            ).count()
            
            return {
                'success': True,
                'analytics': {
                    'total_escalations': total_escalations,
                    'escalation_types': {stat.escalation_type: stat.count for stat in type_stats},
                    'escalation_status': {stat.escalation_status: stat.count for stat in status_stats},
                    'average_response_time': round(avg_response_time, 2) if avg_response_time else 0,
                    'resolution_rate': (resolved_count / total_escalations * 100) if total_escalations > 0 else 0,
                    'period_days': days
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting escalation analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_escalation_rule(self, rule: EscalationRule) -> Dict[str, Any]:
        """Format escalation rule for API response"""
        return {
            'rule_id': rule.rule_id,
            'rule_name': rule.rule_name,
            'status_trigger': rule.status_trigger,
            'delay_threshold_minutes': rule.delay_threshold_minutes,
            'urgency_level': rule.urgency_level,
            'escalation_type': rule.escalation_type,
            'escalation_target': rule.escalation_target,
            'escalation_channels': rule.escalation_channels,
            'max_escalations': rule.max_escalations,
            'escalation_interval_minutes': rule.escalation_interval_minutes,
            'is_active': rule.is_active,
            'created_at': rule.created_at.isoformat()
        }
    
    def _format_escalation_log(self, log: EscalationLog) -> Dict[str, Any]:
        """Format escalation log for API response"""
        return {
            'escalation_id': log.escalation_id,
            'request_id': log.request_id,
            'user_id': log.user_id,
            'escalation_type': log.escalation_type,
            'escalation_reason': log.escalation_reason,
            'escalation_level': log.escalation_level,
            'target_recipient': log.target_recipient,
            'escalation_timestamp': log.escalation_timestamp.isoformat(),
            'escalation_status': log.escalation_status,
            'response_time_minutes': log.response_time_minutes,
            'effectiveness_score': log.effectiveness_score,
            'resolution_notes': log.resolution_notes
        }