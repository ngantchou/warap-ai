"""
Notification Retry Service for handling failed WhatsApp messages
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.notification import NotificationQueue
from app.services.whatsapp_service import WhatsAppService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class NotificationRetryService:
    """Service for retrying failed notifications"""
    
    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService()
    
    async def process_failed_notifications(self) -> int:
        """Process all failed notifications that need retry"""
        try:
            # Get notifications that need retry
            notifications = self._get_notifications_for_retry()
            
            logger.info(f"Found {len(notifications)} notifications to retry")
            
            successful_retries = 0
            for notification in notifications:
                if await self._retry_notification(notification):
                    successful_retries += 1
                    
                # Small delay between retries to avoid overwhelming the API
                await asyncio.sleep(0.5)
            
            logger.info(f"Successfully retried {successful_retries}/{len(notifications)} notifications")
            return successful_retries
            
        except Exception as e:
            logger.error(f"Error processing failed notifications: {e}")
            return 0
    
    def _get_notifications_for_retry(self) -> List[NotificationQueue]:
        """Get notifications that are ready for retry"""
        try:
            # Get notifications that:
            # 1. Are failed or pending
            # 2. Haven't exceeded max retries
            # 3. Haven't been retried in the last 5 minutes
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            
            notifications = self.db.query(NotificationQueue).filter(
                and_(
                    NotificationQueue.status.in_(['failed', 'pending']),
                    NotificationQueue.retry_count < NotificationQueue.max_retries,
                    NotificationQueue.is_active == True,
                    or_(
                        NotificationQueue.last_retry_at.is_(None),
                        NotificationQueue.last_retry_at < five_minutes_ago
                    )
                )
            ).order_by(NotificationQueue.created_at.asc()).limit(20).all()
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting notifications for retry: {e}")
            return []
    
    async def _retry_notification(self, notification: NotificationQueue) -> bool:
        """Retry a single notification"""
        try:
            # Get user phone number from user_id
            user_phone = self._get_user_phone(notification.user_id)
            if not user_phone:
                logger.warning(f"No phone found for user {notification.user_id}")
                notification.status = "failed"
                notification.error_message = "User phone not found"
                try:
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                return False
            
            # Attempt to send the message
            success = self.whatsapp_service.send_message(user_phone, notification.message)
            
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
                else:
                    notification.status = "pending"
                    logger.info(f"Notification {notification.id} retry {notification.retry_count} failed, will retry later")
            
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            
            return success
            
        except Exception as e:
            logger.error(f"Error retrying notification {notification.id}: {e}")
            
            try:
                notification.retry_count += 1
                notification.last_retry_at = datetime.utcnow()
                notification.status = "failed"
                notification.error_message = str(e)
                self.db.commit()
            except Exception:
                self.db.rollback()
            
            return False
    
    def _get_user_phone(self, user_id: str) -> Optional[str]:
        """Get user phone number from database"""
        try:
            from app.models.database_models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            return user.whatsapp_id if user else None
            
        except Exception as e:
            logger.error(f"Error getting user phone: {e}")
            return None
    
    def get_retry_statistics(self) -> dict:
        """Get statistics about notification retries"""
        try:
            from sqlalchemy import func
            
            stats = self.db.query(
                NotificationQueue.status,
                func.count(NotificationQueue.id).label('count')
            ).group_by(NotificationQueue.status).all()
            
            result = {
                'total': sum(stat.count for stat in stats),
                'by_status': {stat.status: stat.count for stat in stats}
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting retry statistics: {e}")
            return {'total': 0, 'by_status': {}}
    
    def cleanup_old_notifications(self, days_old: int = 7) -> int:
        """Clean up old notifications"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            deleted = self.db.query(NotificationQueue).filter(
                and_(
                    NotificationQueue.created_at < cutoff_date,
                    NotificationQueue.status.in_(['sent', 'failed'])
                )
            ).delete()
            
            self.db.commit()
            
            logger.info(f"Cleaned up {deleted} old notifications")
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")
            return 0