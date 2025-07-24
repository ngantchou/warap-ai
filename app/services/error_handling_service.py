"""
Comprehensive Error Handling Service for Djobea AI
Handles WhatsApp failures, provider matching issues, and system errors
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.models.notification import NotificationQueue
from app.models.database_models import ServiceRequest, User, Provider
from app.services.notification_retry_service import NotificationRetryService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class ErrorHandlingService:
    """Comprehensive error handling for system failures"""
    
    def __init__(self, db: Session):
        self.db = db
        self.retry_service = NotificationRetryService(db)
    
    async def handle_whatsapp_failure(self, user_id: str, request_id: int, message: str, notification_type: str = "error") -> bool:
        """Handle WhatsApp service failures"""
        try:
            # Store failed notification for retry
            notification = NotificationQueue(
                user_id=user_id,
                request_id=request_id,
                message=message,
                notification_type=notification_type,
                status="failed",
                retry_count=0,
                max_retries=5,  # Higher retry count for critical notifications
                error_message="WhatsApp service unavailable"
            )
            
            self.db.add(notification)
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            
            logger.info(f"WhatsApp failure handled for user {user_id}, request {request_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling WhatsApp failure: {e}")
            return False
    
    async def handle_provider_matching_failure(self, request: ServiceRequest) -> bool:
        """Handle cases where no providers are found"""
        try:
            user = self.db.query(User).filter(User.id == request.user_id).first()
            if not user:
                logger.error(f"User not found for request {request.id}")
                return False
            
            # Create comprehensive error message
            error_message = f"""
🚨 **Service temporairement indisponible**

Nous n'avons pas pu trouver de prestataire disponible pour votre demande de {request.service_type} à {request.location}.

🔄 **Options disponibles :**
1. Nous continuons à chercher des prestataires
2. Élargissement de la zone de recherche
3. Nous vous contacterons dès qu'un prestataire sera disponible

📞 **Assistance urgente :** Contactez le service client au 237 XXX XXX XXX

**Référence :** REQ-{request.id}
"""
            
            # Store error notification
            await self.handle_whatsapp_failure(
                user_id=request.user_id,
                request_id=request.id,
                message=error_message,
                notification_type="provider_not_found"
            )
            
            # Update request status
            request.status = "provider_search_failed"
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            
            # Log for manual intervention
            logger.warning(f"Provider matching failed for request {request.id}: {request.service_type} in {request.location}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling provider matching failure: {e}")
            return False
    
    async def handle_system_error(self, error_type: str, error_message: str, context: Dict[str, Any]) -> bool:
        """Handle general system errors"""
        try:
            # Log system error
            logger.error(f"System error [{error_type}]: {error_message}")
            logger.error(f"Context: {context}")
            
            # If there's a user and request involved, notify them
            if 'user_id' in context and 'request_id' in context:
                fallback_message = f"""
⚠️ **Erreur technique temporaire**

Nous rencontrons une difficulté technique avec votre demande.

🔧 **Actions prises :**
- Votre demande est enregistrée (REF: REQ-{context['request_id']})
- Nos équipes techniques sont notifiées
- Nous vous contacterons dès que possible

Nous nous excusons pour ce désagrément.
"""
                
                await self.handle_whatsapp_failure(
                    user_id=context['user_id'],
                    request_id=context['request_id'],
                    message=fallback_message,
                    notification_type="system_error"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling system error: {e}")
            return False
    
    async def monitor_and_retry_failed_operations(self) -> Dict[str, int]:
        """Monitor and retry failed operations"""
        try:
            # Retry failed notifications
            retried_notifications = await self.retry_service.process_failed_notifications()
            
            # Check for requests stuck in processing
            stuck_requests = await self._handle_stuck_requests()
            
            # Clean up old notifications
            cleaned_notifications = self.retry_service.cleanup_old_notifications(days_old=7)
            
            stats = {
                'retried_notifications': retried_notifications,
                'handled_stuck_requests': stuck_requests,
                'cleaned_notifications': cleaned_notifications
            }
            
            logger.info(f"Error handling monitoring completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in monitoring and retry: {e}")
            return {'error': str(e)}
    
    async def _handle_stuck_requests(self) -> int:
        """Handle requests stuck in processing states"""
        try:
            # Find requests stuck in processing for more than 30 minutes
            thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
            
            stuck_requests = self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.status.in_(['provider_search', 'provider_notified']),
                    ServiceRequest.created_at < thirty_minutes_ago
                )
            ).all()
            
            handled_count = 0
            for request in stuck_requests:
                try:
                    # Try to recover the request
                    if request.status == 'provider_search':
                        await self.handle_provider_matching_failure(request)
                    elif request.status == 'provider_notified':
                        # Reset to search for new providers
                        request.status = 'provider_search'
                        self.db.commit()
                        # Trigger new provider search
                        await self.handle_provider_matching_failure(request)
                    
                    handled_count += 1
                    
                except Exception as e:
                    logger.error(f"Error handling stuck request {request.id}: {e}")
            
            if handled_count > 0:
                logger.info(f"Handled {handled_count} stuck requests")
            
            return handled_count
            
        except Exception as e:
            logger.error(f"Error handling stuck requests: {e}")
            return 0
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        try:
            # Notification retry statistics
            retry_stats = self.retry_service.get_retry_statistics()
            
            # Request failure statistics
            request_failures = self.db.query(
                ServiceRequest.status,
                func.count(ServiceRequest.id).label('count')
            ).filter(
                ServiceRequest.status.in_(['provider_search_failed', 'system_error', 'cancelled'])
            ).group_by(ServiceRequest.status).all()
            
            # Recent error patterns
            recent_errors = self.db.query(NotificationQueue).filter(
                NotificationQueue.created_at > (datetime.utcnow() - timedelta(hours=24))
            ).count()
            
            return {
                'notification_retries': retry_stats,
                'request_failures': {status: count for status, count in request_failures},
                'recent_errors_24h': recent_errors,
                'system_health': self._assess_system_health()
            }
            
        except Exception as e:
            logger.error(f"Error getting error statistics: {e}")
            return {'error': str(e)}
    
    def _assess_system_health(self) -> str:
        """Assess overall system health"""
        try:
            # Check recent success rate
            recent_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.created_at > (datetime.utcnow() - timedelta(hours=2))
            ).count()
            
            if recent_requests == 0:
                return "healthy"  # No recent activity
            
            failed_requests = self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.created_at > (datetime.utcnow() - timedelta(hours=2)),
                    ServiceRequest.status.in_(['provider_search_failed', 'system_error'])
                )
            ).count()
            
            success_rate = (recent_requests - failed_requests) / recent_requests
            
            if success_rate >= 0.9:
                return "healthy"
            elif success_rate >= 0.7:
                return "degraded"
            else:
                return "critical"
                
        except Exception as e:
            logger.error(f"Error assessing system health: {e}")
            return "unknown"
    
    async def create_manual_intervention_alert(self, request_id: int, alert_type: str, description: str) -> bool:
        """Create alert for manual intervention"""
        try:
            # In a real system, this would integrate with monitoring tools
            # For now, we'll log it prominently
            logger.critical(f"MANUAL INTERVENTION REQUIRED - {alert_type}")
            logger.critical(f"Request ID: {request_id}")
            logger.critical(f"Description: {description}")
            logger.critical(f"Time: {datetime.utcnow()}")
            
            # You could also send this to a monitoring service, Slack, etc.
            return True
            
        except Exception as e:
            logger.error(f"Error creating manual intervention alert: {e}")
            return False