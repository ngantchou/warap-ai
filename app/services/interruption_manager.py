"""
Interruption Manager - Advanced conversation interruption handling
Manages topic changes, cancellations, backtracking, and conversation recovery
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import json

from app.services.dialogue_flow_manager import DialogueState, DialogueContext
from app.services.ai_service import AIService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class InterruptionType(Enum):
    """Types of conversation interruptions"""
    TOPIC_CHANGE = "topic_change"        # User changes subject
    CANCELLATION = "cancellation"        # User wants to cancel
    MODIFICATION = "modification"        # User wants to modify info
    CLARIFICATION = "clarification"      # User asks for clarification
    BACKTRACK = "backtrack"             # User wants to go back
    NEW_REQUEST = "new_request"         # User starts new request
    PAUSE = "pause"                     # User wants to pause
    RESUME = "resume"                   # User wants to resume
    ESCALATION = "escalation"           # User wants human help
    COMPLAINT = "complaint"             # User has a complaint

class InterruptionSeverity(Enum):
    """Severity levels for interruptions"""
    LOW = 1      # Minor clarification
    MEDIUM = 2   # Topic change or modification
    HIGH = 3     # Cancellation or major change
    CRITICAL = 4 # System failure or escalation

@dataclass
class InterruptionEvent:
    """Interruption event details"""
    type: InterruptionType
    severity: InterruptionSeverity
    message: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    previous_state: DialogueState = None
    confidence: float = 0.0
    recovery_actions: List[str] = field(default_factory=list)

@dataclass
class InterruptionState:
    """Current interruption state"""
    is_interrupted: bool = False
    current_interruption: Optional[InterruptionEvent] = None
    interruption_history: List[InterruptionEvent] = field(default_factory=list)
    recovery_stack: List[DialogueState] = field(default_factory=list)
    saved_context: Dict[str, Any] = field(default_factory=dict)
    interruption_count: int = 0
    last_interruption_time: Optional[datetime] = None

class InterruptionManager:
    """
    Advanced interruption management system
    """
    
    def __init__(self):
        self.ai_service = AIService()
        
        # Interruption detection patterns
        self.interruption_patterns = self._initialize_interruption_patterns()
        
        # Recovery strategies
        self.recovery_strategies = self._initialize_recovery_strategies()
        
        # Interruption metrics
        self.metrics = {
            "total_interruptions": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "interruption_types": {},
            "average_recovery_time": 0.0
        }
    
    def _initialize_interruption_patterns(self) -> Dict[InterruptionType, Dict[str, Any]]:
        """Initialize interruption detection patterns"""
        return {
            InterruptionType.CANCELLATION: {
                "keywords": [
                    "annuler", "cancel", "stop", "arrêter", "laisser tomber",
                    "oublier", "ne veux plus", "changer d'avis", "abandon"
                ],
                "phrases": [
                    "je ne veux plus",
                    "laisse tomber",
                    "oublie ça",
                    "c'est bon",
                    "pas besoin",
                    "annule tout"
                ],
                "patterns": [
                    r"(annul|cancel|stop|arrêt)",
                    r"(ne\s+veux\s+plus|ne\s+veux\s+pas)",
                    r"(laisse\s+tomber|oublie\s+ça)"
                ],
                "confidence_threshold": 0.8
            },
            
            InterruptionType.TOPIC_CHANGE: {
                "keywords": [
                    "plutôt", "finalement", "en fait", "non", "autre chose",
                    "différent", "changer", "modifier", "nouveau"
                ],
                "phrases": [
                    "en fait c'est",
                    "plutôt que",
                    "finalement je veux",
                    "non c'est",
                    "autre chose",
                    "pas ça"
                ],
                "patterns": [
                    r"(plutôt|finalement|en\s+fait)",
                    r"(non\s+c'est|pas\s+ça|autre\s+chose)",
                    r"(nouveau|différent|changer)"
                ],
                "confidence_threshold": 0.7
            },
            
            InterruptionType.MODIFICATION: {
                "keywords": [
                    "modifier", "changer", "corriger", "rectifier", "pas ça",
                    "erreur", "me trompe", "mauvais", "faux"
                ],
                "phrases": [
                    "je me trompe",
                    "c'est faux",
                    "pas correct",
                    "je veux changer",
                    "corriger ça",
                    "modifier ma réponse"
                ],
                "patterns": [
                    r"(modifi|chang|corrig|rectifi)",
                    r"(erreur|faux|mauvais|pas\s+correct)",
                    r"(me\s+trompe|pas\s+ça)"
                ],
                "confidence_threshold": 0.7
            },
            
            InterruptionType.CLARIFICATION: {
                "keywords": [
                    "comprends pas", "expliquer", "clarifier", "préciser",
                    "que veux-tu dire", "comment", "pourquoi", "qu'est-ce que"
                ],
                "phrases": [
                    "je ne comprends pas",
                    "que veux-tu dire",
                    "peux-tu expliquer",
                    "comment ça",
                    "qu'est-ce que ça veut dire",
                    "précise"
                ],
                "patterns": [
                    r"(comprends?\s+pas|comprends?\s+rien)",
                    r"(expliqu|clarifi|précis)",
                    r"(comment|pourquoi|qu'est-ce)"
                ],
                "confidence_threshold": 0.8
            },
            
            InterruptionType.BACKTRACK: {
                "keywords": [
                    "retour", "revenir", "avant", "précédent", "reprendre",
                    "recommencer", "étape d'avant", "en arrière"
                ],
                "phrases": [
                    "revenir en arrière",
                    "étape précédente",
                    "reprendre depuis",
                    "recommencer",
                    "retour à"
                ],
                "patterns": [
                    r"(retour|revenir|avant|précédent)",
                    r"(recommenc|reprend|arrière)",
                    r"(étape\s+d'avant|étape\s+précédente)"
                ],
                "confidence_threshold": 0.7
            },
            
            InterruptionType.NEW_REQUEST: {
                "keywords": [
                    "nouvelle demande", "autre service", "autre problème",
                    "nouveau", "différent", "pas le même", "autre chose"
                ],
                "phrases": [
                    "nouvelle demande",
                    "autre service",
                    "autre problème",
                    "quelque chose de différent",
                    "pas le même problème",
                    "commencer nouveau"
                ],
                "patterns": [
                    r"(nouvelle?\s+demande|nouveau\s+service)",
                    r"(autre\s+service|autre\s+problème)",
                    r"(différent|pas\s+le\s+même)"
                ],
                "confidence_threshold": 0.8
            },
            
            InterruptionType.ESCALATION: {
                "keywords": [
                    "parler à quelqu'un", "humain", "personne", "responsable",
                    "pas satisfait", "n'aide pas", "pas bon", "service client"
                ],
                "phrases": [
                    "parler à quelqu'un",
                    "un humain",
                    "une personne",
                    "le responsable",
                    "service client",
                    "pas satisfait"
                ],
                "patterns": [
                    r"(parler\s+à|humain|personne|responsable)",
                    r"(service\s+client|pas\s+satisfait)",
                    r"(n'aide\s+pas|pas\s+bon)"
                ],
                "confidence_threshold": 0.9
            },
            
            InterruptionType.COMPLAINT: {
                "keywords": [
                    "plainte", "problème avec", "pas content", "mécontent",
                    "mal fait", "lent", "pas efficace", "ne marche pas"
                ],
                "phrases": [
                    "j'ai une plainte",
                    "problème avec le service",
                    "pas content du tout",
                    "mal fait",
                    "trop lent",
                    "ne marche pas bien"
                ],
                "patterns": [
                    r"(plainte|problème\s+avec|pas\s+content)",
                    r"(mal\s+fait|lent|pas\s+efficace)",
                    r"(ne\s+marche\s+pas|mécontent)"
                ],
                "confidence_threshold": 0.8
            }
        }
    
    def _initialize_recovery_strategies(self) -> Dict[InterruptionType, Dict[str, Any]]:
        """Initialize recovery strategies for each interruption type"""
        return {
            InterruptionType.CANCELLATION: {
                "immediate_actions": [
                    "acknowledge_cancellation",
                    "offer_alternatives",
                    "save_partial_data"
                ],
                "recovery_message": "🔄 J'ai annulé votre demande. Puis-je vous aider avec autre chose ?",
                "next_state": DialogueState.GREETING,
                "clear_context": True
            },
            
            InterruptionType.TOPIC_CHANGE: {
                "immediate_actions": [
                    "detect_new_topic",
                    "save_current_context",
                    "restart_collection"
                ],
                "recovery_message": "✏️ J'ai noté le changement. Commençons avec votre nouvelle demande.",
                "next_state": DialogueState.SERVICE_COLLECTION,
                "clear_context": False
            },
            
            InterruptionType.MODIFICATION: {
                "immediate_actions": [
                    "identify_field_to_modify",
                    "clear_incorrect_data",
                    "resume_from_modification"
                ],
                "recovery_message": "📝 Pas de problème, nous allons corriger cela. Que souhaitez-vous modifier ?",
                "next_state": DialogueState.CLARIFICATION,
                "clear_context": False
            },
            
            InterruptionType.CLARIFICATION: {
                "immediate_actions": [
                    "provide_explanation",
                    "simplify_question",
                    "offer_examples"
                ],
                "recovery_message": "💡 Laissez-moi vous expliquer plus clairement.",
                "next_state": DialogueState.CLARIFICATION,
                "clear_context": False
            },
            
            InterruptionType.BACKTRACK: {
                "immediate_actions": [
                    "identify_target_step",
                    "restore_previous_state",
                    "continue_from_step"
                ],
                "recovery_message": "⏪ Retour à l'étape précédente. Continuons depuis là.",
                "next_state": DialogueState.COLLECTING,
                "clear_context": False
            },
            
            InterruptionType.NEW_REQUEST: {
                "immediate_actions": [
                    "save_current_session",
                    "clear_current_context",
                    "start_new_session"
                ],
                "recovery_message": "🆕 Nouvelle demande démarrée. Que puis-je faire pour vous ?",
                "next_state": DialogueState.GREETING,
                "clear_context": True
            },
            
            InterruptionType.ESCALATION: {
                "immediate_actions": [
                    "log_escalation_request",
                    "provide_contact_info",
                    "offer_immediate_help"
                ],
                "recovery_message": "👥 Je comprends. Puis-je d'abord essayer de vous aider ? Sinon, voici comment contacter notre équipe.",
                "next_state": DialogueState.ESCALATION,
                "clear_context": False
            },
            
            InterruptionType.COMPLAINT: {
                "immediate_actions": [
                    "acknowledge_complaint",
                    "log_complaint",
                    "offer_resolution"
                ],
                "recovery_message": "😔 Je suis désolé pour ce désagrément. Laissez-moi essayer de résoudre votre problème.",
                "next_state": DialogueState.COMPLAINT_HANDLING,
                "clear_context": False
            }
        }
    
    async def detect_interruption(
        self,
        message: str,
        dialogue_context: DialogueContext,
        interruption_state: InterruptionState
    ) -> Optional[InterruptionEvent]:
        """
        Detect interruption in user message
        """
        message_lower = message.lower()
        detected_interruptions = []
        
        # Check each interruption type
        for interruption_type, patterns in self.interruption_patterns.items():
            confidence = 0.0
            
            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in message_lower:
                    confidence += 0.3
            
            # Check phrases
            for phrase in patterns["phrases"]:
                if phrase in message_lower:
                    confidence += 0.5
            
            # Check regex patterns
            import re
            for pattern in patterns["patterns"]:
                if re.search(pattern, message_lower):
                    confidence += 0.4
            
            # Normalize confidence
            confidence = min(confidence, 1.0)
            
            # Check if confidence meets threshold
            if confidence >= patterns["confidence_threshold"]:
                detected_interruptions.append((interruption_type, confidence))
        
        # If no pattern-based detection, use AI
        if not detected_interruptions:
            ai_detection = await self._ai_based_interruption_detection(
                message, dialogue_context
            )
            if ai_detection:
                detected_interruptions.append(ai_detection)
        
        # Select best interruption
        if detected_interruptions:
            best_interruption = max(detected_interruptions, key=lambda x: x[1])
            interruption_type, confidence = best_interruption
            
            # Determine severity
            severity = self._determine_interruption_severity(
                interruption_type, confidence, dialogue_context
            )
            
            return InterruptionEvent(
                type=interruption_type,
                severity=severity,
                message=message,
                timestamp=datetime.now(),
                context=dialogue_context.collected_info.copy(),
                previous_state=dialogue_context.current_state,
                confidence=confidence
            )
        
        return None
    
    async def _ai_based_interruption_detection(
        self,
        message: str,
        dialogue_context: DialogueContext
    ) -> Optional[Tuple[InterruptionType, float]]:
        """
        Use AI to detect subtle interruptions
        """
        detection_prompt = f"""
        Analyser ce message pour détecter une interruption dans la conversation.
        
        CONTEXTE ACTUEL:
        - État: {dialogue_context.current_state.value}
        - Info collectée: {dialogue_context.collected_info}
        - Historique: {dialogue_context.conversation_history[-3:] if dialogue_context.conversation_history else []}
        
        NOUVEAU MESSAGE: "{message}"
        
        Types d'interruption possibles:
        1. CANCELLATION - Veut annuler
        2. TOPIC_CHANGE - Change de sujet
        3. MODIFICATION - Veut modifier info
        4. CLARIFICATION - Demande clarification
        5. BACKTRACK - Veut revenir en arrière
        6. NEW_REQUEST - Nouvelle demande
        7. ESCALATION - Veut parler à humain
        8. COMPLAINT - Se plaint du service
        
        Répondre en JSON:
        {{
            "is_interruption": true/false,
            "type": "TYPE_NAME",
            "confidence": 0.0-1.0,
            "reason": "explication"
        }}
        """
        
        try:
            response = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": detection_prompt}],
                max_tokens=200
            )
            
            # Parse JSON response
            import json
            result = json.loads(response.strip())
            
            if result.get("is_interruption") and result.get("confidence", 0) > 0.6:
                interruption_type = InterruptionType(result["type"].lower())
                confidence = result["confidence"]
                return (interruption_type, confidence)
        
        except Exception as e:
            logger.error(f"AI interruption detection failed: {e}")
        
        return None
    
    def _determine_interruption_severity(
        self,
        interruption_type: InterruptionType,
        confidence: float,
        dialogue_context: DialogueContext
    ) -> InterruptionSeverity:
        """
        Determine severity of interruption
        """
        # Base severity by type
        base_severity = {
            InterruptionType.CLARIFICATION: InterruptionSeverity.LOW,
            InterruptionType.MODIFICATION: InterruptionSeverity.MEDIUM,
            InterruptionType.TOPIC_CHANGE: InterruptionSeverity.MEDIUM,
            InterruptionType.BACKTRACK: InterruptionSeverity.MEDIUM,
            InterruptionType.NEW_REQUEST: InterruptionSeverity.HIGH,
            InterruptionType.CANCELLATION: InterruptionSeverity.HIGH,
            InterruptionType.ESCALATION: InterruptionSeverity.CRITICAL,
            InterruptionType.COMPLAINT: InterruptionSeverity.CRITICAL
        }
        
        severity = base_severity.get(interruption_type, InterruptionSeverity.MEDIUM)
        
        # Adjust based on confidence
        if confidence > 0.9:
            severity = InterruptionSeverity(min(severity.value + 1, 4))
        elif confidence < 0.7:
            severity = InterruptionSeverity(max(severity.value - 1, 1))
        
        # Adjust based on context
        completion_progress = len(dialogue_context.collected_info) / 5  # Assume 5 total fields
        if completion_progress > 0.8 and severity.value > 2:
            severity = InterruptionSeverity(severity.value - 1)  # Less severe when near completion
        
        return severity
    
    async def handle_interruption(
        self,
        interruption: InterruptionEvent,
        dialogue_context: DialogueContext,
        interruption_state: InterruptionState,
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle interruption and manage recovery
        """
        logger.info(f"Handling interruption: {interruption.type.value} (severity: {interruption.severity.value})")
        
        # Update interruption state
        interruption_state.is_interrupted = True
        interruption_state.current_interruption = interruption
        interruption_state.interruption_history.append(interruption)
        interruption_state.interruption_count += 1
        interruption_state.last_interruption_time = datetime.now()
        
        # Get recovery strategy
        recovery_strategy = self.recovery_strategies.get(interruption.type)
        if not recovery_strategy:
            return await self._handle_unknown_interruption(interruption, dialogue_context)
        
        # Execute recovery actions
        recovery_result = await self._execute_recovery_actions(
            interruption, recovery_strategy, dialogue_context, interruption_state, db
        )
        
        # Update metrics
        self.metrics["total_interruptions"] += 1
        self.metrics["interruption_types"][interruption.type.value] = (
            self.metrics["interruption_types"].get(interruption.type.value, 0) + 1
        )
        
        return recovery_result
    
    async def _execute_recovery_actions(
        self,
        interruption: InterruptionEvent,
        recovery_strategy: Dict[str, Any],
        dialogue_context: DialogueContext,
        interruption_state: InterruptionState,
        db: Session
    ) -> Dict[str, Any]:
        """
        Execute recovery actions based on strategy
        """
        recovery_actions = recovery_strategy["immediate_actions"]
        
        # Save current context if needed
        if not recovery_strategy.get("clear_context", False):
            interruption_state.saved_context = dialogue_context.collected_info.copy()
            interruption_state.recovery_stack.append(dialogue_context.current_state)
        
        # Execute each recovery action
        for action in recovery_actions:
            await self._execute_recovery_action(
                action, interruption, dialogue_context, interruption_state, db
            )
        
        # Generate recovery response
        recovery_response = await self._generate_recovery_response(
            interruption, recovery_strategy, dialogue_context
        )
        
        # Update dialogue state
        new_state = DialogueState(recovery_strategy["next_state"])
        
        # Clear context if required
        if recovery_strategy.get("clear_context", False):
            dialogue_context.collected_info.clear()
            dialogue_context.missing_info = ["service_type", "location", "description", "urgency"]
        
        return {
            "response": recovery_response,
            "new_state": new_state,
            "interruption_handled": True,
            "recovery_actions_executed": recovery_actions,
            "context_preserved": not recovery_strategy.get("clear_context", False)
        }
    
    async def _execute_recovery_action(
        self,
        action: str,
        interruption: InterruptionEvent,
        dialogue_context: DialogueContext,
        interruption_state: InterruptionState,
        db: Session
    ) -> None:
        """
        Execute individual recovery action
        """
        if action == "acknowledge_cancellation":
            logger.info(f"Acknowledging cancellation for user")
        
        elif action == "save_current_context":
            interruption_state.saved_context = dialogue_context.collected_info.copy()
        
        elif action == "detect_new_topic":
            new_topic = await self._detect_new_topic(interruption.message, dialogue_context)
            interruption.context["new_topic"] = new_topic
        
        elif action == "identify_field_to_modify":
            field_to_modify = await self._identify_modification_field(
                interruption.message, dialogue_context
            )
            interruption.context["field_to_modify"] = field_to_modify
        
        elif action == "provide_explanation":
            explanation = await self._generate_explanation(dialogue_context)
            interruption.context["explanation"] = explanation
        
        elif action == "log_escalation_request":
            await self._log_escalation_request(interruption, dialogue_context, db)
        
        elif action == "log_complaint":
            await self._log_complaint(interruption, dialogue_context, db)
        
        # Add more recovery actions as needed
        logger.info(f"Executed recovery action: {action}")
    
    async def _detect_new_topic(
        self,
        message: str,
        dialogue_context: DialogueContext
    ) -> Optional[str]:
        """
        Detect new topic in topic change interruption
        """
        detection_prompt = f"""
        Détecter le nouveau sujet dans ce message:
        
        MESSAGE: "{message}"
        CONTEXTE ACTUEL: {dialogue_context.collected_info}
        
        Extraire le nouveau service demandé (plomberie, électricité, électroménager) ou "autre".
        Répondre uniquement par le nom du service.
        """
        
        try:
            response = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": detection_prompt}],
                max_tokens=50
            )
            
            return response.strip().lower()
        
        except Exception as e:
            logger.error(f"New topic detection failed: {e}")
            return None
    
    async def _identify_modification_field(
        self,
        message: str,
        dialogue_context: DialogueContext
    ) -> Optional[str]:
        """
        Identify which field user wants to modify
        """
        identification_prompt = f"""
        Identifier quel champ l'utilisateur veut modifier:
        
        MESSAGE: "{message}"
        INFORMATIONS ACTUELLES: {dialogue_context.collected_info}
        
        Champs possibles: service_type, location, description, urgency, contact_info
        
        Répondre uniquement par le nom du champ ou "unknown".
        """
        
        try:
            response = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": identification_prompt}],
                max_tokens=50
            )
            
            return response.strip().lower()
        
        except Exception as e:
            logger.error(f"Field identification failed: {e}")
            return "unknown"
    
    async def _generate_explanation(
        self,
        dialogue_context: DialogueContext
    ) -> str:
        """
        Generate explanation for clarification
        """
        explanation_prompt = f"""
        Générer une explication claire pour aider l'utilisateur:
        
        ÉTAT ACTUEL: {dialogue_context.current_state.value}
        INFORMATIONS COLLECTÉES: {dialogue_context.collected_info}
        INFORMATIONS MANQUANTES: {dialogue_context.missing_info}
        
        Expliquer ce qui est demandé et pourquoi c'est nécessaire.
        Utiliser un langage simple et des exemples concrets.
        """
        
        try:
            response = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": explanation_prompt}],
                max_tokens=200
            )
            
            return response.strip()
        
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return "Laissez-moi vous expliquer plus clairement ce dont j'ai besoin."
    
    async def _log_escalation_request(
        self,
        interruption: InterruptionEvent,
        dialogue_context: DialogueContext,
        db: Session
    ) -> None:
        """
        Log escalation request for human intervention
        """
        escalation_data = {
            "timestamp": interruption.timestamp.isoformat(),
            "user_message": interruption.message,
            "dialogue_state": dialogue_context.current_state.value,
            "collected_info": dialogue_context.collected_info,
            "confidence": interruption.confidence,
            "reason": "user_requested_human_help"
        }
        
        logger.info(f"Escalation request logged: {escalation_data}")
        # In a real system, this would be saved to database
    
    async def _log_complaint(
        self,
        interruption: InterruptionEvent,
        dialogue_context: DialogueContext,
        db: Session
    ) -> None:
        """
        Log complaint for quality improvement
        """
        complaint_data = {
            "timestamp": interruption.timestamp.isoformat(),
            "user_message": interruption.message,
            "dialogue_state": dialogue_context.current_state.value,
            "collected_info": dialogue_context.collected_info,
            "conversation_history": dialogue_context.conversation_history,
            "confidence": interruption.confidence
        }
        
        logger.info(f"Complaint logged: {complaint_data}")
        # In a real system, this would be saved to database
    
    async def _generate_recovery_response(
        self,
        interruption: InterruptionEvent,
        recovery_strategy: Dict[str, Any],
        dialogue_context: DialogueContext
    ) -> str:
        """
        Generate contextual recovery response
        """
        base_message = recovery_strategy["recovery_message"]
        
        # Customize message based on interruption context
        if interruption.type == InterruptionType.TOPIC_CHANGE:
            new_topic = interruption.context.get("new_topic")
            if new_topic:
                base_message += f" Je vois que vous voulez du service de {new_topic}."
        
        elif interruption.type == InterruptionType.MODIFICATION:
            field_to_modify = interruption.context.get("field_to_modify")
            if field_to_modify and field_to_modify in dialogue_context.collected_info:
                current_value = dialogue_context.collected_info[field_to_modify]
                base_message += f" Vous voulez modifier '{field_to_modify}' (actuellement: {current_value}) ?"
        
        elif interruption.type == InterruptionType.CLARIFICATION:
            explanation = interruption.context.get("explanation")
            if explanation:
                base_message += f"\n\n{explanation}"
        
        elif interruption.type == InterruptionType.ESCALATION:
            base_message += "\n\nPour contacter notre équipe : support@djobea.ai"
        
        return base_message
    
    async def _handle_unknown_interruption(
        self,
        interruption: InterruptionEvent,
        dialogue_context: DialogueContext
    ) -> Dict[str, Any]:
        """
        Handle unknown interruption types
        """
        logger.warning(f"Unknown interruption type: {interruption.type}")
        
        return {
            "response": "🤔 Je ne suis pas sûr de comprendre. Pouvez-vous clarifier votre demande ?",
            "new_state": DialogueState.CLARIFICATION,
            "interruption_handled": False,
            "recovery_actions_executed": ["request_clarification"],
            "context_preserved": True
        }
    
    async def recover_from_interruption(
        self,
        interruption_state: InterruptionState,
        dialogue_context: DialogueContext,
        db: Session
    ) -> Dict[str, Any]:
        """
        Recover from interruption and resume normal flow
        """
        if not interruption_state.is_interrupted:
            return {
                "recovered": False,
                "message": "No interruption to recover from"
            }
        
        # Restore context if available
        if interruption_state.saved_context:
            dialogue_context.collected_info.update(interruption_state.saved_context)
        
        # Restore previous state if available
        if interruption_state.recovery_stack:
            previous_state = interruption_state.recovery_stack.pop()
            dialogue_context.current_state = previous_state
        
        # Clear interruption state
        interruption_state.is_interrupted = False
        interruption_state.current_interruption = None
        interruption_state.saved_context.clear()
        
        # Update metrics
        self.metrics["successful_recoveries"] += 1
        
        return {
            "recovered": True,
            "message": "✅ Conversation reprise. Continuons où nous en étions.",
            "restored_context": interruption_state.saved_context,
            "new_state": dialogue_context.current_state
        }
    
    def get_interruption_metrics(self) -> Dict[str, Any]:
        """Get interruption handling metrics"""
        return {
            "metrics": self.metrics,
            "interruption_patterns": {
                int_type.value: {
                    "keywords_count": len(patterns["keywords"]),
                    "phrases_count": len(patterns["phrases"]),
                    "confidence_threshold": patterns["confidence_threshold"]
                }
                for int_type, patterns in self.interruption_patterns.items()
            },
            "recovery_strategies": {
                int_type.value: {
                    "actions_count": len(strategy["immediate_actions"]),
                    "next_state": strategy["next_state"],
                    "clears_context": strategy.get("clear_context", False)
                }
                for int_type, strategy in self.recovery_strategies.items()
            }
        }
    
    def analyze_interruption_patterns(
        self,
        interruption_history: List[InterruptionEvent]
    ) -> Dict[str, Any]:
        """Analyze patterns in interruption history"""
        if not interruption_history:
            return {"patterns": [], "recommendations": []}
        
        # Count interruption types
        type_counts = {}
        for interruption in interruption_history:
            type_counts[interruption.type.value] = type_counts.get(interruption.type.value, 0) + 1
        
        # Find most common interruption
        most_common = max(type_counts, key=type_counts.get)
        
        # Calculate average confidence
        avg_confidence = sum(i.confidence for i in interruption_history) / len(interruption_history)
        
        # Generate recommendations
        recommendations = []
        
        if type_counts.get("topic_change", 0) > 2:
            recommendations.append("Améliorer la clarté des questions initiales")
        
        if type_counts.get("clarification", 0) > 3:
            recommendations.append("Simplifier le langage et ajouter plus d'exemples")
        
        if avg_confidence < 0.7:
            recommendations.append("Améliorer la détection d'interruption")
        
        return {
            "patterns": {
                "most_common_interruption": most_common,
                "total_interruptions": len(interruption_history),
                "type_distribution": type_counts,
                "average_confidence": avg_confidence
            },
            "recommendations": recommendations
        }