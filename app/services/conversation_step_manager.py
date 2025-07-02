"""
Conversation Step Manager for Djobea AI
Manages conversation flow with button-based interactions and system codes
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json
import uuid

from sqlalchemy.orm import Session
from loguru import logger

from app.models.database_models import User, ServiceRequest, Conversation, RequestStatus
from app.services.ai_service import AIService
from app.config import get_settings

settings = get_settings()
ai_service = AIService()

class ConversationStep(Enum):
    """Conversation step states"""
    INITIAL = "initial"
    SERVICE_SELECTION = "service_selection"
    LOCATION_INPUT = "location_input"
    DESCRIPTION_INPUT = "description_input"
    URGENCY_SELECTION = "urgency_selection"
    CONFIRMATION = "confirmation"
    CANCELLATION_CONFIRM = "cancellation_confirm"
    MODIFICATION_SELECTION = "modification_selection"
    PAYMENT_SELECTION = "payment_selection"
    COMPLETED = "completed"

class SystemAction(Enum):
    """System action codes"""
    SEND_MESSAGE = "send_message"
    CREATE_SERVICE_REQUEST = "create_service_request"
    CANCEL_SERVICE_REQUEST = "cancel_service_request"
    UPDATE_SERVICE_REQUEST = "update_service_request"
    SEND_BUTTONS = "send_buttons"
    SEARCH_PROVIDERS = "search_providers"
    PROCESS_PAYMENT = "process_payment"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    REQUEST_CLARIFICATION = "request_clarification"

@dataclass
class ButtonOption:
    """Button option for user interface"""
    text: str
    value: str
    action: str = "select"
    style: str = "primary"  # primary, secondary, success, danger

@dataclass
class StepResponse:
    """Response from step processing"""
    message: str
    buttons: List[ButtonOption]
    next_step: ConversationStep
    system_action: SystemAction
    data: Dict[str, Any]
    requires_input: bool = False

class ConversationStepManager:
    """Manages conversation flow with steps and buttons"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_steps: Dict[str, ConversationStep] = {}
        self.user_data: Dict[str, Dict[str, Any]] = {}
    
    def get_user_step(self, user_id: str) -> ConversationStep:
        """Get current step for user"""
        return self.user_steps.get(user_id, ConversationStep.INITIAL)
    
    def set_user_step(self, user_id: str, step: ConversationStep):
        """Set current step for user"""
        self.user_steps[user_id] = step
        logger.info(f"User {user_id} moved to step: {step.value}")
    
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user conversation data"""
        return self.user_data.get(user_id, {})
    
    def set_user_data(self, user_id: str, key: str, value: Any):
        """Set user conversation data"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id][key] = value
    
    async def process_message(self, user_id: str, message: str, button_value: Optional[str] = None) -> StepResponse:
        """Process user message and return appropriate response"""
        current_step = self.get_user_step(user_id)
        user_data = self.get_user_data(user_id)
        
        logger.info(f"Processing message for user {user_id}, step: {current_step.value}, message: {message}")
        
        # Handle button clicks
        if button_value:
            return await self._handle_button_click(user_id, button_value, current_step, user_data)
        
        # Handle text input based on current step
        if current_step == ConversationStep.INITIAL:
            return await self._handle_initial_message(user_id, message)
        elif current_step == ConversationStep.SERVICE_SELECTION:
            return await self._handle_service_selection(user_id, message)
        elif current_step == ConversationStep.LOCATION_INPUT:
            return await self._handle_location_input(user_id, message)
        elif current_step == ConversationStep.DESCRIPTION_INPUT:
            return await self._handle_description_input(user_id, message)
        elif current_step == ConversationStep.URGENCY_SELECTION:
            return await self._handle_urgency_selection(user_id, message)
        elif current_step == ConversationStep.CANCELLATION_CONFIRM:
            return await self._handle_cancellation_confirm(user_id, message)
        else:
            # Use LLM to analyze uninterpreted messages
            return await self._analyze_with_llm(user_id, message, current_step)
    
    async def _handle_initial_message(self, user_id: str, message: str) -> StepResponse:
        """Handle initial user message"""
        # Analyze if user wants to cancel existing request
        if any(word in message.lower() for word in ["annul", "cancel", "stop", "arrêt"]):
            return await self._handle_cancellation_request(user_id)
        
        # Analyze if user is describing a service need
        service_analysis = await self._analyze_service_need(message)
        
        if service_analysis.get("has_service_need", False):
            service_type = service_analysis.get("service_type")
            if service_type:
                self.set_user_data(user_id, "service_type", service_type)
                self.set_user_step(user_id, ConversationStep.LOCATION_INPUT)
                
                return StepResponse(
                    message=f"🔧 Service détecté: **{service_type}**\n\nOù se trouve le problème? Précisez votre adresse ou quartier:",
                    buttons=[],
                    next_step=ConversationStep.LOCATION_INPUT,
                    system_action=SystemAction.SEND_MESSAGE,
                    data={"service_type": service_type},
                    requires_input=True
                )
        
        # Show service selection buttons
        return StepResponse(
            message="👋 Bonjour! Quel type de service recherchez-vous?",
            buttons=[
                ButtonOption("🔧 Plomberie", "plomberie", "select_service"),
                ButtonOption("⚡ Électricité", "electricite", "select_service"),
                ButtonOption("🏠 Électroménager", "electromenager", "select_service"),
                ButtonOption("❓ Autre", "autre", "select_service")
            ],
            next_step=ConversationStep.SERVICE_SELECTION,
            system_action=SystemAction.SEND_BUTTONS,
            data={}
        )
    
    async def _handle_button_click(self, user_id: str, button_value: str, current_step: ConversationStep, user_data: Dict) -> StepResponse:
        """Handle button click actions"""
        if button_value.startswith("select_service_"):
            service_type = button_value.replace("select_service_", "")
            self.set_user_data(user_id, "service_type", service_type)
            self.set_user_step(user_id, ConversationStep.LOCATION_INPUT)
            
            return StepResponse(
                message=f"🔧 Service sélectionné: **{service_type}**\n\nOù se trouve le problème? Précisez votre adresse ou quartier:",
                buttons=[],
                next_step=ConversationStep.LOCATION_INPUT,
                system_action=SystemAction.SEND_MESSAGE,
                data={"service_type": service_type},
                requires_input=True
            )
        
        elif button_value == "confirm_yes":
            return await self._create_service_request(user_id, user_data)
        
        elif button_value == "confirm_no":
            self.set_user_step(user_id, ConversationStep.INITIAL)
            return StepResponse(
                message="❌ Demande annulée. Que puis-je faire d'autre pour vous?",
                buttons=[],
                next_step=ConversationStep.INITIAL,
                system_action=SystemAction.SEND_MESSAGE,
                data={}
            )
        
        elif button_value == "cancel_yes":
            return await self._execute_cancellation(user_id)
        
        elif button_value == "cancel_no":
            self.set_user_step(user_id, ConversationStep.INITIAL)
            return StepResponse(
                message="✅ Votre demande reste active. Que puis-je faire d'autre pour vous?",
                buttons=[],
                next_step=ConversationStep.INITIAL,
                system_action=SystemAction.SEND_MESSAGE,
                data={}
            )
        
        # Default fallback
        return await self._analyze_with_llm(user_id, button_value, current_step)
    
    async def _handle_cancellation_request(self, user_id: str) -> StepResponse:
        """Handle user request to cancel"""
        # Find user's active service request
        user = self.db.query(User).filter(User.phone_number == user_id).first()
        if not user:
            return StepResponse(
                message="❌ Aucune demande trouvée à annuler.",
                buttons=[],
                next_step=ConversationStep.INITIAL,
                system_action=SystemAction.SEND_MESSAGE,
                data={}
            )
        
        active_request = self.db.query(ServiceRequest).filter(
            ServiceRequest.user_id == user.id,
            ServiceRequest.status.in_([RequestStatus.PENDING, RequestStatus.ASSIGNED])
        ).first()
        
        if not active_request:
            return StepResponse(
                message="❌ Aucune demande active à annuler.",
                buttons=[],
                next_step=ConversationStep.INITIAL,
                system_action=SystemAction.SEND_MESSAGE,
                data={}
            )
        
        self.set_user_data(user_id, "cancel_request_id", active_request.id)
        self.set_user_step(user_id, ConversationStep.CANCELLATION_CONFIRM)
        
        return StepResponse(
            message=f"""❌ **Confirmation d'annulation**

Êtes-vous sûr de vouloir annuler cette demande?

🔧 **Service**: {active_request.service_type}
📍 **Lieu**: {active_request.location}
📅 **Créée**: {active_request.created_at.strftime('%d/%m/%Y %H:%M')}

Cette action est irréversible.""",
            buttons=[
                ButtonOption("✅ Oui, annuler", "cancel_yes", "confirm", "danger"),
                ButtonOption("❌ Non, garder", "cancel_no", "confirm", "secondary")
            ],
            next_step=ConversationStep.CANCELLATION_CONFIRM,
            system_action=SystemAction.SEND_BUTTONS,
            data={"cancel_request_id": active_request.id}
        )
    
    async def _execute_cancellation(self, user_id: str) -> StepResponse:
        """Execute the cancellation"""
        user_data = self.get_user_data(user_id)
        request_id = user_data.get("cancel_request_id")
        
        if not request_id:
            return StepResponse(
                message="❌ Erreur: Demande d'annulation non trouvée.",
                buttons=[],
                next_step=ConversationStep.INITIAL,
                system_action=SystemAction.SEND_MESSAGE,
                data={}
            )
        
        service_request = self.db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if service_request:
            service_request.status = RequestStatus.CANCELLED
            service_request.updated_at = datetime.utcnow()
            self.db.commit()
            
            self.set_user_step(user_id, ConversationStep.INITIAL)
            
            return StepResponse(
                message="✅ **Demande annulée avec succès**\n\nVotre demande a été annulée. Aucun frais ne sera appliqué.\n\nQue puis-je faire d'autre pour vous?",
                buttons=[],
                next_step=ConversationStep.INITIAL,
                system_action=SystemAction.CANCEL_SERVICE_REQUEST,
                data={"cancelled_request_id": request_id}
            )
        
        return StepResponse(
            message="❌ Erreur lors de l'annulation. Contactez le support.",
            buttons=[],
            next_step=ConversationStep.INITIAL,
            system_action=SystemAction.ESCALATE_TO_HUMAN,
            data={}
        )
    
    async def _analyze_service_need(self, message: str) -> Dict[str, Any]:
        """Analyze if message contains service need using AI"""
        try:
            analysis_prompt = f"""
            Analysez ce message d'un utilisateur pour déterminer s'il décrit un besoin de service à domicile:
            
            Message: "{message}"
            
            Répondez en JSON avec:
            {{
                "has_service_need": true/false,
                "service_type": "plomberie"/"électricité"/"électroménager"/null,
                "confidence": 0.0-1.0,
                "keywords_found": ["mot1", "mot2"]
            }}
            """
            
            response = await ai_service.generate_response(analysis_prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error analyzing service need: {e}")
            return {"has_service_need": False, "service_type": None, "confidence": 0.0}
    
    async def _analyze_with_llm(self, user_id: str, message: str, current_step: ConversationStep) -> StepResponse:
        """Use LLM to analyze uninterpreted messages and return system codes"""
        try:
            context_prompt = f"""
            Contexte: Utilisateur {user_id} à l'étape {current_step.value}
            Message: "{message}"
            
            Analysez ce message et retournez une action système appropriée en JSON:
            {{
                "system_action": "send_message"/"request_clarification"/"escalate_to_human",
                "message": "Réponse à envoyer à l'utilisateur",
                "confidence": 0.0-1.0,
                "next_step": "initial"/"service_selection"/etc,
                "requires_buttons": true/false,
                "suggested_buttons": [
                    {{"text": "Texte", "value": "valeur", "action": "action"}}
                ]
            }}
            """
            
            response = await ai_service.generate_response(context_prompt)
            analysis = json.loads(response)
            
            # Convert to StepResponse
            next_step = ConversationStep(analysis.get("next_step", "initial"))
            system_action = SystemAction(analysis.get("system_action", "send_message"))
            
            buttons = []
            if analysis.get("requires_buttons", False):
                for btn_data in analysis.get("suggested_buttons", []):
                    buttons.append(ButtonOption(
                        text=btn_data["text"],
                        value=btn_data["value"],
                        action=btn_data.get("action", "select")
                    ))
            
            self.set_user_step(user_id, next_step)
            
            return StepResponse(
                message=analysis["message"],
                buttons=buttons,
                next_step=next_step,
                system_action=system_action,
                data={"ai_confidence": analysis.get("confidence", 0.0)}
            )
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            
            # Fallback response
            return StepResponse(
                message="Je n'ai pas bien compris votre demande. Pouvez-vous reformuler ou choisir une option?",
                buttons=[
                    ButtonOption("🔧 Nouveau service", "new_service", "start"),
                    ButtonOption("❌ Annuler demande", "cancel_request", "cancel"),
                    ButtonOption("❓ Aide", "help", "help")
                ],
                next_step=ConversationStep.INITIAL,
                system_action=SystemAction.REQUEST_CLARIFICATION,
                data={}
            )
    
    def format_response_for_web(self, response: StepResponse) -> Dict[str, Any]:
        """Format response for web chat widget"""
        return {
            "message": response.message,
            "buttons": [
                {
                    "text": btn.text,
                    "value": btn.value,
                    "action": btn.action,
                    "style": btn.style
                }
                for btn in response.buttons
            ],
            "system_action": response.system_action.value,
            "next_step": response.next_step.value,
            "requires_input": response.requires_input,
            "data": response.data
        }