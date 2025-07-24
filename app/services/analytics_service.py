"""
Analytics Service for Real-time Tracking System
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, case
from loguru import logger

from app.models.tracking_models import (
    RequestStatus, StatusHistory, NotificationLog, EscalationLog,
    TrackingAnalytics, TrackingUserPreference
)
from app.database import get_db

class AnalyticsService:
    """Service for tracking system analytics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Request completion metrics
            completion_stats = self._get_completion_metrics(start_date)
            
            # Response time metrics
            response_time_stats = self._get_response_time_metrics(start_date)
            
            # Notification performance
            notification_stats = self._get_notification_performance(start_date)
            
            # Escalation metrics
            escalation_stats = self._get_escalation_metrics(start_date)
            
            # User satisfaction metrics
            satisfaction_stats = self._get_satisfaction_metrics(start_date)
            
            return {
                'success': True,
                'period_days': days,
                'metrics': {
                    'completion': completion_stats,
                    'response_time': response_time_stats,
                    'notifications': notification_stats,
                    'escalations': escalation_stats,
                    'satisfaction': satisfaction_stats
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Get real-time dashboard data"""
        try:
            # Current active requests
            active_requests = self.db.query(RequestStatus).filter(
                RequestStatus.current_status.in_([
                    'pending', 'provider_search', 'provider_found', 
                    'provider_contacted', 'provider_accepted', 
                    'provider_enroute', 'service_started'
                ])
            ).count()
            
            # Requests completed today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            completed_today = self.db.query(RequestStatus).filter(
                and_(
                    RequestStatus.current_status == 'completed',
                    RequestStatus.updated_at >= today_start
                )
            ).count()
            
            # Urgent requests
            urgent_requests = self.db.query(RequestStatus).filter(
                and_(
                    RequestStatus.urgency_level == 'urgent',
                    RequestStatus.current_status != 'completed'
                )
            ).count()
            
            # Notifications sent today
            notifications_today = self.db.query(NotificationLog).filter(
                NotificationLog.sent_timestamp >= today_start
            ).count()
            
            # Escalations today
            escalations_today = self.db.query(EscalationLog).filter(
                EscalationLog.escalation_timestamp >= today_start
            ).count()
            
            # Average response time today
            avg_response_time = self.db.query(
                func.avg(StatusHistory.duration_in_previous_status)
            ).filter(
                and_(
                    StatusHistory.change_timestamp >= today_start,
                    StatusHistory.duration_in_previous_status.isnot(None)
                )
            ).scalar()
            
            return {
                'success': True,
                'dashboard': {
                    'active_requests': active_requests,
                    'completed_today': completed_today,
                    'urgent_requests': urgent_requests,
                    'notifications_today': notifications_today,
                    'escalations_today': escalations_today,
                    'avg_response_time_minutes': round(avg_response_time / 60, 2) if avg_response_time else 0,
                    'last_updated': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time dashboard: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_service_analytics(self, service_type: str = None, 
                            zone: str = None, days: int = 30) -> Dict[str, Any]:
        """Get service-specific analytics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Base query
            query = self.db.query(TrackingAnalytics).filter(
                TrackingAnalytics.created_at >= start_date
            )
            
            if service_type:
                query = query.filter(TrackingAnalytics.service_type == service_type)
            
            if zone:
                query = query.filter(TrackingAnalytics.zone == zone)
            
            analytics = query.all()
            
            if not analytics:
                return {
                    'success': True,
                    'analytics': {
                        'total_requests': 0,
                        'average_duration': 0,
                        'completion_rate': 0,
                        'satisfaction_score': 0
                    }
                }
            
            # Calculate metrics
            total_requests = len(analytics)
            avg_duration = sum(a.total_duration_minutes for a in analytics) / total_requests
            completed_requests = sum(1 for a in analytics if a.completion_date)
            completion_rate = (completed_requests / total_requests) * 100
            
            satisfaction_scores = [a.user_satisfaction_score for a in analytics if a.user_satisfaction_score]
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
            
            return {
                'success': True,
                'filters': {
                    'service_type': service_type,
                    'zone': zone,
                    'period_days': days
                },
                'analytics': {
                    'total_requests': total_requests,
                    'average_duration_minutes': round(avg_duration, 2),
                    'completion_rate': round(completion_rate, 2),
                    'average_satisfaction': round(avg_satisfaction, 2),
                    'notifications_per_request': sum(a.notifications_sent for a in analytics) / total_requests,
                    'escalations_per_request': sum(a.escalations_count for a in analytics) / total_requests
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting service analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user-specific analytics"""
        try:
            # User requests
            user_requests = self.db.query(RequestStatus).filter(
                RequestStatus.user_id == user_id
            ).count()
            
            # User notifications
            user_notifications = self.db.query(NotificationLog).filter(
                NotificationLog.user_id == user_id
            ).count()
            
            # User preferences
            user_prefs = self.db.query(TrackingUserPreference).filter(
                TrackingUserPreference.user_id == user_id
            ).first()
            
            # User satisfaction
            user_satisfaction = self.db.query(
                func.avg(NotificationLog.satisfaction_score)
            ).filter(
                and_(
                    NotificationLog.user_id == user_id,
                    NotificationLog.satisfaction_score.isnot(None)
                )
            ).scalar()
            
            # Response rate
            responses = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.user_id == user_id,
                    NotificationLog.user_response.isnot(None)
                )
            ).count()
            
            response_rate = (responses / user_notifications * 100) if user_notifications > 0 else 0
            
            return {
                'success': True,
                'user_id': user_id,
                'analytics': {
                    'total_requests': user_requests,
                    'total_notifications': user_notifications,
                    'response_rate': round(response_rate, 2),
                    'average_satisfaction': round(user_satisfaction, 2) if user_satisfaction else 0,
                    'has_preferences': user_prefs is not None,
                    'preferred_channels': user_prefs.preferred_channels if user_prefs else ['whatsapp'],
                    'notification_frequency': user_prefs.notification_frequency if user_prefs else 'immediate'
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_optimization_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate optimization recommendations"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Identify slow processes
            slow_processes = self._identify_slow_processes(start_date)
            
            # Notification optimization
            notification_optimization = self._analyze_notification_effectiveness(start_date)
            
            # Escalation optimization
            escalation_optimization = self._analyze_escalation_patterns(start_date)
            
            # User experience optimization
            ux_optimization = self._analyze_user_experience(start_date)
            
            return {
                'success': True,
                'report_date': datetime.utcnow().isoformat(),
                'period_days': days,
                'optimizations': {
                    'slow_processes': slow_processes,
                    'notifications': notification_optimization,
                    'escalations': escalation_optimization,
                    'user_experience': ux_optimization
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating optimization report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_completion_metrics(self, start_date: datetime) -> Dict[str, Any]:
        """Get completion metrics"""
        try:
            # Total requests
            total_requests = self.db.query(RequestStatus).filter(
                RequestStatus.created_at >= start_date
            ).count()
            
            # Completed requests
            completed_requests = self.db.query(RequestStatus).filter(
                and_(
                    RequestStatus.created_at >= start_date,
                    RequestStatus.current_status == 'completed'
                )
            ).count()
            
            # Cancelled requests
            cancelled_requests = self.db.query(RequestStatus).filter(
                and_(
                    RequestStatus.created_at >= start_date,
                    RequestStatus.current_status == 'cancelled'
                )
            ).count()
            
            # Completion rate
            completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_requests': total_requests,
                'completed_requests': completed_requests,
                'cancelled_requests': cancelled_requests,
                'completion_rate': round(completion_rate, 2),
                'success_rate': round((completed_requests / (total_requests - cancelled_requests) * 100) if (total_requests - cancelled_requests) > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting completion metrics: {str(e)}")
            return {}
    
    def _get_response_time_metrics(self, start_date: datetime) -> Dict[str, Any]:
        """Get response time metrics"""
        try:
            # Status changes with duration
            status_changes = self.db.query(StatusHistory).filter(
                and_(
                    StatusHistory.change_timestamp >= start_date,
                    StatusHistory.duration_in_previous_status.isnot(None)
                )
            ).all()
            
            if not status_changes:
                return {
                    'average_response_time': 0,
                    'median_response_time': 0,
                    'fastest_response': 0,
                    'slowest_response': 0
                }
            
            durations = [change.duration_in_previous_status for change in status_changes]
            durations.sort()
            
            avg_duration = sum(durations) / len(durations)
            median_duration = durations[len(durations) // 2]
            
            return {
                'average_response_time': round(avg_duration / 60, 2),  # Convert to minutes
                'median_response_time': round(median_duration / 60, 2),
                'fastest_response': round(min(durations) / 60, 2),
                'slowest_response': round(max(durations) / 60, 2),
                'total_status_changes': len(status_changes)
            }
            
        except Exception as e:
            logger.error(f"Error getting response time metrics: {str(e)}")
            return {}
    
    def _get_notification_performance(self, start_date: datetime) -> Dict[str, Any]:
        """Get notification performance metrics"""
        try:
            # Total notifications
            total_notifications = self.db.query(NotificationLog).filter(
                NotificationLog.sent_timestamp >= start_date
            ).count()
            
            # Successful deliveries
            successful_deliveries = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.sent_timestamp >= start_date,
                    NotificationLog.delivery_status == 'delivered'
                )
            ).count()
            
            # User responses
            user_responses = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.sent_timestamp >= start_date,
                    NotificationLog.user_response.isnot(None)
                )
            ).count()
            
            return {
                'total_notifications': total_notifications,
                'delivery_rate': round((successful_deliveries / total_notifications * 100) if total_notifications > 0 else 0, 2),
                'response_rate': round((user_responses / total_notifications * 100) if total_notifications > 0 else 0, 2),
                'engagement_score': round((user_responses / successful_deliveries * 100) if successful_deliveries > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting notification performance: {str(e)}")
            return {}
    
    def _get_escalation_metrics(self, start_date: datetime) -> Dict[str, Any]:
        """Get escalation metrics"""
        try:
            # Total escalations
            total_escalations = self.db.query(EscalationLog).filter(
                EscalationLog.escalation_timestamp >= start_date
            ).count()
            
            # Resolved escalations
            resolved_escalations = self.db.query(EscalationLog).filter(
                and_(
                    EscalationLog.escalation_timestamp >= start_date,
                    EscalationLog.escalation_status == 'resolved'
                )
            ).count()
            
            # Average response time
            avg_response_time = self.db.query(
                func.avg(EscalationLog.response_time_minutes)
            ).filter(
                and_(
                    EscalationLog.escalation_timestamp >= start_date,
                    EscalationLog.response_time_minutes.isnot(None)
                )
            ).scalar()
            
            return {
                'total_escalations': total_escalations,
                'resolution_rate': round((resolved_escalations / total_escalations * 100) if total_escalations > 0 else 0, 2),
                'average_response_time': round(avg_response_time, 2) if avg_response_time else 0,
                'escalation_frequency': round(total_escalations / 30, 2)  # Per day
            }
            
        except Exception as e:
            logger.error(f"Error getting escalation metrics: {str(e)}")
            return {}
    
    def _get_satisfaction_metrics(self, start_date: datetime) -> Dict[str, Any]:
        """Get satisfaction metrics"""
        try:
            # Satisfaction scores
            satisfaction_scores = self.db.query(NotificationLog.satisfaction_score).filter(
                and_(
                    NotificationLog.sent_timestamp >= start_date,
                    NotificationLog.satisfaction_score.isnot(None)
                )
            ).all()
            
            if not satisfaction_scores:
                return {
                    'average_satisfaction': 0,
                    'satisfaction_count': 0,
                    'satisfaction_distribution': {}
                }
            
            scores = [score[0] for score in satisfaction_scores]
            avg_satisfaction = sum(scores) / len(scores)
            
            # Distribution
            distribution = {}
            for i in range(1, 6):
                distribution[f'{i}_star'] = scores.count(i)
            
            return {
                'average_satisfaction': round(avg_satisfaction, 2),
                'satisfaction_count': len(scores),
                'satisfaction_distribution': distribution,
                'satisfaction_rate': round((len([s for s in scores if s >= 4]) / len(scores) * 100), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting satisfaction metrics: {str(e)}")
            return {}
    
    def _identify_slow_processes(self, start_date: datetime) -> List[Dict[str, Any]]:
        """Identify slow processes"""
        try:
            # Get processes that take longer than average
            slow_processes = []
            
            # TODO: Implement process analysis
            # For now, return example recommendations
            return [
                {
                    'process': 'provider_search',
                    'average_duration': 12.5,
                    'recommended_duration': 8.0,
                    'improvement_potential': '35%',
                    'recommendation': 'Optimize provider matching algorithm'
                },
                {
                    'process': 'provider_acceptance',
                    'average_duration': 18.2,
                    'recommended_duration': 12.0,
                    'improvement_potential': '34%',
                    'recommendation': 'Implement faster notification system'
                }
            ]
            
        except Exception as e:
            logger.error(f"Error identifying slow processes: {str(e)}")
            return []
    
    def _analyze_notification_effectiveness(self, start_date: datetime) -> Dict[str, Any]:
        """Analyze notification effectiveness"""
        try:
            # TODO: Implement notification analysis
            return {
                'optimal_frequency': 'immediate',
                'best_channels': ['whatsapp', 'sms'],
                'peak_response_times': ['09:00-11:00', '14:00-16:00'],
                'recommendations': [
                    'Reduce notification frequency for non-urgent requests',
                    'Use WhatsApp for immediate notifications',
                    'Schedule bulk notifications during peak hours'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing notification effectiveness: {str(e)}")
            return {}
    
    def _analyze_escalation_patterns(self, start_date: datetime) -> Dict[str, Any]:
        """Analyze escalation patterns"""
        try:
            # TODO: Implement escalation analysis
            return {
                'most_common_triggers': ['provider_delay', 'service_quality'],
                'peak_escalation_times': ['17:00-19:00', '08:00-10:00'],
                'recommendations': [
                    'Implement proactive provider monitoring',
                    'Increase escalation threshold during peak hours',
                    'Add quality checkpoints during service delivery'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing escalation patterns: {str(e)}")
            return {}
    
    def _analyze_user_experience(self, start_date: datetime) -> Dict[str, Any]:
        """Analyze user experience"""
        try:
            # TODO: Implement UX analysis
            return {
                'satisfaction_drivers': ['response_speed', 'communication_clarity'],
                'pain_points': ['long_wait_times', 'unclear_status_updates'],
                'recommendations': [
                    'Improve status update clarity',
                    'Reduce response time for urgent requests',
                    'Add progress indicators for long processes'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user experience: {str(e)}")
            return {}