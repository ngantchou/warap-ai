"""
Notification Service - Service pour l'envoi de notifications
"""
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models.request_management_models import RequestNotification

class NotificationService:
    """Service pour gérer les notifications"""
    
    def __init__(self):
        self.delivery_methods = {
            "whatsapp": self._send_whatsapp_notification,
            "email": self._send_email_notification,
            "sms": self._send_sms_notification
        }
    
    async def send_notification(
        self,
        db: Session,
        recipient_id: str,
        notification_type: str,
        title: str,
        message: str,
        request_id: Optional[str] = None,
        delivery_method: str = "whatsapp",
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Envoyer une notification"""
        
        # Créer l'enregistrement de notification
        notification = RequestNotification(
            notification_id=f"notif_{uuid.uuid4().hex[:12]}",
            request_id=request_id,
            recipient_id=recipient_id,
            recipient_type="user",
            notification_type=notification_type,
            title=title,
            message=message,
            delivery_method=delivery_method,
            status="pending"
        )
        
        db.add(notification)
        db.commit()
        
        # Envoyer la notification
        try:
            delivery_handler = self.delivery_methods.get(delivery_method)
            if delivery_handler:
                result = await delivery_handler(recipient_id, title, message)
                
                if result["success"]:
                    notification.status = "sent"
                    notification.sent_at = datetime.utcnow()
                    notification.delivered_at = datetime.utcnow()
                else:
                    notification.status = "failed"
                    notification.last_error = result.get("error", "Unknown error")
                    notification.retry_count += 1
                
                db.commit()
                return result
            else:
                return {"success": False, "error": f"Delivery method {delivery_method} not supported"}
                
        except Exception as e:
            notification.status = "failed"
            notification.last_error = str(e)
            notification.retry_count += 1
            db.commit()
            
            return {"success": False, "error": str(e)}
    
    async def _send_whatsapp_notification(
        self,
        recipient_id: str,
        title: str,
        message: str
    ) -> Dict[str, Any]:
        """Envoyer une notification WhatsApp"""
        
        # Simulation d'envoi WhatsApp
        # Dans un vrai système, ceci ferait appel à l'API Twilio
        
        formatted_message = f"🔔 *{title}*\n\n{message}"
        
        # Simuler l'envoi
        return {
            "success": True,
            "message": "WhatsApp notification sent successfully",
            "recipient": recipient_id,
            "formatted_message": formatted_message
        }
    
    async def _send_email_notification(
        self,
        recipient_id: str,
        title: str,
        message: str
    ) -> Dict[str, Any]:
        """Envoyer une notification par email"""
        
        # Simulation d'envoi email
        return {
            "success": True,
            "message": "Email notification sent successfully",
            "recipient": recipient_id
        }
    
    async def _send_sms_notification(
        self,
        recipient_id: str,
        title: str,
        message: str
    ) -> Dict[str, Any]:
        """Envoyer une notification par SMS"""
        
        # Simulation d'envoi SMS
        return {
            "success": True,
            "message": "SMS notification sent successfully",
            "recipient": recipient_id
        }
    
    async def get_notification_history(
        self,
        db: Session,
        recipient_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Récupérer l'historique des notifications"""
        
        notifications = db.query(RequestNotification).filter(
            RequestNotification.recipient_id == recipient_id
        ).order_by(RequestNotification.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": notif.notification_id,
                "type": notif.notification_type,
                "title": notif.title,
                "message": notif.message,
                "status": notif.status,
                "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
                "delivered_at": notif.delivered_at.isoformat() if notif.delivered_at else None,
                "created_at": notif.created_at.isoformat()
            }
            for notif in notifications
        ]
    
    async def retry_failed_notifications(self, db: Session) -> Dict[str, Any]:
        """Réessayer les notifications échouées"""
        
        failed_notifications = db.query(RequestNotification).filter(
            RequestNotification.status == "failed",
            RequestNotification.retry_count < 3
        ).all()
        
        results = []
        for notification in failed_notifications:
            result = await self.send_notification(
                db,
                notification.recipient_id,
                notification.notification_type,
                notification.title,
                notification.message,
                notification.request_id,
                notification.delivery_method
            )
            results.append(result)
        
        return {
            "success": True,
            "retried_count": len(results),
            "results": results
        }