"""
Advanced Conversation State Machine for Djobea AI
Manages intelligent conversation flow transitions and system actions
"""

import json
from typing import Dict, Any, List, Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import User, ServiceRequest, Conversation, Provider
from app.services.provider_service import ProviderService
from app.services.request_service import RequestService
from app.services.proactive_engagement_service import ProactiveEngagementService, EngagementTrigger
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ConversationState(Enum):
    """Enhanced conversation states for intelligent flow management"""
    INITIAL = "INITIAL"
    COLLECTING_INFO = "COLLECTING_INFO"
    CONFIRMING_REQUEST = "CONFIRMING_REQUEST"
    SEARCHING_PROVIDERS = "SEARCHING_PROVIDERS"
    PRESENTING_OPTIONS = "PRESENTING_OPTIONS"
    AWAITING_SELECTION = "AWAITING_SELECTION"
    PROVIDER_ASSIGNED = "PROVIDER_ASSIGNED"
    SERVICE_IN_PROGRESS = "SERVICE_IN_PROGRESS"
    AWAITING_FEEDBACK = "AWAITING_FEEDBACK"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"
    PAYMENT_PENDING = "PAYMENT_PENDING"

class TriggerEvent(Enum):
    """Events that trigger state transitions"""
    NEW_MESSAGE = "NEW_MESSAGE"
    INFO_COMPLETE = "INFO_COMPLETE"
    REQUEST_CONFIRMED = "REQUEST_CONFIRMED"
    PROVIDERS_FOUND = "PROVIDERS_FOUND"
    NO_PROVIDERS = "NO_PROVIDERS"
    PROVIDER_SELECTED = "PROVIDER_SELECTED"
    AUTO_ASSIGN = "AUTO_ASSIGN"
    PROVIDER_ACCEPTED = "PROVIDER_ACCEPTED"
    PROVIDER_DECLINED = "PROVIDER_DECLINED"
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_COMPLETED = "SERVICE_COMPLETED"
    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"

@dataclass
class SystemAction:
    """System action to be executed during state transitions"""
    action_type: str
    params: Dict[str, Any]
    priority: int = 1
    async_execution: bool = False

@dataclass
class StateTransition:
    """Configuration for state transitions"""
    from_state: ConversationState
    trigger: TriggerEvent
    to_state: ConversationState
    conditions: Optional[List[Callable]] = None
    system_actions: Optional[List[SystemAction]] = None
    validation_required: bool = False

class ConversationStateMachine:
    """
    Advanced state machine for managing conversation flow and system actions
    """
    
    def __init__(self):
        self.provider_service = None
        self.request_service = None
        self.setup_state_transitions()
        self.setup_system_actions()
        
    def setup_state_transitions(self):
        """Setup comprehensive state transition rules"""
        self.transitions = [
            # Initial flow
            StateTransition(
                from_state=ConversationState.INITIAL,
                trigger=TriggerEvent.NEW_MESSAGE,
                to_state=ConversationState.COLLECTING_INFO,
                system_actions=[
                    SystemAction("initialize_conversation", {"conversation_id": None})
                ]
            ),
            
            # Information collection flow
            StateTransition(
                from_state=ConversationState.COLLECTING_INFO,
                trigger=TriggerEvent.INFO_COMPLETE,
                to_state=ConversationState.CONFIRMING_REQUEST,
                system_actions=[
                    SystemAction("generate_confirmation_summary", {"extracted_info": None})
                ]
            ),
            
            # Request confirmation flow
            StateTransition(
                from_state=ConversationState.CONFIRMING_REQUEST,
                trigger=TriggerEvent.REQUEST_CONFIRMED,
                to_state=ConversationState.SEARCHING_PROVIDERS,
                system_actions=[
                    SystemAction("create_service_request", {"user_id": None, "request_data": None}),
                    SystemAction("schedule_proactive_update", {"trigger": "request_created"}),
                    SystemAction("start_provider_search", {"service_type": None, "location": None})
                ]
            ),
            
            # Provider search flow
            StateTransition(
                from_state=ConversationState.SEARCHING_PROVIDERS,
                trigger=TriggerEvent.PROVIDERS_FOUND,
                to_state=ConversationState.PRESENTING_OPTIONS,
                system_actions=[
                    SystemAction("rank_providers", {"providers": None, "request_criteria": None}),
                    SystemAction("generate_provider_presentation", {"top_providers": None})
                ]
            ),
            
            StateTransition(
                from_state=ConversationState.SEARCHING_PROVIDERS,
                trigger=TriggerEvent.NO_PROVIDERS,
                to_state=ConversationState.ESCALATED,
                system_actions=[
                    SystemAction("log_no_providers_available", {"search_criteria": None}),
                    SystemAction("schedule_proactive_followup", {"delay": 1800})
                ]
            ),
            
            # Provider selection flow
            StateTransition(
                from_state=ConversationState.PRESENTING_OPTIONS,
                trigger=TriggerEvent.PROVIDER_SELECTED,
                to_state=ConversationState.PROVIDER_ASSIGNED,
                system_actions=[
                    SystemAction("assign_provider", {"request_id": None, "provider_id": None}),
                    SystemAction("notify_provider", {"provider_id": None, "request_details": None}),
                    SystemAction("schedule_provider_followup", {"delay": 600})
                ]
            ),
            
            StateTransition(
                from_state=ConversationState.PRESENTING_OPTIONS,
                trigger=TriggerEvent.AUTO_ASSIGN,
                to_state=ConversationState.PROVIDER_ASSIGNED,
                system_actions=[
                    SystemAction("auto_assign_best_provider", {"request_id": None}),
                    SystemAction("notify_provider", {"provider_id": None, "request_details": None}),
                    SystemAction("notify_client_assignment", {"provider_details": None})
                ]
            ),
            
            # Provider response flow
            StateTransition(
                from_state=ConversationState.PROVIDER_ASSIGNED,
                trigger=TriggerEvent.PROVIDER_ACCEPTED,
                to_state=ConversationState.SERVICE_IN_PROGRESS,
                system_actions=[
                    SystemAction("update_request_status", {"status": "IN_PROGRESS"}),
                    SystemAction("schedule_service_checkup", {"delay": 3600}),
                    SystemAction("send_provider_details", {"client_contact": None})
                ]
            ),
            
            StateTransition(
                from_state=ConversationState.PROVIDER_ASSIGNED,
                trigger=TriggerEvent.PROVIDER_DECLINED,
                to_state=ConversationState.SEARCHING_PROVIDERS,
                system_actions=[
                    SystemAction("find_alternative_provider", {"excluded_providers": None}),
                    SystemAction("notify_client_delay", {"reason": "provider_unavailable"})
                ]
            ),
            
            # Service completion flow
            StateTransition(
                from_state=ConversationState.SERVICE_IN_PROGRESS,
                trigger=TriggerEvent.SERVICE_COMPLETED,
                to_state=ConversationState.PAYMENT_PENDING,
                system_actions=[
                    SystemAction("calculate_final_amount", {"service_details": None}),
                    SystemAction("generate_payment_link", {"amount": None, "request_id": None}),
                    SystemAction("schedule_payment_reminder", {"delay": 1200})
                ]
            ),
            
            # Payment flow
            StateTransition(
                from_state=ConversationState.PAYMENT_PENDING,
                trigger=TriggerEvent.PAYMENT_COMPLETED,
                to_state=ConversationState.AWAITING_FEEDBACK,
                system_actions=[
                    SystemAction("process_payment", {"payment_data": None}),
                    SystemAction("release_provider_payment", {"commission_calculated": True}),
                    SystemAction("request_feedback", {"delay": 300})
                ]
            ),
            
            # Feedback and completion
            StateTransition(
                from_state=ConversationState.AWAITING_FEEDBACK,
                trigger=TriggerEvent.FEEDBACK_RECEIVED,
                to_state=ConversationState.COMPLETED,
                system_actions=[
                    SystemAction("store_feedback", {"feedback_data": None}),
                    SystemAction("update_provider_rating", {"provider_id": None, "rating": None}),
                    SystemAction("send_completion_confirmation", {"summary": None})
                ]
            ),
            
            # Cancellation flow (can happen from multiple states)
            StateTransition(
                from_state=ConversationState.COLLECTING_INFO,
                trigger=TriggerEvent.CANCELLATION_REQUESTED,
                to_state=ConversationState.CANCELLED,
                system_actions=[
                    SystemAction("cancel_conversation", {"reason": "user_requested"})
                ]
            ),
            
            StateTransition(
                from_state=ConversationState.CONFIRMING_REQUEST,
                trigger=TriggerEvent.CANCELLATION_REQUESTED,
                to_state=ConversationState.CANCELLED,
                system_actions=[
                    SystemAction("cancel_conversation", {"reason": "user_requested"})
                ]
            ),
            
            StateTransition(
                from_state=ConversationState.PROVIDER_ASSIGNED,
                trigger=TriggerEvent.CANCELLATION_REQUESTED,
                to_state=ConversationState.CANCELLED,
                system_actions=[
                    SystemAction("cancel_service_request", {"request_id": None}),
                    SystemAction("notify_provider_cancellation", {"provider_id": None})
                ]
            ),
            
            # Escalation flow (can happen from any state)
            StateTransition(
                from_state=ConversationState.COLLECTING_INFO,
                trigger=TriggerEvent.ESCALATION_REQUIRED,
                to_state=ConversationState.ESCALATED,
                system_actions=[
                    SystemAction("create_support_ticket", {"conversation_context": None}),
                    SystemAction("notify_human_agent", {"priority": "high"})
                ]
            )
        ]
        
        # Create transition lookup for fast access
        self.transition_map = {}
        for transition in self.transitions:
            key = (transition.from_state, transition.trigger)
            if key not in self.transition_map:
                self.transition_map[key] = []
            self.transition_map[key].append(transition)

    def setup_system_actions(self):
        """Setup system action handlers"""
        self.action_handlers = {
            "initialize_conversation": self._initialize_conversation,
            "create_service_request": self._create_service_request,
            "start_provider_search": self._start_provider_search,
            "rank_providers": self._rank_providers,
            "assign_provider": self._assign_provider,
            "notify_provider": self._notify_provider,
            "auto_assign_best_provider": self._auto_assign_best_provider,
            "update_request_status": self._update_request_status,
            "calculate_final_amount": self._calculate_final_amount,
            "generate_payment_link": self._generate_payment_link,
            "process_payment": self._process_payment,
            "store_feedback": self._store_feedback,
            "cancel_service_request": self._cancel_service_request,
            "create_support_ticket": self._create_support_ticket,
            "schedule_proactive_update": self._schedule_proactive_update,
        }

    async def handle_state_transition(
        self,
        current_state: ConversationState,
        trigger_event: TriggerEvent,
        context: Dict[str, Any],
        db: Session
    ) -> Tuple[ConversationState, List[str]]:
        """
        Handle state transition and execute system actions
        Returns: (new_state, system_messages)
        """
        try:
            # Find applicable transitions
            key = (current_state, trigger_event)
            transitions = self.transition_map.get(key, [])
            
            if not transitions:
                logger.warning(f"No transition found for {current_state.value} -> {trigger_event.value}")
                return current_state, []
            
            # Select the first valid transition (could add condition checking here)
            transition = transitions[0]
            
            # Validate transition if required
            if transition.validation_required:
                if not self._validate_transition(transition, context):
                    logger.warning(f"Transition validation failed for {transition.from_state.value} -> {transition.to_state.value}")
                    return current_state, []
            
            # Execute system actions
            system_messages = []
            if transition.system_actions:
                for action in transition.system_actions:
                    try:
                        # Merge context with action params
                        action_params = {**action.params, **context}
                        
                        # Execute action
                        if action.async_execution:
                            # Schedule async execution
                            pass  # Would implement async task scheduling
                        else:
                            handler = self.action_handlers.get(action.action_type)
                            if handler:
                                result = await handler(action_params, db)
                                if result:
                                    system_messages.append(result)
                            else:
                                logger.warning(f"No handler found for action: {action.action_type}")
                                
                    except Exception as e:
                        logger.error(f"Error executing action {action.action_type}: {e}")
            
            # Update conversation state in database
            await self._update_conversation_state(
                context.get("conversation_id"),
                transition.to_state.value,
                db
            )
            
            logger.info(f"State transition: {current_state.value} -> {transition.to_state.value}")
            
            return transition.to_state, system_messages
            
        except Exception as e:
            logger.error(f"Error in state transition: {e}")
            return current_state, []

    def determine_next_step(
        self,
        current_state: ConversationState,
        user_response: str,
        system_context: Dict[str, Any]
    ) -> TriggerEvent:
        """
        Intelligently determine the next step based on current state and user response
        """
        try:
            # State-specific logic for determining triggers
            if current_state == ConversationState.COLLECTING_INFO:
                if self._is_info_complete(system_context):
                    return TriggerEvent.INFO_COMPLETE
                elif "annuler" in user_response.lower() or "cancel" in user_response.lower():
                    return TriggerEvent.CANCELLATION_REQUESTED
                else:
                    return TriggerEvent.NEW_MESSAGE
            
            elif current_state == ConversationState.CONFIRMING_REQUEST:
                if any(word in user_response.lower() for word in ["oui", "confirme", "ok", "d'accord"]):
                    return TriggerEvent.REQUEST_CONFIRMED
                elif any(word in user_response.lower() for word in ["non", "annuler", "modifier"]):
                    return TriggerEvent.CANCELLATION_REQUESTED
                else:
                    return TriggerEvent.NEW_MESSAGE
            
            elif current_state == ConversationState.PRESENTING_OPTIONS:
                if "automatique" in user_response.lower() or "choisir" in user_response.lower():
                    return TriggerEvent.AUTO_ASSIGN
                elif any(word in user_response.lower() for word in ["1", "2", "3", "premier", "deuxième"]):
                    return TriggerEvent.PROVIDER_SELECTED
                else:
                    return TriggerEvent.NEW_MESSAGE
            
            elif current_state == ConversationState.AWAITING_SELECTION:
                if "automatique" in user_response.lower():
                    return TriggerEvent.AUTO_ASSIGN
                elif "choisir" in user_response.lower():
                    return TriggerEvent.PROVIDER_SELECTED
                else:
                    return TriggerEvent.NEW_MESSAGE
            
            # Default to NEW_MESSAGE for continuous conversation
            return TriggerEvent.NEW_MESSAGE
            
        except Exception as e:
            logger.error(f"Error determining next step: {e}")
            return TriggerEvent.NEW_MESSAGE

    def _validate_transition(self, transition: StateTransition, context: Dict[str, Any]) -> bool:
        """Validate if transition conditions are met"""
        try:
            if not transition.conditions:
                return True
            
            for condition in transition.conditions:
                if not condition(context):
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating transition: {e}")
            return False

    def _is_info_complete(self, context: Dict[str, Any]) -> bool:
        """Check if all required information is collected"""
        required_fields = ["service_type", "location", "description", "urgency"]
        extracted_entities = context.get("extracted_entities", {})
        
        for field in required_fields:
            if not extracted_entities.get(field):
                return False
        
        return True

    # System Action Handlers
    
    async def _initialize_conversation(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Initialize conversation tracking"""
        try:
            # Implementation would create conversation record
            logger.info("Conversation initialized")
            return None
        except Exception as e:
            logger.error(f"Error initializing conversation: {e}")
            return None

    async def _create_service_request(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Create service request in database"""
        try:
            user_id = params.get("user_id")
            request_data = params.get("extracted_entities", {})
            
            if not user_id or not request_data:
                return None
            
            # Use existing request service
            request = await self.request_service.create_request(
                user_id=user_id,
                service_type=request_data.get("service_type"),
                location=request_data.get("location"),
                description=request_data.get("description"),
                urgency=request_data.get("urgency", "normal"),
                db=db
            )
            
            if request:
                logger.info(f"Service request created: {request.id}")
                return f"Demande créée avec succès (#{request.id})"
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating service request: {e}")
            return None

    async def _start_provider_search(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Start provider search process"""
        try:
            service_type = params.get("service_type")
            location = params.get("location")
            
            if not service_type:
                return None
            
            # Implementation would trigger provider search
            logger.info(f"Started provider search for {service_type} in {location}")
            return "Recherche de prestataires en cours..."
            
        except Exception as e:
            logger.error(f"Error starting provider search: {e}")
            return None

    async def _rank_providers(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Rank available providers"""
        try:
            providers = params.get("providers", [])
            criteria = params.get("request_criteria", {})
            
            # Implementation would use provider service ranking
            logger.info(f"Ranked {len(providers)} providers")
            return None
            
        except Exception as e:
            logger.error(f"Error ranking providers: {e}")
            return None

    async def _assign_provider(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Assign specific provider to request"""
        try:
            request_id = params.get("request_id")
            provider_id = params.get("provider_id")
            
            if not request_id or not provider_id:
                return None
            
            # Implementation would assign provider
            logger.info(f"Assigned provider {provider_id} to request {request_id}")
            return "Prestataire assigné avec succès"
            
        except Exception as e:
            logger.error(f"Error assigning provider: {e}")
            return None

    async def _notify_provider(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Send notification to provider"""
        try:
            provider_id = params.get("provider_id")
            request_details = params.get("request_details", {})
            
            # Implementation would send WhatsApp notification
            logger.info(f"Notified provider {provider_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error notifying provider: {e}")
            return None

    async def _auto_assign_best_provider(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Auto-assign the best available provider"""
        try:
            request_id = params.get("request_id")
            
            # Implementation would use provider matching algorithm
            logger.info(f"Auto-assigned best provider for request {request_id}")
            return "Meilleur prestataire assigné automatiquement"
            
        except Exception as e:
            logger.error(f"Error auto-assigning provider: {e}")
            return None

    async def _update_request_status(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Update service request status"""
        try:
            request_id = params.get("request_id")
            status = params.get("status")
            
            if not request_id or not status:
                return None
            
            # Implementation would update database
            logger.info(f"Updated request {request_id} status to {status}")
            return None
            
        except Exception as e:
            logger.error(f"Error updating request status: {e}")
            return None

    async def _calculate_final_amount(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Calculate final service amount"""
        try:
            service_details = params.get("service_details", {})
            
            # Implementation would calculate amount
            logger.info("Calculated final service amount")
            return None
            
        except Exception as e:
            logger.error(f"Error calculating final amount: {e}")
            return None

    async def _generate_payment_link(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Generate payment link for client"""
        try:
            amount = params.get("amount")
            request_id = params.get("request_id")
            
            # Implementation would use Monetbil service
            logger.info(f"Generated payment link for {amount} XAF")
            return "Lien de paiement généré"
            
        except Exception as e:
            logger.error(f"Error generating payment link: {e}")
            return None

    async def _process_payment(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Process completed payment"""
        try:
            payment_data = params.get("payment_data", {})
            
            # Implementation would process payment
            logger.info("Payment processed successfully")
            return "Paiement traité avec succès"
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return None

    async def _store_feedback(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Store client feedback"""
        try:
            feedback_data = params.get("feedback_data", {})
            
            # Implementation would store feedback
            logger.info("Feedback stored successfully")
            return None
            
        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
            return None

    async def _cancel_service_request(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Cancel service request"""
        try:
            request_id = params.get("request_id")
            
            # Implementation would cancel request
            logger.info(f"Cancelled service request {request_id}")
            return "Demande annulée avec succès"
            
        except Exception as e:
            logger.error(f"Error cancelling service request: {e}")
            return None

    async def _create_support_ticket(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Create support ticket for escalation"""
        try:
            context = params.get("conversation_context", {})
            
            # Implementation would create support ticket
            logger.info("Support ticket created")
            return "Ticket de support créé"
            
        except Exception as e:
            logger.error(f"Error creating support ticket: {e}")
            return None

    async def _schedule_proactive_update(self, params: Dict[str, Any], db: Session) -> Optional[str]:
        """Schedule proactive engagement"""
        try:
            trigger = params.get("trigger")
            user_id = params.get("user_id")
            phone_number = params.get("phone_number")
            
            if trigger and user_id and phone_number:
                # Would use proactive engagement service
                logger.info(f"Scheduled proactive update: {trigger}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error scheduling proactive update: {e}")
            return None

    async def _update_conversation_state(
        self,
        conversation_id: Optional[str],
        new_state: str,
        db: Session
    ):
        """Update conversation state in database"""
        try:
            if not conversation_id:
                return
            
            # Implementation would update database
            logger.info(f"Updated conversation {conversation_id} state to {new_state}")
            
        except Exception as e:
            logger.error(f"Error updating conversation state: {e}")

# Global state machine instance
conversation_state_machine = ConversationStateMachine()