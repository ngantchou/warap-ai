"""
Proactive Monitoring Service for Communication System
Real-time monitoring and debugging of proactive updates
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.database_models import ServiceRequest, User, Provider
from app.models.notification import NotificationQueue
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class ProactiveMonitoringService:
    """Service for monitoring proactive update system health"""
    
    def __init__(self, db: Session):
        self.db = db
        self.monitoring_stats = {
            'active_requests': 0,
            'failed_updates': 0,
            'successful_updates': 0,
            'timeout_warnings': 0,
            'errors_last_hour': 0,
            'last_check': datetime.utcnow()
        }
    
    async def get_system_health_status(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            # Get current time for comparisons
            current_time = datetime.utcnow()
            one_hour_ago = current_time - timedelta(hours=1)
            
            # Active requests in proactive update states
            active_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status.in_(['PROVIDER_NOTIFIED', 'PROVIDER_SEARCH', 'PENDING'])
            ).count()
            
            # Failed notifications in last hour
            failed_notifications_1h = self.db.query(NotificationQueue).filter(
                NotificationQueue.created_at > one_hour_ago,
                NotificationQueue.status == 'failed'
            ).count()
            
            # Successful notifications in last hour
            successful_notifications_1h = self.db.query(NotificationQueue).filter(
                NotificationQueue.created_at > one_hour_ago,
                NotificationQueue.status == 'sent'
            ).count()
            
            # Pending retry notifications
            pending_retries = self.db.query(NotificationQueue).filter(
                NotificationQueue.status == 'failed',
                NotificationQueue.retry_count < NotificationQueue.max_retries
            ).count()
            
            # Long-running requests (over 30 minutes)
            long_running_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == 'PROVIDER_NOTIFIED',
                ServiceRequest.created_at < (current_time - timedelta(minutes=30))
            ).count()
            
            # Calculate success rate
            total_notifications = failed_notifications_1h + successful_notifications_1h
            success_rate = (successful_notifications_1h / total_notifications * 100) if total_notifications > 0 else 0
            
            # Determine health status
            if success_rate >= 90 and long_running_requests == 0:
                health_status = "healthy"
            elif success_rate >= 70 and long_running_requests <= 2:
                health_status = "degraded"
            else:
                health_status = "critical"
            
            return {
                'health_status': health_status,
                'success_rate': round(success_rate, 2),
                'active_requests': active_requests,
                'failed_notifications_1h': failed_notifications_1h,
                'successful_notifications_1h': successful_notifications_1h,
                'pending_retries': pending_retries,
                'long_running_requests': long_running_requests,
                'total_notifications_1h': total_notifications,
                'last_check': current_time.isoformat(),
                'recommendations': self._generate_recommendations(
                    health_status, success_rate, long_running_requests, pending_retries
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting system health status: {e}")
            return {
                'health_status': 'unknown',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
    
    def _generate_recommendations(self, health_status: str, success_rate: float, 
                                long_running: int, pending_retries: int) -> List[str]:
        """Generate recommendations based on system health"""
        recommendations = []
        
        if health_status == "critical":
            recommendations.append("🚨 URGENT: Fix Twilio WhatsApp channel configuration")
            recommendations.append("🔧 Check API credentials and channel settings")
            
        if success_rate < 70:
            recommendations.append("📱 Implement SMS/Email fallback communication")
            recommendations.append("⚡ Consider upgrading Twilio account for higher limits")
            
        if long_running > 0:
            recommendations.append(f"⏰ {long_running} requests have been waiting >30 minutes")
            recommendations.append("🔄 Consider expanding provider network")
            
        if pending_retries > 5:
            recommendations.append(f"🔄 {pending_retries} notifications pending retry")
            recommendations.append("🛠️ Review retry mechanism effectiveness")
            
        if not recommendations:
            recommendations.append("✅ System operating normally")
            
        return recommendations
    
    async def get_detailed_error_analysis(self) -> Dict[str, Any]:
        """Get detailed analysis of recent errors"""
        try:
            current_time = datetime.utcnow()
            one_hour_ago = current_time - timedelta(hours=1)
            
            # Get recent failed notifications with error details
            failed_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.created_at > one_hour_ago,
                NotificationQueue.status == 'failed'
            ).order_by(NotificationQueue.created_at.desc()).limit(10).all()
            
            # Analyze error patterns
            error_patterns = {}
            for notification in failed_notifications:
                error_msg = notification.error_message or "Unknown error"
                error_type = self._categorize_error(error_msg)
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1
            
            # Get problematic requests
            problematic_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == 'PROVIDER_NOTIFIED',
                ServiceRequest.created_at < (current_time - timedelta(minutes=15))
            ).order_by(ServiceRequest.created_at.asc()).limit(5).all()
            
            return {
                'recent_errors': [
                    {
                        'id': n.id,
                        'user_id': n.user_id,
                        'error_message': n.error_message,
                        'notification_type': n.notification_type,
                        'retry_count': n.retry_count,
                        'created_at': n.created_at.isoformat() if n.created_at else None
                    }
                    for n in failed_notifications
                ],
                'error_patterns': error_patterns,
                'problematic_requests': [
                    {
                        'id': r.id,
                        'user_id': r.user_id,
                        'service_type': r.service_type,
                        'status': r.status,
                        'created_at': r.created_at.isoformat() if r.created_at else None,
                        'minutes_elapsed': int((current_time - r.created_at).total_seconds() / 60) if r.created_at else 0
                    }
                    for r in problematic_requests
                ],
                'analysis_time': current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed error analysis: {e}")
            return {
                'error': str(e),
                'analysis_time': datetime.utcnow().isoformat()
            }
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize error message into type"""
        error_msg = error_message.lower()
        
        if "channel" in error_msg or "63007" in error_msg:
            return "whatsapp_channel_config"
        elif "daily" in error_msg or "limit" in error_msg or "63038" in error_msg:
            return "daily_limit_exceeded"
        elif "phone" in error_msg or "user" in error_msg:
            return "user_lookup_error"
        elif "timeout" in error_msg or "connection" in error_msg:
            return "network_timeout"
        elif "database" in error_msg or "transaction" in error_msg:
            return "database_error"
        else:
            return "unknown_error"
    
    async def get_proactive_update_status(self) -> Dict[str, Any]:
        """Get status of proactive update system"""
        try:
            current_time = datetime.utcnow()
            
            # Get requests currently in proactive update cycle
            active_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status.in_(['PROVIDER_NOTIFIED', 'PROVIDER_SEARCH'])
            ).all()
            
            # Analyze each request
            request_analysis = []
            for request in active_requests:
                time_elapsed = (current_time - request.created_at).total_seconds() / 60
                
                # Check for recent notifications
                recent_notifications = self.db.query(NotificationQueue).filter(
                    NotificationQueue.request_id == request.id,
                    NotificationQueue.created_at > (current_time - timedelta(minutes=10))
                ).count()
                
                request_analysis.append({
                    'request_id': request.id,
                    'user_id': request.user_id,
                    'service_type': request.service_type,
                    'status': request.status,
                    'minutes_elapsed': int(time_elapsed),
                    'recent_notifications': recent_notifications,
                    'urgency': request.urgency,
                    'location': request.location[:50] if request.location else None,
                    'needs_attention': time_elapsed > 30 or recent_notifications == 0
                })
            
            # Calculate system metrics
            total_active = len(active_requests)
            needs_attention = sum(1 for r in request_analysis if r['needs_attention'])
            
            return {
                'total_active_requests': total_active,
                'requests_needing_attention': needs_attention,
                'requests_analysis': request_analysis,
                'system_performance': {
                    'average_processing_time': self._calculate_avg_processing_time(),
                    'success_rate_24h': self._calculate_success_rate_24h(),
                    'provider_response_rate': self._calculate_provider_response_rate()
                },
                'status_time': current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting proactive update status: {e}")
            return {
                'error': str(e),
                'status_time': datetime.utcnow().isoformat()
            }
    
    def _calculate_avg_processing_time(self) -> float:
        """Calculate average processing time for completed requests"""
        try:
            completed_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == 'COMPLETED',
                ServiceRequest.created_at > (datetime.utcnow() - timedelta(days=1))
            ).all()
            
            if not completed_requests:
                return 0.0
            
            total_time = sum(
                (r.completed_at - r.created_at).total_seconds() / 60 
                for r in completed_requests 
                if r.completed_at
            )
            
            return round(total_time / len(completed_requests), 2)
            
        except Exception as e:
            logger.error(f"Error calculating average processing time: {e}")
            return 0.0
    
    def _calculate_success_rate_24h(self) -> float:
        """Calculate success rate in last 24 hours"""
        try:
            since_24h = datetime.utcnow() - timedelta(hours=24)
            
            total_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.created_at > since_24h
            ).count()
            
            completed_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.created_at > since_24h,
                ServiceRequest.status == 'COMPLETED'
            ).count()
            
            return round((completed_requests / total_requests * 100), 2) if total_requests > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 0.0
    
    def _calculate_provider_response_rate(self) -> float:
        """Calculate provider response rate"""
        try:
            since_24h = datetime.utcnow() - timedelta(hours=24)
            
            notified_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.created_at > since_24h,
                ServiceRequest.status.in_(['PROVIDER_NOTIFIED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED'])
            ).count()
            
            accepted_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.created_at > since_24h,
                ServiceRequest.status.in_(['ASSIGNED', 'IN_PROGRESS', 'COMPLETED'])
            ).count()
            
            return round((accepted_requests / notified_requests * 100), 2) if notified_requests > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating provider response rate: {e}")
            return 0.0
    
    async def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        try:
            health_status = await self.get_system_health_status()
            error_analysis = await self.get_detailed_error_analysis()
            proactive_status = await self.get_proactive_update_status()
            
            return {
                'report_timestamp': datetime.utcnow().isoformat(),
                'system_health': health_status,
                'error_analysis': error_analysis,
                'proactive_updates': proactive_status,
                'summary': {
                    'overall_status': health_status.get('health_status', 'unknown'),
                    'immediate_actions_needed': health_status.get('health_status') == 'critical',
                    'primary_issues': [
                        pattern for pattern, count in error_analysis.get('error_patterns', {}).items() 
                        if count > 2
                    ],
                    'system_recommendations': health_status.get('recommendations', [])
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating monitoring report: {e}")
            return {
                'error': str(e),
                'report_timestamp': datetime.utcnow().isoformat()
            }