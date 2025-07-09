"""
Natural Response Generator for Djobea AI
Generates human-like, contextually appropriate responses that hide system complexity
"""

import asyncio
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.config import get_settings
from app.services.ai_service import AIService
from app.utils.conversation_state import ConversationState
from loguru import logger

settings = get_settings()


class NaturalResponseGenerator:
    """
    Generates natural, contextual responses that feel human and hide system operations
    Adapts tone and content based on conversation context and user preferences
    """
    
    def __init__(self):
        self.ai_service = AIService()
        
        # Cameroon-specific response templates
        self.response_templates = {
            "greeting": [
                "Bonjour ! Je suis votre assistant Djobea AI pour les services à domicile. Comment puis-je vous aider aujourd'hui ?",
                "Salut ! Djobea AI à votre service. De quel problème domestique puis-je m'occuper pour vous ?",
                "Bonsoir ! C'est Djobea AI, votre solution pour tous vos besoins de services à domicile.",
            ],
            "service_acknowledgment": [
                "Je comprends votre problème de {service_type}. Laissez-moi vous trouver le bon prestataire.",
                "D'accord, un souci de {service_type}. Je vais m'en occuper tout de suite.",
                "Parfait, {service_type} - je connais d'excellents prestataires pour ça.",
            ],
            "information_gathering": [
                "Pour mieux vous aider, pouvez-vous me dire où vous vous trouvez exactement ?",
                "Décrivez-moi un peu plus le problème pour que je trouve le spécialiste qu'il vous faut.",
                "Dans quel quartier êtes-vous ? Et pouvez-vous me donner plus de détails ?",
            ],
            "confirmation": [
                "Parfait ! Je recherche un prestataire disponible pour vous.",
                "C'est noté ! Je vous trouve quelqu'un de compétent dans les minutes qui viennent.",
                "Très bien, je m'occupe de votre demande immédiatement.",
            ],
            "status_updates": [
                "Je suis en train de contacter des prestataires dans votre secteur...",
                "Recherche en cours... Je vous tiens au courant dès que j'ai du nouveau.",
                "J'ai trouvé plusieurs prestataires, je leur transmets votre demande maintenant.",
            ],
            "provider_found": [
                "Excellente nouvelle ! {provider_name} peut intervenir chez vous.",
                "J'ai trouvé ! {provider_name} est disponible et accepte votre demande.",
                "Parfait ! {provider_name} va s'occuper de votre problème.",
            ],
            "emergency_response": [
                "Je comprends l'urgence ! Je contacte immédiatement nos prestataires les plus rapides.",
                "Situation d'urgence notée ! Je traite votre demande en priorité absolue.",
                "C'est urgent, je m'en occupe tout de suite ! Recherche prioritaire en cours...",
            ],
            "no_provider": [
                "Je n'ai pas trouvé de prestataire disponible pour le moment. Puis-je noter votre demande pour plus tard ?",
                "Tous nos prestataires semblent occupés. Voulez-vous que je continue à chercher ?",
                "Aucun prestataire disponible immédiatement. Je peux programmer pour plus tard si vous voulez.",
            ],
            "cancellation_confirmed": [
                "D'accord, j'annule votre demande. Pas de problème !",
                "Demande annulée comme demandé. N'hésitez pas si vous avez besoin d'aide plus tard.",
                "C'est fait, votre demande est annulée. Je reste disponible si besoin.",
            ],
            "general_help": [
                "Je peux vous aider avec la plomberie, l'électricité, ou la réparation d'électroménager. Que puis-je faire pour vous ?",
                "Djobea AI couvre tous vos besoins : plomberie, électricité, électroménager. Dites-moi tout !",
                "Services à domicile - plomberie, électricité, réparations - je suis là pour vous aider !",
            ]
        }
        
        # Contextual modifiers for natural variation
        self.time_based_greetings = {
            "morning": ["Bonjour", "Bon matin"],
            "afternoon": ["Bonjour", "Bonsoir"],
            "evening": ["Bonsoir", "Salut"],
            "night": ["Bonsoir", "Salut"]
        }
        
        # Urgency level modifiers
        self.urgency_modifiers = {
            "low": ["quand vous avez le temps", "pas pressé", "à votre convenance"],
            "normal": ["dès que possible", "dans les meilleurs délais"],
            "high": ["rapidement", "assez vite", "dans l'heure si possible"],
            "urgent": ["immédiatement", "tout de suite", "en urgence absolue"]
        }
    
    async def generate_natural_response(
        self, 
        intent_analysis: Dict[str, Any],
        conversation_state: ConversationState,
        processing_result: Dict[str, Any],
        user_message: str
    ) -> str:
        """
        Generate contextually appropriate, natural response based on intent and results
        """
        
        intent = intent_analysis.get("primary_intent", "general_inquiry")
        
        logger.info(f"Response generator - intent: {intent}, action: {processing_result.get('action')}")
        
        try:
            if intent == "new_service_request":
                return await self._handle_service_request_response(
                    intent_analysis, processing_result, conversation_state
                )
            
            elif intent == "status_inquiry":
                return self._handle_status_response(processing_result, conversation_state)
            
            elif intent == "cancel_request":
                return self._handle_cancellation_response(processing_result)
            
            elif intent == "emergency":
                return await self._handle_emergency_response(
                    intent_analysis, processing_result, conversation_state
                )
            
            elif intent == "continue_previous":
                return await self._handle_continuation_response(
                    intent_analysis, processing_result, conversation_state
                )
            
            else:
                return self._handle_general_response(user_message, conversation_state)
        
        except Exception as e:
            logger.error(f"Error generating natural response: {e}")
            return self._get_fallback_response()
    
    async def _handle_service_request_response(
        self, 
        intent_analysis: Dict[str, Any],
        processing_result: Dict[str, Any],
        conversation_state: ConversationState
    ) -> str:
        """Handle responses for service requests"""
        
        action = processing_result.get("action", "")
        service_info = processing_result.get("service_info", {})
        partial_data = processing_result.get("partial_data", {})
        missing_fields = processing_result.get("missing_fields", [])
        
        logger.info(f"Service request response - action: {action}, service_info: {service_info}, partial_data: {partial_data}")
        
        if action in ["continue_conversation", "continue_gathering"]:
            # Need more information - use partial_data if service_info is empty
            data_to_use = service_info if service_info else partial_data
            logger.info(f"Generating information request for missing fields: {missing_fields}")
            return await self._generate_information_request(missing_fields, data_to_use, conversation_state)
        
        elif action in ["request_created", "request_completed"]:
            # Service request successfully created
            service_type = service_info.get("service_type", "service")
            
            # Generate natural confirmation with hidden provider search
            confirmations = [
                f"Parfait ! J'ai bien compris votre problème de {service_type}. Je vous trouve un prestataire compétent immédiatement.",
                f"C'est noté ! Votre demande de {service_type} est en cours de traitement. Recherche du meilleur prestataire...",
                f"Très bien ! Je m'occupe de votre {service_type} tout de suite. Quelques secondes le temps de trouver la bonne personne."
            ]
            
            confirmation = random.choice(confirmations)
            
            # Add pricing estimate naturally
            pricing = self._get_pricing_estimate(service_type)
            if pricing:
                confirmation += f"\n\nPour info, ce type d'intervention coûte généralement entre {pricing}."
            
            # Add timeline expectation
            confirmation += "\n\nJe vous tiens au courant dès qu'un prestataire accepte votre demande !"
            
            return confirmation
        
        else:
            return "Je prends en compte votre demande. Un moment s'il vous plaît..."
    
    async def _generate_information_request(
        self, 
        missing_fields: List[str],
        partial_info: Dict[str, Any],
        conversation_state: ConversationState
    ) -> str:
        """Generate natural request for missing information"""
        
        # Use AI to generate contextual questions
        context_prompt = f"""
        L'utilisateur a fait une demande de service mais il manque des informations.
        
        Informations déjà collectées: {partial_info}
        Informations manquantes: {missing_fields}
        
        Génère une question naturelle et amicale pour obtenir les informations manquantes.
        Adapte ton ton au contexte camerounais et reste conversationnel.
        
        Évite les formulations techniques ou robotiques.
        """
        
        user_prompt = """
        Génère une seule question naturelle pour compléter la demande de service.
        Sois chaleureux et professionnel comme un vrai assistant humain.
        """
        
        try:
            ai_response = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=context_prompt,
                max_tokens=200,
                temperature=0.7
            )
            
            return ai_response
            
        except Exception:
            # Fallback to template-based responses
            if "location" in missing_fields:
                return random.choice([
                    "Dans quel quartier de Douala êtes-vous ? Ça m'aide à trouver le prestataire le plus proche.",
                    "Pouvez-vous me dire où vous vous trouvez exactement ? Bonamoussadi, Akwa, ou autre ?",
                    "Votre adresse ou quartier, s'il vous plaît ? C'est pour vous envoyer quelqu'un de disponible près de chez vous."
                ])
            
            elif "service_type" in missing_fields:
                return random.choice([
                    "De quel type de problème s'agit-il exactement ? Plomberie, électricité, ou électroménager ?",
                    "Quel service vous faut-il ? Je peux vous aider avec la plomberie, l'électricité, ou les réparations d'appareils.",
                    "Précisez-moi le type de problème pour que je trouve le bon spécialiste !"
                ])
            
            elif "description" in missing_fields:
                return random.choice([
                    "Pouvez-vous me décrire le problème plus en détail ?",
                    "Dites-moi ce qui ne va pas exactement, ça m'aide à bien orienter.",
                    "Décrivez-moi un peu plus la situation pour que je trouve la bonne solution."
                ])
            
            else:
                return "Pouvez-vous me donner quelques détails supplémentaires pour que je puisse mieux vous aider ?"
    
    def _handle_status_response(
        self, 
        processing_result: Dict[str, Any],
        conversation_state: ConversationState
    ) -> str:
        """Handle status inquiry responses"""
        
        action = processing_result.get("action", "")
        
        if action == "no_active_requests":
            return random.choice([
                "Vous n'avez pas de demande en cours actuellement. Voulez-vous faire une nouvelle demande ?",
                "Aucune demande active pour le moment. De quoi avez-vous besoin aujourd'hui ?",
                "Pas de service en cours. Je peux vous aider avec un nouveau problème si vous voulez !"
            ])
        
        elif action == "status_provided":
            requests = processing_result.get("requests", [])
            
            if not requests:
                return "Aucune demande en cours pour le moment."
            
            # Generate natural status update
            request = requests[0]  # Most recent
            status = request.get("status", "")
            service_type = request.get("service_type", "service")
            
            status_messages = {
                "PENDING": f"Votre demande de {service_type} est en cours de traitement. Je recherche le meilleur prestataire pour vous.",
                "PROVIDER_NOTIFIED": f"J'ai trouvé des prestataires pour votre {service_type} et je leur ai transmis votre demande. Attente de leur réponse...",
                "ASSIGNED": f"Excellente nouvelle ! Un prestataire a accepté votre demande de {service_type}. Il va vous contacter directement.",
                "IN_PROGRESS": f"Votre service de {service_type} est en cours. Le prestataire devrait être chez vous ou en route."
            }
            
            return status_messages.get(status, f"Votre demande de {service_type} est en cours de traitement.")
    
    def _handle_cancellation_response(self, processing_result: Dict[str, Any]) -> str:
        """Handle cancellation responses"""
        
        action = processing_result.get("action", "")
        
        if action == "no_cancellable_requests":
            return random.choice([
                "Vous n'avez pas de demande en cours à annuler. Tout est déjà terminé !",
                "Aucune demande active à annuler pour le moment.",
                "Pas de service en cours d'annulation possible."
            ])
        
        elif action == "request_cancelled":
            return random.choice(self.response_templates["cancellation_confirmed"]) + \
                   " Si vous changez d'avis, n'hésitez pas à refaire une demande !"
        
        return "D'accord, je m'occupe de l'annulation."
    
    async def _handle_emergency_response(
        self, 
        intent_analysis: Dict[str, Any],
        processing_result: Dict[str, Any],
        conversation_state: ConversationState
    ) -> str:
        """Handle emergency situation responses"""
        
        service_type = processing_result.get("service_info", {}).get("service_type", "service")
        
        emergency_response = random.choice(self.response_templates["emergency_response"])
        
        # Add specific emergency context
        emergency_additions = [
            f"Votre urgence de {service_type} est ma priorité absolue !",
            f"Je traite votre {service_type} urgent immédiatement.",
            f"Situation d'urgence {service_type} - recherche prioritaire activée !"
        ]
        
        full_response = emergency_response + "\n\n" + random.choice(emergency_additions)
        
        # Add expected timeline for emergencies
        full_response += "\n\nPour les urgences, nos prestataires répondent généralement dans les 5-10 minutes. Je vous tiens informé !"
        
        return full_response
    
    async def _handle_continuation_response(
        self, 
        intent_analysis: Dict[str, Any],
        processing_result: Dict[str, Any],
        conversation_state: ConversationState
    ) -> str:
        """Handle conversation continuation responses"""
        
        action = processing_result.get("action", "")
        
        if action == "continue_gathering":
            missing_fields = processing_result.get("missing_fields", [])
            partial_data = processing_result.get("partial_data", {})
            return await self._generate_information_request(missing_fields, partial_data, conversation_state)
        
        elif action == "request_completed":
            service_info = processing_result.get("service_info", {})
            service_type = service_info.get("service_type", "service")
            
            return f"Parfait ! Maintenant j'ai tout ce qu'il faut pour votre {service_type}. " + \
                   "Je lance la recherche de prestataire immédiatement !"
        
        return "Merci pour ces précisions. Je continue le traitement de votre demande."
    
    def _handle_general_response(self, user_message: str, conversation_state: ConversationState) -> str:
        """Handle general inquiries and small talk"""
        
        # Check if it's a greeting
        greeting_indicators = ["bonjour", "salut", "hello", "bonsoir", "hi"]
        if any(indicator in user_message.lower() for indicator in greeting_indicators):
            return self._get_contextual_greeting()
        
        # Check if asking about services
        service_indicators = ["service", "aide", "help", "problème", "problem", "besoin", "need"]
        if any(indicator in user_message.lower() for indicator in service_indicators):
            return random.choice(self.response_templates["general_help"])
        
        # Default friendly response
        return random.choice([
            "Je suis là pour vous aider avec tous vos besoins de services à domicile. Que puis-je faire pour vous ?",
            "Djobea AI à votre service ! Plomberie, électricité, électroménager - dites-moi tout !",
            "Comment puis-je vous aider aujourd'hui ? Je m'occupe de tous vos services à domicile."
        ])
    
    def _get_contextual_greeting(self) -> str:
        """Get greeting based on time of day"""
        
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 12:
            time_period = "morning"
        elif 12 <= current_hour < 17:
            time_period = "afternoon"
        elif 17 <= current_hour < 22:
            time_period = "evening"
        else:
            time_period = "night"
        
        greeting = random.choice(self.time_based_greetings[time_period])
        
        return f"{greeting} ! Je suis votre assistant Djobea AI pour les services à domicile. " + \
               "Comment puis-je vous aider aujourd'hui ?"
    
    def _get_pricing_estimate(self, service_type: str) -> Optional[str]:
        """Get pricing estimate for service type"""
        
        pricing = settings.service_pricing.get(service_type)
        if pricing:
            min_price = pricing["min"]
            max_price = pricing["max"]
            return f"{min_price:,} - {max_price:,} XAF"
        
        return None
    
    def _get_fallback_response(self) -> str:
        """Fallback response when generation fails"""
        
        return random.choice([
            "Je suis là pour vous aider ! Pouvez-vous me dire de quel service vous avez besoin ?",
            "Djobea AI à votre service. Décrivez-moi votre problème et je vous trouve la solution !",
            "Bonjour ! Comment puis-je vous aider avec vos services à domicile aujourd'hui ?"
        ])
    
    def _get_fallback_response(self) -> str:
        """Fallback response when generation fails"""
        
        return random.choice([
            "Je suis là pour vous aider ! Pouvez-vous me dire de quel service vous avez besoin ?",
            "Djobea AI à votre service. Décrivez-moi votre problème et je vous trouve la solution !",
            "Bonjour ! Comment puis-je vous aider avec vos services à domicile aujourd'hui ?"
        ])