"""
Quick Actions Menu System for Djobea AI
Handles user action commands and menu generation
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database_models import (
    ServiceRequest, User, Provider, RequestStatus, ActionType,
    UserAction, RequestModification, SupportTicket, SupportTicketStatus
)
from app.services.whatsapp_service import WhatsAppService
from app.services.provider_service import ProviderService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QuickActionsService:
    """Manages quick actions menu and user control features"""
    
    def __init__(self, db: Session):
        self.db = db
        self.whatsapp_service = WhatsAppService()
        self.provider_service = ProviderService(db)
    
    def generate_actions_menu(self, request_id: int, language: str = "french") -> str:
        """Generate standardized quick actions menu"""
        if language.lower() == "english":
            menu = """
🎯 *Quick Actions Menu*

1️⃣ *STATUS* - Check request status
2️⃣ *MODIFY* - Change request details  
3️⃣ *CANCEL* - Cancel your request
4️⃣ *HELP* - Get assistance
5️⃣ *PROFILE* - View provider profile
6️⃣ *CONTACT* - Contact your provider

Type the *NUMBER* or *KEYWORD* to select an action.
Example: Type "1" or "STATUS"
"""
        else:  # French
            menu = """
🎯 *Menu Actions Rapides*

1️⃣ *STATUT* - Vérifier le statut
2️⃣ *MODIFIER* - Changer les détails
3️⃣ *ANNULER* - Annuler la demande
4️⃣ *AIDE* - Obtenir de l'assistance
5️⃣ *PROFIL* - Voir le profil prestataire
6️⃣ *CONTACT* - Contacter le prestataire

Tapez le *NUMÉRO* ou *MOT-CLÉ* pour sélectionner.
Exemple : Tapez "1" ou "STATUT"
"""
        
        return menu.strip()
    
    def detect_action_command(self, message: str) -> Optional[ActionType]:
        """Detect if message contains an action command"""
        message_lower = message.lower().strip()
        
        # Action mapping (French/English and numbers)
        action_map = {
            # Status checking
            "1": ActionType.STATUS_CHECK,
            "statut": ActionType.STATUS_CHECK,
            "status": ActionType.STATUS_CHECK,
            "état": ActionType.STATUS_CHECK,
            
            # Modify request
            "2": ActionType.MODIFY_REQUEST,
            "modifier": ActionType.MODIFY_REQUEST,
            "modify": ActionType.MODIFY_REQUEST,
            "changer": ActionType.MODIFY_REQUEST,
            "change": ActionType.MODIFY_REQUEST,
            
            # Cancel request
            "3": ActionType.CANCEL_REQUEST,
            "annuler": ActionType.CANCEL_REQUEST,
            "cancel": ActionType.CANCEL_REQUEST,
            "stop": ActionType.CANCEL_REQUEST,
            
            # Help
            "4": ActionType.HELP_REQUEST,
            "aide": ActionType.HELP_REQUEST,
            "help": ActionType.HELP_REQUEST,
            "support": ActionType.HELP_REQUEST,
            
            # Provider profile
            "5": ActionType.PROVIDER_PROFILE,
            "profil": ActionType.PROVIDER_PROFILE,
            "profile": ActionType.PROVIDER_PROFILE,
            "prestataire": ActionType.PROVIDER_PROFILE,
            
            # Contact provider
            "6": ActionType.CONTACT_PROVIDER,
            "contact": ActionType.CONTACT_PROVIDER,
            "contacter": ActionType.CONTACT_PROVIDER,
            "appeler": ActionType.CONTACT_PROVIDER,
            "call": ActionType.CONTACT_PROVIDER,
        }
        
        return action_map.get(message_lower)
    
    async def handle_action_command(
        self, 
        user_id: int, 
        whatsapp_id: str, 
        action: ActionType, 
        message: str = ""
    ) -> str:
        """Process action command and return response"""
        try:
            # Log user action
            self._log_user_action(user_id, action, {"message": message})
            
            # Get user's most recent request
            recent_request = self._get_user_recent_request(user_id)
            
            if not recent_request and action != ActionType.HELP_REQUEST:
                return self._no_request_response(action)
            
            # Route to appropriate handler
            if action == ActionType.STATUS_CHECK:
                return await self._handle_status_check(recent_request, whatsapp_id)
            elif action == ActionType.MODIFY_REQUEST:
                return await self._handle_modify_request(recent_request, whatsapp_id)
            elif action == ActionType.CANCEL_REQUEST:
                return await self._handle_cancel_request(recent_request, whatsapp_id)
            elif action == ActionType.HELP_REQUEST:
                return await self._handle_help_request(user_id, whatsapp_id)
            elif action == ActionType.PROVIDER_PROFILE:
                return await self._handle_provider_profile(recent_request, whatsapp_id)
            elif action == ActionType.CONTACT_PROVIDER:
                return await self._handle_contact_provider(recent_request, whatsapp_id)
            else:
                return "❌ Action non reconnue. Utilisez le menu d'actions rapides."
                
        except Exception as e:
            logger.error("action_command_error", extra={
                "user_id": user_id,
                "action": action.value,
                "error": str(e)
            })
            return "❌ Erreur lors du traitement de votre demande. Réessayez dans un moment."
    
    async def _handle_status_check(self, request: ServiceRequest, whatsapp_id: str) -> str:
        """Handle status check action"""
        response_parts = ["📊 *Statut de votre demande*\n"]
        
        # Basic info
        response_parts.append(f"🆔 *Demande* : #{request.id}")
        response_parts.append(f"🔧 *Service* : {request.service_type.title()}")
        response_parts.append(f"📍 *Lieu* : {request.location}")
        response_parts.append(f"📅 *Créée* : {request.created_at.strftime('%d/%m/%Y %H:%M')}")
        
        # Status-specific information
        status_emoji = {
            RequestStatus.PENDING: "⏳",
            RequestStatus.ASSIGNED: "✅",
            RequestStatus.IN_PROGRESS: "🔄",
            RequestStatus.COMPLETED: "✅",
            RequestStatus.PAYMENT_PENDING: "💰",
            RequestStatus.PAYMENT_COMPLETED: "💚",
            RequestStatus.CANCELLED: "❌"
        }
        
        emoji = status_emoji.get(request.status, "❓")
        response_parts.append(f"\n{emoji} *Statut* : {request.status}")
        
        # Provider information if assigned
        if request.provider_id and request.provider:
            provider = request.provider
            response_parts.append(f"\n👷 *Prestataire assigné* :")
            response_parts.append(f"• Nom : {provider.name}")
            response_parts.append(f"• Note : {'⭐' * int(provider.rating or 0)}")
            response_parts.append(f"• Téléphone : {provider.phone_number}")
        
        # Timeline information
        if request.accepted_at:
            response_parts.append(f"✅ *Accepté* : {request.accepted_at.strftime('%d/%m/%Y %H:%M')}")
        
        if request.completed_at:
            response_parts.append(f"✅ *Terminé* : {request.completed_at.strftime('%d/%m/%Y %H:%M')}")
        
        # Next steps
        response_parts.append(f"\n📋 *Prochaines étapes* :")
        if request.status == RequestStatus.PENDING:
            response_parts.append("• Recherche d'un prestataire en cours")
            response_parts.append("• Vous serez notifié dès qu'un prestataire accepte")
        elif request.status == RequestStatus.ASSIGNED:
            response_parts.append("• Le prestataire va vous contacter bientôt")
            response_parts.append("• Préparez l'accès au lieu d'intervention")
        elif request.status == RequestStatus.IN_PROGRESS:
            response_parts.append("• L'intervention est en cours")
            response_parts.append("• Restez disponible pour le prestataire")
        elif request.status == RequestStatus.COMPLETED:
            response_parts.append("• Service terminé avec succès")
            response_parts.append("• Paiement requis via mobile money")
        
        # Add quick actions menu
        response_parts.append(f"\n{self.generate_actions_menu(request.id)}")
        
        return "\n".join(response_parts)
    
    async def _handle_modify_request(self, request: ServiceRequest, whatsapp_id: str) -> str:
        """Handle request modification action"""
        if request.status not in [RequestStatus.PENDING, RequestStatus.ASSIGNED]:
            return (
                "❌ *Modification impossible*\n\n"
                f"Votre demande est actuellement *{request.status}*.\n"
                "Les modifications ne sont possibles que pour les demandes "
                "en attente ou assignées.\n\n"
                "💡 Contactez le support si vous avez besoin d'aide."
            )
        
        response = """
✏️ *Modification de votre demande*

Que souhaitez-vous modifier ?

1️⃣ *DESCRIPTION* - Changer la description du problème
2️⃣ *LIEU* - Modifier l'adresse
3️⃣ *URGENCE* - Changer le niveau d'urgence

Tapez le numéro ou le mot-clé pour continuer.
Exemple : "1" ou "DESCRIPTION"

⚠️ *Note* : Modifier le lieu ou le service peut nécessiter 
une nouvelle recherche de prestataire.
"""
        
        return response.strip()
    
    async def _handle_cancel_request(self, request: ServiceRequest, whatsapp_id: str) -> str:
        """Handle request cancellation action"""
        if request.status in [RequestStatus.COMPLETED, RequestStatus.CANCELLED]:
            status_msg = "terminée" if request.status == RequestStatus.COMPLETED else "déjà annulée"
            return f"❌ Cette demande est {status_msg} et ne peut pas être annulée."
        
        # Check if provider is already working
        if request.status == RequestStatus.IN_PROGRESS:
            return """
⚠️ *Annulation complexe*

Votre demande est en cours d'exécution.
L'annulation à ce stade peut entraîner des frais.

Pour continuer l'annulation, contactez notre support :
📞 +237 6XX XXX XXX
📧 support@djobea.ai

Ou tapez *AIDE* pour créer un ticket de support.
"""
        
        # Standard cancellation
        cancel_fee = ""
        if request.status == RequestStatus.ASSIGNED:
            cancel_fee = "\n⚠️ Des frais d'annulation de 500 XAF peuvent s'appliquer."
        
        response = f"""
❌ *Confirmation d'annulation*

Êtes-vous sûr de vouloir annuler cette demande ?

🔧 *Service* : {request.service_type.title()}
📍 *Lieu* : {request.location}
📅 *Créée* : {request.created_at.strftime('%d/%m/%Y %H:%M')}
{cancel_fee}

Tapez *OUI* pour confirmer l'annulation
Tapez *NON* pour garder votre demande

Cette action est irréversible.
"""
        
        return response.strip()
    
    async def _handle_help_request(self, user_id: int, whatsapp_id: str) -> str:
        """Handle help and support request"""
        response = """
🆘 *Centre d'aide Djobea AI*

*Questions fréquentes :*

❓ *Comment ça marche ?*
1. Décrivez votre problème
2. Nous trouvons un prestataire
3. Le prestataire vous contacte
4. Payez après le service

❓ *Combien ça coûte ?*
• Plomberie : 5 000 - 15 000 XAF
• Électricité : 3 000 - 10 000 XAF
• Électroménager : 2 000 - 8 000 XAF

❓ *Comment payer ?*
• MTN Mobile Money
• Orange Money
• Express Union

*Besoin d'aide personnalisée ?*
Tapez *TICKET* pour créer un ticket de support

*Contact direct :*
📞 +237 6XX XXX XXX
📧 support@djobea.ai
🕒 Lun-Ven 8h-18h

Tapez *MENU* pour revenir aux actions rapides.
"""
        
        return response.strip()
    
    async def _handle_provider_profile(self, request: ServiceRequest, whatsapp_id: str) -> str:
        """Handle provider profile view"""
        if not request.provider_id or not request.provider:
            return (
                "👤 *Aucun prestataire assigné*\n\n"
                "Votre demande n'a pas encore de prestataire assigné.\n"
                "Vous recevrez ces informations dès qu'un prestataire accepte.\n\n"
                "Tapez *STATUT* pour vérifier l'avancement."
            )
        
        provider = request.provider
        rating_stars = "⭐" * int(provider.rating or 0)
        rating_stars += "☆" * (5 - int(provider.rating or 0))
        
        response = f"""
👤 *Profil du prestataire*

*Informations générales :*
• Nom : {provider.name}
• Spécialité : {', '.join(provider.services or [])}
• Note : {rating_stars} ({provider.rating or 0}/5)
• Jobs terminés : {provider.total_jobs or 0}

*Contact :*
• Téléphone : {provider.phone_number}
• WhatsApp : {provider.whatsapp_id}

*Zone de couverture :*
• {', '.join(provider.coverage_areas or ['Bonamoussadi'])}

*Statut :*
{"🟢 Disponible" if provider.is_available else "🟡 Occupé"}

💡 *Conseil* : Vous pouvez contacter directement 
le prestataire pour discuter des détails.

Tapez *CONTACT* pour obtenir les instructions de contact.
"""
        
        return response.strip()
    
    async def _handle_contact_provider(self, request: ServiceRequest, whatsapp_id: str) -> str:
        """Handle provider contact information"""
        if not request.provider_id or not request.provider:
            return (
                "📞 *Aucun prestataire à contacter*\n\n"
                "Votre demande n'a pas encore de prestataire assigné.\n"
                "Vous pourrez le contacter dès qu'un prestataire accepte.\n\n"
                "Tapez *STATUT* pour vérifier l'avancement."
            )
        
        provider = request.provider
        
        response = f"""
📞 *Contacter votre prestataire*

👤 *{provider.name}*
📱 *{provider.phone_number}*

*Comment contacter :*

1️⃣ *Appel direct*
Appelez : {provider.phone_number}

2️⃣ *WhatsApp*
Envoyez un message à : {provider.whatsapp_id}

3️⃣ *Message suggéré :*
"Bonjour, je suis votre client Djobea AI pour 
la demande #{request.id} à {request.location}. 
Quand pouvez-vous intervenir ?"

⚠️ *Important* :
• Mentionnez toujours votre demande #{request.id}
• Soyez poli et respectueux
• Confirmez les détails de l'intervention

🆘 En cas de problème, tapez *AIDE*
"""
        
        return response.strip()
    
    def _get_user_recent_request(self, user_id: int) -> Optional[ServiceRequest]:
        """Get user's most recent service request"""
        return (
            self.db.query(ServiceRequest)
            .filter(ServiceRequest.user_id == user_id)
            .order_by(desc(ServiceRequest.created_at))
            .first()
        )
    
    def _no_request_response(self, action: ActionType) -> str:
        """Response when user has no requests"""
        return (
            "🔍 *Aucune demande trouvée*\n\n"
            "Vous n'avez pas encore de demande de service.\n"
            "Décrivez votre problème pour commencer :\n\n"
            "Exemple : 'J'ai une fuite d'eau dans ma cuisine à Bonamoussadi'"
        )
    
    def _log_user_action(self, user_id: int, action: ActionType, details: Dict = None):
        """Log user action for analytics"""
        try:
            user_action = UserAction(
                user_id=user_id,
                action_type=action.value,
                action_details=details or {},
                success=True
            )
            self.db.add(user_action)
            self.db.commit()
        except Exception as e:
            logger.error("user_action_log_error", extra={
                "user_id": user_id,
                "action": action.value,
                "error": str(e)
            })
    
    def create_support_ticket(
        self, 
        user_id: int, 
        title: str, 
        description: str, 
        request_id: Optional[int] = None,
        priority: str = "medium"
    ) -> int:
        """Create a support ticket"""
        try:
            ticket = SupportTicket(
                user_id=user_id,
                request_id=request_id,
                title=title,
                description=description,
                status=SupportTicketStatus.OPEN,
                priority=priority
            )
            self.db.add(ticket)
            self.db.commit()
            
            logger.info("support_ticket_created", extra={
                "user_id": user_id,
                "ticket_id": ticket.id,
                "priority": priority
            })
            
            return ticket.id
            
        except Exception as e:
            logger.error("support_ticket_error", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    def track_request_modification(
        self,
        request_id: int,
        user_id: int,
        field_modified: str,
        old_value: str,
        new_value: str,
        reason: Optional[str] = None
    ):
        """Track request modifications"""
        try:
            modification = RequestModification(
                request_id=request_id,
                user_id=user_id,
                field_modified=field_modified,
                old_value=old_value,
                new_value=new_value,
                modification_reason=reason
            )
            self.db.add(modification)
            self.db.commit()
            
            logger.info("request_modified", extra={
                "request_id": request_id,
                "user_id": user_id,
                "field": field_modified
            })
            
        except Exception as e:
            logger.error("modification_tracking_error", extra={
                "request_id": request_id,
                "error": str(e)
            })