"""
Sprint 3 - WhatsApp Notification Service
Automated notifications to providers with response handling and fallback logic
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models.database_models import Provider, ServiceRequest, RequestStatus
from app.services.whatsapp_service import WhatsAppService
from app.services.provider_matcher import ProviderMatcher, ProviderScore
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationStatus(str, Enum):
    """Notification status tracking"""
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    FAILED = "failed"


@dataclass
class ProviderNotification:
    """Provider notification tracking"""
    provider_id: int
    provider: Provider
    request_id: int
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    response_message: Optional[str] = None
    timeout_minutes: int = 10


class WhatsAppNotificationService:
    """WhatsApp notification service with automatic fallback logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService()
        self.provider_matcher = ProviderMatcher(db)
        
        # Notification settings
        self.provider_response_timeout_minutes = 10
        self.max_fallback_attempts = 3
        self.extended_delay_message_threshold = 20  # minutes
        
        # Track active notifications
        self.active_notifications: Dict[int, List[ProviderNotification]] = {}
        
    async def notify_providers_for_request(self, request: ServiceRequest) -> bool:
        """
        Main notification flow with fallback logic
        
        Process:
        1. Find and rank best providers
        2. Notify first provider
        3. Wait for response with timeout
        4. If no response, try next provider
        5. If all fail, notify client of extended delay
        """
        try:
            logger.info(f"Starting provider notification for request {request.id}")
            
            # Get best matched providers
            best_providers = self.provider_matcher.get_best_providers(
                request, limit=self.max_fallback_attempts
            )
            
            if not best_providers:
                logger.warning(f"No available providers found for request {request.id}")
                await self._notify_client_no_providers(request)
                return False
            
            # Initialize notification tracking
            notifications = []
            for provider_score in best_providers:
                notification = ProviderNotification(
                    provider_id=provider_score.provider_id,
                    provider=provider_score.provider,
                    request_id=request.id,
                    status=NotificationStatus.PENDING
                )
                notifications.append(notification)
            
            self.active_notifications[request.id] = notifications
            
            # Update request status
            request.status = RequestStatus.PENDING
            self.db.commit()
            
            # Start fallback notification process
            success = await self._process_fallback_notifications(request, notifications)
            
            if not success:
                await self._notify_client_extended_delay(request)
            
            return success
            
        except Exception as e:
            logger.error(f"Error in provider notification process: {e}")
            return False
    
    async def _process_fallback_notifications(self, request: ServiceRequest, notifications: List[ProviderNotification]) -> bool:
        """Process provider notifications with fallback logic"""
        
        for i, notification in enumerate(notifications):
            try:
                logger.info(f"Notifying provider {notification.provider_id} (attempt {i+1}/{len(notifications)})")
                
                # Send notification to provider
                success = await self.notify_provider(notification.provider, request)
                
                if success:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.now()
                    
                    # Update request status
                    request.status = "prestataire_notifie"
                    self.db.commit()
                    
                    # Wait for provider response with timeout
                    response_received = await self._wait_for_provider_response(
                        notification, self.provider_response_timeout_minutes
                    )
                    
                    if response_received:
                        if notification.status == NotificationStatus.ACCEPTED:
                            logger.info(f"Provider {notification.provider_id} accepted request {request.id}")
                            
                            # Update request with accepted provider
                            request.status = RequestStatus.ASSIGNED
                            request.provider_id = notification.provider_id
                            request.accepted_at = datetime.now()
                            self.db.commit()
                            
                            # Notify client of acceptance
                            await self._notify_client_provider_found(request, notification.provider)
                            
                            return True
                        
                        elif notification.status == NotificationStatus.REJECTED:
                            logger.info(f"Provider {notification.provider_id} rejected request {request.id}")
                            # Continue to next provider
                            continue
                    
                    else:
                        # Timeout - mark as such and continue
                        notification.status = NotificationStatus.TIMEOUT
                        logger.info(f"Provider {notification.provider_id} timed out for request {request.id}")
                        continue
                
                else:
                    notification.status = NotificationStatus.FAILED
                    logger.error(f"Failed to send notification to provider {notification.provider_id}")
                    continue
                    
            except Exception as e:
                logger.error(f"Error processing notification for provider {notification.provider_id}: {e}")
                notification.status = NotificationStatus.FAILED
                continue
        
        # If we reach here, all providers failed/rejected/timed out
        logger.warning(f"All providers failed for request {request.id}")
        return False
    
    async def notify_provider(self, provider: Provider, request_details: ServiceRequest) -> bool:
        """
        Send formatted notification message to provider
        
        Uses exact template specified in requirements
        """
        try:
            # Format the notification message
            message = self._format_provider_message(provider, request_details)
            
            # Send WhatsApp message
            success = self.whatsapp_service.send_message(
                provider.phone_number, 
                message
            )
            
            if success:
                logger.info(f"Provider notification sent successfully to {provider.name} ({provider.phone_number})")
            else:
                logger.error(f"Failed to send provider notification to {provider.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending provider notification: {e}")
            return False
    
    def _format_provider_message(self, provider: Provider, request: ServiceRequest) -> str:
        """Format provider notification message using exact template"""
        
        # Map service types to French display names
        service_display_names = {
            "plomberie": "Plomberie",
            "électricité": "Électricité", 
            "réparation électroménager": "Réparation Électroménager"
        }
        
        service_name = service_display_names.get(request.service_type, request.service_type.title())
        
        # Format timing
        timing = request.preferred_time or request.urgency or "Dès que possible"
        
        message = f"""🔧 NOUVELLE MISSION DJOBEA

Service : {service_name}
Lieu : {request.location}
Problème : {request.description}
Délai : {timing}

Répondez :
✅ OUI pour accepter
❌ NON pour refuser

⏰ Réponse attendue sous 10 min"""

        return message
    
    async def process_provider_response(self, provider_phone: str, response_message: str) -> bool:
        """
        Process provider response (OUI/NON) and update request status
        """
        try:
            # Find provider by phone number
            provider = self.db.query(Provider).filter(
                Provider.phone_number == provider_phone
            ).first()
            
            if not provider:
                logger.error(f"Provider not found for phone number: {provider_phone}")
                return False
            
            # Find active notification for this provider
            notification = self._find_active_notification(provider.id)
            
            if not notification:
                logger.warning(f"No active notification found for provider {provider.id}")
                return False
            
            # Process response
            response_lower = response_message.lower().strip()
            
            if any(word in response_lower for word in ['oui', 'yes', 'ok', 'accepte', 'accept']):
                notification.status = NotificationStatus.ACCEPTED
                notification.responded_at = datetime.now()
                notification.response_message = response_message
                
                logger.info(f"Provider {provider.id} accepted request {notification.request_id}")
                return True
                
            elif any(word in response_lower for word in ['non', 'no', 'refuse', 'reject']):
                notification.status = NotificationStatus.REJECTED
                notification.responded_at = datetime.now()
                notification.response_message = response_message
                
                logger.info(f"Provider {provider.id} rejected request {notification.request_id}")
                return True
            
            else:
                # Ambiguous response - ask for clarification
                clarification_msg = """Merci pour votre réponse. 

Pour confirmer votre décision, veuillez répondre simplement :
✅ OUI pour accepter la mission
❌ NON pour refuser la mission"""
                
                self.whatsapp_service.send_message(provider.phone_number, clarification_msg)
                return False
                
        except Exception as e:
            logger.error(f"Error processing provider response: {e}")
            return False
    
    def _find_active_notification(self, provider_id: int) -> Optional[ProviderNotification]:
        """Find active notification for a provider"""
        for request_notifications in self.active_notifications.values():
            for notification in request_notifications:
                if (notification.provider_id == provider_id and 
                    notification.status == NotificationStatus.SENT):
                    return notification
        return None
    
    async def _wait_for_provider_response(self, notification: ProviderNotification, timeout_minutes: int) -> bool:
        """Wait for provider response with timeout"""
        timeout_seconds = timeout_minutes * 60
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            if notification.status in [NotificationStatus.ACCEPTED, NotificationStatus.REJECTED]:
                return True
            
            # Wait 30 seconds before checking again
            await asyncio.sleep(30)
        
        # Timeout reached
        return False
    
    async def _notify_client_provider_found(self, request: ServiceRequest, provider: Provider) -> bool:
        """Notify client that a provider has been found"""
        try:
            user = self.db.query(Provider).filter(Provider.id == request.user_id).first()
            if not user:
                return False
            
            message = f"""✅ Parfait ! Votre demande a été acceptée.

🔧 Prestataire : {provider.name}
📱 Contact : {provider.phone_number}
⭐ Note : {provider.rating}/5 ({provider.total_jobs} missions)

Le prestataire va vous contacter directement pour organiser l'intervention.

💰 Commission Djobea : 15% du montant final
📞 Support : Contactez-nous si besoin

Merci de faire confiance à Djobea ! 🙏"""
            
            # Get user phone from request (need to implement user lookup)
            # For now, we'll need to add this functionality
            return True
            
        except Exception as e:
            logger.error(f"Error notifying client of provider found: {e}")
            return False
    
    async def _notify_client_no_providers(self, request: ServiceRequest) -> bool:
        """Notify client that no providers are available"""
        try:
            message = f"""😔 Désolé, aucun prestataire n'est disponible actuellement pour votre demande.

🔄 Solutions :
• Nous continuons à chercher
• Élargir la zone géographique
• Reporter à plus tard

📞 Notre équipe va vous contacter pour trouver une solution.

Merci pour votre patience ! 🙏"""
            
            # Send to user (need user phone number)
            return True
            
        except Exception as e:
            logger.error(f"Error notifying client of no providers: {e}")
            return False
    
    async def _notify_client_extended_delay(self, request: ServiceRequest) -> bool:
        """Notify client of extended delay due to no responses"""
        try:
            message = f"""⏰ Mise à jour sur votre demande

Nous recherchons activement un prestataire pour votre demande.
Le délai peut être un peu plus long que prévu.

🔄 Actions en cours :
• Recherche élargie
• Contact de prestataires supplémentaires
• Vérification de disponibilités

📞 Nous vous recontactons dès qu'un prestataire est trouvé.

Merci pour votre patience ! 🙏"""
            
            # Send to user
            return True
            
        except Exception as e:
            logger.error(f"Error notifying client of extended delay: {e}")
            return False
    
    def get_notification_metrics(self) -> Dict:
        """Get notification system metrics"""
        try:
            total_notifications = sum(len(notifications) for notifications in self.active_notifications.values())
            
            if total_notifications == 0:
                return {
                    "total_notifications": 0,
                    "acceptance_rate": 0.0,
                    "average_response_time_minutes": 0.0,
                    "timeout_rate": 0.0
                }
            
            accepted = 0
            rejected = 0
            timeouts = 0
            response_times = []
            
            for notifications in self.active_notifications.values():
                for notification in notifications:
                    if notification.status == NotificationStatus.ACCEPTED:
                        accepted += 1
                        if notification.sent_at and notification.responded_at:
                            response_time = (notification.responded_at - notification.sent_at).total_seconds() / 60
                            response_times.append(response_time)
                    elif notification.status == NotificationStatus.REJECTED:
                        rejected += 1
                        if notification.sent_at and notification.responded_at:
                            response_time = (notification.responded_at - notification.sent_at).total_seconds() / 60
                            response_times.append(response_time)
                    elif notification.status == NotificationStatus.TIMEOUT:
                        timeouts += 1
            
            total_responses = accepted + rejected
            acceptance_rate = (accepted / total_responses) if total_responses > 0 else 0.0
            timeout_rate = (timeouts / total_notifications) if total_notifications > 0 else 0.0
            avg_response_time = (sum(response_times) / len(response_times)) if response_times else 0.0
            
            return {
                "total_notifications": total_notifications,
                "acceptance_rate": acceptance_rate,
                "average_response_time_minutes": avg_response_time,
                "timeout_rate": timeout_rate,
                "accepted": accepted,
                "rejected": rejected,
                "timeouts": timeouts
            }
            
        except Exception as e:
            logger.error(f"Error calculating notification metrics: {e}")
            return {}