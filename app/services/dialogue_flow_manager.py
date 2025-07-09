"""
Dialogue Flow Manager - Multi-turn conversation orchestration
Manages progressive information collection and conversation flow optimization
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import json

from app.models.conversation_session import ConversationSession
from app.models.action_codes import ActionCode
from app.services.ai_service import AIService
from app.services.session_manager import SessionManager
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class DialogueState(Enum):
    """Dialogue flow states"""
    GREETING = "greeting"
    SERVICE_COLLECTION = "service_collection"
    LOCATION_COLLECTION = "location_collection"
    DESCRIPTION_COLLECTION = "description_collection"
    URGENCY_COLLECTION = "urgency_collection"
    CONTACT_COLLECTION = "contact_collection"
    COLLECTING = "collecting"
    VALIDATION = "validation"
    CONFIRMATION = "confirmation"
    COMPLETION = "completion"
    INTERRUPTION = "interruption"
    CLARIFICATION = "clarification"
    BACKTRACK = "backtrack"
    ESCALATION = "escalation"
    COMPLAINT_HANDLING = "complaint_handling"
    ERROR = "error"

class InformationPriority(Enum):
    """Information collection priority levels"""
    CRITICAL = 1  # Service type, location
    HIGH = 2      # Description, urgency
    MEDIUM = 3    # Contact details, timing
    LOW = 4       # Additional preferences

@dataclass
class InformationField:
    """Information field definition"""
    name: str
    display_name: str
    priority: InformationPriority
    required: bool = True
    validation_rules: List[str] = field(default_factory=list)
    collection_prompts: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

@dataclass
class DialogueContext:
    """Dialogue context and state"""
    current_state: DialogueState
    collected_info: Dict[str, Any] = field(default_factory=dict)
    missing_info: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)
    interruption_stack: List[DialogueState] = field(default_factory=list)
    retry_count: int = 0
    optimization_score: float = 0.0
    user_profile: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CollectionStrategy:
    """Information collection strategy"""
    multi_extract: bool = True
    context_aware: bool = True
    progressive_validation: bool = True
    smart_suggestions: bool = True
    interruption_handling: bool = True

class DialogueFlowManager:
    """
    Advanced dialogue flow manager for multi-turn conversations
    """
    
    def __init__(self):
        self.ai_service = AIService()
        self.session_manager = SessionManager()
        
        # Information schema
        self.information_schema = self._initialize_information_schema()
        
        # Collection strategies
        self.collection_strategy = CollectionStrategy()
        
        # Performance metrics
        self.metrics = {
            "avg_turns_per_completion": 0.0,
            "completion_rate": 0.0,
            "interruption_recovery_rate": 0.0,
            "optimization_effectiveness": 0.0
        }
        
        # State transitions
        self.state_transitions = {
            DialogueState.GREETING: [DialogueState.SERVICE_COLLECTION, DialogueState.INTERRUPTION],
            DialogueState.SERVICE_COLLECTION: [DialogueState.LOCATION_COLLECTION, DialogueState.DESCRIPTION_COLLECTION, DialogueState.CLARIFICATION],
            DialogueState.LOCATION_COLLECTION: [DialogueState.DESCRIPTION_COLLECTION, DialogueState.URGENCY_COLLECTION, DialogueState.VALIDATION],
            DialogueState.DESCRIPTION_COLLECTION: [DialogueState.URGENCY_COLLECTION, DialogueState.CONTACT_COLLECTION, DialogueState.VALIDATION],
            DialogueState.URGENCY_COLLECTION: [DialogueState.CONTACT_COLLECTION, DialogueState.VALIDATION],
            DialogueState.CONTACT_COLLECTION: [DialogueState.VALIDATION],
            DialogueState.VALIDATION: [DialogueState.CONFIRMATION, DialogueState.BACKTRACK],
            DialogueState.CONFIRMATION: [DialogueState.COMPLETION, DialogueState.BACKTRACK],
            DialogueState.COMPLETION: [],
            DialogueState.INTERRUPTION: [DialogueState.SERVICE_COLLECTION, DialogueState.BACKTRACK],
            DialogueState.CLARIFICATION: [DialogueState.SERVICE_COLLECTION, DialogueState.LOCATION_COLLECTION, DialogueState.DESCRIPTION_COLLECTION],
            DialogueState.BACKTRACK: [DialogueState.SERVICE_COLLECTION, DialogueState.LOCATION_COLLECTION, DialogueState.DESCRIPTION_COLLECTION]
        }
    
    def _initialize_information_schema(self) -> Dict[str, InformationField]:
        """Initialize information collection schema"""
        return {
            "service_type": InformationField(
                name="service_type",
                display_name="Type de service",
                priority=InformationPriority.CRITICAL,
                required=True,
                validation_rules=["must_be_in_supported_services"],
                collection_prompts=[
                    "Quel type de service vous faut-il ?",
                    "De quel service avez-vous besoin ?",
                    "Que puis-je faire pour vous aider ?"
                ],
                examples=["plomberie", "électricité", "réparation électroménager"]
            ),
            "location": InformationField(
                name="location",
                display_name="Localisation",
                priority=InformationPriority.CRITICAL,
                required=True,
                validation_rules=["must_be_in_coverage_area"],
                collection_prompts=[
                    "Où êtes-vous situé ?",
                    "Quelle est votre adresse ?",
                    "Dans quel quartier de Bonamoussadi êtes-vous ?"
                ],
                examples=["Bonamoussadi Village", "Bonamoussadi Carrefour", "Bonamoussadi Ndokoti"]
            ),
            "description": InformationField(
                name="description",
                display_name="Description du problème",
                priority=InformationPriority.HIGH,
                required=True,
                collection_prompts=[
                    "Pouvez-vous décrire le problème ?",
                    "Que se passe-t-il exactement ?",
                    "Expliquez-moi votre situation"
                ],
                dependencies=["service_type"]
            ),
            "urgency": InformationField(
                name="urgency",
                display_name="Urgence",
                priority=InformationPriority.HIGH,
                required=True,
                validation_rules=["must_be_valid_urgency"],
                collection_prompts=[
                    "C'est urgent ?",
                    "Quand souhaitez-vous l'intervention ?",
                    "Quel est le délai souhaité ?"
                ],
                examples=["urgent", "aujourd'hui", "demain", "cette semaine"]
            ),
            "contact_info": InformationField(
                name="contact_info",
                display_name="Contact",
                priority=InformationPriority.MEDIUM,
                required=False,
                collection_prompts=[
                    "Comment le prestataire peut-il vous contacter ?",
                    "Avez-vous un numéro de téléphone préféré ?"
                ]
            )
        }
    
    async def process_dialogue_turn(
        self,
        session: ConversationSession,
        message: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process a single dialogue turn with multi-extraction and optimization
        """
        # Get or create dialogue context
        dialogue_context = await self._get_dialogue_context(session, db)
        
        # Detect interruptions and topic changes
        interruption_detected = await self._detect_interruption(message, dialogue_context)
        
        if interruption_detected:
            return await self._handle_interruption(session, message, dialogue_context, db)
        
        # Extract information with multi-field capability
        extracted_info = await self._extract_multiple_information(message, dialogue_context)
        
        # Update dialogue context
        dialogue_context = await self._update_dialogue_context(
            dialogue_context, extracted_info, session, db
        )
        
        # Determine next state and action
        next_state = await self._determine_next_state(dialogue_context)
        
        # Generate contextual response
        response = await self._generate_contextual_response(
            dialogue_context, next_state, extracted_info
        )
        
        # Update session and save context
        await self._save_dialogue_context(session, dialogue_context, db)
        
        return {
            "response": response["message"],
            "dialogue_state": next_state.value,
            "collected_info": dialogue_context.collected_info,
            "missing_info": dialogue_context.missing_info,
            "completion_progress": self._calculate_completion_progress(dialogue_context),
            "optimization_score": dialogue_context.optimization_score,
            "suggested_actions": response.get("suggested_actions", []),
            "validation_errors": dialogue_context.validation_errors
        }
    
    async def _extract_multiple_information(
        self,
        message: str,
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """
        Extract multiple information fields from a single message
        """
        # Build extraction prompt based on missing information
        missing_fields = [
            self.information_schema[field] for field in dialogue_context.missing_info
            if field in self.information_schema
        ]
        
        extraction_prompt = self._build_extraction_prompt(missing_fields, dialogue_context)
        
        # Use AI to extract information
        extraction_result = await self.ai_service.extract_request_info(
            message, dialogue_context.conversation_history[-5:]
        )
        
        # Process and validate extracted information
        validated_info = await self._validate_extracted_info(extraction_result, dialogue_context)
        
        return validated_info
    
    def _build_extraction_prompt(
        self,
        missing_fields: List[InformationField],
        dialogue_context: DialogueContext
    ) -> str:
        """
        Build dynamic extraction prompt based on missing information
        """
        current_info = dialogue_context.collected_info
        
        prompt = f"""
        Analyser le message utilisateur et extraire les informations suivantes si disponibles:
        
        CONTEXTE ACTUEL:
        {json.dumps(current_info, indent=2, ensure_ascii=False)}
        
        INFORMATIONS À RECHERCHER (par ordre de priorité):
        """
        
        for field in sorted(missing_fields, key=lambda x: x.priority.value):
            prompt += f"""
        
        {field.display_name.upper()}:
        - Nom: {field.name}
        - Requis: {'Oui' if field.required else 'Non'}
        - Exemples: {', '.join(field.examples) if field.examples else 'Aucun'}
        - Règles: {', '.join(field.validation_rules) if field.validation_rules else 'Aucune'}
        """
        
        prompt += """
        
        INSTRUCTIONS:
        1. Extraire TOUTES les informations disponibles dans le message
        2. Respecter les règles de validation
        3. Marquer les informations incomplètes ou ambiguës
        4. Proposer des clarifications si nécessaire
        
        RÉPONSE FORMAT JSON:
        {
            "extracted_fields": {
                "field_name": "value",
                ...
            },
            "validation_issues": [
                {
                    "field": "field_name",
                    "issue": "description",
                    "suggestion": "clarification"
                }
            ],
            "confidence_scores": {
                "field_name": 0.8,
                ...
            },
            "needs_clarification": ["field_name", ...],
            "suggested_questions": ["question1", "question2", ...],
            "completion_status": "partial|complete|unclear"
        }
        """
        
        return prompt
    
    async def _validate_extracted_info(
        self,
        extraction_result: Dict[str, Any],
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """
        Validate and process extracted information
        """
        validated_info = {}
        validation_errors = []
        
        extracted_fields = extraction_result.get("extracted_fields", {})
        
        for field_name, value in extracted_fields.items():
            if field_name in self.information_schema:
                field_schema = self.information_schema[field_name]
                
                # Apply validation rules
                validation_result = await self._apply_validation_rules(
                    field_name, value, field_schema, dialogue_context
                )
                
                if validation_result["valid"]:
                    validated_info[field_name] = value
                else:
                    validation_errors.extend(validation_result["errors"])
        
        return {
            "validated_fields": validated_info,
            "validation_errors": validation_errors,
            "confidence_scores": extraction_result.get("confidence_scores", {}),
            "needs_clarification": extraction_result.get("needs_clarification", []),
            "suggested_questions": extraction_result.get("suggested_questions", [])
        }
    
    async def _apply_validation_rules(
        self,
        field_name: str,
        value: Any,
        field_schema: InformationField,
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """
        Apply validation rules to extracted information
        """
        validation_result = {"valid": True, "errors": []}
        
        for rule in field_schema.validation_rules:
            if rule == "must_be_in_supported_services":
                if value not in ["plomberie", "électricité", "réparation électroménager"]:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Service '{value}' non supporté")
            
            elif rule == "must_be_in_coverage_area":
                if "bonamoussadi" not in value.lower() and "douala" not in value.lower():
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Zone '{value}' non couverte")
            
            elif rule == "must_be_valid_urgency":
                valid_urgencies = ["urgent", "normal", "flexible", "aujourd'hui", "demain", "cette semaine"]
                if value.lower() not in valid_urgencies:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Urgence '{value}' non reconnue")
        
        return validation_result
    
    async def _determine_next_state(
        self,
        dialogue_context: DialogueContext
    ) -> DialogueState:
        """
        Determine next dialogue state based on context and optimization
        """
        current_state = dialogue_context.current_state
        collected_info = dialogue_context.collected_info
        missing_info = dialogue_context.missing_info
        
        # If all critical information is collected, move to validation
        critical_fields = [
            field for field, schema in self.information_schema.items()
            if schema.priority == InformationPriority.CRITICAL and schema.required
        ]
        
        if all(field in collected_info for field in critical_fields):
            if not missing_info:
                return DialogueState.VALIDATION
            elif all(
                self.information_schema[field].priority.value > InformationPriority.HIGH.value
                for field in missing_info
            ):
                return DialogueState.VALIDATION
        
        # Determine next collection state based on priority
        if "service_type" not in collected_info:
            return DialogueState.SERVICE_COLLECTION
        elif "location" not in collected_info:
            return DialogueState.LOCATION_COLLECTION
        elif "description" not in collected_info:
            return DialogueState.DESCRIPTION_COLLECTION
        elif "urgency" not in collected_info:
            return DialogueState.URGENCY_COLLECTION
        elif "contact_info" not in collected_info:
            return DialogueState.CONTACT_COLLECTION
        
        return DialogueState.VALIDATION
    
    async def _generate_contextual_response(
        self,
        dialogue_context: DialogueContext,
        next_state: DialogueState,
        extracted_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate contextual response based on dialogue state and extracted information
        """
        collected_info = dialogue_context.collected_info
        missing_info = dialogue_context.missing_info
        suggested_questions = extracted_info.get("suggested_questions", [])
        
        # Build response based on state
        response_parts = []
        
        # Acknowledge extracted information
        if extracted_info.get("validated_fields"):
            acknowledgment = self._build_acknowledgment(extracted_info["validated_fields"])
            response_parts.append(acknowledgment)
        
        # Handle validation errors
        if dialogue_context.validation_errors:
            error_response = self._build_error_response(dialogue_context.validation_errors)
            response_parts.append(error_response)
        
        # Generate next question or action
        if next_state == DialogueState.VALIDATION:
            validation_response = self._build_validation_response(collected_info)
            response_parts.append(validation_response)
        elif next_state == DialogueState.COMPLETION:
            completion_response = self._build_completion_response(collected_info)
            response_parts.append(completion_response)
        else:
            next_question = await self._generate_next_question(next_state, missing_info, suggested_questions)
            response_parts.append(next_question)
        
        # Combine response parts
        full_response = "\n\n".join(response_parts)
        
        return {
            "message": full_response,
            "suggested_actions": self._generate_suggested_actions(next_state, missing_info),
            "completion_progress": self._calculate_completion_progress(dialogue_context)
        }
    
    def _build_acknowledgment(self, validated_fields: Dict[str, Any]) -> str:
        """Build acknowledgment for extracted information"""
        acknowledgments = []
        
        for field, value in validated_fields.items():
            if field in self.information_schema:
                display_name = self.information_schema[field].display_name
                acknowledgments.append(f"✓ {display_name}: {value}")
        
        if acknowledgments:
            return f"Parfait ! J'ai noté :\n" + "\n".join(acknowledgments)
        
        return ""
    
    def _build_error_response(self, validation_errors: List[str]) -> str:
        """Build response for validation errors"""
        if not validation_errors:
            return ""
        
        error_response = "⚠️ Il y a quelques points à clarifier :\n"
        error_response += "\n".join(f"• {error}" for error in validation_errors)
        
        return error_response
    
    def _build_validation_response(self, collected_info: Dict[str, Any]) -> str:
        """Build validation response with collected information"""
        response = "📋 Récapitulatif de votre demande :\n\n"
        
        for field, value in collected_info.items():
            if field in self.information_schema:
                display_name = self.information_schema[field].display_name
                response += f"• {display_name}: {value}\n"
        
        response += "\n✅ Ces informations sont-elles correctes ?\n"
        response += "Répondez 'OUI' pour confirmer ou précisez ce qui doit être modifié."
        
        return response
    
    def _build_completion_response(self, collected_info: Dict[str, Any]) -> str:
        """Build completion response"""
        return (
            "🎉 Parfait ! Votre demande est complète.\n\n"
            "Je recherche maintenant un prestataire disponible dans votre zone.\n"
            "Vous recevrez une notification dès qu'un professionnel acceptera votre demande."
        )
    
    async def _generate_next_question(
        self,
        next_state: DialogueState,
        missing_info: List[str],
        suggested_questions: List[str]
    ) -> str:
        """Generate next question based on state and missing information"""
        if suggested_questions:
            return suggested_questions[0]
        
        # Default questions based on state
        if next_state == DialogueState.SERVICE_COLLECTION:
            return (
                "🔧 Quel type de service vous faut-il ?\n\n"
                "Nous proposons :\n"
                "• Plomberie (fuites, canalisations, robinetterie...)\n"
                "• Électricité (pannes, installations, réparations...)\n"
                "• Réparation d'électroménager (frigo, machine à laver, climatiseur...)"
            )
        
        elif next_state == DialogueState.LOCATION_COLLECTION:
            return (
                "📍 Où êtes-vous situé ?\n\n"
                "Nous intervenons dans la zone de Bonamoussadi, Douala.\n"
                "Précisez votre quartier et votre adresse."
            )
        
        elif next_state == DialogueState.DESCRIPTION_COLLECTION:
            return (
                "🔍 Pouvez-vous décrire votre problème ?\n\n"
                "Plus vous êtes précis, mieux nous pourrons vous aider.\n"
                "N'hésitez pas à donner des détails sur la situation."
            )
        
        elif next_state == DialogueState.URGENCY_COLLECTION:
            return (
                "⏰ Quand souhaitez-vous l'intervention ?\n\n"
                "• Urgent (dans l'heure)\n"
                "• Aujourd'hui\n"
                "• Demain\n"
                "• Cette semaine\n"
                "• Pas pressé"
            )
        
        elif next_state == DialogueState.CONTACT_COLLECTION:
            return (
                "📞 Comment le prestataire peut-il vous contacter ?\n\n"
                "Nous utilisons déjà ce numéro WhatsApp, mais avez-vous un autre numéro préféré ?"
            )
        
        return "Comment puis-je vous aider davantage ?"
    
    def _generate_suggested_actions(
        self,
        next_state: DialogueState,
        missing_info: List[str]
    ) -> List[str]:
        """Generate suggested actions for the user"""
        actions = []
        
        if next_state == DialogueState.SERVICE_COLLECTION:
            actions = ["Plomberie", "Électricité", "Électroménager"]
        elif next_state == DialogueState.URGENCY_COLLECTION:
            actions = ["Urgent", "Aujourd'hui", "Demain", "Cette semaine"]
        elif next_state == DialogueState.VALIDATION:
            actions = ["OUI", "Modifier", "Annuler"]
        
        return actions
    
    def _calculate_completion_progress(self, dialogue_context: DialogueContext) -> float:
        """Calculate completion progress percentage"""
        total_fields = len(self.information_schema)
        collected_fields = len(dialogue_context.collected_info)
        
        # Weight by priority
        total_weight = sum(
            1 / field.priority.value for field in self.information_schema.values()
        )
        
        collected_weight = sum(
            1 / self.information_schema[field].priority.value
            for field in dialogue_context.collected_info
            if field in self.information_schema
        )
        
        return (collected_weight / total_weight) * 100
    
    async def _detect_interruption(
        self,
        message: str,
        dialogue_context: DialogueContext
    ) -> bool:
        """Detect interruptions and topic changes"""
        # Keywords that indicate interruption
        interruption_keywords = [
            "stop", "arrêt", "annuler", "cancel", "nouveau", "autre", "différent",
            "changer", "modifier", "plutôt", "finalement", "non", "pas ça"
        ]
        
        message_lower = message.lower()
        
        # Check for interruption keywords
        for keyword in interruption_keywords:
            if keyword in message_lower:
                return True
        
        # Check for topic change using AI
        if len(dialogue_context.conversation_history) > 2:
            topic_change_prompt = f"""
            Analyser si ce message indique un changement de sujet ou une interruption:
            
            CONTEXTE: {dialogue_context.collected_info}
            NOUVEAU MESSAGE: {message}
            
            Répondre par 'OUI' si c'est une interruption, 'NON' sinon.
            """
            
            # Simple heuristic for now - can be enhanced with AI
            current_service = dialogue_context.collected_info.get("service_type", "")
            new_services = ["plomberie", "électricité", "électroménager"]
            
            for service in new_services:
                if service in message_lower and service != current_service:
                    return True
        
        return False
    
    async def _handle_interruption(
        self,
        session: ConversationSession,
        message: str,
        dialogue_context: DialogueContext,
        db: Session
    ) -> Dict[str, Any]:
        """Handle interruption and manage conversation flow"""
        # Save current state to interruption stack
        dialogue_context.interruption_stack.append(dialogue_context.current_state)
        
        # Determine interruption type
        if any(word in message.lower() for word in ["annuler", "cancel", "stop"]):
            # Cancellation
            dialogue_context.current_state = DialogueState.GREETING
            dialogue_context.collected_info.clear()
            dialogue_context.missing_info.clear()
            
            response = (
                "🔄 Demande annulée.\n\n"
                "Je suis à votre disposition pour une nouvelle demande.\n"
                "Que puis-je faire pour vous ?"
            )
        
        elif any(word in message.lower() for word in ["nouveau", "autre", "différent"]):
            # New request
            dialogue_context.current_state = DialogueState.SERVICE_COLLECTION
            dialogue_context.collected_info.clear()
            dialogue_context.missing_info = list(self.information_schema.keys())
            
            response = (
                "🆕 Nouvelle demande démarrée.\n\n"
                "Quel type de service vous faut-il ?\n"
                "• Plomberie\n"
                "• Électricité\n"
                "• Réparation d'électroménager"
            )
        
        else:
            # Topic change - try to extract new information
            extracted_info = await self._extract_multiple_information(message, dialogue_context)
            
            if extracted_info.get("validated_fields"):
                # Update with new information
                dialogue_context.collected_info.update(extracted_info["validated_fields"])
                dialogue_context.current_state = DialogueState.SERVICE_COLLECTION
                
                response = (
                    f"✏️ Modification prise en compte.\n\n"
                    f"Nouvelle information : {extracted_info['validated_fields']}\n\n"
                    f"Continuons avec votre demande..."
                )
            else:
                # Unclear interruption
                response = (
                    "🤔 Je ne suis pas sûr de comprendre.\n\n"
                    "Souhaitez-vous :\n"
                    "• Annuler la demande actuelle\n"
                    "• Modifier quelque chose\n"
                    "• Commencer une nouvelle demande"
                )
        
        return {
            "response": response,
            "dialogue_state": dialogue_context.current_state.value,
            "collected_info": dialogue_context.collected_info,
            "missing_info": dialogue_context.missing_info,
            "completion_progress": self._calculate_completion_progress(dialogue_context),
            "interruption_handled": True
        }
    
    async def _get_dialogue_context(
        self,
        session: ConversationSession,
        db: Session
    ) -> DialogueContext:
        """Get or create dialogue context for session"""
        # Try to load existing context from session metadata
        if hasattr(session, 'dialogue_context') and session.dialogue_context:
            context_data = session.dialogue_context
            
            return DialogueContext(
                current_state=DialogueState(context_data.get("current_state", "greeting")),
                collected_info=context_data.get("collected_info", {}),
                missing_info=context_data.get("missing_info", list(self.information_schema.keys())),
                validation_errors=context_data.get("validation_errors", []),
                conversation_history=context_data.get("conversation_history", []),
                interruption_stack=context_data.get("interruption_stack", []),
                retry_count=context_data.get("retry_count", 0),
                optimization_score=context_data.get("optimization_score", 0.0),
                user_profile=context_data.get("user_profile", {})
            )
        
        # Create new context
        return DialogueContext(
            current_state=DialogueState.GREETING,
            missing_info=list(self.information_schema.keys())
        )
    
    async def _update_dialogue_context(
        self,
        dialogue_context: DialogueContext,
        extracted_info: Dict[str, Any],
        session: ConversationSession,
        db: Session
    ) -> DialogueContext:
        """Update dialogue context with extracted information"""
        # Update collected information
        if extracted_info.get("validated_fields"):
            dialogue_context.collected_info.update(extracted_info["validated_fields"])
            
            # Remove collected fields from missing info
            for field in extracted_info["validated_fields"]:
                if field in dialogue_context.missing_info:
                    dialogue_context.missing_info.remove(field)
        
        # Update validation errors
        dialogue_context.validation_errors = extracted_info.get("validation_errors", [])
        
        # Update conversation history
        dialogue_context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "message": session.last_message if hasattr(session, 'last_message') else "",
            "extracted_info": extracted_info.get("validated_fields", {}),
            "state": dialogue_context.current_state.value
        })
        
        # Calculate optimization score
        dialogue_context.optimization_score = self._calculate_optimization_score(dialogue_context)
        
        return dialogue_context
    
    def _calculate_optimization_score(self, dialogue_context: DialogueContext) -> float:
        """Calculate optimization score based on efficiency metrics"""
        # Factors: information density, turn efficiency, error rate
        
        total_turns = len(dialogue_context.conversation_history)
        if total_turns == 0:
            return 0.0
        
        # Information density: info collected per turn
        info_density = len(dialogue_context.collected_info) / total_turns
        
        # Turn efficiency: progress per turn
        completion_progress = self._calculate_completion_progress(dialogue_context)
        turn_efficiency = completion_progress / total_turns if total_turns > 0 else 0
        
        # Error rate: validation errors per turn
        error_rate = len(dialogue_context.validation_errors) / total_turns
        
        # Combined score (0-1)
        optimization_score = (
            info_density * 0.4 +
            turn_efficiency * 0.4 +
            (1 - error_rate) * 0.2
        )
        
        return min(max(optimization_score, 0.0), 1.0)
    
    async def _save_dialogue_context(
        self,
        session: ConversationSession,
        dialogue_context: DialogueContext,
        db: Session
    ) -> None:
        """Save dialogue context to session"""
        context_data = {
            "current_state": dialogue_context.current_state.value,
            "collected_info": dialogue_context.collected_info,
            "missing_info": dialogue_context.missing_info,
            "validation_errors": dialogue_context.validation_errors,
            "conversation_history": dialogue_context.conversation_history[-10:],  # Keep last 10 turns
            "interruption_stack": dialogue_context.interruption_stack,
            "retry_count": dialogue_context.retry_count,
            "optimization_score": dialogue_context.optimization_score,
            "user_profile": dialogue_context.user_profile
        }
        
        # Save to session (this would be implemented in the session manager)
        await self.session_manager.update_session_metadata(
            session.session_id, {"dialogue_context": context_data}, db
        )
    
    async def get_dialogue_metrics(self) -> Dict[str, Any]:
        """Get dialogue performance metrics"""
        return {
            "metrics": self.metrics,
            "information_schema": {
                name: {
                    "display_name": field.display_name,
                    "priority": field.priority.value,
                    "required": field.required
                }
                for name, field in self.information_schema.items()
            },
            "state_transitions": {
                state.value: [s.value for s in transitions]
                for state, transitions in self.state_transitions.items()
            }
        }
    
    async def optimize_dialogue_flow(
        self,
        user_profile: Dict[str, Any],
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """Optimize dialogue flow based on user profile and history"""
        # Analyze user patterns
        user_patterns = self._analyze_user_patterns(user_profile, conversation_history)
        
        # Suggest optimizations
        optimizations = {
            "recommended_questions": self._get_personalized_questions(user_patterns),
            "information_priority": self._adjust_information_priority(user_patterns),
            "conversation_style": self._recommend_conversation_style(user_patterns),
            "efficiency_improvements": self._suggest_efficiency_improvements(user_patterns)
        }
        
        return optimizations
    
    def _analyze_user_patterns(
        self,
        user_profile: Dict[str, Any],
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze user conversation patterns"""
        # Implement pattern analysis
        patterns = {
            "preferred_information_order": [],
            "response_style": "formal",
            "average_message_length": 0,
            "interruption_frequency": 0,
            "completion_rate": 0.0
        }
        
        return patterns
    
    def _get_personalized_questions(self, user_patterns: Dict[str, Any]) -> List[str]:
        """Get personalized questions based on user patterns"""
        return [
            "Question personnalisée basée sur l'historique",
            "Question adaptée au style de l'utilisateur"
        ]
    
    def _adjust_information_priority(self, user_patterns: Dict[str, Any]) -> Dict[str, int]:
        """Adjust information collection priority based on user patterns"""
        return {
            "service_type": 1,
            "location": 2,
            "urgency": 3,
            "description": 4,
            "contact_info": 5
        }
    
    def _recommend_conversation_style(self, user_patterns: Dict[str, Any]) -> str:
        """Recommend conversation style based on user patterns"""
        return "formal"  # or "casual", "professional", etc.
    
    def _suggest_efficiency_improvements(self, user_patterns: Dict[str, Any]) -> List[str]:
        """Suggest efficiency improvements"""
        return [
            "Combiner les questions de localisation et d'urgence",
            "Utiliser des suggestions automatiques",
            "Réduire le nombre de validations"
        ]