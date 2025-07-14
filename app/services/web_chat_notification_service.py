"""
Web Chat Notification Service for Djobea AI
Handles notifications through web chat channel since requests come from web chat
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.database_models import ServiceRequest, User, Provider, RequestStatus, Conversation


class WebChatNotificationService:
    """Service for sending notifications through web chat channel"""
    
    def __init__(self):
        self.active_notifications: Dict[int, List[dict]] = {}
        self.notification_queue: List[dict] = []
    
    async def send_web_chat_notification(self, user_id, message: str, notification_type: str = "info") -> bool:
        """Send notification through web chat channel"""
        try:
            db = next(get_db())
            try:
                # Handle both string and integer user_id
                if isinstance(user_id, str) and user_id.startswith('237'):  # Cameroon phone number format
                    user = db.query(User).filter(User.phone_number == user_id).first()
                    if not user:
                        logger.warning(f"User with phone number {user_id} not found")
                        return False
                    actual_user_id = user.id
                    logger.info(f"Found user {actual_user_id} for phone number {user_id}")
                else:
                    # Handle integer user_id or string user_id that's not a phone number
                    actual_user_id = int(user_id)
                    logger.info(f"Using user ID {actual_user_id} directly")
                
                # Validate that actual_user_id is an integer
                if not isinstance(actual_user_id, int):
                    logger.error(f"Invalid user ID type: {type(actual_user_id)}, value: {actual_user_id}")
                    return False
                
                # Store notification in conversation history for web chat retrieval
                notification = Conversation(
                    user_id=actual_user_id,
                    message_type="outgoing",  # This is a system notification going to user
                    message_content=f"[SYSTEM_NOTIFICATION] {message}",
                    ai_response=message,
                    confidence_score=1.0,
                    action_code="SYSTEM_NOTIFICATION",
                    conversation_state="NOTIFICATION_SENT",
                    action_success=True
                )
                
                db.add(notification)
                db.commit()
                
                # Add to active notifications for real-time display
                notification_key = str(actual_user_id)  # Use actual user ID as key
                if notification_key not in self.active_notifications:
                    self.active_notifications[notification_key] = []
                
                self.active_notifications[notification_key].append({
                    "id": notification.id,
                    "message": message,
                    "type": notification_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "read": False
                })
                
                # Keep only last 10 notifications per user
                if len(self.active_notifications[notification_key]) > 10:
                    self.active_notifications[notification_key] = self.active_notifications[notification_key][-10:]
                
                logger.info(f"Web chat notification sent to user {user_id}: {notification_type}")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error sending web chat notification: {e}")
            # Log the full exception for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def send_instant_confirmation(self, request_id: int, user_id: str) -> bool:
        """Send instant confirmation through web chat"""
        try:
            db = next(get_db())
            try:
                request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
                if not request:
                    logger.error(f"Request {request_id} not found for confirmation")
                    return False
                
                # Generate confirmation message
                message = f"""✅ **Demande confirmée !**

Votre demande de **{request.service_type}** a été reçue et traitée.

📍 **Lieu**: {request.location}
📝 **Description**: {request.description}
⏰ **Urgence**: {request.urgency or 'Normal'}

🔍 Je recherche maintenant un prestataire disponible dans votre zone.
📱 Vous recevrez une notification dès qu'un prestataire accepte votre demande.

💬 N'hésitez pas à me poser des questions si besoin !"""
                
                return await self.send_web_chat_notification(user_id, message, "confirmation")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error sending instant confirmation: {e}")
            return False
    
    async def send_status_update(self, request_id: int, user_id: str, status: str) -> bool:
        """Send status update through web chat"""
        try:
            db = next(get_db())
            try:
                request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
                if not request:
                    logger.error(f"Request {request_id} not found for status update")
                    return False
                
                # Generate status-specific message
                if status == "provider_assigned":
                    provider = db.query(Provider).filter(Provider.id == request.assigned_provider_id).first()
                    message = f"""🎉 **Prestataire trouvé !**

Un prestataire a accepté votre demande de **{request.service_type}**.

👨‍🔧 **Prestataire**: {provider.name if provider else 'En cours de confirmation'}
📞 **Contact**: {provider.phone if provider else 'Information à venir'}
⭐ **Note**: {provider.rating if provider else 'N/A'}/5

Le prestataire va vous contacter sous peu pour confirmer les détails.

📱 Vous pouvez me demander des informations sur votre demande à tout moment !"""
                
                elif status == "in_progress":
                    message = f"""🔧 **Service en cours**

Votre demande de **{request.service_type}** est maintenant en cours de traitement.

Le prestataire travaille actuellement sur votre problème.

📱 Je vous tiendrai informé des mises à jour !"""
                
                elif status == "completed":
                    message = f"""✅ **Service terminé !**

Votre demande de **{request.service_type}** a été terminée avec succès.

📝 N'hésitez pas à évaluer le service reçu.
💬 Si vous avez d'autres besoins, je suis là pour vous aider !"""
                
                else:
                    message = f"""📋 **Mise à jour de votre demande**

Statut de votre demande de **{request.service_type}**: {status}

📱 Je continue à vous tenir informé des développements !"""
                
                return await self.send_web_chat_notification(user_id, message, "status_update")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error sending status update: {e}")
            return False
    
    async def send_provider_notification(self, provider_id: str, request_id: int) -> bool:
        """Send notification to provider through web chat (if they use web interface)"""
        try:
            db = next(get_db())
            try:
                request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
                provider = db.query(Provider).filter(Provider.id == provider_id).first()
                
                if not request or not provider:
                    logger.error(f"Request {request_id} or provider {provider_id} not found")
                    return False
                
                message = f"""🚨 **Nouvelle demande de service**

Une nouvelle demande correspond à votre expertise :

🔧 **Service**: {request.service_type}
📍 **Lieu**: {request.location}
📝 **Description**: {request.description}
⏰ **Urgence**: {request.urgency or 'Normal'}

💰 **Estimation**: {self._get_price_estimate(request.service_type)}

Souhaitez-vous accepter cette demande ?
- Tapez "OUI" pour accepter
- Tapez "NON" pour refuser"""
                
                # Use provider's phone as user_id for web chat
                return await self.send_web_chat_notification(provider.phone, message, "provider_request")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error sending provider notification: {e}")
            return False
    
    def _get_price_estimate(self, service_type: str) -> str:
        """Get price estimate for service type"""
        pricing = {
            "Plomberie": "5 000 - 15 000 XAF",
            "Électricité": "3 000 - 10 000 XAF",
            "Électroménager": "2 000 - 8 000 XAF"
        }
        return pricing.get(service_type, "2 000 - 10 000 XAF")
    
    async def get_user_notifications(self, user_id: str) -> List[dict]:
        """Get active notifications for a user"""
        # Handle phone number format
        if user_id.startswith('237'):  # Cameroon phone number format
            db = next(get_db())
            try:
                user = db.query(User).filter(User.phone_number == user_id).first()
                if user:
                    user_id = str(user.id)
            finally:
                db.close()
        
        return self.active_notifications.get(user_id, [])
    
    async def mark_notification_read(self, user_id: str, notification_id: int) -> bool:
        """Mark a notification as read"""
        try:
            user_notifications = self.active_notifications.get(user_id, [])
            for notification in user_notifications:
                if notification["id"] == notification_id:
                    notification["read"] = True
                    return True
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    async def clear_user_notifications(self, user_id: str) -> bool:
        """Clear all notifications for a user"""
        try:
            if user_id in self.active_notifications:
                self.active_notifications[user_id] = []
            return True
        except Exception as e:
            logger.error(f"Error clearing notifications: {e}")
            return False


# Global instance
web_chat_notification_service = WebChatNotificationService()