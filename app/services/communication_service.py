"""
Enhanced Communication Service for Djobea AI
Handles proactive status updates and instant confirmations
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.config import get_settings
from app.database import get_db
from app.models.database_models import ServiceRequest, User, Provider, RequestStatus
from app.services.whatsapp_service import WhatsAppService
from app.services.provider_profile_service import get_provider_profile_service


class CommunicationService:
    """Service for proactive communication and status updates"""
    
    def __init__(self):
        self.settings = get_settings()
        self.whatsapp_service = WhatsAppService()
        self.active_tasks: Dict[int, asyncio.Task] = {}
    
    def get_pricing_estimate(self, service_type: str) -> Dict[str, any]:
        """Get pricing estimate for a service type"""
        pricing = self.settings.service_pricing.get(service_type.lower(), {
            "min": 2000,
            "max": 10000,
            "description": "Service standard"
        })
        return pricing
    
    def format_price_range(self, pricing: Dict[str, any]) -> str:
        """Format price range in XAF"""
        min_price = f"{pricing['min']:,}".replace(",", " ")
        max_price = f"{pricing['max']:,}".replace(",", " ")
        return f"{min_price} - {max_price} XAF"
    
    async def send_instant_confirmation(self, request_id: int, db: Session) -> bool:
        """Send instant confirmation within 30 seconds of request receipt"""
        try:
            # Get request details
            request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
            if not request:
                logger.error(f"Request {request_id} not found for confirmation")
                return False
            
            user = db.query(User).filter(User.id == request.user_id).first()
            if not user:
                logger.error(f"User not found for request {request_id}")
                return False
            
            # Get pricing estimate
            pricing = self.get_pricing_estimate(request.service_type)
            price_range = self.format_price_range(pricing)
            
            # Generate enhanced confirmation message with scheduling
            confirmation_message = self._generate_enhanced_confirmation_message(
                request,
                price_range,
                pricing["description"]
            )
            
            # Send confirmation
            success = self.whatsapp_service.send_message(
                user.whatsapp_id,
                confirmation_message
            )
            
            if success:
                logger.info(f"Instant confirmation sent for request {request_id}")
                
                # Start proactive update task
                await self.start_proactive_updates(request_id, db)
            else:
                logger.error(f"Failed to send confirmation for request {request_id}")
                # Notify user about internal service error if confirmation fails
                await self._notify_user_about_confirmation_error(request, user)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending instant confirmation for request {request_id}: {e}")
            # Try to notify user about confirmation error
            try:
                request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
                if request and request.user:
                    await self._notify_user_about_confirmation_error(request, request.user)
            except Exception as notify_error:
                logger.error(f"Failed to notify user about confirmation error: {notify_error}")
            return False
    
    async def start_proactive_updates(self, request_id: int, db: Session) -> None:
        """Start background task for proactive status updates"""
        try:
            # Cancel existing task if running
            if request_id in self.active_tasks:
                self.active_tasks[request_id].cancel()
            
            # Create new task
            task = asyncio.create_task(self._proactive_update_loop(request_id))
            self.active_tasks[request_id] = task
            
            logger.info(f"Started proactive updates for request {request_id}")
            
        except Exception as e:
            logger.error(f"Error starting proactive updates for request {request_id}: {e}")
    
    async def _proactive_update_loop(self, request_id: int) -> None:
        """Background loop for sending proactive updates"""
        try:
            update_count = 0
            max_updates = 30  # Maximum updates to prevent infinite loops
            
            while update_count < max_updates:
                await asyncio.sleep(60)  # Check every minute
                
                # Get fresh database session
                db = next(get_db())
                try:
                    request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
                    if not request:
                        logger.warning(f"Request {request_id} not found during proactive updates")
                        break
                    
                    # Stop updates if request is completed or cancelled
                    if request.status in [RequestStatus.COMPLETED, RequestStatus.CANCELLED]:
                        logger.info(f"Stopping proactive updates for completed/cancelled request {request_id}")
                        break
                    
                    # Calculate time since request creation
                    time_since_creation = datetime.utcnow() - request.created_at
                    minutes_elapsed = int(time_since_creation.total_seconds() / 60)
                    
                    # Determine update frequency based on urgency
                    is_urgent = request.urgency and "urgent" in request.urgency.lower()
                    update_interval = (
                        self.settings.urgent_update_interval_minutes if is_urgent 
                        else self.settings.proactive_update_interval_minutes
                    )
                    
                    # Send update if it's time
                    if minutes_elapsed > 0 and minutes_elapsed % update_interval == 0:
                        await self._send_status_update(request, db)
                        update_count += 1
                    
                    # Send countdown warnings
                    timeout_minutes = self.settings.provider_response_timeout_minutes
                    time_remaining = timeout_minutes - minutes_elapsed
                    
                    if time_remaining == self.settings.countdown_threshold_minutes:
                        await self._send_countdown_warning(request, time_remaining, db)
                    
                    # Handle timeout
                    if minutes_elapsed >= timeout_minutes and request.status == RequestStatus.PROVIDER_NOTIFIED:
                        await self._handle_timeout(request, db)
                        break
                
                finally:
                    db.close()
            
        except asyncio.CancelledError:
            logger.info(f"Proactive updates cancelled for request {request_id}")
        except Exception as e:
            logger.error(f"Error in proactive update loop for request {request_id}: {e}")
        finally:
            # Clean up task reference
            if request_id in self.active_tasks:
                del self.active_tasks[request_id]
    
    async def _send_status_update(self, request: ServiceRequest, db: Session) -> None:
        """Send status update based on current request state"""
        try:
            user = db.query(User).filter(User.id == request.user_id).first()
            if not user:
                return
            
            message = self._generate_status_update_message(request)
            
            await self.whatsapp_service.send_message(user.whatsapp_id, message)
            logger.info(f"Status update sent for request {request.id}")
            
        except Exception as e:
            logger.error(f"Error sending status update for request {request.id}: {e}")
    
    async def _send_countdown_warning(self, request: ServiceRequest, minutes_remaining: int, db: Session) -> None:
        """Send countdown warning when timeout approaches"""
        try:
            user = db.query(User).filter(User.id == request.user_id).first()
            if not user:
                return
            
            message = f"""⏰ *Mise à jour importante*

Plus que *{minutes_remaining} minutes* pour qu'un prestataire accepte votre demande de {request.service_type}.

🔄 Je continue à chercher des professionnels disponibles dans votre zone.

💬 Vous pouvez me poser des questions à tout moment !"""
            
            await self.whatsapp_service.send_message(user.whatsapp_id, message)
            logger.info(f"Countdown warning sent for request {request.id}")
            
        except Exception as e:
            logger.error(f"Error sending countdown warning for request {request.id}: {e}")
    
    async def _handle_timeout(self, request: ServiceRequest, db: Session) -> None:
        """Handle request timeout and initiate fallback"""
        try:
            user = db.query(User).filter(User.id == request.user_id).first()
            if not user:
                return
            
            message = f"""😔 *Délai dépassé*

Aucun prestataire n'a répondu dans les temps pour votre demande de {request.service_type}.

🔍 *Que puis-je faire maintenant ?*
• Rechercher dans une zone plus large
• Vous proposer d'autres créneaux horaires
• Vous suggérer des alternatives

💬 Écrivez-moi pour que je trouve une solution adaptée !"""
            
            await self.whatsapp_service.send_message(user.whatsapp_id, message)
            logger.info(f"Timeout message sent for request {request.id}")
            
        except Exception as e:
            logger.error(f"Error handling timeout for request {request.id}: {e}")
    
    async def send_provider_acceptance(self, request_id: int, provider_id: int, db: Session) -> bool:
        """Send enhanced message when provider accepts request with detailed profile"""
        try:
            from app.models.database_models import Provider
            from app.config import get_settings
            
            request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
            user = db.query(User).filter(User.id == request.user_id).first()
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            
            if not all([request, user, provider]):
                logger.error(f"Missing data for provider acceptance notification")
                return False
            
            # Get enhanced provider profile
            profile_service = get_provider_profile_service(db)
            provider_intro = profile_service.generate_provider_introduction(provider_id)
            
            # Generate trust explanation
            trust_explanation = profile_service.generate_trust_explanation(provider_id, request.service_type)
            
            # Build public profile URL if available
            profile_url = ""
            if provider.public_profile_slug:
                settings = get_settings()
                profile_url = f"{settings.base_url}/provider/{provider.public_profile_slug}"
            
            # Combine introduction with next steps and profile link
            message_parts = [
                provider_intro["message"],
                "",
                trust_explanation,
                ""
            ]
            
            # Add profile link if available
            if profile_url:
                message_parts.extend([
                    "👤 *Voir le profil complet* :",
                    f"🔗 {profile_url}",
                    "",
                    "📱 *Contact direct* :",
                    f"https://wa.me/{provider.whatsapp_id}?text=Bonjour {provider.name}, j'ai accepté votre proposition via Djobea AI",
                    ""
                ])
            
            message_parts.extend([
                "🕐 *Prochaines étapes* :",
                "1. Le prestataire va vous contacter directement",
                "2. Confirmez les détails et le prix",
                "3. Planifiez l'intervention",
                "",
                "💰 *Paiement sécurisé disponible via l'application*"
            ])
            
            message = "\n".join(message_parts)
            
            success = self.whatsapp_service.send_message(user.whatsapp_id, message)
            
            if success:
                # Stop proactive updates
                if request_id in self.active_tasks:
                    self.active_tasks[request_id].cancel()
                    del self.active_tasks[request_id]
                
                logger.info(f"Provider acceptance notification sent for request {request_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending provider acceptance for request {request_id}: {e}")
            return False
    
    def _generate_enhanced_confirmation_message(self, request: ServiceRequest, price_range: str, description: str) -> str:
        """Generate enhanced confirmation message with scheduling and location details"""
        from app.services.scheduling_service import SchedulingService
        
        service_emoji = {
            "plomberie": "🔧",
            "électricité": "⚡", 
            "réparation électroménager": "🏠"
        }.get(request.service_type.lower(), "🛠")
        
        # Build base message
        message_parts = [
            "✅ *Demande reçue et confirmée !*",
            "",
            f"{service_emoji} *Service* : {request.service_type.title()}",
            f"📍 *Zone* : {request.location}",
            f"💰 *Tarif estimé* : {price_range}",
        ]
        
        # Add scheduling information if available
        if request.scheduling_preference or request.urgency_supplement > 0:
            from app.services.scheduling_service import SchedulingService
            
            scheduling_service = SchedulingService(db=None)  # Read-only for message generation
            
            if request.scheduling_preference:
                time_label = scheduling_service._get_time_slot_label(
                    scheduling_service.SchedulingPreference(request.scheduling_preference)
                )
                message_parts.append(f"⏰ *Horaire souhaité* : {time_label}")
            
            if request.urgency_supplement > 0:
                supplement = int(request.urgency_supplement)
                message_parts.append(f"💰 *Supplément urgence* : +{supplement:,} XAF".replace(",", " "))
        
        # Add location details if available
        if request.landmark_references:
            message_parts.append(f"🗺 *Repères* : {request.landmark_references}")
            
        if request.location_confirmed:
            message_parts.append("✅ *Localisation confirmée*")
        
        # Add service description
        message_parts.extend([
            f"📋 *Inclut* : {description}",
            "",
            "🔍 *Recherche en cours...*",
            "Je contacte les meilleurs prestataires de votre zone."
        ])
        
        # Add timing information
        if request.scheduling_preference == "URGENT":
            message_parts.extend([
                "",
                "🚨 *Demande urgente*",
                "⏱ *Réponse attendue* : sous 2 minutes",
                "📱 *Contact direct* : dès confirmation"
            ])
        else:
            message_parts.extend([
                "",
                "⏱ *Réponse attendue* : sous 5 minutes",
                "📱 *Mise à jour* : toutes les 2-3 minutes"
            ])
        
        # Add helpful tips
        message_parts.extend([
            "",
            "💡 *Le saviez-vous ?*",
            "• Tous nos prestataires sont vérifiés",
            "• Le tarif final peut varier selon la complexité",
            "• Paiement sécurisé via mobile money",
            "",
            "🤝 *Djobea AI* - Votre assistant de confiance !"
        ])
        
        return "\n".join(message_parts)
    
    def _generate_confirmation_message(self, service_type: str, location: str, price_range: str, description: str) -> str:
        """Legacy confirmation message method (kept for compatibility)"""
        service_emoji = {
            "plomberie": "🔧",
            "électricité": "⚡", 
            "réparation électroménager": "🏠"
        }.get(service_type.lower(), "🛠")
        
        return f"""✅ *Demande reçue et confirmée !*

{service_emoji} *Service* : {service_type.title()}
📍 *Zone* : {location}
💰 *Tarif estimé* : {price_range}
📋 *Inclut* : {description}

🔍 *Recherche en cours...*
Je contacte les meilleurs prestataires de votre zone.

⏱ *Réponse attendue* : sous 5 minutes
📱 *Mise à jour* : toutes les 2-3 minutes

💡 *Le saviez-vous ?*
• Tous nos prestataires sont vérifiés
• Le tarif final peut varier selon la complexité
• Paiement sécurisé via mobile money

🤝 *Djobea AI* - Votre assistant de confiance !"""
    
    def _generate_status_update_message(self, request: ServiceRequest) -> str:
        """Generate status update message based on request state"""
        time_since_creation = datetime.utcnow() - request.created_at
        minutes_elapsed = int(time_since_creation.total_seconds() / 60)
        
        if request.status == RequestStatus.PENDING:
            return f"""🔍 *Recherche active*

Je continue à analyser votre demande de {request.service_type}.

⏱ *Temps écoulé* : {minutes_elapsed} minutes
🎯 *Statut* : Finalisation des détails

💬 *Besoin de préciser quelque chose ?*"""
        
        elif request.status == RequestStatus.PROVIDER_NOTIFIED:
            return f"""📞 *Prestataires contactés*

J'ai notifié plusieurs professionnels qualifiés pour votre {request.service_type}.

⏱ *Temps écoulé* : {minutes_elapsed} minutes
🎯 *Statut* : En attente de réponse des prestataires
🔄 *Action* : Suivi actif en cours

⚡ *Patience...* Les meilleurs prestataires arrivent !"""
        
        else:
            return f"""🔄 *Mise à jour*

Votre demande de {request.service_type} est en cours de traitement.

⏱ *Temps écoulé* : {minutes_elapsed} minutes
💪 *Djobea AI* continue de chercher pour vous !"""
    
    def stop_proactive_updates(self, request_id: int) -> None:
        """Stop proactive updates for a request"""
        try:
            if request_id in self.active_tasks:
                self.active_tasks[request_id].cancel()
                del self.active_tasks[request_id]
                logger.info(f"Stopped proactive updates for request {request_id}")
        except Exception as e:
            logger.error(f"Error stopping proactive updates for request {request_id}: {e}")
    
    async def send_error_message(self, user_whatsapp_id: str, error_type: str = "general") -> bool:
        """Send helpful error message with suggestions"""
        try:
            error_messages = {
                "general": """😕 *Oups ! Un petit problème*

Je rencontre une difficulté technique temporaire.

🔄 *Solutions* :
• Réessayez dans quelques minutes
• Reformulez votre demande
• Contactez-nous si le problème persiste

🤝 *Djobea AI* - Nous sommes là pour vous !""",
                
                "no_providers": """😔 *Aucun prestataire disponible*

Malheureusement, aucun professionnel n'est disponible immédiatement dans votre zone.

💡 *Alternatives* :
• Essayer une zone voisine
• Prévoir l'intervention pour plus tard
• Changer le type de service

💬 *Dites-moi comment vous préférez procéder !*""",
                
                "invalid_location": """📍 *Zone non couverte*

Je ne trouve pas de prestataires dans cette zone pour le moment.

🎯 *Zones couvertes* :
• Bonamoussadi et environs
• Centre-ville de Douala
• Bonapriso, Deido

💬 *Précisez votre quartier pour que je vous aide mieux !*"""
            }
            
            message = error_messages.get(error_type, error_messages["general"])
            
            success = await self.whatsapp_service.send_message(user_whatsapp_id, message)
            logger.info(f"Error message sent to {user_whatsapp_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending error message to {user_whatsapp_id}: {e}")
            return False
    
    async def _notify_user_about_confirmation_error(self, request: ServiceRequest, user: User) -> bool:
        """Notify user about confirmation message delivery failure"""
        try:
            error_message = f"""⚠️ *Information - Problème de Notification*

Votre demande de {request.service_type} à {request.location} est bien enregistrée et en cours de traitement.

🔧 *Problème technique temporaire* : Nous rencontrons actuellement des difficultés avec notre service de notification automatique.

✅ *Situation actuelle* :
- Votre demande est prioritaire
- Nous recherchons activement un prestataire
- Le traitement continue normalement

⏰ *Délai estimé* : La recherche de prestataires peut prendre quelques minutes supplémentaires (10-15 minutes au lieu de 5-10 minutes).

💰 *Tarif estimé* : {self._get_price_estimate(request.service_type)}

Vous serez informé dès qu'un professionnel accepte votre demande.

Merci de votre patience ! 🙏

📞 *Djobea AI* - Service de mise en relation"""
            
            # Try to send via WhatsApp (this might also fail, but it's worth trying)
            success = self.whatsapp_service.send_message(user.whatsapp_id, error_message)
            
            if success:
                logger.info(f"User {user.id} notified about confirmation error for request {request.id}")
            else:
                logger.error(f"Failed to notify user {user.id} about confirmation error - WhatsApp service unavailable")
            
            return success
            
        except Exception as e:
            logger.error(f"Error notifying user about confirmation error: {e}")
            return False
    
    def _get_price_estimate(self, service_type: str) -> str:
        """Get price estimate for a service type"""
        pricing = self.settings.service_pricing.get(service_type.lower(), {})
        if pricing:
            min_price = pricing.get("min", 0)
            max_price = pricing.get("max", 0)
            return f"{min_price:,} - {max_price:,} XAF".replace(",", " ")
        return "À négocier"