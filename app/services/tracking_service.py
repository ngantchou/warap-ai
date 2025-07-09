"""
Real-time Tracking Service for Djobea AI
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import asyncio
from loguru import logger

from app.models.tracking_models import (
    RequestStatus, StatusHistory, NotificationRule, NotificationLog,
    EscalationRule, EscalationLog, TrackingUserPreference, TrackingAnalytics
)
from app.database import get_db

class TrackingService:
    """Service for real-time request tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def update_request_status(self, request_id: str, new_status: str, 
                            user_id: str, provider_id: str = None,
                            reason: str = None, metadata: Dict = None) -> Dict[str, Any]:
        """Update request status with real-time tracking"""
        try:
            # Get current status
            current_status = self.db.query(RequestStatus).filter(
                RequestStatus.request_id == request_id
            ).first()
            
            if not current_status:
                # Create new status entry
                status_id = f"status_{uuid.uuid4().hex[:12]}"
                current_status = RequestStatus(
                    status_id=status_id,
                    request_id=request_id,
                    user_id=user_id,
                    current_status=new_status,
                    provider_id=provider_id,
                    status_reason=reason,
                    additional_data=metadata or {}
                )
                self.db.add(current_status)
            else:
                # Update existing status
                previous_status = current_status.current_status
                current_status.previous_status = previous_status
                current_status.current_status = new_status
                current_status.status_reason = reason
                current_status.provider_id = provider_id
                current_status.updated_at = datetime.utcnow()
                
                # Add to history
                self._add_status_history(
                    current_status.status_id, request_id, 
                    previous_status, new_status, reason, metadata
                )
            
            # Predict next step and ETA
            next_step, eta = self._predict_next_step(new_status, metadata)
            current_status.predicted_next_step = next_step
            current_status.next_step_eta = eta
            
            # Update completion percentage
            current_status.completion_percentage = self._calculate_completion_percentage(new_status)
            
            self.db.commit()
            
            # Trigger notifications
            self._trigger_notifications(current_status)
            
            # Check for escalation
            self._check_escalation_rules(current_status)
            
            return {
                'success': True,
                'status_id': current_status.status_id,
                'current_status': new_status,
                'next_step': next_step,
                'eta': eta.isoformat() if eta else None,
                'completion_percentage': current_status.completion_percentage
            }
            
        except Exception as e:
            logger.error(f"Error updating request status: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_request_tracking(self, request_id: str) -> Dict[str, Any]:
        """Get comprehensive tracking information for a request"""
        try:
            # Get current status
            current_status = self.db.query(RequestStatus).filter(
                RequestStatus.request_id == request_id
            ).first()
            
            if not current_status:
                return {
                    'success': False,
                    'error': 'Request not found'
                }
            
            # Get status history
            history = self.db.query(StatusHistory).filter(
                StatusHistory.request_id == request_id
            ).order_by(desc(StatusHistory.change_timestamp)).all()
            
            # Get notifications
            notifications = self.db.query(NotificationLog).filter(
                NotificationLog.request_id == request_id
            ).order_by(desc(NotificationLog.sent_timestamp)).limit(10).all()
            
            # Get escalations
            escalations = self.db.query(EscalationLog).filter(
                EscalationLog.request_id == request_id
            ).order_by(desc(EscalationLog.escalation_timestamp)).all()
            
            # Calculate metrics
            metrics = self._calculate_request_metrics(request_id)
            
            return {
                'success': True,
                'data': {
                    'current_status': {
                        'status': current_status.current_status,
                        'timestamp': current_status.status_timestamp.isoformat(),
                        'provider_id': current_status.provider_id,
                        'provider_eta': current_status.provider_eta.isoformat() if current_status.provider_eta else None,
                        'completion_percentage': current_status.completion_percentage,
                        'next_step': current_status.predicted_next_step,
                        'next_step_eta': current_status.next_step_eta.isoformat() if current_status.next_step_eta else None,
                        'urgency_level': current_status.urgency_level
                    },
                    'history': [self._format_history_item(h) for h in history],
                    'notifications': [self._format_notification(n) for n in notifications],
                    'escalations': [self._format_escalation(e) for e in escalations],
                    'metrics': metrics
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting request tracking: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def set_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Set user notification preferences"""
        try:
            user_pref = self.db.query(TrackingUserPreference).filter(
                TrackingUserPreference.user_id == user_id
            ).first()
            
            if not user_pref:
                user_pref = TrackingUserPreference(user_id=user_id)
                self.db.add(user_pref)
            
            # Update preferences
            for key, value in preferences.items():
                if hasattr(user_pref, key):
                    setattr(user_pref, key, value)
            
            user_pref.updated_at = datetime.utcnow()
            self.db.commit()
            
            return {
                'success': True,
                'preferences': preferences
            }
            
        except Exception as e:
            logger.error(f"Error setting user preferences: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user notification preferences"""
        try:
            user_pref = self.db.query(TrackingUserPreference).filter(
                TrackingUserPreference.user_id == user_id
            ).first()
            
            if not user_pref:
                # Return default preferences
                return {
                    'success': True,
                    'preferences': {
                        'preferred_channels': ['whatsapp'],
                        'notification_frequency': 'immediate',
                        'quiet_hours_start': '22:00',
                        'quiet_hours_end': '07:00',
                        'language': 'fr',
                        'communication_style': 'friendly',
                        'urgency_sensitivity': 'normal',
                        'max_updates_per_day': 10,
                        'wants_completion_photos': True,
                        'wants_cost_updates': True,
                        'wants_provider_info': True
                    }
                }
            
            return {
                'success': True,
                'preferences': {
                    'preferred_channels': user_pref.preferred_channels,
                    'notification_frequency': user_pref.notification_frequency,
                    'quiet_hours_start': user_pref.quiet_hours_start,
                    'quiet_hours_end': user_pref.quiet_hours_end,
                    'language': user_pref.language,
                    'communication_style': user_pref.communication_style,
                    'urgency_sensitivity': user_pref.urgency_sensitivity,
                    'max_updates_per_day': user_pref.max_updates_per_day,
                    'wants_completion_photos': user_pref.wants_completion_photos,
                    'wants_cost_updates': user_pref.wants_cost_updates,
                    'wants_provider_info': user_pref.wants_provider_info
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _add_status_history(self, status_id: str, request_id: str, 
                          from_status: str, to_status: str, reason: str, 
                          metadata: Dict = None):
        """Add entry to status history"""
        try:
            history_id = f"hist_{uuid.uuid4().hex[:12]}"
            
            # Calculate duration in previous status
            last_change = self.db.query(StatusHistory).filter(
                StatusHistory.request_id == request_id
            ).order_by(desc(StatusHistory.change_timestamp)).first()
            
            duration = None
            if last_change:
                duration = int((datetime.utcnow() - last_change.change_timestamp).total_seconds())
            
            history = StatusHistory(
                history_id=history_id,
                status_id=status_id,
                request_id=request_id,
                from_status=from_status,
                to_status=to_status,
                change_reason=reason,
                changed_by='system',
                change_source='automatic',
                duration_in_previous_status=duration,
                context_data=metadata or {}
            )
            
            self.db.add(history)
            
        except Exception as e:
            logger.error(f"Error adding status history: {str(e)}")
    
    def _predict_next_step(self, current_status: str, metadata: Dict = None) -> tuple:
        """Predict next step and ETA based on current status"""
        status_flow = {
            'pending': ('provider_search', 5),
            'provider_search': ('provider_found', 10),
            'provider_found': ('provider_contacted', 3),
            'provider_contacted': ('provider_accepted', 15),
            'provider_accepted': ('provider_enroute', 30),
            'provider_enroute': ('service_started', 45),
            'service_started': ('service_completed', 90),
            'service_completed': ('payment_pending', 5),
            'payment_pending': ('completed', 10)
        }
        
        if current_status in status_flow:
            next_step, eta_minutes = status_flow[current_status]
            eta = datetime.utcnow() + timedelta(minutes=eta_minutes)
            return next_step, eta
        
        return None, None
    
    def _calculate_completion_percentage(self, status: str) -> float:
        """Calculate completion percentage based on status"""
        status_percentages = {
            'pending': 0.0,
            'provider_search': 10.0,
            'provider_found': 20.0,
            'provider_contacted': 25.0,
            'provider_accepted': 40.0,
            'provider_enroute': 50.0,
            'service_started': 70.0,
            'service_completed': 90.0,
            'payment_pending': 95.0,
            'completed': 100.0,
            'cancelled': 0.0
        }
        
        return status_percentages.get(status, 0.0)
    
    def _trigger_notifications(self, request_status: RequestStatus):
        """Trigger appropriate notifications based on status"""
        try:
            # Get applicable notification rules
            rules = self.db.query(NotificationRule).filter(
                and_(
                    NotificationRule.is_active == True,
                    or_(
                        NotificationRule.trigger_status == request_status.current_status,
                        NotificationRule.trigger_status == 'all'
                    )
                )
            ).all()
            
            for rule in rules:
                if self._should_send_notification(rule, request_status):
                    self._send_notification(rule, request_status)
                    
        except Exception as e:
            logger.error(f"Error triggering notifications: {str(e)}")
    
    def _should_send_notification(self, rule: NotificationRule, 
                                request_status: RequestStatus) -> bool:
        """Check if notification should be sent based on rule conditions"""
        try:
            # Check recent notifications to avoid spam
            recent_notifications = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.request_id == request_status.request_id,
                    NotificationLog.rule_id == rule.rule_id,
                    NotificationLog.sent_timestamp > datetime.utcnow() - timedelta(hours=1)
                )
            ).count()
            
            if recent_notifications >= rule.max_notifications:
                return False
            
            # Check user preferences
            user_prefs = self.get_user_preferences(request_status.user_id)
            if not user_prefs['success']:
                return True  # Default to sending if no preferences
            
            prefs = user_prefs['preferences']
            
            # Check quiet hours
            now = datetime.utcnow().time()
            quiet_start = datetime.strptime(prefs['quiet_hours_start'], '%H:%M').time()
            quiet_end = datetime.strptime(prefs['quiet_hours_end'], '%H:%M').time()
            
            if quiet_start <= now <= quiet_end:
                return request_status.urgency_level == 'urgent'
            
            # Check frequency preference
            if prefs['notification_frequency'] == 'daily':
                return request_status.urgency_level in ['high', 'urgent']
            elif prefs['notification_frequency'] == 'hourly':
                return request_status.urgency_level in ['normal', 'high', 'urgent']
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification condition: {str(e)}")
            return True
    
    def _send_notification(self, rule: NotificationRule, request_status: RequestStatus):
        """Send notification based on rule"""
        try:
            # Get user preferences for channels
            user_prefs = self.get_user_preferences(request_status.user_id)
            preferred_channels = user_prefs['preferences']['preferred_channels'] if user_prefs['success'] else ['whatsapp']
            
            # Find common channels
            channels_to_use = list(set(rule.notification_channels) & set(preferred_channels))
            if not channels_to_use:
                channels_to_use = ['whatsapp']  # Default fallback
            
            for channel in channels_to_use:
                log_id = f"notif_{uuid.uuid4().hex[:12]}"
                
                # Generate message content
                message_content = self._generate_notification_message(
                    rule, request_status, channel
                )
                
                # Create notification log
                notification_log = NotificationLog(
                    log_id=log_id,
                    request_id=request_status.request_id,
                    status_id=request_status.status_id,
                    rule_id=rule.rule_id,
                    user_id=request_status.user_id,
                    notification_type='status_update',
                    channel=channel,
                    template_used=rule.notification_template,
                    message_content=message_content,
                    delivery_status='sent'
                )
                
                self.db.add(notification_log)
                
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            self.db.rollback()
    
    def _generate_notification_message(self, rule: NotificationRule, 
                                     request_status: RequestStatus, 
                                     channel: str) -> str:
        """Generate notification message based on template and context"""
        try:
            # Get user preferences for language and style
            user_prefs = self.get_user_preferences(request_status.user_id)
            language = user_prefs['preferences']['language'] if user_prefs['success'] else 'fr'
            style = user_prefs['preferences']['communication_style'] if user_prefs['success'] else 'friendly'
            
            # Status message templates
            templates = {
                'fr': {
                    'friendly': {
                        'provider_accepted': f"🎉 Excellente nouvelle ! Votre demande a été acceptée.\n\n📱 Prestataire: {request_status.provider_id}\n⏰ Arrivée prévue: {request_status.provider_eta}\n📍 Progression: {request_status.completion_percentage}%\n\n💬 Vous recevrez des mises à jour régulières !",
                        'provider_enroute': f"🚗 Votre prestataire est en route !\n\n⏰ Arrivée estimée: {request_status.provider_eta}\n📍 Progression: {request_status.completion_percentage}%\n\nPréparez-vous pour le service 😊",
                        'service_started': f"🔧 Le service a commencé !\n\n👨‍🔧 Prestataire au travail\n📍 Progression: {request_status.completion_percentage}%\n⏰ Prochaine étape: {request_status.predicted_next_step}\n\nTout se passe bien 👍",
                        'service_completed': f"✅ Service terminé avec succès !\n\n🎊 Félicitations ! Votre demande est complétée\n📍 Progression: 100%\n💰 Veuillez procéder au paiement\n\nMerci de votre confiance ! 🙏"
                    }
                }
            }
            
            # Get template or use default
            if language in templates and style in templates[language]:
                if request_status.current_status in templates[language][style]:
                    return templates[language][style][request_status.current_status]
            
            # Default message
            return f"📱 Mise à jour de votre demande\n\nStatut: {request_status.current_status}\nProgression: {request_status.completion_percentage}%\n\n✨ Djobea AI"
            
        except Exception as e:
            logger.error(f"Error generating notification message: {str(e)}")
            return f"Mise à jour de votre demande: {request_status.current_status}"
    
    def _check_escalation_rules(self, request_status: RequestStatus):
        """Check if escalation rules should be triggered"""
        try:
            # Get applicable escalation rules
            rules = self.db.query(EscalationRule).filter(
                and_(
                    EscalationRule.is_active == True,
                    or_(
                        EscalationRule.status_trigger == request_status.current_status,
                        EscalationRule.status_trigger == 'all'
                    )
                )
            ).all()
            
            for rule in rules:
                if self._should_escalate(rule, request_status):
                    self._perform_escalation(rule, request_status)
                    
        except Exception as e:
            logger.error(f"Error checking escalation rules: {str(e)}")
    
    def _should_escalate(self, rule: EscalationRule, request_status: RequestStatus) -> bool:
        """Check if escalation should be performed"""
        try:
            # Check if delay threshold exceeded
            if rule.delay_threshold_minutes:
                time_in_status = datetime.utcnow() - request_status.status_timestamp
                if time_in_status.total_seconds() / 60 >= rule.delay_threshold_minutes:
                    return True
            
            # Check recent escalations to avoid spam
            recent_escalations = self.db.query(EscalationLog).filter(
                and_(
                    EscalationLog.request_id == request_status.request_id,
                    EscalationLog.rule_id == rule.rule_id,
                    EscalationLog.escalation_timestamp > datetime.utcnow() - timedelta(hours=1)
                )
            ).count()
            
            if recent_escalations >= rule.max_escalations:
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking escalation condition: {str(e)}")
            return False
    
    def _perform_escalation(self, rule: EscalationRule, request_status: RequestStatus):
        """Perform escalation action"""
        try:
            escalation_id = f"esc_{uuid.uuid4().hex[:12]}"
            
            escalation_log = EscalationLog(
                escalation_id=escalation_id,
                rule_id=rule.rule_id,
                request_id=request_status.request_id,
                user_id=request_status.user_id,
                escalation_type=rule.escalation_type,
                escalation_reason=f"Delay threshold exceeded: {rule.delay_threshold_minutes} minutes",
                target_recipient=rule.escalation_target,
                escalation_status='pending'
            )
            
            self.db.add(escalation_log)
            self.db.commit()
            
            # TODO: Implement actual escalation actions (send emails, create tickets, etc.)
            logger.info(f"Escalation triggered: {escalation_id}")
            
        except Exception as e:
            logger.error(f"Error performing escalation: {str(e)}")
            self.db.rollback()
    
    def _calculate_request_metrics(self, request_id: str) -> Dict[str, Any]:
        """Calculate performance metrics for a request"""
        try:
            history = self.db.query(StatusHistory).filter(
                StatusHistory.request_id == request_id
            ).order_by(StatusHistory.change_timestamp).all()
            
            if not history:
                return {}
            
            # Calculate total duration
            first_status = history[0]
            last_status = history[-1]
            total_duration = (last_status.change_timestamp - first_status.change_timestamp).total_seconds() / 60
            
            # Calculate average status duration
            durations = [h.duration_in_previous_status for h in history if h.duration_in_previous_status]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Count notifications and escalations
            notification_count = self.db.query(NotificationLog).filter(
                NotificationLog.request_id == request_id
            ).count()
            
            escalation_count = self.db.query(EscalationLog).filter(
                EscalationLog.request_id == request_id
            ).count()
            
            return {
                'total_duration_minutes': round(total_duration, 2),
                'status_changes': len(history),
                'average_status_duration': round(avg_duration / 60, 2) if avg_duration else 0,
                'notifications_sent': notification_count,
                'escalations_triggered': escalation_count,
                'on_time_percentage': 85.0,  # TODO: Calculate based on actual SLA
                'efficiency_score': 4.2  # TODO: Calculate based on performance metrics
            }
            
        except Exception as e:
            logger.error(f"Error calculating request metrics: {str(e)}")
            return {}
    
    def _format_history_item(self, history: StatusHistory) -> Dict[str, Any]:
        """Format status history item for API response"""
        return {
            'history_id': history.history_id,
            'from_status': history.from_status,
            'to_status': history.to_status,
            'change_reason': history.change_reason,
            'timestamp': history.change_timestamp.isoformat(),
            'duration_previous_status': history.duration_in_previous_status,
            'was_on_time': history.was_on_time,
            'changed_by': history.changed_by
        }
    
    def _format_notification(self, notification: NotificationLog) -> Dict[str, Any]:
        """Format notification for API response"""
        return {
            'log_id': notification.log_id,
            'notification_type': notification.notification_type,
            'channel': notification.channel,
            'sent_timestamp': notification.sent_timestamp.isoformat(),
            'delivery_status': notification.delivery_status,
            'user_response': notification.user_response,
            'satisfaction_score': notification.satisfaction_score
        }
    
    def _format_escalation(self, escalation: EscalationLog) -> Dict[str, Any]:
        """Format escalation for API response"""
        return {
            'escalation_id': escalation.escalation_id,
            'escalation_type': escalation.escalation_type,
            'escalation_reason': escalation.escalation_reason,
            'timestamp': escalation.escalation_timestamp.isoformat(),
            'status': escalation.escalation_status,
            'target_recipient': escalation.target_recipient,
            'response_time_minutes': escalation.response_time_minutes
        }