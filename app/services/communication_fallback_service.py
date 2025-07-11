"""
Communication Fallback Service for handling WhatsApp failures
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models.notification import NotificationQueue
from app.models.database_models import ServiceRequest, User, Provider
from app.services.whatsapp_service import WhatsAppService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class CommunicationFallbackService:
    """Service for handling communication failures with multiple fallback options"""
    
    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService()
        self.fallback_channels = ['whatsapp', 'sms', 'email', 'internal']
        self.retry_delays = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour
    
    async def send_message_with_fallback(self, user_id: str, message: str, message_type: str = "info") -> bool:
        """Send message with automatic fallback to alternative channels"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            # Try primary channel (WhatsApp)
            success = await self._try_whatsapp_delivery(user, message)
            if success:
                return True
            
            # Fallback to SMS (if phone number available)
            if hasattr(user, 'phone_number') and user.phone_number:
                success = await self._try_sms_delivery(user, message)
                if success:
                    return True
            
            # Fallback to Email (if email available)
            if hasattr(user, 'email') and user.email:
                success = await self._try_email_delivery(user, message)
                if success:
                    return True
            
            # Final fallback - store for manual intervention
            await self._store_for_manual_intervention(user, message, message_type)
            return False
            
        except Exception as e:
            logger.error(f"Error in communication fallback: {e}")
            return False
    
    async def _try_whatsapp_delivery(self, user: User, message: str) -> bool:
        """Try WhatsApp delivery"""
        try:
            if not user.whatsapp_id:
                return False
                
            success = self.whatsapp_service.send_message(user.whatsapp_id, message)
            if success:
                logger.info(f"WhatsApp message sent successfully to {user.id}")
                return True
            else:
                logger.warning(f"WhatsApp delivery failed for {user.id}")
                return False
                
        except Exception as e:
            logger.error(f"WhatsApp delivery error: {e}")
            return False
    
    async def _try_sms_delivery(self, user: User, message: str) -> bool:
        """Try SMS delivery as fallback"""
        try:
            # This would integrate with an SMS service like Twilio SMS
            # For now, we'll log and store for later implementation
            logger.info(f"SMS fallback attempted for {user.id} - storing for future implementation")
            
            # Store SMS notification for future implementation
            notification = NotificationQueue(
                user_id=user.id,
                message=message,
                notification_type="sms_fallback",
                status="pending",
                error_message="SMS service not yet implemented"
            )
            
            self.db.add(notification)
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            
            return False  # Return False until SMS is implemented
            
        except Exception as e:
            logger.error(f"SMS fallback error: {e}")
            return False
    
    async def _try_email_delivery(self, user: User, message: str) -> bool:
        """Try Email delivery as fallback"""
        try:
            # This would integrate with an email service
            # For now, we'll log and store for later implementation
            logger.info(f"Email fallback attempted for {user.id} - storing for future implementation")
            
            # Store email notification for future implementation
            notification = NotificationQueue(
                user_id=user.id,
                message=message,
                notification_type="email_fallback",
                status="pending",
                error_message="Email service not yet implemented"
            )
            
            self.db.add(notification)
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            
            return False  # Return False until email is implemented
            
        except Exception as e:
            logger.error(f"Email fallback error: {e}")
            return False
    
    async def _store_for_manual_intervention(self, user: User, message: str, message_type: str):
        """Store message for manual intervention"""
        try:
            notification = NotificationQueue(
                user_id=user.id,
                message=message,
                notification_type=f"manual_intervention_{message_type}",
                status="failed",
                error_message="All communication channels failed",
                max_retries=0  # No auto-retry for manual intervention
            )
            
            self.db.add(notification)
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            
            logger.critical(f"MANUAL INTERVENTION REQUIRED: Communication failed for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error storing for manual intervention: {e}")
    
    async def check_and_retry_failed_messages(self) -> Dict[str, int]:
        """Check for failed messages and retry them"""
        try:
            # Get failed notifications that haven't exceeded retry limits
            failed_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.status == "failed",
                NotificationQueue.retry_count < NotificationQueue.max_retries,
                NotificationQueue.notification_type.in_(["whatsapp", "confirmation", "status_update"])
            ).limit(10).all()
            
            retry_stats = {
                'attempted': len(failed_notifications),
                'successful': 0,
                'failed': 0
            }
            
            for notification in failed_notifications:
                success = await self._retry_failed_notification(notification)
                if success:
                    retry_stats['successful'] += 1
                else:
                    retry_stats['failed'] += 1
                    
                # Small delay between retries
                await asyncio.sleep(0.5)
            
            logger.info(f"Retry stats: {retry_stats}")
            return retry_stats
            
        except Exception as e:
            logger.error(f"Error checking and retrying failed messages: {e}")
            return {'error': str(e)}
    
    async def _retry_failed_notification(self, notification: NotificationQueue) -> bool:
        """Retry a single failed notification"""
        try:
            # Try to send the message again
            success = await self.send_message_with_fallback(
                notification.user_id,
                notification.message,
                notification.notification_type
            )
            
            # Update notification status
            notification.retry_count += 1
            notification.last_retry_at = datetime.utcnow()
            
            if success:
                notification.status = "sent"
                notification.sent_at = datetime.utcnow()
                logger.info(f"Successfully retried notification {notification.id}")
            else:
                if notification.retry_count >= notification.max_retries:
                    notification.status = "failed"
                    notification.error_message = "Max retries exceeded"
                    logger.warning(f"Notification {notification.id} failed after {notification.retry_count} retries")
            
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            
            return success
            
        except Exception as e:
            logger.error(f"Error retrying notification {notification.id}: {e}")
            return False
    
    def get_communication_health_status(self) -> Dict[str, Any]:
        """Get communication system health status"""
        try:
            # Check recent message success rates
            recent_time = datetime.utcnow() - timedelta(hours=1)
            
            total_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.created_at > recent_time
            ).count()
            
            successful_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.created_at > recent_time,
                NotificationQueue.status == "sent"
            ).count()
            
            failed_notifications = self.db.query(NotificationQueue).filter(
                NotificationQueue.created_at > recent_time,
                NotificationQueue.status == "failed"
            ).count()
            
            success_rate = (successful_notifications / total_notifications * 100) if total_notifications > 0 else 0
            
            # Determine health status
            if success_rate >= 90:
                health_status = "healthy"
            elif success_rate >= 70:
                health_status = "degraded"
            else:
                health_status = "critical"
            
            return {
                'health_status': health_status,
                'success_rate': round(success_rate, 2),
                'total_notifications_1h': total_notifications,
                'successful_notifications_1h': successful_notifications,
                'failed_notifications_1h': failed_notifications,
                'channels_available': ['whatsapp'],
                'channels_planned': ['sms', 'email'],
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting communication health status: {e}")
            return {
                'health_status': 'unknown',
                'error': str(e)
            }