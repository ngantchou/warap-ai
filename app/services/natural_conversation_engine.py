"""
Natural Conversation Engine for Djobea AI
Creates seamless, human-like conversations where database operations are completely invisible
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from sqlalchemy.orm import Session
from anthropic import Anthropic

from app.config import get_settings
from app.services.ai_service import AIService
from app.services.context_manager import ConversationContextManager
from app.services.intent_analyzer import IntentAnalyzer
from app.services.response_generator import NaturalResponseGenerator
from app.utils.conversation_state import ConversationState, ConversationPhase
from app.models.database_models import User, ServiceRequest, Conversation, RequestStatus
from app.services.provider_service import ProviderService
from app.services.whatsapp_service import WhatsAppService
# from app.services.notification_service import NotificationService
from loguru import logger

settings = get_settings()


class ConversationIntent(Enum):
    """User conversation intentions"""
    NEW_SERVICE_REQUEST = "new_service_request"
    STATUS_INQUIRY = "status_inquiry"
    MODIFY_REQUEST = "modify_request"
    CANCEL_REQUEST = "cancel_request"
    PROVIDER_FEEDBACK = "provider_feedback"
    GENERAL_INQUIRY = "general_inquiry"
    CONTINUE_PREVIOUS = "continue_previous"
    EMERGENCY = "emergency"


@dataclass
class ConversationResult:
    """Result of conversation processing"""
    response_message: str
    conversation_state: ConversationState
    system_actions: List[Dict[str, Any]]
    user_context_updated: bool = False
    requires_follow_up: bool = False
    confidence_score: float = 0.0


class NaturalConversationEngine:
    """
    Core conversation engine that creates natural, fluid conversations
    where users never know they're interacting with a database system
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
        self.context_manager = ConversationContextManager(db)
        self.intent_analyzer = IntentAnalyzer()
        self.response_generator = NaturalResponseGenerator()
        self.provider_service = ProviderService(db)
        self.whatsapp_service = WhatsAppService()
        # self.notification_service = NotificationService()
        
        # Conversation memory - maintains context across messages
        self.active_conversations: Dict[str, ConversationState] = {}
        # Persistent conversation data that accumulates information
        self.conversation_data: Dict[str, Dict[str, Any]] = {}
    
    async def process_natural_conversation(
        self, 
        user_identifier: str, 
        message: str,
        whatsapp_id: Optional[str] = None
    ) -> ConversationResult:
        """
        Main entry point for processing natural conversations
        Completely hides database operations behind natural language
        """
        try:
            logger.info(f"Processing natural conversation for {user_identifier}: {message}")
            
            # Get or create conversation context
            conversation_state = await self._get_conversation_context(user_identifier)
            
            # Analyze user intent naturally
            intent_analysis = await self.intent_analyzer.analyze_intent(
                message, conversation_state.get_history(), conversation_state.current_phase
            )
            
            # Update conversation context with new message
            await self.context_manager.add_message(
                user_identifier, message, "user", intent_analysis
            )
            
            # Accumulate extracted information from this message
            extracted_info = intent_analysis.get('extracted_info', {})
            if user_identifier in self.conversation_data:
                # Merge new information with accumulated data
                for key, value in extracted_info.items():
                    if value is not None:
                        self.conversation_data[user_identifier]['collected_info'][key] = value
                        if conversation_state.pending_request_data is None:
                            conversation_state.pending_request_data = {}
                        conversation_state.pending_request_data[key] = value
            
            # Process based on detected intent
            result = await self._process_by_intent(
                user_identifier, message, intent_analysis, conversation_state
            )
            
            # Generate natural response
            logger.info(f"Processing result before response generation: {result}")
            final_response = await self.response_generator.generate_natural_response(
                intent_analysis, conversation_state, result, message
            )
            logger.info(f"Generated response: {final_response}")
            
            # Update conversation state
            conversation_state.last_message = message
            conversation_state.last_response = final_response
            conversation_state.message_count += 1
            
            # Save conversation state
            self.active_conversations[user_identifier] = conversation_state
            
            # Log conversation for analytics (invisible to user)
            await self._log_conversation_analytics(user_identifier, message, final_response, intent_analysis)
            
            return ConversationResult(
                response_message=final_response,
                conversation_state=conversation_state,
                system_actions=result.get("system_actions", []),
                user_context_updated=True,
                requires_follow_up=intent_analysis.get("requires_follow_up", False),
                confidence_score=intent_analysis.get("confidence", 0.8)
            )
            
        except Exception as e:
            logger.error(f"Error in natural conversation processing: {e}")
            # Graceful fallback
            return await self._generate_fallback_response(user_identifier, message)
    
    async def _get_conversation_context(self, user_identifier: str) -> ConversationState:
        """Get existing conversation context or create new one with accumulated data persistence"""
        if user_identifier in self.active_conversations:
            # Update from persistent data
            existing_state = self.active_conversations[user_identifier]
            if user_identifier in self.conversation_data:
                # Merge accumulated data
                stored_data = self.conversation_data[user_identifier]
                if 'collected_info' in stored_data:
                    existing_state.collected_info.update(stored_data['collected_info'])
                if 'pending_request_data' in stored_data:
                    existing_state.pending_request_data = stored_data['pending_request_data']
            return existing_state
        
        # Initialize persistent data storage for this user
        if user_identifier not in self.conversation_data:
            self.conversation_data[user_identifier] = {
                'collected_info': {},
                'pending_request_data': {},
                'conversation_history': [],
                'current_phase': 'greeting',
                'message_count': 0
            }
        
        # Load from database or create new
        context = await self.context_manager.get_or_create_context(user_identifier)
        
        # Get persistent data
        stored_data = self.conversation_data[user_identifier]
        
        conversation_state = ConversationState(
            user_identifier=user_identifier,
            current_phase=ConversationPhase.GREETING,
            context_data=context,
            message_count=stored_data.get('message_count', 0)
        )
        
        # Restore accumulated data
        conversation_state.collected_info = stored_data.get('collected_info', {})
        conversation_state.pending_request_data = stored_data.get('pending_request_data', None)
        
        # Store in active conversations
        self.active_conversations[user_identifier] = conversation_state
        
        return conversation_state
    
    async def _process_by_intent(
        self, 
        user_identifier: str, 
        message: str, 
        intent_analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Process conversation based on detected intent"""
        
        intent = ConversationIntent(intent_analysis.get("primary_intent", "general_inquiry"))
        logger.info(f"Processing intent: {intent} for user {user_identifier}")
        
        # Check if we're in an ongoing conversation and should continue gathering information
        if (conversation_state.current_phase == ConversationPhase.INFORMATION_GATHERING or 
            conversation_state.pending_request_data is not None or
            (user_identifier in self.conversation_data and 
             self.conversation_data[user_identifier]['collected_info'] and
             any(self.conversation_data[user_identifier]['collected_info'].values()))):
            # Force continuation of previous conversation regardless of detected intent
            return await self._handle_continuation(user_identifier, message, intent_analysis, conversation_state)
        
        if intent == ConversationIntent.NEW_SERVICE_REQUEST:
            # Always process service requests through the continuation logic to handle missing fields
            result = await self._handle_service_request(user_identifier, message, intent_analysis, conversation_state)
            
            # If the service request needs continuation, make sure we set it up correctly
            if result.get("action") == "continue_conversation":
                conversation_state.current_phase = ConversationPhase.INFORMATION_GATHERING
                return result
            
            return result
        
        elif intent == ConversationIntent.STATUS_INQUIRY:
            return await self._handle_status_inquiry(user_identifier, conversation_state)
        
        elif intent == ConversationIntent.CANCEL_REQUEST:
            return await self._handle_cancellation(user_identifier, message, conversation_state)
        
        elif intent == ConversationIntent.MODIFY_REQUEST:
            return await self._handle_modification(user_identifier, message, intent_analysis, conversation_state)
        
        elif intent == ConversationIntent.EMERGENCY:
            return await self._handle_emergency(user_identifier, message, intent_analysis, conversation_state)
        
        elif intent == ConversationIntent.CONTINUE_PREVIOUS:
            return await self._handle_continuation(user_identifier, message, intent_analysis, conversation_state)
        
        else:
            return await self._handle_general_inquiry(user_identifier, message, conversation_state)
    
    async def _handle_service_request(
        self, 
        user_identifier: str, 
        message: str, 
        intent_analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle new service requests naturally with accumulated data"""
        
        logger.info(f"Entering _handle_service_request for user {user_identifier}")
        
        # Extract service information from current message
        current_info = intent_analysis.get("extracted_info", {})
        
        # Merge with accumulated conversation data
        accumulated_info = self.conversation_data.get(user_identifier, {}).get('collected_info', {})
        
        # Combine all collected information (prioritize new info over old, but filter None values)
        service_info = {**accumulated_info}
        for key, value in current_info.items():
            if value is not None and value != "":
                service_info[key] = value
        
        # Update persistent data
        if user_identifier in self.conversation_data:
            self.conversation_data[user_identifier]['collected_info'].update(service_info)
        
        # Get or create user (invisible to user)
        user = await self._get_or_create_user(user_identifier)
        
        # Check if we have enough information using accumulated data
        required_fields = ["service_type", "location", "description"]
        missing_fields = [field for field in required_fields if not service_info.get(field) or service_info.get(field) is None]
        
        # Log debug info for troubleshooting
        logger.info(f"Service info collected: {service_info}")
        logger.info(f"Missing fields identified: {missing_fields}")
        
        if missing_fields:
            # Continue conversation to gather missing info naturally
            conversation_state.current_phase = ConversationPhase.INFORMATION_GATHERING
            conversation_state.pending_request_data = service_info
            
            # Ensure state persistence
            if user_identifier in self.conversation_data:
                self.conversation_data[user_identifier]['current_phase'] = 'information_gathering'
                self.conversation_data[user_identifier]['pending_request_data'] = service_info
            
            logger.info(f"Continuing conversation for user {user_identifier} - missing: {missing_fields}")
            
            return {
                "action": "continue_conversation",
                "missing_fields": missing_fields,
                "partial_data": service_info,
                "system_actions": []
            }
        
        # We have enough information - create service request (invisible to user)
        service_request = await self._create_service_request(user, service_info)
        
        # Start provider matching process (invisible to user)
        await self._initiate_provider_matching(service_request)
        
        # Update conversation state
        conversation_state.current_phase = ConversationPhase.REQUEST_PROCESSING
        conversation_state.active_request_id = service_request.id
        
        return {
            "action": "request_created",
            "request_id": service_request.id,
            "service_info": service_info,
            "system_actions": [
                {"type": "provider_search", "request_id": service_request.id},
                {"type": "instant_confirmation", "request_id": service_request.id}
            ]
        }
    
    async def _handle_status_inquiry(self, user_identifier: str, conversation_state: ConversationState) -> Dict[str, Any]:
        """Handle status inquiries naturally"""
        
        user = await self._get_or_create_user(user_identifier)
        
        # Get user's current requests (invisible database query)
        current_requests = self.db.query(ServiceRequest)\
            .filter(ServiceRequest.user_id == user.id)\
            .filter(ServiceRequest.status.in_([
                RequestStatus.PENDING, 
                RequestStatus.PROVIDER_NOTIFIED, 
                RequestStatus.ASSIGNED, 
                RequestStatus.IN_PROGRESS
            ]))\
            .order_by(ServiceRequest.created_at.desc())\
            .all()
        
        if not current_requests:
            # No active requests
            return {
                "action": "no_active_requests",
                "system_actions": []
            }
        
        # Return status information
        return {
            "action": "status_provided",
            "requests": [self._format_request_info(req) for req in current_requests],
            "system_actions": []
        }
    
    async def _handle_cancellation(
        self, 
        user_identifier: str, 
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle cancellation requests naturally"""
        
        user = await self._get_or_create_user(user_identifier)
        
        # Find cancellable requests
        active_requests = self.db.query(ServiceRequest)\
            .filter(ServiceRequest.user_id == user.id)\
            .filter(ServiceRequest.status.in_([
                RequestStatus.PENDING, 
                RequestStatus.PROVIDER_NOTIFIED
            ]))\
            .order_by(ServiceRequest.created_at.desc())\
            .all()
        
        if not active_requests:
            return {
                "action": "no_cancellable_requests",
                "system_actions": []
            }
        
        # Process cancellation
        request_to_cancel = active_requests[0]  # Most recent
        request_to_cancel.status = RequestStatus.CANCELLED
        request_to_cancel.updated_at = datetime.utcnow()
        self.db.commit()
        
        conversation_state.current_phase = ConversationPhase.COMPLETION
        
        return {
            "action": "request_cancelled",
            "cancelled_request": self._format_request_info(request_to_cancel),
            "system_actions": [
                {"type": "cancel_provider_notifications", "request_id": request_to_cancel.id}
            ]
        }
    
    async def _handle_emergency(
        self, 
        user_identifier: str, 
        message: str, 
        intent_analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle emergency situations with priority processing"""
        
        # Process as urgent service request
        service_info = intent_analysis.get("extracted_info", {})
        service_info["urgency"] = "URGENT"
        service_info["priority"] = "HIGH"
        
        # Fast-track processing
        user = await self._get_or_create_user(user_identifier)
        service_request = await self._create_service_request(user, service_info)
        
        # Priority provider matching
        await self._initiate_emergency_provider_matching(service_request)
        
        conversation_state.current_phase = ConversationPhase.EMERGENCY_PROCESSING
        conversation_state.active_request_id = service_request.id
        
        return {
            "action": "emergency_processed",
            "request_id": service_request.id,
            "service_info": service_info,
            "system_actions": [
                {"type": "emergency_provider_search", "request_id": service_request.id},
                {"type": "immediate_confirmation", "request_id": service_request.id}
            ]
        }
    
    async def _handle_continuation(
        self, 
        user_identifier: str, 
        message: str, 
        intent_analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle continuation of previous conversation"""
        
        # Get accumulated data from persistent storage
        accumulated_info = self.conversation_data.get(user_identifier, {}).get('collected_info', {})
        
        # Get new information from current message
        new_info = intent_analysis.get("extracted_info", {})
        
        # Merge all information (prioritize new over old, but keep existing if new is None)
        for key, value in new_info.items():
            if value is not None:
                accumulated_info[key] = value
        
        # Update persistent storage
        if user_identifier in self.conversation_data:
            self.conversation_data[user_identifier]['collected_info'] = accumulated_info
        
        # Update conversation state
        conversation_state.pending_request_data = accumulated_info
        conversation_state.current_phase = ConversationPhase.INFORMATION_GATHERING
        
        # Check if complete now using accumulated data
        required_fields = ["service_type", "location", "description"]
        missing_fields = [field for field in required_fields if not accumulated_info.get(field)]
        
        if not missing_fields:
            # Now complete - create request
            user = await self._get_or_create_user(user_identifier)
            service_request = await self._create_service_request(user, accumulated_info)
            await self._initiate_provider_matching(service_request)
            
            conversation_state.current_phase = ConversationPhase.REQUEST_PROCESSING
            conversation_state.active_request_id = service_request.id
            conversation_state.pending_request_data = None
            
            return {
                "action": "request_completed",
                "request_id": service_request.id,
                "service_info": accumulated_info,
                "system_actions": [
                    {"type": "provider_search", "request_id": service_request.id}
                ]
            }
        else:
            return {
                "action": "continue_gathering",
                "missing_fields": missing_fields,
                "partial_data": accumulated_info,
                "system_actions": []
            }
    
    async def _handle_general_inquiry(
        self, 
        user_identifier: str, 
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle general inquiries and small talk"""
        
        return {
            "action": "general_response",
            "system_actions": []
        }
    
    async def _get_or_create_user(self, user_identifier: str) -> User:
        """Get or create user (invisible to conversation)"""
        
        # Try phone number format first
        if user_identifier.startswith("237") or user_identifier.startswith("+237"):
            phone = user_identifier.replace("+", "")
            user = self.db.query(User).filter(User.whatsapp_id == phone).first()
            if user:
                return user
        
        # Try web session format
        user = self.db.query(User).filter(User.whatsapp_id == user_identifier).first()
        if user:
            return user
        
        # Create new user
        user = User(
            whatsapp_id=user_identifier,
            phone_number=user_identifier if user_identifier.startswith("237") else None,
            created_at=datetime.utcnow()
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Created new user: {user.id} for identifier: {user_identifier}")
        return user
    
    async def _create_service_request(self, user: User, service_info: Dict[str, Any]) -> ServiceRequest:
        """Create service request (invisible to conversation)"""
        
        service_request = ServiceRequest(
            user_id=user.id,
            service_type=service_info.get("service_type"),
            description=service_info.get("description"),
            location=service_info.get("location"),
            urgency=service_info.get("urgency", "normal"),
            status=RequestStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(service_request)
        self.db.commit()
        self.db.refresh(service_request)
        
        logger.info(f"Created service request: {service_request.id} for user: {user.id}")
        return service_request
    
    async def _initiate_provider_matching(self, service_request: ServiceRequest):
        """Start provider matching process (invisible to user)"""
        
        # This will be handled by the existing provider matching system
        # in the background without user awareness
        asyncio.create_task(
            self.notification_service.notify_providers_for_request(service_request)
        )
    
    async def _initiate_emergency_provider_matching(self, service_request: ServiceRequest):
        """Priority provider matching for emergencies"""
        
        # Enhanced priority matching
        asyncio.create_task(
            self.notification_service.notify_providers_for_request(service_request)
        )
    
    def _format_request_info(self, request: ServiceRequest) -> Dict[str, Any]:
        """Format request information for responses"""
        
        return {
            "id": request.id,
            "service_type": request.service_type,
            "description": request.description,
            "location": request.location,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "urgency": request.urgency
        }
    
    async def _log_conversation_analytics(
        self, 
        user_identifier: str, 
        message: str, 
        response: str, 
        intent_analysis: Dict[str, Any]
    ):
        """Log conversation for analytics (invisible to user)"""
        
        try:
            user = await self._get_or_create_user(user_identifier)
            
            conversation = Conversation(
                user_id=user.id,
                message_type="incoming",
                message_content=message,
                ai_response=response,
                created_at=datetime.utcnow()
            )
            
            self.db.add(conversation)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging conversation analytics: {e}")
    
    async def _generate_fallback_response(self, user_identifier: str, message: str) -> ConversationResult:
        """Generate fallback response when system fails"""
        
        fallback_message = """
        Bonjour ! Je suis l'assistant Djobea AI pour les services à domicile. 
        
        Je peux vous aider avec :
        🔧 Problèmes de plomberie
        ⚡ Problèmes électriques  
        🏠 Réparation d'électroménager
        
        Décrivez-moi votre problème et je trouverai le bon prestataire pour vous !
        """
        
        conversation_state = ConversationState(
            user_identifier=user_identifier,
            current_phase=ConversationPhase.GREETING
        )
        
        return ConversationResult(
            response_message=fallback_message,
            conversation_state=conversation_state,
            system_actions=[],
            confidence_score=0.5
        )