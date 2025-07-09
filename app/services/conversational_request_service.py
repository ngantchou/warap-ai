"""
Conversational Request Service - Interface conversationnelle pour la gestion des demandes
"""
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.request_management_models import (
    UserRequest, RequestConversationLog, ConversationAction,
    RequestStatus, RequestPriority
)
from app.services.request_management_service import RequestManagementService
# from app.services.ai_service import AIService

class ConversationalRequestService:
    """Service pour gérer les interactions conversationnelles avec les demandes"""
    
    def __init__(self):
        self.request_service = RequestManagementService()
        # self.ai_service = AIService()
        
        # Patterns de reconnaissance d'intention
        self.intent_patterns = {
            "view_requests": [
                r"voir mes demandes?",
                r"mes demandes?",
                r"liste.*demandes?",
                r"afficher.*demandes?",
                r"check.*requests?",
                r"show.*requests?"
            ],
            "view_details": [
                r"détails? de la demande",
                r"voir la demande",
                r"infos? sur",
                r"details? about",
                r"show request",
                r"demande numéro"
            ],
            "modify_request": [
                r"modifier.*demande",
                r"changer.*demande",
                r"edit.*request",
                r"change.*request",
                r"update.*request",
                r"corriger"
            ],
            "cancel_request": [
                r"annuler.*demande",
                r"cancel.*request",
                r"supprimer.*demande",
                r"delete.*request",
                r"je ne veux plus",
                r"arrêter"
            ],
            "create_request": [
                r"nouvelle demande",
                r"créer.*demande",
                r"new request",
                r"create request",
                r"j'ai besoin",
                r"je voudrais"
            ],
            "request_help": [
                r"aide",
                r"help",
                r"comment",
                r"que puis-je faire",
                r"what can i do"
            ]
        }
        
        # Templates de réponse
        self.response_templates = {
            "requests_list": """📋 **Vos demandes actives :**

{requests_list}

💡 *Pour voir les détails d'une demande, tapez "voir demande [numéro]"*
*Pour modifier une demande, tapez "modifier demande [numéro]"*
*Pour annuler une demande, tapez "annuler demande [numéro]"*""",
            
            "request_details": """📝 **Détails de la demande #{request_id}**

**Titre :** {title}
**Description :** {description}
**Service :** {service_type}
**Lieu :** {location}
**Statut :** {status}
**Priorité :** {priority}
**Créée le :** {created_at}
**Dernière modification :** {updated_at}

{modification_options}""",
            
            "modification_success": """✅ **Demande modifiée avec succès !**

{modifications_summary}

Votre demande a été mise à jour. {next_steps}""",
            
            "cancellation_confirmation": """⚠️ **Confirmation d'annulation**

Êtes-vous sûr de vouloir annuler cette demande ?

**Demande :** {title}
**Statut actuel :** {status}

Tapez "OUI" pour confirmer ou "NON" pour annuler.""",
            
            "help_message": """🤖 **Aide - Gestion des demandes**

**Commandes disponibles :**
• `voir mes demandes` - Afficher toutes vos demandes
• `voir demande [numéro]` - Détails d'une demande
• `modifier demande [numéro]` - Modifier une demande
• `annuler demande [numéro]` - Annuler une demande
• `nouvelle demande` - Créer une nouvelle demande

**Exemples :**
• "Voir mes demandes en cours"
• "Modifier ma demande de plomberie"
• "Annuler la demande 12345"
• "Changer l'adresse de ma demande"

*Vous pouvez utiliser un langage naturel !*""",
            
            "error_message": """❌ **Erreur**

{error_details}

{suggestions}"""
        }
    
    async def process_conversation_message(
        self,
        db: Session,
        user_id: str,
        message: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Traiter un message conversationnel"""
        
        # Analyser l'intention
        intent_result = await self._analyze_intent(message)
        
        # Logger la conversation
        await self._log_conversation(
            db, user_id, message, intent_result["action"], 
            intent_result["confidence"], conversation_context
        )
        
        # Traiter selon l'intention
        if intent_result["action"] == ConversationAction.VIEW_REQUESTS:
            return await self._handle_view_requests(db, user_id, intent_result)
        
        elif intent_result["action"] == ConversationAction.VIEW_DETAILS:
            return await self._handle_view_details(db, user_id, intent_result)
        
        elif intent_result["action"] == ConversationAction.MODIFY_REQUEST:
            return await self._handle_modify_request(db, user_id, intent_result, conversation_context)
        
        elif intent_result["action"] == ConversationAction.CANCEL_REQUEST:
            return await self._handle_cancel_request(db, user_id, intent_result, conversation_context)
        
        elif intent_result["action"] == ConversationAction.CREATE_REQUEST:
            return await self._handle_create_request(db, user_id, intent_result, conversation_context)
        
        else:
            return await self._handle_help_request(db, user_id)
    
    async def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """Analyser l'intention d'un message"""
        
        message_lower = message.lower()
        best_match = None
        best_confidence = 0.0
        
        # Rechercher les patterns
        for action, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    confidence = len(re.findall(pattern, message_lower)) * 0.3
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = action
        
        # Extraire les entités (numéros de demande, etc.)
        entities = self._extract_entities(message)
        
        return {
            "action": ConversationAction(best_match) if best_match else ConversationAction.CONFIRM_ACTION,
            "confidence": min(best_confidence, 1.0),
            "entities": entities,
            "original_message": message
        }
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extraire les entités du message"""
        
        entities = {}
        
        # Extraire les identifiants de demande
        request_id_patterns = [
            r"demande\s+(\w+)",
            r"request\s+(\w+)",
            r"numéro\s+(\w+)",
            r"#(\w+)",
            r"req_(\w+)"
        ]
        
        for pattern in request_id_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                entities["request_id"] = matches[0]
                break
        
        # Extraire les champs de modification
        modification_patterns = {
            "title": r"titre\s*[:\-]?\s*([^\n]+)",
            "description": r"description\s*[:\-]?\s*([^\n]+)",
            "location": r"(?:lieu|adresse|location)\s*[:\-]?\s*([^\n]+)",
            "priority": r"priorité\s*[:\-]?\s*(urgent|haute|normal|basse)"
        }
        
        for field, pattern in modification_patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                entities[field] = matches[0].strip()
        
        # Extraire les confirmations
        if re.search(r'\b(oui|yes|confirmer?|ok)\b', message.lower()):
            entities["confirmation"] = True
        elif re.search(r'\b(non|no|annuler|cancel)\b', message.lower()):
            entities["confirmation"] = False
        
        return entities
    
    async def _handle_view_requests(
        self,
        db: Session,
        user_id: str,
        intent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gérer l'affichage des demandes"""
        
        # Récupérer les demandes
        requests = await self.request_service.get_user_requests(db, user_id)
        
        if not requests:
            return {
                "success": True,
                "response": "📭 Vous n'avez aucune demande active pour le moment.\n\n💡 *Tapez 'nouvelle demande' pour créer votre première demande.*",
                "requires_action": False
            }
        
        # Formater la liste
        requests_list = []
        for req in requests:
            status_emoji = self._get_status_emoji(req.status)
            requests_list.append(
                f"{status_emoji} **#{req.request_id}** - {req.title}\n"
                f"   📍 {req.location} | 📅 {req.created_at.strftime('%d/%m/%Y')}\n"
                f"   🏷️ {req.status}"
            )
        
        response = self.response_templates["requests_list"].format(
            requests_list="\n\n".join(requests_list)
        )
        
        return {
            "success": True,
            "response": response,
            "requires_action": False,
            "data": {"requests": [{"id": req.request_id, "title": req.title} for req in requests]}
        }
    
    async def _handle_view_details(
        self,
        db: Session,
        user_id: str,
        intent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gérer l'affichage des détails d'une demande"""
        
        request_id = intent_result["entities"].get("request_id")
        
        if not request_id:
            return {
                "success": False,
                "response": "❌ Veuillez préciser le numéro de la demande.\n\n*Exemple : 'voir demande 12345'*",
                "requires_action": False
            }
        
        # Récupérer la demande
        request = await self.request_service.get_request_details(db, request_id, user_id)
        
        if not request:
            return {
                "success": False,
                "response": f"❌ Demande #{request_id} non trouvée ou accès refusé.",
                "requires_action": False
            }
        
        # Déterminer les options de modification
        modification_options = self._get_modification_options(request.status)
        
        response = self.response_templates["request_details"].format(
            request_id=request.request_id,
            title=request.title,
            description=request.description,
            service_type=request.service_type,
            location=request.location,
            status=request.status,
            priority=request.priority,
            created_at=request.created_at.strftime('%d/%m/%Y à %H:%M'),
            updated_at=request.updated_at.strftime('%d/%m/%Y à %H:%M'),
            modification_options=modification_options
        )
        
        return {
            "success": True,
            "response": response,
            "requires_action": False,
            "data": {
                "request_id": request.request_id,
                "status": request.status,
                "can_modify": request.status in [RequestStatus.DRAFT.value, RequestStatus.PENDING.value]
            }
        }
    
    async def _handle_modify_request(
        self,
        db: Session,
        user_id: str,
        intent_result: Dict[str, Any],
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Gérer la modification d'une demande"""
        
        request_id = intent_result["entities"].get("request_id")
        
        if not request_id:
            return {
                "success": False,
                "response": "❌ Veuillez préciser le numéro de la demande à modifier.\n\n*Exemple : 'modifier demande 12345'*",
                "requires_action": False
            }
        
        # Extraire les modifications
        modifications = {}
        for field in ["title", "description", "location", "priority"]:
            if field in intent_result["entities"]:
                modifications[field] = intent_result["entities"][field]
        
        if not modifications:
            return {
                "success": True,
                "response": f"🔧 **Modification de la demande #{request_id}**\n\n"
                          f"Que souhaitez-vous modifier ?\n\n"
                          f"**Exemples :**\n"
                          f"• *Titre: Nouveau titre*\n"
                          f"• *Description: Nouvelle description*\n"
                          f"• *Lieu: Nouvelle adresse*\n"
                          f"• *Priorité: urgent*",
                "requires_action": True,
                "data": {"request_id": request_id, "awaiting_modification": True}
            }
        
        # Appliquer les modifications
        result = await self.request_service.modify_request(
            db, request_id, user_id, modifications, conversation_context
        )
        
        if result["success"]:
            modifications_summary = "\n".join([
                f"• **{mod['field']}** : {mod['old_value']} → {mod['new_value']}"
                for mod in result["modifications_applied"]
            ])
            
            next_steps = self._get_next_steps(result["request"].status)
            
            response = self.response_templates["modification_success"].format(
                modifications_summary=modifications_summary,
                next_steps=next_steps
            )
            
            return {
                "success": True,
                "response": response,
                "requires_action": False,
                "data": {"request_id": request_id, "modifications": result["modifications_applied"]}
            }
        else:
            return {
                "success": False,
                "response": f"❌ Impossible de modifier la demande :\n\n{result['error']}",
                "requires_action": False
            }
    
    async def _handle_cancel_request(
        self,
        db: Session,
        user_id: str,
        intent_result: Dict[str, Any],
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Gérer l'annulation d'une demande"""
        
        request_id = intent_result["entities"].get("request_id")
        confirmation = intent_result["entities"].get("confirmation")
        
        if not request_id:
            return {
                "success": False,
                "response": "❌ Veuillez préciser le numéro de la demande à annuler.\n\n*Exemple : 'annuler demande 12345'*",
                "requires_action": False
            }
        
        # Vérifier si confirmation requise
        if confirmation is None:
            request = await self.request_service.get_request_details(db, request_id, user_id)
            if not request:
                return {
                    "success": False,
                    "response": f"❌ Demande #{request_id} non trouvée.",
                    "requires_action": False
                }
            
            response = self.response_templates["cancellation_confirmation"].format(
                title=request.title,
                status=request.status
            )
            
            return {
                "success": True,
                "response": response,
                "requires_action": True,
                "data": {"request_id": request_id, "awaiting_confirmation": True}
            }
        
        # Traiter la confirmation
        if confirmation:
            reason = conversation_context.get("reason", "Annulation demandée par l'utilisateur")
            result = await self.request_service.cancel_request(
                db, request_id, user_id, reason, conversation_context
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "response": f"✅ **Demande #{request_id} annulée avec succès.**\n\n"
                              f"Vous recevrez une confirmation par WhatsApp.",
                    "requires_action": False
                }
            else:
                return {
                    "success": False,
                    "response": f"❌ Impossible d'annuler la demande :\n\n{result['error']}",
                    "requires_action": False
                }
        else:
            return {
                "success": True,
                "response": f"↩️ **Annulation annulée.**\n\nLa demande #{request_id} reste active.",
                "requires_action": False
            }
    
    async def _handle_create_request(
        self,
        db: Session,
        user_id: str,
        intent_result: Dict[str, Any],
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Gérer la création d'une nouvelle demande"""
        
        return {
            "success": True,
            "response": """🆕 **Création d'une nouvelle demande**

Pour créer une nouvelle demande, j'ai besoin de quelques informations :

**1. Type de service** (plomberie, électricité, etc.)
**2. Description** du problème
**3. Adresse** où intervenir
**4. Priorité** (normal, urgent)

*Vous pouvez tout me dire en une seule fois ou répondre étape par étape.*

**Exemple :**
*"Nouvelle demande plomberie : fuite d'eau dans la cuisine, 123 rue de la Paix, Bonamoussadi, urgent"*""",
            "requires_action": True,
            "data": {"creating_new_request": True}
        }
    
    async def _handle_help_request(
        self,
        db: Session,
        user_id: str
    ) -> Dict[str, Any]:
        """Gérer les demandes d'aide"""
        
        return {
            "success": True,
            "response": self.response_templates["help_message"],
            "requires_action": False
        }
    
    async def _log_conversation(
        self,
        db: Session,
        user_id: str,
        message: str,
        detected_action: str,
        confidence: float,
        conversation_context: Optional[Dict[str, Any]] = None
    ):
        """Logger une interaction conversationnelle"""
        
        # Créer un ID de conversation unique
        conversation_id = f"conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
        
        # Déterminer la demande liée si applicable
        request_id = None
        if conversation_context:
            request_id = conversation_context.get("request_id")
        
        log = RequestConversationLog(
            request_id=request_id,
            conversation_id=conversation_id,
            user_message=message,
            detected_action=detected_action,
            intent_confidence=confidence,
            extracted_data=json.dumps(conversation_context or {}),
            conversation_state="active"
        )
        
        db.add(log)
        db.commit()
    
    def _get_status_emoji(self, status: str) -> str:
        """Obtenir l'emoji correspondant au statut"""
        
        emoji_map = {
            RequestStatus.DRAFT.value: "📝",
            RequestStatus.PENDING.value: "⏳",
            RequestStatus.ASSIGNED.value: "👥",
            RequestStatus.IN_PROGRESS.value: "🔧",
            RequestStatus.COMPLETED.value: "✅",
            RequestStatus.CANCELLED.value: "❌"
        }
        
        return emoji_map.get(status, "📋")
    
    def _get_modification_options(self, status: str) -> str:
        """Obtenir les options de modification selon le statut"""
        
        if status == RequestStatus.DRAFT.value:
            return "💡 *Vous pouvez modifier tous les détails de cette demande.*"
        elif status == RequestStatus.PENDING.value:
            return "⚠️ *Modifications limitées - contactez le support pour les changements majeurs.*"
        elif status in [RequestStatus.ASSIGNED.value, RequestStatus.IN_PROGRESS.value]:
            return "🔒 *Demande en cours - modifications restreintes.*"
        else:
            return "🚫 *Aucune modification possible pour ce statut.*"
    
    def _get_next_steps(self, status: str) -> str:
        """Obtenir les prochaines étapes selon le statut"""
        
        if status == RequestStatus.DRAFT.value:
            return "Tapez 'confirmer demande' pour la soumettre."
        elif status == RequestStatus.PENDING.value:
            return "Nous recherchons un prestataire pour vous."
        elif status == RequestStatus.ASSIGNED.value:
            return "Un prestataire va vous contacter prochainement."
        else:
            return "Nous vous tiendrons informé des prochaines étapes."