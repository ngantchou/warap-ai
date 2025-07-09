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

# Global conversation cache to maintain state across instances
CONVERSATION_CACHE = {}
CONVERSATION_DATA_CACHE = {}


class ConversationIntent(Enum):
    """User conversation intentions"""
    NEW_SERVICE_REQUEST = "new_service_request"
    STATUS_INQUIRY = "status_inquiry"
    VIEW_MY_REQUESTS = "view_my_requests"
    VIEW_REQUEST_DETAILS = "view_request_details"
    MODIFY_REQUEST = "modify_request"
    CANCEL_REQUEST = "cancel_request"
    PROVIDER_FEEDBACK = "provider_feedback"
    GENERAL_INQUIRY = "general_inquiry"
    CONTINUE_PREVIOUS = "continue_previous"
    EMERGENCY = "emergency"
    INFO_REQUEST = "info_request"  # For FAQ, pricing, service info, etc.
    HUMAN_CONTACT = "human_contact"  # For requesting human support


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
        
        # Use global cache to maintain state across instances
        global CONVERSATION_CACHE, CONVERSATION_DATA_CACHE
        self.active_conversations = CONVERSATION_CACHE
        self.conversation_data = CONVERSATION_DATA_CACHE
    
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
            
            # Pass intent as string to response generator  
            intent_analysis_for_response = intent_analysis.copy()
            intent_analysis_for_response["primary_intent"] = intent_analysis.get("primary_intent", "general_inquiry")
            
            final_response = await self.response_generator.generate_natural_response(
                intent_analysis_for_response, conversation_state, result, message
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
        
        primary_intent = intent_analysis.get("primary_intent", "general_inquiry")
        
        # Map string intents to enum values
        intent_mapping = {
            "new_service_request": ConversationIntent.NEW_SERVICE_REQUEST,
            "status_inquiry": ConversationIntent.STATUS_INQUIRY,
            "view_my_requests": ConversationIntent.VIEW_MY_REQUESTS,
            "view_request_details": ConversationIntent.VIEW_REQUEST_DETAILS,
            "modify_request": ConversationIntent.MODIFY_REQUEST,
            "cancel_request": ConversationIntent.CANCEL_REQUEST,
            "provider_feedback": ConversationIntent.PROVIDER_FEEDBACK,
            "general_inquiry": ConversationIntent.GENERAL_INQUIRY,
            "continue_previous": ConversationIntent.CONTINUE_PREVIOUS,
            "emergency": ConversationIntent.EMERGENCY,
            "info_request": ConversationIntent.INFO_REQUEST,
            "human_contact": ConversationIntent.HUMAN_CONTACT
        }
        
        intent = intent_mapping.get(primary_intent, ConversationIntent.GENERAL_INQUIRY)
        logger.info(f"Processing intent: {intent} for user {user_identifier}")
        
        # Direct routing for specific intents
        if intent == ConversationIntent.HUMAN_CONTACT:
            logger.info(f"Routing HUMAN_CONTACT to handler for user {user_identifier}")
            # Clear conversation state for human contact requests
            conversation_state.current_phase = ConversationPhase.GREETING
            conversation_state.pending_request_data = None
            if user_identifier in self.conversation_data:
                self.conversation_data[user_identifier]['collected_info'] = {}
            return await self._handle_human_contact_request(user_identifier, message, conversation_state)
        
        elif intent == ConversationIntent.INFO_REQUEST:
            logger.info(f"Routing INFO_REQUEST to LLM conversation manager for user {user_identifier}")
            # Clear conversation state for informational intents
            conversation_state.current_phase = ConversationPhase.GREETING
            conversation_state.pending_request_data = None
            if user_identifier in self.conversation_data:
                self.conversation_data[user_identifier]['collected_info'] = {}
            return await self._handle_info_request(user_identifier, message, conversation_state)
        
        # Check if we're in an ongoing conversation and should continue gathering information
        # BUT allow specific intents to override this behavior
        exempt_intents = [ConversationIntent.VIEW_MY_REQUESTS, ConversationIntent.VIEW_REQUEST_DETAILS, 
                         ConversationIntent.MODIFY_REQUEST, ConversationIntent.CANCEL_REQUEST, 
                         ConversationIntent.STATUS_INQUIRY]
        
        # Skip continuation logic for priority intents
        if intent not in exempt_intents and (conversation_state.current_phase == ConversationPhase.INFORMATION_GATHERING or 
             conversation_state.pending_request_data is not None or
             (user_identifier in self.conversation_data and 
              self.conversation_data[user_identifier]['collected_info'] and
              any(self.conversation_data[user_identifier]['collected_info'].values()))):
            # Force continuation of previous conversation for non-specific intents
            logger.info("Routing to continuation handler")
            return await self._handle_continuation(user_identifier, message, intent_analysis, conversation_state)
        
        # Handle explicit continuation intent first
        if intent == ConversationIntent.CONTINUE_PREVIOUS:
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
        
        elif intent == ConversationIntent.VIEW_MY_REQUESTS:
            logger.info(f"Routing to view_my_requests handler for user {user_identifier}")
            # Clear conversation state for specific intents - don't continue previous conversations
            conversation_state.current_phase = ConversationPhase.GREETING
            conversation_state.pending_request_data = None
            # Clear conversation data cache temporarily for this intent
            if user_identifier in self.conversation_data:
                self.conversation_data[user_identifier]['collected_info'] = {}
            return await self._handle_view_my_requests(user_identifier, conversation_state)
        
        elif intent == ConversationIntent.VIEW_REQUEST_DETAILS:
            logger.info(f"Routing to view_request_details handler for user {user_identifier}")
            request_ref = intent_analysis.get("request_reference")
            logger.info(f"DEBUG - request_ref from intent_analysis: {request_ref}")
            # Use the original message for better handling
            original_message = message.strip()
            logger.info(f"DEBUG - original_message: {original_message}")
            # Clear conversation state for specific intents
            conversation_state.current_phase = ConversationPhase.GREETING
            conversation_state.pending_request_data = None
            if user_identifier in self.conversation_data:
                self.conversation_data[user_identifier]['collected_info'] = {}
            return await self._handle_view_request_details(user_identifier, original_message, conversation_state)
        
        elif intent == ConversationIntent.CANCEL_REQUEST:
            return await self._handle_cancellation(user_identifier, message, conversation_state)
        
        elif intent == ConversationIntent.MODIFY_REQUEST:
            return await self._handle_modification(user_identifier, message, intent_analysis, conversation_state)
        
        elif intent == ConversationIntent.EMERGENCY:
            return await self._handle_emergency(user_identifier, message, intent_analysis, conversation_state)
        
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
        else:
            # Initialize if not exists
            self.conversation_data[user_identifier] = {
                'collected_info': service_info,
                'pending_request_data': {},
                'conversation_history': [],
                'current_phase': 'information_gathering',
                'message_count': 0
            }
        
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
                RequestStatus.PENDING.value, 
                RequestStatus.ASSIGNED.value, 
                RequestStatus.IN_PROGRESS.value
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
                RequestStatus.PENDING.value
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
        request_to_cancel.status = RequestStatus.CANCELLED.value
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
        
        # Log debug info
        logger.info(f"Continuation - accumulated_info: {accumulated_info}")
        logger.info(f"Continuation - new_info: {new_info}")
        
        # Merge all information (prioritize new over old, but keep existing if new is None)
        for key, value in new_info.items():
            if value is not None and value != "":
                accumulated_info[key] = value
        
        # Update persistent storage
        if user_identifier in self.conversation_data:
            self.conversation_data[user_identifier]['collected_info'] = accumulated_info
        else:
            # Initialize if not exists
            self.conversation_data[user_identifier] = {
                'collected_info': accumulated_info,
                'pending_request_data': {},
                'conversation_history': [],
                'current_phase': 'information_gathering',
                'message_count': 0
            }
        
        # Update conversation state
        conversation_state.pending_request_data = accumulated_info
        conversation_state.current_phase = ConversationPhase.INFORMATION_GATHERING
        
        # Check if complete now using accumulated data - relaxed requirement
        required_fields = ["service_type", "location"]
        missing_fields = [field for field in required_fields if not accumulated_info.get(field) or accumulated_info.get(field) is None]
        
        logger.info(f"Continuation - final accumulated_info: {accumulated_info}")
        logger.info(f"Continuation - missing_fields: {missing_fields}")
        
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
    
    async def _handle_view_my_requests(
        self, 
        user_identifier: str, 
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle viewing user's existing requests"""
        
        try:
            user = await self._get_or_create_user(user_identifier)
            
            # Get all user's requests (both active and completed)
            all_requests = self.db.query(ServiceRequest)\
                .filter(ServiceRequest.user_id == user.id)\
                .order_by(ServiceRequest.created_at.desc())\
                .all()
            
            if not all_requests:
                return {
                    "action": "no_requests_found",
                    "system_actions": []
                }
            
            # Separate active and completed requests
            active_requests = [req for req in all_requests if req.status in [
                RequestStatus.PENDING.value, RequestStatus.ASSIGNED.value, RequestStatus.IN_PROGRESS.value
            ]]
            
            completed_requests = [req for req in all_requests if req.status in [
                RequestStatus.COMPLETED.value, RequestStatus.CANCELLED.value
            ]]
            
            # Debug: Log the raw request data
            logger.info(f"DEBUG - Active requests: {len(active_requests)}")
            logger.info(f"DEBUG - Completed requests: {len(completed_requests)}")
            
            # Format request info carefully
            active_formatted = []
            for req in active_requests:
                try:
                    formatted = self._format_request_info(req)
                    active_formatted.append(formatted)
                    logger.info(f"DEBUG - Formatted active request: {formatted}")
                except Exception as e:
                    logger.error(f"DEBUG - Error formatting active request {req.id}: {e}")
                    
            completed_formatted = []
            for req in completed_requests:
                try:
                    formatted = self._format_request_info(req)
                    completed_formatted.append(formatted)
                    logger.info(f"DEBUG - Formatted completed request: {formatted}")
                except Exception as e:
                    logger.error(f"DEBUG - Error formatting completed request {req.id}: {e}")
            
            return {
                "action": "requests_listed",
                "active_requests": active_formatted,
                "completed_requests": completed_formatted,
                "system_actions": []
            }
            
        except Exception as e:
            logger.error(f"DEBUG - Error in _handle_view_my_requests: {e}")
            import traceback
            logger.error(f"DEBUG - Traceback: {traceback.format_exc()}")
            raise
    
    async def _handle_view_request_details(
        self, 
        user_identifier: str, 
        request_reference: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle viewing details of a specific request"""
        
        try:
            user = await self._get_or_create_user(user_identifier)
            
            # Get user's requests ordered by creation date (newest first)
            all_requests = self.db.query(ServiceRequest)\
                .filter(ServiceRequest.user_id == user.id)\
                .order_by(ServiceRequest.created_at.desc())\
                .all()
            
            if not all_requests:
                return {
                    "action": "request_not_found",
                    "request_reference": request_reference,
                    "system_actions": []
                }
            
            request = None
            
            # Try to find request by different reference formats
            if request_reference.startswith("DJB-"):
                # Direct DJB-XXX format
                request_id = int(request_reference.split('-')[-1])
                request = self.db.query(ServiceRequest)\
                    .filter(ServiceRequest.user_id == user.id)\
                    .filter(ServiceRequest.id == request_id)\
                    .first()
            else:
                # Simple number - treat as position in user's request list
                try:
                    position = int(request_reference)
                    if 1 <= position <= len(all_requests):
                        request = all_requests[position - 1]  # Convert to 0-based index
                except ValueError:
                    pass
            
            if not request:
                return {
                    "action": "request_not_found",
                    "request_reference": request_reference,
                    "system_actions": []
                }
            
            # Format detailed request information
            request_details = self._format_detailed_request_info(request)
            
            return {
                "action": "show_request_details",
                "request_details": request_details,
                "system_actions": []
            }
            
        except Exception as e:
            logger.error(f"Error in _handle_view_request_details: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "action": "error",
                "error_message": "Erreur lors de la récupération des détails de la demande",
                "system_actions": []
            }
    
    async def _handle_modification(
        self, 
        user_identifier: str, 
        message: str,
        intent_analysis: Dict[str, Any],
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle request modification naturally"""
        
        user = await self._get_or_create_user(user_identifier)
        
        # Check if there's a specific request ID mentioned
        request_id = self._extract_request_id(message)
        
        # Get modifiable requests
        modifiable_requests = self.db.query(ServiceRequest)\
            .filter(ServiceRequest.user_id == user.id)\
            .filter(ServiceRequest.status.in_([
                RequestStatus.PENDING.value
            ]))\
            .order_by(ServiceRequest.created_at.desc())\
            .all()
        
        if not modifiable_requests:
            return {
                "action": "no_modifiable_requests",
                "system_actions": []
            }
        
        # If specific request ID mentioned, find it
        if request_id:
            target_request = next(
                (req for req in modifiable_requests if str(req.id) == request_id or 
                 f"DJB-{str(req.id).zfill(3)}" == request_id.upper()), 
                None
            )
            if target_request:
                return {
                    "action": "show_request_details",
                    "request_details": self._format_request_info(target_request),
                    "modification_options": ["description", "urgency", "location"],
                    "system_actions": []
                }
        
        # Show all modifiable requests for selection
        return {
            "action": "show_modifiable_requests",
            "modifiable_requests": [self._format_request_info(req) for req in modifiable_requests],
            "system_actions": []
        }
    
    async def _handle_info_request(
        self, 
        user_identifier: str, 
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle information requests (FAQ, help, service info) using LLM system"""
        
        # Clear any ongoing conversation state for info requests
        conversation_state.current_phase = ConversationPhase.GREETING
        conversation_state.pending_request_data = None
        if user_identifier in self.conversation_data:
            self.conversation_data[user_identifier]['collected_info'] = {}
        
        # Import here to avoid circular import
        from app.services.llm_conversation_manager import LLMConversationManager
        
        # Create LLM conversation manager
        llm_manager = LLMConversationManager(self.db)
        
        # Process the message through the LLM system
        try:
            llm_result = await llm_manager.process_message(
                user_identifier=user_identifier,
                message=message,
                session_id=f"info_request_{user_identifier}"
            )
            
            # Extract the response from LLM result
            response_text = llm_result.get('response', 'Je peux vous aider avec vos questions.')
            
            return {
                "action": "llm_info_response",
                "response": response_text,
                "system_actions": []
            }
        except Exception as e:
            logger.error(f"Error in LLM info request processing: {e}")
            # Fallback to basic info handling
            message_lower = message.lower()
            
            if "faq" in message_lower or "aide" in message_lower:
                return {
                    "action": "provide_faq",
                    "system_actions": []
                }
            elif "tarif" in message_lower or "prix" in message_lower:
                return {
                    "action": "provide_pricing",
                    "system_actions": []
                }
            elif "service" in message_lower:
                return {
                    "action": "provide_services",
                    "system_actions": []
                }
            else:
                return {
                    "action": "provide_general_info",
                    "system_actions": []
                }
    
    async def _handle_human_contact_request(
        self, 
        user_identifier: str, 
        message: str,
        conversation_state: ConversationState
    ) -> Dict[str, Any]:
        """Handle requests to speak with a human"""
        
        # Clear any ongoing conversation state for human contact requests
        conversation_state.current_phase = ConversationPhase.GREETING
        conversation_state.pending_request_data = None
        if user_identifier in self.conversation_data:
            self.conversation_data[user_identifier]['collected_info'] = {}
        
        # Get user information for context
        user = await self._get_or_create_user(user_identifier)
        
        # Check if user has any active requests
        active_requests = self.db.query(ServiceRequest)\
            .filter(ServiceRequest.user_id == user.id)\
            .filter(ServiceRequest.status.in_([
                RequestStatus.PENDING.value,
                RequestStatus.ASSIGNED.value,
                RequestStatus.IN_PROGRESS.value
            ]))\
            .order_by(ServiceRequest.created_at.desc())\
            .all()
        
        # Context for human contact
        context = {
            "user_phone": user.phone_number,
            "user_name": user.name,
            "active_requests_count": len(active_requests),
            "recent_requests": [self._format_request_info(req) for req in active_requests[:3]] if active_requests else [],
            "contact_reason": message.lower()
        }
        
        return {
            "action": "human_contact_response",
            "context": context,
            "system_actions": ["create_support_ticket"]
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
        try:
            if hasattr(self, 'notification_service') and self.notification_service:
                asyncio.create_task(
                    self.notification_service.notify_providers_for_request(service_request)
                )
            else:
                # Fallback: Log that provider matching would start here
                logger.info(f"Provider matching initiated for request {service_request.id}")
                # The existing provider matching system will pick this up
        except Exception as e:
            logger.error(f"Error initiating provider matching: {e}")
            # Continue without failing the conversation
    
    async def _initiate_emergency_provider_matching(self, service_request: ServiceRequest):
        """Priority provider matching for emergencies"""
        
        # Enhanced priority matching
        try:
            if hasattr(self, 'notification_service') and self.notification_service:
                asyncio.create_task(
                    self.notification_service.notify_providers_for_request(service_request)
                )
            else:
                # Fallback: Log that emergency provider matching would start here
                logger.info(f"Emergency provider matching initiated for request {service_request.id}")
                # The existing provider matching system will pick this up with priority
        except Exception as e:
            logger.error(f"Error initiating emergency provider matching: {e}")
            # Continue without failing the conversation
    
    def _extract_request_id(self, message: str) -> Optional[str]:
        """Extract request ID from user message"""
        import re
        
        # Look for patterns like "DJB-001", "DJB-015", or just "001", "015"
        patterns = [
            r'DJB-(\d{3})',
            r'#(\d{3})',
            r'(\d{3})',
            r'demande\s+(\d+)',
            r'request\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1) if pattern.startswith('DJB') or pattern.startswith('#') else match.group(1)
        
        return None
    
    def _format_request_info(self, request: ServiceRequest) -> Dict[str, Any]:
        """Format request information for responses"""
        
        return {
            "id": request.id,
            "request_code": f"DJB-{str(request.id).zfill(3)}",
            "service_type": request.service_type,
            "description": request.description,
            "location": request.location,
            "status": request.status,
            "created_at": request.created_at.isoformat(),
            "urgency": request.urgency
        }
    
    def _format_detailed_request_info(self, request: ServiceRequest) -> Dict[str, Any]:
        """Format detailed request information for specific request view"""
        
        # Simple time display without timezone complications
        time_display = "Récemment"
        
        # Try to format creation time safely
        try:
            if hasattr(request, 'created_at') and request.created_at:
                # Convert to string and extract date/time part
                created_str = str(request.created_at)
                if ' ' in created_str:
                    date_part, time_part = created_str.split(' ', 1)
                    time_display = f"Créé: {date_part} {time_part[:8]}"  # Show only HH:MM:SS
                else:
                    time_display = f"Créé: {created_str[:19]}"
        except Exception:
            time_display = "Récemment"
        
        # Get status display
        status_display = {
            "en attente": "⏳ En attente",
            "assigned": "👤 Assigné",
            "in_progress": "🔧 En cours",
            "completed": "✅ Terminé",
            "cancelled": "❌ Annulé"
        }.get(request.status, request.status)
        
        # Get urgency display
        urgency_display = {
            "urgent": "🚨 Urgent",
            "normal": "📋 Normal",
            "low": "⏰ Faible"
        }.get(request.urgency, request.urgency)
        
        # Get service type display
        service_display = {
            "plomberie": "🔧 Plomberie",
            "électricité": "⚡ Électricité",
            "réparation électroménager": "🏠 Électroménager"
        }.get(request.service_type, request.service_type)
        
        return {
            "id": request.id,
            "request_code": f"DJB-{str(request.id).zfill(3)}",
            "service_type": request.service_type,
            "service_display": service_display,
            "description": request.description,
            "location": request.location,
            "status": request.status,
            "status_display": status_display,
            "urgency": request.urgency,
            "urgency_display": urgency_display,
            "created_at": request.created_at.isoformat(),
            "time_since_creation": time_display,
            "updated_at": request.updated_at.isoformat() if request.updated_at else None
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