"""
Djobea AI Conversation Manager - Sprint 2
Handles intelligent conversation understanding and information extraction
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json
import re
from dataclasses import dataclass
from anthropic import Anthropic
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.database_models import ActionType, User, Conversation
from app.models.cultural_models import EmotionalProfile, ConversationEmotion
from app.services.emotional_intelligence_service import EmotionalIntelligenceService
from app.services.personalization_service import PersonalizationService
from loguru import logger
settings = get_settings()

@dataclass
class RequestInfo:
    """Structured information extracted from conversation"""
    service_type: Optional[str] = None  # plomberie, électricité, réparation électroménager
    location: Optional[str] = None      # address in Bonamoussadi
    description: Optional[str] = None   # problem details
    urgency: Optional[str] = None       # urgent, cet après-midi, demain, etc.
    confidence_score: float = 0.0       # extraction confidence
    
    # Enhanced scheduling information
    scheduling_preference: Optional[str] = None  # URGENT, TODAY, TOMORROW_MORNING, etc.
    preferred_time_details: Optional[str] = None # specific time details from user
    
    # Enhanced location information
    landmark_references: Optional[List[str]] = None  # mentioned landmarks
    location_confidence: float = 0.0  # location recognition confidence

    def is_complete(self) -> bool:
        """Check if all required information is present"""
        return all([
            self.service_type,
            self.location,
            self.description,
            self.urgency or self.scheduling_preference  # Either old urgency or new scheduling
        ])

    def missing_fields(self) -> List[str]:
        """Get list of missing required fields"""
        missing = []
        if not self.service_type: missing.append("service_type")
        if not self.location: missing.append("location")
        if not self.description: missing.append("description") 
        if not (self.urgency or self.scheduling_preference): missing.append("timing")
        return missing


class DjobeaConversationManager:
    """
    LangChain-inspired conversation manager for Djobea AI
    Handles multi-turn conversations and intelligent extraction
    """
    
    def __init__(self, emotional_intelligence_service: Optional[EmotionalIntelligenceService] = None):
        """Initialize conversation manager with Claude API and emotional intelligence"""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.conversation_memory: Dict[str, List[Dict]] = {}
        self.request_state: Dict[str, RequestInfo] = {}  # Track accumulated request info per user
        self.emotional_intelligence = emotional_intelligence_service
        self.personalization_service = PersonalizationService()
        
        # Comprehensive Cameroon-specific expressions
        self.local_expressions = {
            # Electrical issues
            "courant a jump": "panne électrique",
            "light don go": "coupure électricité", 
            "no current": "pas d'électricité",
            "current no dey": "pas d'électricité",
            
            # Water issues
            "coule-coule": "fuite d'eau",
            "wata no dey comot": "pas d'eau",
            "pipe don burst": "canalisation cassée",
            "water no dey flow": "pas d'eau",
            
            # General expressions
            "don spoil": "cassé",
            "no dey work": "ne marche pas",
            "i want make": "je veux que"
        }
        
    async def process_message_with_emotions(
        self, 
        db: Session, 
        user_id: str, 
        message: str, 
        conversation_id: Optional[int] = None
    ) -> Tuple[str, RequestInfo, Optional[ConversationEmotion]]:
        """
        Process incoming message with emotional intelligence and cultural awareness
        
        Args:
            db: Database session
            user_id: WhatsApp user identifier
            message: User message content
            conversation_id: Database conversation ID
            
        Returns:
            Tuple of (bot_response, extracted_request_info, emotion_analysis)
        """
        try:
            # Normalize message for better understanding
            normalized_message = self._normalize_message(message)
            
            # Get conversation history
            history = self.conversation_memory.get(user_id, [])
            
            # Add current message to history
            history.append({
                "role": "user",
                "content": normalized_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Analyze emotional content if emotional intelligence is available
            conversation_emotion = None
            if self.emotional_intelligence and conversation_id:
                conversation_emotion = await self.emotional_intelligence.analyze_conversation_emotion(
                    db, conversation_id, message, int(user_id)
                )
            
            # Extract request information with accumulation
            request_info = self._extract_and_accumulate_info(user_id, history)
            
            # Generate culturally and emotionally appropriate response
            if self.emotional_intelligence and conversation_emotion:
                # Check for emergency situations
                is_emergency = await self.emotional_intelligence.detect_emergency_situation(
                    message, conversation_emotion
                )
                
                if is_emergency:
                    response = await self.emotional_intelligence.generate_emotionally_aware_response(
                        db, int(user_id), "emergency"
                    )
                else:
                    # Generate response based on emotional context
                    situation = "service_request" if request_info.service_type else "general_conversation"
                    response = await self.emotional_intelligence.generate_emotionally_aware_response(
                        db, int(user_id), situation, conversation_emotion=conversation_emotion
                    )
            else:
                # Fallback to standard response generation
                response = self.generate_response(history, request_info)
            
            # Apply personalization to the response
            if self.personalization_service:
                try:
                    # Learn from this conversation
                    await self.personalization_service.learn_from_conversation(
                        db, int(user_id), {
                            'message': message,
                            'response': response,
                            'conversation_id': conversation_id,
                            'request_info': request_info.__dict__ if request_info else None
                        }
                    )
                    
                    # Personalize the response
                    personalized_response = await self.personalization_service.personalize_message(
                        db, int(user_id), response, {
                            'request_info': request_info.__dict__ if request_info else None,
                            'emotional_context': conversation_emotion.__dict__ if conversation_emotion else None,
                            'conversation_type': 'service_request' if request_info and request_info.service_type else 'general'
                        }
                    )
                    response = personalized_response
                except Exception as e:
                    logger.error(f"Personalization error: {e}")
                    # Continue with original response if personalization fails
            
            # Add bot response to history
            history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update memory
            self.conversation_memory[user_id] = history[-10:]  # Keep last 10 messages
            
            logger.info(f"Processed message for user {user_id}, confidence: {request_info.confidence_score}")
            
            return response, request_info, conversation_emotion
            
        except Exception as e:
            logger.error(f"Error processing message with emotions: {str(e)}")
            return self._get_error_response(), RequestInfo(), None

    async def process_message_with_personalization(
        self, 
        db: Session, 
        user_id: str, 
        message: str
    ) -> Tuple[str, RequestInfo]:
        """
        Process message with full personalization and learning
        
        Args:
            db: Database session
            user_id: WhatsApp user identifier
            message: User message content
            
        Returns:
            Tuple of (personalized_response, extracted_request_info)
        """
        try:
            # Normalize message for better understanding
            normalized_message = self._normalize_message(message)
            
            # Get conversation history from database (full session context) 
            history = self._load_conversation_history_from_db(db, user_id)
            
            # Add current message to history
            history.append({
                "role": "user",
                "content": normalized_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Extract request information with accumulation
            request_info = self._extract_and_accumulate_info(user_id, history)
            
            # Generate base response with database interaction logic
            base_response = await self._generate_response_with_db_logic(db, history, request_info, user_id)
            
            # Get user numeric ID for personalization
            user_numeric_id = self._extract_user_numeric_id(db, user_id)
            
            if user_numeric_id:
                try:
                    # Apply personalization to response
                    personalized_response = await self.personalization_service.personalize_message(
                        db=db,
                        user_id=user_numeric_id,
                        base_message=base_response,
                        context={
                            'conversation_history': history,
                            'request_info': request_info.__dict__,
                            'message_type': 'service_response',
                            'confidence_score': request_info.confidence_score
                        }
                    )
                    
                    # Learn from this conversation
                    await self.personalization_service.learn_from_conversation(
                        db=db,
                        user_id=user_numeric_id,
                        conversation={
                            'user_message': normalized_message,
                            'ai_response': personalized_response,
                            'request_info': request_info.__dict__,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                    
                    response = personalized_response
                except Exception as personalization_error:
                    logger.error(f"Personalization failed: {personalization_error}")
                    response = base_response
            else:
                response = base_response
            
            # Add bot response to history
            history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update memory
            self.conversation_memory[user_id] = history[-10:]  # Keep last 10 messages
            
            logger.info(f"Processed personalized message for user {user_id}, confidence: {request_info.confidence_score}")
            
            return response, request_info
            
        except Exception as e:
            logger.error(f"Error processing message with personalization: {str(e)}")
            # Fallback to non-personalized processing
            return self.process_message(user_id, message)

    def process_message(self, user_id: str, message: str) -> Tuple[str, RequestInfo]:
        """
        Process incoming message and return response with extracted info (backward compatibility)
        
        Args:
            user_id: WhatsApp user identifier
            message: User message content
            
        Returns:
            Tuple of (bot_response, extracted_request_info)
        """
        try:
            # Normalize message for better understanding
            normalized_message = self._normalize_message(message)
            
            # Get conversation history
            history = self.conversation_memory.get(user_id, [])
            
            # Add current message to history
            history.append({
                "role": "user",
                "content": normalized_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Extract request information with accumulation
            request_info = self._extract_and_accumulate_info(user_id, history)
            
            # Generate appropriate response
            response = self.generate_response(history, request_info)
            
            # Add bot response to history
            history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update memory
            self.conversation_memory[user_id] = history[-10:]  # Keep last 10 messages
            
            logger.info(f"Processed message for user {user_id}, confidence: {request_info.confidence_score}")
            
            return response, request_info
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return self._get_error_response(), RequestInfo()
    
    def extract_request_info(self, conversation_history: List[Dict]) -> RequestInfo:
        """
        Extract service request information from conversation using Claude
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            RequestInfo object with extracted data
        """
        try:
            # Build conversation context
            context = self._build_conversation_context(conversation_history)
            
            extraction_prompt = f"""
Tu es un assistant expert pour extraire des informations de demandes de services à domicile au Cameroun.

CONTEXTE: Djobea AI connecte les clients aux prestataires à Douala (quartier Bonamoussadi).

SERVICES DISPONIBLES:
- plomberie (robinet, tuyaux, WC, douche, évacuation)
- électricité (prises, câbles, disjoncteur, éclairage, "courant")
- réparation électroménager (frigo, machine à laver, climatiseur, TV)

CONVERSATION COMPLÈTE:
{context}

EXPRESSIONS LOCALES À COMPRENDRE:
- "courant a jump" = panne électrique
- "coule-coule" = fuite d'eau  
- "no current" = pas d'électricité
- "wata no dey comot" = pas d'eau
- "light don go" = coupure électricité

PRÉFÉRENCES HORAIRES À DÉTECTER:
- "dans l'heure", "urgent", "maintenant" → URGENT
- "aujourd'hui", "cet après-midi" → TODAY
- "demain matin" → TOMORROW_MORNING
- "demain après-midi" → TOMORROW_AFTERNOON
- "cette semaine", "quand vous pouvez" → THIS_WEEK
- "weekend", "samedi", "dimanche" → WEEKEND

LANDMARKS BONAMOUSSADI À RECONNAÎTRE:
- Station Total, Marché Central, Carrefour, Hôpital, École, Pharmacie
- Banque Atlantique, Mosquée, Église, Rond-point
- "près du marché", "derrière la pharmacie", "côté hôpital", "près de Total"

INSTRUCTIONS CRITIQUES - TRÈS IMPORTANT:
1. ACCUMULE TOUTES LES INFORMATIONS de la conversation COMPLÈTE - ne perds JAMAIS les informations déjà fournies
2. Si le client mentionne "électroménager", "électricité", "plomberie" → GARDE définitivement dans service_type
3. Si le client dit "Bonamoussadi", "près de Total Bonamoussadi", "Douala centre" → GARDE définitivement comme location
4. Si le client dit "urgent", "maintenant", "aujourd'hui" → GARDE définitivement comme urgency
5. ÉVITE ABSOLUMENT de redemander des informations déjà fournies dans la conversation
6. Merge TOUJOURS les nouvelles informations avec les anciennes - ne remplace JAMAIS par null

EXEMPLE D'ACCUMULATION CORRECTE:
- Message 1: "J'ai un problème électrique" → service_type: "électricité"  
- Message 2: "Je suis à Bonamoussadi" → service_type: "électricité", location: "Bonamoussadi"
- Message 3: "Mon frigo ne marche pas" → service_type: "réparation électroménager", location: "Bonamoussadi"

TÂCHE: Extrais ces informations au format JSON en ACCUMULANT tout de la conversation:
{{
    "service_type": "plomberie|électricité|réparation électroménager|null",
    "location": "adresse précise à Bonamoussadi ou null",
    "description": "description détaillée du problème ou null", 
    "urgency": "urgent|cet après-midi|demain|cette semaine|null",
    "scheduling_preference": "URGENT|TODAY|TOMORROW_MORNING|TOMORROW_AFTERNOON|THIS_WEEK|WEEKEND|null",
    "preferred_time_details": "détails spécifiques horaires mentionnés ou null",
    "landmark_references": ["liste des landmarks mentionnés"],
    "location_confidence": 0.0-1.0,
    "confidence_score": 0.0-1.0
}}

ACCUMULE ET PRESERVE toutes les informations données dans la conversation COMPLÈTE, pas seulement le dernier message.
"""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": extraction_prompt}]
            )
            
            # Parse JSON response from Claude
            response_text = response.content[0].text if response.content else ""
            
            if not response_text.strip():
                logger.warning("Empty response from Claude, using default RequestInfo")
                return RequestInfo()
            
            # Clean and extract JSON
            response_text = response_text.strip()
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '{' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                response_text = response_text[json_start:json_end]
            
            try:
                extracted_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}, response: {response_text[:200]}")
                return RequestInfo()
            
            return RequestInfo(
                service_type=extracted_data.get("service_type"),
                location=extracted_data.get("location"),
                description=extracted_data.get("description"),
                urgency=extracted_data.get("urgency"),
                confidence_score=float(extracted_data.get("confidence_score", 0.0)),
                scheduling_preference=extracted_data.get("scheduling_preference"),
                preferred_time_details=extracted_data.get("preferred_time_details"),
                landmark_references=extracted_data.get("landmark_references", []),
                location_confidence=float(extracted_data.get("location_confidence", 0.0))
            )
            
        except Exception as e:
            logger.error(f"Error extracting request info: {str(e)}")
            return RequestInfo()
    
    def generate_response(self, conversation_history: List[Dict], request_info: RequestInfo) -> str:
        """
        Generate contextual response based on conversation and extracted info
        
        Args:
            conversation_history: Conversation messages
            request_info: Currently extracted information
            
        Returns:
            Generated response string
        """
        try:
            if request_info.is_complete():
                # Check if this is a follow-up message after request completion
                recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
                has_recent_completion = any("recherche maintenant un prestataire" in msg.get("content", "").lower() 
                                          or "demande est en cours" in msg.get("content", "").lower()
                                          or "je recherche maintenant" in msg.get("content", "").lower()
                                          or "en cours de traitement" in msg.get("content", "").lower()
                                          for msg in recent_messages if msg.get("role") == "assistant")
                
                # Debug logging
                logger.info(f"Debug - Recent messages count: {len(recent_messages)}")
                logger.info(f"Debug - Has recent completion: {has_recent_completion}")
                if recent_messages:
                    for i, msg in enumerate(recent_messages):
                        if msg.get("role") == "assistant":
                            content_snippet = msg.get("content", "")[:100]
                            logger.info(f"Debug - Assistant message {i}: {content_snippet}...")
                
                if has_recent_completion and conversation_history:
                    # Get the last user message for continuous conversation
                    last_user_message = ""
                    for msg in reversed(conversation_history):
                        if msg.get("role") == "user":
                            last_user_message = msg.get("content", "")
                            break
                    
                    # Generate continuous conversation response
                    return self._generate_continuous_response(request_info, last_user_message)
                else:
                    # First time request completion
                    return self._generate_confirmation_response(request_info)
            else:
                return self._generate_question_response(conversation_history, request_info)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._get_error_response()
    
    def _generate_continuous_response(self, request_info: RequestInfo, last_user_message: str) -> str:
        """Generate continuous conversation response for follow-up messages after request completion"""
        try:
            # Check if user message is a simple acknowledgment or follow-up
            acknowledgment_words = ['ok', 'oui', 'd\'accord', 'bien', 'merci', 'parfait', 'entendu', 'et alors', 'alors']
            is_acknowledgment = any(word in last_user_message.lower() for word in acknowledgment_words) and len(last_user_message.split()) <= 3
            
            if is_acknowledgment:
                # Generate status update and provider suggestions
                service_messages = {
                    'plomberie': {
                        'action': 'recherchons activement un plombier',
                        'tip': '💡 En attendant, si c\'est une fuite importante, n\'hésitez pas à fermer l\'arrivée d\'eau principale pour éviter les dégâts.'
                    },
                    'électricité': {
                        'action': 'recherchons activement un électricien',
                        'tip': '💡 En attendant, évitez de toucher aux fils électriques et vérifiez que le disjoncteur n\'a pas sauté.'
                    },
                    'réparation électroménager': {
                        'action': 'recherchons activement un technicien en électroménager',
                        'tip': '💡 En attendant, débranchez l\'appareil si possible pour éviter d\'aggraver le problème.'
                    }
                }
                
                service_info = service_messages.get(request_info.service_type, service_messages['plomberie'])
                
                response = f"""🔍 **Recherche en cours...**
                
Nous {service_info['action']} disponible dans votre secteur {request_info.location}.

⏱️ **Status actuel :**
• Nous contactons nos meilleurs prestataires de la zone
• Vous devriez recevoir une réponse sous 15-30 minutes
• Dès qu'un professionnel accepte, vous recevrez ses informations

{service_info['tip']}

💬 N'hésitez pas à me poser des questions en attendant !"""
                
                return response
            else:
                # Handle specific questions or concerns
                return f"""Je continue à rechercher un prestataire pour votre demande de {request_info.service_type} à {request_info.location}.

Que puis-je vous expliquer de plus sur le processus ? Vous recevrez une notification dès qu'un professionnel accepte votre demande."""
                
        except Exception as e:
            logger.error(f"Error generating continuous response: {str(e)}")
            return "Nous recherchons activement un prestataire disponible dans votre secteur. Vous recevrez une notification dès qu'un professionnel accepte votre demande."

    def _normalize_message(self, message: str) -> str:
        """Normalize message by handling local expressions and typos"""
        normalized = message.lower().strip()
        
        # Replace local expressions
        for local_expr, standard_expr in self.local_expressions.items():
            normalized = normalized.replace(local_expr, standard_expr)
        
        # Basic typo corrections for common WhatsApp abbreviations
        typo_corrections = {
            "slt": "salut",
            "bjr": "bonjour", 
            "stp": "s'il te plaît",
            "svp": "s'il vous plaît",
            "pb": "problème",
            "qd": "quand",
            "tt": "tout",
            "pr": "pour"
        }
        
        for typo, correction in typo_corrections.items():
            normalized = re.sub(rf'\b{typo}\b', correction, normalized)
        
        return normalized
    
    def detect_quick_action(self, message: str) -> Optional[ActionType]:
        """Detect if message contains a quick action command"""
        message_lower = message.lower().strip()
        
        # Quick action detection mapping
        action_patterns = {
            # Status checking - multiple patterns
            ActionType.STATUS_CHECK: [
                r'\b(statut|status|état)\b',
                r'\b(où\s+en\s+est|avancement)\b',
                r'\b1\b',
                r'\b(comment\s+ça\s+va|nouvelles)\b'
            ],
            
            # Request modification
            ActionType.MODIFY_REQUEST: [
                r'\b(modifier|changer|change|modify)\b',
                r'\b2\b',
                r'\b(correction|corriger)\b'
            ],
            
            # Request cancellation
            ActionType.CANCEL_REQUEST: [
                r'\b(annuler|cancel|stop|arrêter)\b',
                r'\b3\b',
                r'\b(plus\s+besoin|abandon)\b'
            ],
            
            # Help request
            ActionType.HELP_REQUEST: [
                r'\b(aide|help|support|assistance)\b',
                r'\b4\b',
                r'\b(problème|pb|souci)\b'
            ],
            
            # Provider profile
            ActionType.PROVIDER_PROFILE: [
                r'\b(profil|profile|prestataire)\b',
                r'\b5\b',
                r'\b(qui\s+est|informations)\b'
            ],
            
            # Contact provider
            ActionType.CONTACT_PROVIDER: [
                r'\b(contact|contacter|appeler|call)\b',
                r'\b6\b',
                r'\b(téléphone|numéro)\b'
            ]
        }
        
        # Check for action patterns
        for action, patterns in action_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return action
        
        return None
    
    def _extract_and_accumulate_info(self, user_id: str, conversation_history: List[Dict]) -> RequestInfo:
        """
        Extract and accumulate request information from conversation
        This method preserves previously extracted information and merges it with new data
        """
        try:
            # Get existing accumulated information from conversation memory
            existing_info = self._get_accumulated_info_from_memory(user_id)
            
            # Extract new information from the conversation
            new_info = self.extract_request_info(conversation_history)
            
            # Merge information (preserve existing non-null values, update with new non-null values)
            # Use explicit checks to ensure we don't lose existing information
            service_type = new_info.service_type if new_info.service_type else existing_info.service_type
            location = new_info.location if new_info.location else existing_info.location
            description = new_info.description if new_info.description else existing_info.description
            urgency = new_info.urgency if new_info.urgency else existing_info.urgency
            scheduling_preference = new_info.scheduling_preference if new_info.scheduling_preference else existing_info.scheduling_preference
            preferred_time_details = new_info.preferred_time_details if new_info.preferred_time_details else existing_info.preferred_time_details
            
            accumulated_info = RequestInfo(
                service_type=service_type,
                location=location, 
                description=description,
                urgency=urgency,
                confidence_score=max(new_info.confidence_score, existing_info.confidence_score),
                scheduling_preference=scheduling_preference,
                preferred_time_details=preferred_time_details,
                landmark_references=(new_info.landmark_references or []) + (existing_info.landmark_references or []),
                location_confidence=max(new_info.location_confidence, existing_info.location_confidence)
            )
            
            # Remove duplicates from landmark references
            if accumulated_info.landmark_references:
                accumulated_info.landmark_references = list(set(accumulated_info.landmark_references))
            
            # Store the accumulated information in conversation memory
            self._store_accumulated_info_in_memory(user_id, accumulated_info)
            
            logger.info(f"Accumulation for user {user_id}: EXISTING({existing_info.service_type}, {existing_info.location}) + NEW({new_info.service_type}, {new_info.location}) = RESULT({accumulated_info.service_type}, {accumulated_info.location})")
            
            return accumulated_info
            
        except Exception as e:
            logger.error(f"Error accumulating request info: {e}")
            # Return existing info or empty RequestInfo as fallback
            return self.request_state.get(user_id, RequestInfo())

    def _get_accumulated_info_from_memory(self, user_id: str) -> RequestInfo:
        """Get accumulated request information from global class variable"""
        # Use a global class variable to persist across instances
        if not hasattr(DjobeaConversationManager, '_global_request_state'):
            DjobeaConversationManager._global_request_state = {}
        
        return DjobeaConversationManager._global_request_state.get(user_id, RequestInfo())
    
    def _store_accumulated_info_in_memory(self, user_id: str, accumulated_info: RequestInfo) -> None:
        """Store accumulated request information in global class variable"""
        # Use a global class variable to persist across instances
        if not hasattr(DjobeaConversationManager, '_global_request_state'):
            DjobeaConversationManager._global_request_state = {}
        
        DjobeaConversationManager._global_request_state[user_id] = accumulated_info
        
    def _build_conversation_context(self, history: List[Dict]) -> str:
        """Build formatted conversation context for prompts"""
        context_parts = []
        for msg in history[-5:]:  # Last 5 messages for context
            role = "Client" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        return "\n".join(context_parts)
    
    def _generate_confirmation_response(self, request_info: RequestInfo) -> str:
        """Generate confirmation message when all info is collected"""
        return f"""Parfait ! J'ai bien compris votre demande :

🔧 **Service** : {request_info.service_type}
📍 **Localisation** : {request_info.location}  
📝 **Problème** : {request_info.description}
⏰ **Délai** : {request_info.urgency}

Je recherche maintenant un prestataire disponible dans votre zone. Vous recevrez une notification dès qu'un professionnel accepte votre demande.

💰 **Commission Djobea** : 15% du montant de la prestation
⏱️ **Temps de réponse** : Généralement sous 30 minutes

Votre demande est en cours de traitement !"""
    
    def _generate_question_response(self, history: List[Dict], request_info: RequestInfo) -> str:
        """Generate question to collect missing information"""
        try:
            context = self._build_conversation_context(history)
            missing_fields = request_info.missing_fields()
            
            current_info = {
                "service_type": request_info.service_type,
                "location": request_info.location,
                "description": request_info.description,
                "urgency": request_info.urgency
            }
            
            question_prompt = f"""
Tu es l'assistant Djobea AI. Tu dois poser UNE question naturelle en français pour obtenir les informations manquantes.

CONVERSATION ACTUELLE:
{context}

INFORMATIONS DÉJÀ OBTENUES:
{json.dumps(current_info, indent=2)}

INFORMATIONS MANQUANTES: {', '.join(missing_fields)}

RÈGLES:
1. Pose UNE seule question claire et naturelle
2. Sois chaleureux et professionnel  
3. Utilise le contexte camerounais (Bonamoussadi, Douala)
4. Si c'est le premier message, commence par saluer
5. Donne des exemples si nécessaire

EXEMPLES DE QUESTIONS SELON CE QUI MANQUE:
- Service manquant: "Quel type de service vous faut-il ? (plomberie, électricité, ou réparation électroménager)"
- Location manquante: "Pouvez-vous me donner votre adresse précise à Bonamoussadi ?"
- Description manquante: "Pouvez-vous me décrire exactement le problème ?"  
- Délai manquant: "Pour quand souhaitez-vous l'intervention ? (urgent, cet après-midi, demain...)"

Génère UNE question appropriée:
"""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": question_prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            return "Bonjour ! Comment puis-je vous aider avec vos besoins en plomberie, électricité ou réparation électroménager à Bonamoussadi ?"
    
    def _extract_user_numeric_id(self, db: Session, user_id: str) -> Optional[int]:
        """Extract numeric user ID from database for personalization with error recovery"""
        try:
            # For web sessions, skip database queries to avoid connection issues
            if user_id.startswith('web_'):
                logger.debug(f"Web session user {user_id}, skipping database lookup")
                return None
                
            user = db.query(User).filter(User.phone_number == user_id).first()
            if not user:
                # Check if user_id is already numeric
                if user_id.isdigit():
                    return int(user_id)
                return None
            return user.id
        except Exception as e:
            logger.error(f"Error extracting user numeric ID: {e}")
            # Attempt to recover from database connection issues
            try:
                db.rollback()
                logger.info("Database session rolled back after error")
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
            return None
    
    def _get_error_response(self) -> str:
        """Fallback response for errors"""
        return """Désolé, j'ai rencontré un problème technique. 

Pouvez-vous me dire :
1. Quel service vous faut-il ? (plomberie, électricité, réparation électroménager)
2. Votre adresse à Bonamoussadi ?
3. Le problème exact ?
4. Pour quand ? (urgent, aujourd'hui, demain...)

Je vous aiderai dès que possible !"""
    
    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Get conversation history for a user"""
        return self.conversation_memory.get(user_id, [])
    
    def _load_conversation_history_from_db(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        Load full conversation history from database for complete session context
        
        Args:
            db: Database session
            user_id: WhatsApp user identifier
            
        Returns:
            List of conversation messages with role and content
        """
        try:
            from app.models.database_models import User, Conversation
            
            # Get user from database
            user = db.query(User).filter(User.phone_number == user_id).first()
            if not user:
                return []
            
            # Get all conversations for this user (recent session)
            conversations = (
                db.query(Conversation)
                .filter(Conversation.user_id == user.id)
                .order_by(Conversation.created_at.desc())
                .limit(20)  # Get last 20 messages for full context
                .all()
            )
            
            # Convert to conversation format
            history = []
            for conv in reversed(conversations):  # Reverse to get chronological order
                # Add user message
                if conv.message_content and conv.message_type == "incoming":
                    history.append({
                        "role": "user",
                        "content": conv.message_content,
                        "timestamp": conv.created_at.isoformat()
                    })
                
                # Add assistant response
                if conv.ai_response:
                    history.append({
                        "role": "assistant", 
                        "content": conv.ai_response,
                        "timestamp": conv.created_at.isoformat()
                    })
            
            logger.info(f"Loaded {len(history)} messages from database for user {user_id}")
            return history
            
        except Exception as e:
            logger.error(f"Error loading conversation history from DB: {e}")
            # Fallback to memory
            return self.conversation_memory.get(user_id, [])
    
    async def _generate_response_with_db_logic(
        self, 
        db: Session, 
        history: List[Dict[str, Any]], 
        request_info: RequestInfo,
        user_id: str
    ) -> str:
        """
        Generate response with proper database interaction logic
        
        Args:
            db: Database session
            history: Full conversation history
            request_info: Extracted request information
            user_id: WhatsApp user identifier
            
        Returns:
            Response string with appropriate database actions taken
        """
        try:
            from app.models.database_models import User, ServiceRequest, Provider
            from app.services.provider_service import ProviderService
            from app.services.whatsapp_service import WhatsAppService
            
            # Get user from database
            user = db.query(User).filter(User.phone_number == user_id).first()
            if not user:
                return self._get_error_response()
            
            # Check if this is a complete request that needs database action
            if request_info.is_complete():
                # Check if we already have a service request for this user
                existing_request = (
                    db.query(ServiceRequest)
                    .filter(ServiceRequest.user_id == user.id)
                    .filter(ServiceRequest.status.in_(['PENDING', 'PROVIDER_NOTIFIED', 'ASSIGNED']))
                    .first()
                )
                
                # Analyze conversation to determine the proper response
                if existing_request:
                    # User has active request - check if this is a follow-up
                    recent_messages = history[-5:] if len(history) >= 5 else history
                    acknowledgment_patterns = [
                        "ok", "d'accord", "oui", "compris", "bien", "parfait", "merci",
                        "bon", "génial", "super", "excellent", "👍", "👌"
                    ]
                    
                    # Check if last user message is acknowledgment
                    if recent_messages and recent_messages[-1].get("role") == "user":
                        last_user_msg = recent_messages[-1].get("content", "").lower().strip()
                        is_acknowledgment = any(pattern in last_user_msg for pattern in acknowledgment_patterns)
                        
                        if is_acknowledgment:
                            # This is a follow-up after completion - provide status update
                            return self._get_status_update_response(existing_request)
                    
                    # Not an acknowledgment, generate regular response
                    return self.generate_response(history, request_info)
                
                else:
                    # No existing request - create new service request
                    service_request = ServiceRequest(
                        user_id=user.id,
                        service_type=request_info.service_type,
                        location=request_info.location,
                        description=request_info.description,
                        urgency=request_info.urgency,
                        status='PENDING'
                    )
                    
                    db.add(service_request)
                    db.commit()
                    
                    # Start provider matching process (will be handled by background task)
                    logger.info(f"Created service request {service_request.id} for user {user_id}")
                    
                    # Return completion response
                    return self._get_completion_response(request_info)
            
            else:
                # Incomplete request - continue gathering information
                return self.generate_response(history, request_info)
                
        except Exception as e:
            logger.error(f"Error in database logic: {e}")
            return self.generate_response(history, request_info)
    
    def _get_status_update_response(self, service_request) -> str:
        """Generate status update response for existing requests"""
        if service_request.status == 'PENDING':
            return """🔍 **Mise à jour de votre demande**

Nous recherchons toujours un prestataire disponible dans votre zone. Nos équipes travaillent activement pour vous trouver le meilleur professionnel.

⏱️ **Temps estimé**: 5-15 minutes supplémentaires
📞 **Notification**: Vous recevrez un message dès qu'un prestataire accepte

Merci de votre patience !"""
        
        elif service_request.status == 'PROVIDER_NOTIFIED':
            return """⏳ **Notification envoyée**

Un prestataire qualifié a été contacté et examine votre demande. Nous attendons sa confirmation.

🔔 **Prochaine étape**: Vous recevrez ses coordonnées dès acceptation
⏱️ **Temps de réponse**: Généralement sous 10 minutes

Restez connecté !"""
        
        elif service_request.status == 'ASSIGNED':
            return """✅ **Prestataire assigné**

Votre demande a été acceptée ! Le prestataire va vous contacter directement pour organiser l'intervention.

📞 **Contact direct**: Attendez son appel
💰 **Paiement**: Sera traité via Djobea après l'intervention

Bonne réparation !"""
        
        else:
            return """📊 **Statut de votre demande**

Votre demande est en cours de traitement. Nous vous tiendrons informé de toute évolution.

Pour plus d'informations, tapez "statut" à tout moment."""
    
    def _get_completion_response(self, request_info: RequestInfo) -> str:
        """Generate completion response for new requests"""
        service_emoji = {
            'plomberie': '🔧',
            'électricité': '⚡',
            'réparation électroménager': '🔨'
        }.get(request_info.service_type, '🛠️')
        
        return f"""Parfait ! J'ai bien compris votre demande :

{service_emoji} **Service** : {request_info.service_type}
📍 **Localisation** : {request_info.location}
📝 **Problème** : {request_info.description}
⏰ **Délai** : {request_info.urgency}

Je recherche maintenant un prestataire disponible dans votre zone. Vous recevrez une notification dès qu'un professionnel accepte votre demande.

💰 **Commission Djobea** : 15% du montant de la prestation
⏱️ **Temps de réponse** : Généralement sous 30 minutes

Votre demande est en cours de traitement !"""
    
    def clear_conversation(self, user_id: str) -> None:
        """Clear conversation history for a user"""
        if user_id in self.conversation_memory:
            del self.conversation_memory[user_id]
        logger.info(f"Cleared conversation for user {user_id}")


# Global conversation manager instance
conversation_manager = DjobeaConversationManager()