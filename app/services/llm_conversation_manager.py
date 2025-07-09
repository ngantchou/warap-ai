"""
LLM-Driven Conversation Manager for Djobea AI
Uses natural LLM capabilities for intent detection and action codes for fluid interactions
"""

import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.ai_service import AIService
from app.models.database_models import Conversation, User, ServiceRequest
from app.models.dynamic_services import Zone, Service, ServiceZone
from app.utils.conversation_state import ConversationState, ConversationPhase

logger = logging.getLogger(__name__)

class ActionCode(Enum):
    """Action codes for LLM communication"""
    # Information requests
    PROVIDE_FAQ = "provide_faq"
    PROVIDE_SERVICES_LIST = "provide_services_list"
    PROVIDE_PRICING = "provide_pricing"
    PROVIDE_HELP = "provide_help"
    
    # Human contact
    CONNECT_HUMAN = "connect_human"
    ESCALATE_SUPPORT = "escalate_support"
    
    # Service requests
    CREATE_SERVICE_REQUEST = "create_service_request"
    GATHER_SERVICE_INFO = "gather_service_info"
    CONTINUE_CONVERSATION = "continue_conversation"
    
    # Request management
    SHOW_USER_REQUESTS = "show_user_requests"
    SHOW_REQUEST_DETAILS = "show_request_details"
    UPDATE_REQUEST_STATUS = "update_request_status"
    
    # General responses
    PROVIDE_GREETING = "provide_greeting"
    HANDLE_GENERAL_INQUIRY = "handle_general_inquiry"
    
    # Error handling
    HANDLE_ERROR = "handle_error"
    REQUEST_CLARIFICATION = "request_clarification"

class LLMConversationManager:
    """
    Simplified conversation manager that leverages LLM natural capabilities
    with action codes for structured interactions
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
        self.conversation_cache = {}
    
    async def _get_dynamic_services(self) -> List[Dict[str, Any]]:
        """Get available services from database"""
        try:
            services = self.db.query(Service).filter(Service.status == "available").all()
            return [
                {
                    "code": service.code,
                    "name": service.name_fr or service.name,
                    "description": service.description_fr or service.description,
                    "category": service.category.name_fr if hasattr(service, 'category') and service.category else None,
                    "min_price": getattr(service, 'min_price_xaf', None),
                    "max_price": getattr(service, 'max_price_xaf', None)
                }
                for service in services
            ]
        except Exception as e:
            logger.error(f"Error getting dynamic services: {e}")
            # Fallback to static services
            return [
                {"code": "plomberie", "name": "Plomberie", "description": "fuites, robinets, WC, tuyaux", "min_price": 5000, "max_price": 15000},
                {"code": "electricite", "name": "Électricité", "description": "pannes, prises, interrupteurs", "min_price": 3000, "max_price": 10000},
                {"code": "electromenager", "name": "Électroménager", "description": "frigo, machine à laver, four", "min_price": 2000, "max_price": 8000}
            ]
    
    async def _get_dynamic_zones(self) -> List[Dict[str, Any]]:
        """Get available zones from database"""
        try:
            zones = self.db.query(Zone).filter(Zone.is_active == True).all()
            return [
                {
                    "code": zone.code,
                    "name": zone.name_fr or zone.name,
                    "type": zone.zone_type,
                    "full_path": zone.full_path
                }
                for zone in zones
            ]
        except Exception as e:
            logger.error(f"Error getting dynamic zones: {e}")
            # Fallback to static zones
            return [
                {"code": "bonamoussadi", "name": "Bonamoussadi", "type": "district", "full_path": "/cameroun/littoral/douala/bonamoussadi"},
                {"code": "douala", "name": "Douala", "type": "city", "full_path": "/cameroun/littoral/douala"}
            ]
    
    async def process_message(
        self, 
        user_identifier: str, 
        message: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Process user message using LLM-driven approach with action codes"""
        
        try:
            # Get or create user context
            user = await self._get_or_create_user(user_identifier)
            conversation_history = await self._get_conversation_history(user_identifier)
            
            # Let LLM analyze and determine action
            analysis = await self._analyze_with_llm(message, conversation_history, user_identifier)
            
            # Execute the determined action
            result = await self._execute_action(analysis, user_identifier, message)
            
            # Log conversation
            await self._log_conversation(user_identifier, message, result['response'], analysis)
            
            return {
                'response': result['response'],
                'session_id': session_id or user_identifier,
                'request_complete': result.get('request_complete', False),
                'request_id': result.get('request_id'),
                'suggestions': result.get('suggestions', []),
                'needs_info': result.get('needs_info', []),
                'status': result.get('status', 'active'),
                'user_id': user.id,
                'buttons': result.get('buttons', []),
                'system_action': result.get('system_action'),
                'next_step': result.get('next_step')
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'response': "Je suis désolé, je rencontre un problème technique. Pouvez-vous réessayer ?",
                'session_id': session_id or user_identifier,
                'request_complete': False,
                'request_id': None,
                'suggestions': [],
                'needs_info': [],
                'status': 'error',
                'user_id': None,
                'buttons': [],
                'system_action': None,
                'next_step': None
            }
    
    async def _analyze_with_llm(
        self, 
        message: str, 
        conversation_history: List[Dict], 
        user_identifier: str
    ) -> Dict[str, Any]:
        """Use LLM to analyze message and determine appropriate action"""
        
        # Build context from conversation history
        context = ""
        if conversation_history:
            recent_messages = conversation_history[-5:]  # Last 5 exchanges
            context = "\n".join([
                f"User: {msg['message']}\nAssistant: {msg['response']}"
                for msg in recent_messages
            ])
        
        # Get cached conversation state
        cached_state = self.conversation_cache.get(user_identifier, {})
        
        # Get dynamic services and zones
        dynamic_services = await self._get_dynamic_services()
        dynamic_zones = await self._get_dynamic_zones()
        
        # Format services for prompt
        services_text = "\n".join([
            f"- {service['name']}: {service['description']}" + 
            (f" (Prix: {service['min_price']}-{service['max_price']} XAF)" if service['min_price'] and service['max_price'] else "")
            for service in dynamic_services
        ])
        
        # Format zones for prompt
        zones_text = ", ".join([zone['name'] for zone in dynamic_zones])
        
        system_prompt = f"""
        Tu es l'IA conversationnelle de Djobea AI, service camerounais de mise en relation pour services à domicile.
        
        SERVICES DISPONIBLES:
        {services_text}
        
        ZONES DE COUVERTURE: {zones_text}
        
        ACTION CODES DISPONIBLES:
        
        INFORMATIONS:
        - "provide_faq" - Pour FAQ, aide générale
        - "provide_services_list" - Pour liste des services
        - "provide_pricing" - Pour tarifs et prix
        - "provide_help" - Pour aide et support
        
        CONTACT HUMAIN:
        - "connect_human" - Pour parler à quelqu'un
        - "escalate_support" - Pour support avancé
        
        DEMANDES DE SERVICE:
        - "create_service_request" - Créer nouvelle demande (si service_type ET location présents)
        - "gather_service_info" - Collecter informations manquantes
        - "continue_conversation" - Continuer conversation existante
        
        GESTION DEMANDES:
        - "show_user_requests" - Voir demandes existantes
        - "show_request_details" - Détails d'une demande
        
        GÉNÉRAL:
        - "provide_greeting" - Salutation
        - "handle_general_inquiry" - Conversation générale
        
        ERREUR:
        - "handle_error" - Gestion d'erreur
        - "request_clarification" - Demander clarification
        
        CONTEXTE CONVERSATION:
        {context}
        
        ÉTAT CONVERSATIONNEL ACTUEL:
        {json.dumps(cached_state, indent=2)}
        
        Analyse le message et détermine l'action appropriée.
        Priorise les demandes d'information et de contact humain.
        Pour les demandes de service, vérifie si service_type ET location sont présents.
        
        Réponds en JSON strict.
        """
        
        user_prompt = f"""
        Message utilisateur: "{message}"
        
        Analyse ce message et détermine l'action appropriée.
        
        Fournis un JSON avec:
        {{
            "action_code": "code_action_approprié",
            "confidence": 0.0_to_1.0,
            "reasoning": "explication_du_choix",
            "extracted_info": {{
                "service_type": "type_si_détecté",
                "location": "lieu_si_mentionné",
                "description": "description_problème",
                "urgency": "niveau_urgence"
            }},
            "missing_info": ["informations_manquantes"],
            "context_clues": ["indices_contextuels"],
            "user_intent": "intention_utilisateur"
        }}
        
        IMPORTANT: Choisis l'action_code le plus approprié selon le message.
        """
        
        try:
            ai_messages = [{"role": "user", "content": user_prompt}]
            
            response = await self.ai_service.generate_response(
                messages=ai_messages,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            # Extract JSON from response
            if '```json' in response:
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()
            elif '{' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                response = response[json_start:json_end]
            
            analysis = json.loads(response)
            logger.info(f"LLM Analysis: {analysis}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            return {
                "action_code": "handle_general_inquiry",
                "confidence": 0.5,
                "reasoning": "Fallback due to analysis error",
                "extracted_info": {},
                "missing_info": [],
                "context_clues": [],
                "user_intent": "general"
            }
    
    async def _execute_action(
        self, 
        analysis: Dict[str, Any], 
        user_identifier: str, 
        message: str
    ) -> Dict[str, Any]:
        """Execute the determined action code"""
        
        action_code = analysis.get("action_code")
        extracted_info = analysis.get("extracted_info", {})
        
        logger.info(f"Executing action: {action_code} for user {user_identifier}")
        
        try:
            if action_code == "provide_faq":
                return await self._provide_faq()
            
            elif action_code == "provide_services_list":
                return await self._provide_services_list()
            
            elif action_code == "provide_pricing":
                return await self._provide_pricing()
            
            elif action_code == "provide_help":
                return await self._provide_help()
            
            elif action_code == "connect_human":
                return await self._connect_human()
            
            elif action_code == "escalate_support":
                return await self._escalate_support()
            
            elif action_code == "create_service_request":
                return await self._create_service_request(user_identifier, extracted_info)
            
            elif action_code == "gather_service_info":
                return await self._gather_service_info(user_identifier, extracted_info, analysis)
            
            elif action_code == "continue_conversation":
                return await self._continue_conversation(user_identifier, message, analysis)
            
            elif action_code == "show_user_requests":
                return await self._show_user_requests(user_identifier)
            
            elif action_code == "show_request_details":
                return await self._show_request_details(user_identifier, message)
            
            elif action_code == "provide_greeting":
                return await self._provide_greeting()
            
            elif action_code == "handle_general_inquiry":
                return await self._handle_general_inquiry(message)
            
            else:
                return await self._handle_error(f"Unknown action code: {action_code}")
        
        except Exception as e:
            logger.error(f"Error executing action {action_code}: {e}")
            return await self._handle_error(f"Error executing action: {e}")
    
    # Action implementations
    async def _provide_faq(self) -> Dict[str, Any]:
        """Provide FAQ information"""
        response = """
🔧 **FAQ - Djobea AI**

**Qu'est-ce que Djobea AI ?**
Service de mise en relation pour vos besoins à domicile à Bonamoussadi, Douala.

**Quels services proposez-vous ?**
• Plomberie (fuites, robinets, WC)
• Électricité (pannes, prises, éclairage)
• Électroménager (frigo, machine à laver, four)

**Comment ça marche ?**
1. Décrivez votre problème
2. Nous trouvons un prestataire qualifié
3. Intervention rapide chez vous

**Tarifs ?**
• Plomberie: 5,000-15,000 XAF
• Électricité: 3,000-10,000 XAF
• Électroménager: 2,000-8,000 XAF

**Questions ?** Dites-moi "aide" ou décrivez votre problème !
        """
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["J'ai un problème de plomberie", "J'ai une panne électrique", "Mon frigo ne marche pas"]
        }
    
    async def _provide_services_list(self) -> Dict[str, Any]:
        """Provide services list"""
        response = """
🏠 **Services Djobea AI - Bonamoussadi**

🔧 **PLOMBERIE**
• Fuites d'eau et canalisations
• Robinets et éviers
• WC et sanitaires
• Tuyauterie

⚡ **ÉLECTRICITÉ**
• Pannes et coupures
• Prises et interrupteurs
• Éclairage et ventilation
• Tableaux électriques

🏠 **ÉLECTROMÉNAGER**
• Réfrigérateurs et congélateurs
• Machines à laver
• Fours et cuisinières
• Climatisation

**Zone de couverture:** Bonamoussadi, Douala

Décrivez votre problème pour une intervention rapide !
        """
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["Problème de plomberie", "Panne électrique", "Électroménager défaillant"]
        }
    
    async def _provide_pricing(self) -> Dict[str, Any]:
        """Provide pricing information"""
        response = """
💰 **Tarifs Djobea AI**

🔧 **PLOMBERIE**
• Intervention simple: 5,000-8,000 XAF
• Réparation moyenne: 8,000-12,000 XAF
• Gros travaux: 12,000-15,000 XAF

⚡ **ÉLECTRICITÉ**
• Diagnostic: 3,000-5,000 XAF
• Réparation courante: 5,000-8,000 XAF
• Installation: 8,000-10,000 XAF

🏠 **ÉLECTROMÉNAGER**
• Diagnostic: 2,000-3,000 XAF
• Réparation simple: 3,000-6,000 XAF
• Réparation complexe: 6,000-8,000 XAF

**Note:** Tarifs indicatifs, devis précis après évaluation.
**Déplacement:** Gratuit à Bonamoussadi

Décrivez votre problème pour un devis personnalisé !
        """
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["Devis plomberie", "Devis électricité", "Devis électroménager"]
        }
    
    async def _provide_help(self) -> Dict[str, Any]:
        """Provide help information"""
        response = """
🆘 **Aide - Djobea AI**

**Comment demander un service ?**
Dites-moi simplement votre problème, par exemple:
• "J'ai une fuite d'eau"
• "Mon frigo ne marche plus"
• "Panne électrique chez moi"

**Informations utiles à mentionner:**
• Type de problème
• Votre localisation à Bonamoussadi
• Niveau d'urgence

**Commandes utiles:**
• "Mes demandes" - Voir vos demandes
• "Tarifs" - Voir les prix
• "Services" - Liste des services
• "Contact" - Parler à quelqu'un

**Urgence ?** Précisez "urgent" dans votre message.

**Besoin d'aide humaine ?** Dites "contact humain".

Je suis là pour vous aider ! Que puis-je faire pour vous ?
        """
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["Mes demandes", "Tarifs", "Contact humain"]
        }
    
    async def _connect_human(self) -> Dict[str, Any]:
        """Connect to human support"""
        response = """
👤 **Contact Humain - Djobea AI**

Je comprends que vous souhaitez parler à quelqu'un.

**Options de contact:**
📞 **Téléphone:** +237 6 XX XX XX XX
📧 **Email:** support@djobea.ai
💬 **WhatsApp:** +237 6 XX XX XX XX

**Heures d'ouverture:**
• Lundi-Vendredi: 7h00-19h00
• Samedi: 8h00-17h00
• Dimanche: 9h00-15h00

**Urgence 24h/24:**
Pour les urgences (fuites majeures, pannes électriques dangereuses), contactez le +237 6 XX XX XX XX

En attendant, je peux vous aider avec vos demandes de service. Que puis-je faire pour vous ?
        """
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["Urgence", "Nouvelle demande", "Voir mes demandes"]
        }
    
    async def _escalate_support(self) -> Dict[str, Any]:
        """Escalate to advanced support"""
        response = """
🚨 **Support Avancé - Djobea AI**

Votre demande a été remontée à notre équipe support.

**Référence:** SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}

**Délai de réponse:** 15-30 minutes

**Contact direct:**
📞 Support: +237 6 XX XX XX XX
📧 Email: support@djobea.ai

Un agent va vous contacter rapidement pour résoudre votre problème.

En attendant, puis-je vous aider avec autre chose ?
        """
        return {
            'response': response.strip(),
            'request_complete': False,
            'system_action': 'escalate_created',
            'suggestions': ["Nouvelle demande", "Voir mes demandes"]
        }
    
    async def _create_service_request(self, user_identifier: str, extracted_info: Dict) -> Dict[str, Any]:
        """Create a new service request"""
        # Implementation would create actual service request
        service_type = extracted_info.get('service_type')
        location = extracted_info.get('location')
        description = extracted_info.get('description')
        
        # For now, return success message
        response = f"""
✅ **Demande créée avec succès !**

**Service:** {service_type}
**Lieu:** {location}
**Description:** {description}

**Référence:** DJB-{datetime.now().strftime('%Y%m%d%H%M%S')}

🔍 Recherche de prestataires en cours...
Vous recevrez une notification dès qu'un prestataire accepte votre demande.

**Prochaines étapes:**
• Notification de match (2-5 minutes)
• Contact du prestataire
• Intervention planifiée

Tapez "mes demandes" pour suivre votre demande.
        """
        
        return {
            'response': response.strip(),
            'request_complete': True,
            'request_id': f"DJB-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'system_action': 'service_request_created',
            'suggestions': ["Mes demandes", "Nouvelle demande"]
        }
    
    async def _gather_service_info(self, user_identifier: str, extracted_info: Dict, analysis: Dict) -> Dict[str, Any]:
        """Gather missing service information"""
        missing_info = analysis.get('missing_info', [])
        
        # Update conversation cache
        if user_identifier not in self.conversation_cache:
            self.conversation_cache[user_identifier] = {}
        
        # Merge extracted info (prioritize non-null values)
        for key, value in extracted_info.items():
            if value is not None and value != "":
                self.conversation_cache[user_identifier][key] = value
        
        cached_state = self.conversation_cache[user_identifier]
        logger.info(f"Gathering info for {user_identifier}: cached={cached_state}, missing={missing_info}")
        
        # Generate natural question for missing info
        if 'service_type' in missing_info:
            response = "Quel type de service avez-vous besoin ? Plomberie, électricité ou électroménager ?"
            suggestions = ["Plomberie", "Électricité", "Électroménager"]
        elif 'location' in missing_info:
            response = "Où se situe le problème ? (Quartier ou adresse à Bonamoussadi)"
            suggestions = ["Bonamoussadi Centre", "Bonamoussadi Makepe", "Bonamoussadi Rond-point"]
        elif 'description' in missing_info:
            response = "Pouvez-vous décrire le problème en détail ?"
            suggestions = ["Problème urgent", "Problème normal", "Maintenance"]
        else:
            # All info gathered, try to create request
            return await self._create_service_request(user_identifier, cached_state)
        
        return {
            'response': response,
            'request_complete': False,
            'needs_info': missing_info,
            'suggestions': suggestions
        }
    
    async def _continue_conversation(self, user_identifier: str, message: str, analysis: Dict) -> Dict[str, Any]:
        """Continue existing conversation"""
        # Get cached conversation state
        cached_state = self.conversation_cache.get(user_identifier, {})
        extracted_info = analysis.get('extracted_info', {})
        
        # Merge new information (prioritize non-null values)
        for key, value in extracted_info.items():
            if value is not None and value != "":
                cached_state[key] = value
        
        # Update cache
        self.conversation_cache[user_identifier] = cached_state
        
        logger.info(f"Continued conversation for {user_identifier}: {cached_state}")
        
        # Check if we have enough info to create request
        required_fields = ['service_type', 'location']
        missing_fields = [field for field in required_fields if not cached_state.get(field)]
        
        if not missing_fields:
            return await self._create_service_request(user_identifier, cached_state)
        else:
            # Continue gathering info
            return await self._gather_service_info(user_identifier, cached_state, {'missing_info': missing_fields})
    
    async def _show_user_requests(self, user_identifier: str) -> Dict[str, Any]:
        """Show user's requests"""
        response = """
📋 **Vos demandes - Djobea AI**

*Aucune demande trouvée pour le moment.*

Pour créer une nouvelle demande, décrivez simplement votre problème:
• "J'ai une fuite d'eau"
• "Mon frigo ne marche plus"
• "Panne électrique"

Je suis là pour vous aider ! 🔧
        """
        
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["Nouvelle demande", "Aide", "Services"]
        }
    
    async def _show_request_details(self, user_identifier: str, message: str) -> Dict[str, Any]:
        """Show request details"""
        response = """
📄 **Détails de la demande**

*Demande non trouvée.*

Tapez "mes demandes" pour voir toutes vos demandes.
        """
        
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["Mes demandes", "Nouvelle demande"]
        }
    
    async def _provide_greeting(self) -> Dict[str, Any]:
        """Provide greeting message"""
        response = """
👋 **Bonjour ! Je suis l'assistant Djobea AI**

Je vous aide avec tous vos besoins de services à domicile à Bonamoussadi:

🔧 **Plomberie** - Fuites, robinets, WC
⚡ **Électricité** - Pannes, prises, éclairage  
🏠 **Électroménager** - Frigo, machine à laver, four

**Comment puis-je vous aider aujourd'hui ?**
• Décrivez votre problème
• Tapez "services" pour voir tous nos services
• Tapez "aide" pour plus d'informations

Je trouve rapidement le bon prestataire pour vous ! 🚀
        """
        
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["J'ai un problème", "Voir les services", "Aide"]
        }
    
    async def _handle_general_inquiry(self, message: str) -> Dict[str, Any]:
        """Handle general inquiries"""
        response = """
Je suis là pour vous aider avec vos services à domicile ! 🏠

**Que puis-je faire pour vous ?**
• Résoudre un problème de plomberie
• Réparer une panne électrique
• Dépanner un électroménager

**Ou tapez:**
• "services" - Voir tous nos services
• "tarifs" - Voir les prix
• "aide" - Obtenir de l'aide
• "contact" - Parler à quelqu'un

Décrivez simplement votre problème et je m'occupe du reste ! 🔧
        """
        
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["J'ai un problème", "Services", "Tarifs", "Aide"]
        }
    
    async def _handle_error(self, error_message: str) -> Dict[str, Any]:
        """Handle errors"""
        response = """
😔 **Oops ! Petit problème technique**

Je rencontre une difficulté, mais je suis là pour vous aider.

**Essayez de:**
• Reformuler votre demande
• Être plus précis sur votre problème
• Taper "aide" pour voir les options

**Ou contactez-nous:**
📞 +237 6 XX XX XX XX
📧 support@djobea.ai

Je m'excuse pour le dérangement ! 🙏
        """
        
        return {
            'response': response.strip(),
            'request_complete': False,
            'suggestions': ["Aide", "Contact", "Réessayer"]
        }
    
    # Helper methods
    async def _get_or_create_user(self, user_identifier: str) -> User:
        """Get or create user"""
        # Check if user exists
        user = self.db.query(User).filter(User.phone_number == user_identifier).first()
        
        if not user:
            # Create new user
            user = User(
                phone_number=user_identifier,
                whatsapp_id=user_identifier,
                name=f"User {user_identifier[-4:]}"
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        
        return user
    
    async def _get_conversation_history(self, user_identifier: str) -> List[Dict]:
        """Get conversation history"""
        # Implementation would fetch from database
        return []
    
    async def _log_conversation(self, user_identifier: str, message: str, response: str, analysis: Dict):
        """Log conversation"""
        # Implementation would save to database
        pass