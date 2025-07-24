"""
Enhanced Conversation Manager V3
Integrates with session management system for persistent conversations
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.conversation_session import (
    ConversationSession, ConversationState, SessionPhase, ConversationMessage,
    CollectedData, TransitionRule
)
from app.models.action_codes import ActionCode, LLMRequest, LLMResponse
from app.services.session_manager import SessionManager, get_session_manager
from app.services.code_executor import CodeExecutor
from app.services.ai_service import AIService
from app.services.enhanced_conversation_manager_v2 import EnhancedConversationManagerV2
from app.database import get_db

logger = logging.getLogger(__name__)

class EnhancedConversationManagerV3:
    """
    Enhanced conversation manager with session persistence and state management
    """
    
    def __init__(self):
        self.session_manager: SessionManager = None
        self.code_executor = CodeExecutor()
        self.ai_service = AIService()
        self.fallback_manager = EnhancedConversationManagerV2()
        
        # Conversation configuration
        self.max_retry_attempts = 3
        self.state_timeout_minutes = 30
        self.collection_timeout_minutes = 20
        
        # Performance tracking
        self.total_conversations = 0
        self.successful_conversations = 0
        self.session_creations = 0
        self.state_transitions = 0
        
        # Session manager will be initialized on first use
        self._session_manager_initialized = False
    
    async def _initialize_session_manager(self):
        """Initialize session manager"""
        if not self._session_manager_initialized:
            self.session_manager = await get_session_manager()
            await self.session_manager.start_cleanup_task()
            self._session_manager_initialized = True
            logger.info("Session manager initialized for conversation manager V3")
    
    async def process_message(
        self, 
        message: str, 
        phone_number: str, 
        user_id: str = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Process incoming message with session management
        """
        self.total_conversations += 1
        
        try:
            # Initialize session manager if needed
            await self._initialize_session_manager()
            
            # Get or create session
            session = await self._get_or_create_session(user_id or phone_number, phone_number, db)
            
            # Add incoming message to session
            incoming_message = ConversationMessage(
                message_type="incoming",
                content=message,
                timestamp=datetime.now()
            )
            
            await self.session_manager.add_message_to_session(
                session.session_id, incoming_message, db
            )
            
            # Process message based on current state
            response = await self._process_message_by_state(session, message, db)
            
            # Add outgoing response to session
            if response.get('response'):
                outgoing_message = ConversationMessage(
                    message_type="outgoing",
                    content=response['response'],
                    action_code=response.get('action_code'),
                    confidence_score=response.get('confidence_score'),
                    extracted_data=response.get('extracted_data', {}),
                    metadata=response.get('metadata', {}),
                    timestamp=datetime.now()
                )
                
                await self.session_manager.add_message_to_session(
                    session.session_id, outgoing_message, db
                )
            
            # Update session metrics
            session.metrics.update_activity()
            await self.session_manager.update_session(session, db)
            
            # Add session information to response
            response.update({
                'session_id': session.session_id,
                'conversation_state': session.current_state.value,
                'session_phase': session.current_phase.value if session.current_phase else None,
                'data_completeness': session.collected_data.collection_progress,
                'session_active': not session.is_expired()
            })
            
            self.successful_conversations += 1
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
            # Fallback to original conversation manager
            try:
                fallback_response = await self.fallback_manager.process_message(phone_number, message, db)
                return {
                    'response': fallback_response,
                    'conversation_state': 'FALLBACK',
                    'automation_rate': 0.0,
                    'session_data': {
                        'fallback_used': True,
                        'error_type': 'fallback_recovery',
                        'recovery_action': 'retry'
                    }
                }
            except Exception as fallback_error:
                logger.error(f"Fallback manager also failed: {fallback_error}")
                
                return {
                    'response': "Désolé, une erreur technique s'est produite. Veuillez réessayer.",
                    'conversation_state': 'ERROR',
                    'automation_rate': 0.0,
                    'session_data': {
                        'error_handled': True,
                        'error_type': 'system_error',
                        'recovery_action': 'retry'
                    }
                }
    
    async def _get_or_create_session(
        self, 
        user_id: str, 
        phone_number: str, 
        db: Session
    ) -> ConversationSession:
        """
        Get existing session or create new one
        """
        # Try to get existing active session
        session = await self.session_manager.get_user_active_session(user_id, db)
        
        if session:
            # Check if session is still valid
            if not session.is_expired():
                return session
            else:
                # Expire the session
                await self.session_manager.expire_session(session.session_id, db)
        
        # Create new session
        session = await self.session_manager.create_session(
            user_id=user_id,
            phone_number=phone_number,
            initial_state=ConversationState.INITIAL,
            db=db
        )
        
        self.session_creations += 1
        logger.info(f"Created new session {session.session_id} for user {user_id}")
        
        return session
    
    async def _process_message_by_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Process message based on current conversation state
        """
        current_state = session.current_state
        
        # Check for session expiration
        if session.is_expired():
            await self.session_manager.expire_session(session.session_id, db)
            return {
                'response': "Votre session a expiré. Veuillez recommencer votre demande.",
                'action_code': ActionCode.FLOW_RESTART.value,
                'conversation_state': ConversationState.EXPIRED.value
            }
        
        # Route to appropriate handler based on state
        if current_state == ConversationState.INITIAL:
            return await self._handle_initial_state(session, message, db)
        elif current_state == ConversationState.COLLECTING:
            return await self._handle_collecting_state(session, message, db)
        elif current_state == ConversationState.VALIDATING:
            return await self._handle_validating_state(session, message, db)
        elif current_state == ConversationState.CONFIRMING:
            return await self._handle_confirming_state(session, message, db)
        elif current_state == ConversationState.PROCESSING:
            return await self._handle_processing_state(session, message, db)
        elif current_state == ConversationState.COMPLETED:
            return await self._handle_completed_state(session, message, db)
        elif current_state == ConversationState.ERROR:
            return await self._handle_error_state(session, message, db)
        elif current_state == ConversationState.PAUSED:
            return await self._handle_paused_state(session, message, db)
        else:
            # Unknown state, reset to initial
            await self.session_manager.transition_session_state(
                session.session_id, ConversationState.INITIAL, "unknown_state_reset", db
            )
            return await self._handle_initial_state(session, message, db)
    
    async def _handle_initial_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in INITIAL state
        """
        # Create LLM request for initial processing
        llm_request = LLMRequest(
            message=message,
            user_id=session.user_id,
            session_context=session.get_session_summary(),
            dynamic_context=session.collected_data.to_dict(),
            conversation_history=session.get_recent_history(),
            current_state=ConversationState.INITIAL,
            timestamp=datetime.now()
        )
        
        # Get LLM response
        llm_response = await self._get_llm_response(llm_request)
        
        # Execute action code
        result = await self.code_executor.execute_action(
            llm_response, session.phone_number, session.collected_data.to_dict(), db
        )
        
        # Update session based on action result
        if result.success:
            # Update collected data if any
            if result.result_data.get('extracted_data'):
                for field, value in result.result_data['extracted_data'].items():
                    await self.session_manager.update_collected_data(
                        session.session_id, field, value, db=db
                    )
            
            # Transition to collecting state
            await self.session_manager.transition_session_state(
                session.session_id, ConversationState.COLLECTING, "initial_processing_complete", db
            )
            
            self.state_transitions += 1
        
        return {
            'response': result.result_data.get('response_message', llm_response.client_message),
            'action_code': result.action_code.value,
            'confidence_score': llm_response.confidence,
            'extracted_data': result.result_data.get('extracted_data', {}),
            'metadata': result.result_data
        }
    
    async def _handle_collecting_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in COLLECTING state
        """
        # Create LLM request for data collection
        llm_request = LLMRequest(
            message=message,
            user_id=session.user_id,
            session_context=session.get_session_summary(),
            dynamic_context=session.collected_data.to_dict(),
            conversation_history=session.get_recent_history(),
            current_state=ConversationState.COLLECTING,
            timestamp=datetime.now()
        )
        
        # Get LLM response
        llm_response = await self._get_llm_response(llm_request)
        
        # Execute action code
        result = await self.code_executor.execute_action(
            llm_response, session.phone_number, session.collected_data.to_dict(), db
        )
        
        # Update session based on action result
        if result.success:
            # Update collected data
            if result.result_data.get('extracted_data'):
                for field, value in result.result_data['extracted_data'].items():
                    await self.session_manager.update_collected_data(
                        session.session_id, field, value, db=db
                    )
            
            # Check if data collection is complete
            updated_session = await self.session_manager.get_session(session.session_id, db)
            if updated_session and updated_session.can_proceed_to_validation():
                await self.session_manager.transition_session_state(
                    session.session_id, ConversationState.VALIDATING, "data_collection_complete", db
                )
                self.state_transitions += 1
        
        return {
            'response': result.result_data.get('response_message', llm_response.client_message),
            'action_code': result.action_code.value,
            'confidence_score': llm_response.confidence,
            'extracted_data': result.result_data.get('extracted_data', {}),
            'metadata': result.result_data
        }
    
    async def _handle_validating_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in VALIDATING state
        """
        # Create LLM request for validation
        llm_request = LLMRequest(
            message=message,
            user_id=session.user_id,
            session_context=session.get_session_summary(),
            dynamic_context=session.collected_data.to_dict(),
            conversation_history=session.get_recent_history(),
            current_state=ConversationState.VALIDATING,
            timestamp=datetime.now()
        )
        
        # Get LLM response
        llm_response = await self._get_llm_response(llm_request)
        
        # Execute action code
        result = await self.code_executor.execute_action(
            llm_response, session.phone_number, session.collected_data.to_dict(), db
        )
        
        # Update session based on validation result
        if result.success:
            if result.result_data.get('validation_passed'):
                # Proceed to confirmation
                await self.session_manager.transition_session_state(
                    session.session_id, ConversationState.CONFIRMING, "validation_passed", db
                )
                self.state_transitions += 1
            elif result.result_data.get('validation_failed'):
                # Return to collection
                await self.session_manager.transition_session_state(
                    session.session_id, ConversationState.COLLECTING, "validation_failed", db
                )
                self.state_transitions += 1
        
        return {
            'response': result.result_data.get('response_message', llm_response.client_message),
            'action_code': result.action_code.value,
            'confidence_score': llm_response.confidence,
            'extracted_data': result.result_data.get('extracted_data', {}),
            'metadata': result.result_data
        }
    
    async def _handle_confirming_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in CONFIRMING state
        """
        # Create LLM request for confirmation
        llm_request = LLMRequest(
            message=message,
            user_id=session.user_id,
            session_context=session.get_session_summary(),
            dynamic_context=session.collected_data.to_dict(),
            conversation_history=session.get_recent_history(),
            current_state=ConversationState.CONFIRMING,
            timestamp=datetime.now()
        )
        
        # Get LLM response
        llm_response = await self._get_llm_response(llm_request)
        
        # Execute action code
        result = await self.code_executor.execute_action(
            llm_response, session.phone_number, session.collected_data.to_dict(), db
        )
        
        # Update session based on confirmation result
        if result.success:
            if result.result_data.get('confirmation_accepted'):
                # Proceed to processing
                await self.session_manager.transition_session_state(
                    session.session_id, ConversationState.PROCESSING, "confirmation_accepted", db
                )
                self.state_transitions += 1
            elif result.result_data.get('confirmation_rejected'):
                # Return to collection for modifications
                await self.session_manager.transition_session_state(
                    session.session_id, ConversationState.COLLECTING, "confirmation_rejected", db
                )
                self.state_transitions += 1
        
        return {
            'response': result.result_data.get('response_message', llm_response.client_message),
            'action_code': result.action_code.value,
            'confidence_score': llm_response.confidence,
            'extracted_data': result.result_data.get('extracted_data', {}),
            'metadata': result.result_data
        }
    
    async def _handle_processing_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in PROCESSING state
        """
        # Create LLM request for processing
        llm_request = LLMRequest(
            message=message,
            user_id=session.user_id,
            session_context=session.get_session_summary(),
            dynamic_context=session.collected_data.to_dict(),
            conversation_history=session.get_recent_history(),
            current_state=ConversationState.PROCESSING,
            timestamp=datetime.now()
        )
        
        # Get LLM response
        llm_response = await self._get_llm_response(llm_request)
        
        # Execute action code
        result = await self.code_executor.execute_action(
            llm_response, session.phone_number, session.collected_data.to_dict(), db
        )
        
        # Update session based on processing result
        if result.success:
            if result.result_data.get('processing_complete'):
                # Complete the session
                await self.session_manager.complete_session(session.session_id, db)
                self.state_transitions += 1
        
        return {
            'response': result.result_data.get('response_message', llm_response.client_message),
            'action_code': result.action_code.value,
            'confidence_score': llm_response.confidence,
            'extracted_data': result.result_data.get('extracted_data', {}),
            'metadata': result.result_data
        }
    
    async def _handle_completed_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in COMPLETED state
        """
        # For completed sessions, check if this is a new request
        if any(keyword in message.lower() for keyword in ['nouveau', 'nouvelle', 'autre', 'problème']):
            # Create new session for new request
            new_session = await self.session_manager.create_session(
                user_id=session.user_id,
                phone_number=session.phone_number,
                initial_state=ConversationState.INITIAL,
                db=db
            )
            
            # Process the message with new session
            return await self._handle_initial_state(new_session, message, db)
        else:
            # Handle as information request about completed session
            return {
                'response': "Votre demande précédente a été terminée. Pour une nouvelle demande, veuillez m'indiquer votre nouveau problème.",
                'action_code': ActionCode.INFO_SESSION.value,
                'conversation_state': ConversationState.COMPLETED.value
            }
    
    async def _handle_error_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in ERROR state
        """
        # Try to recover from error
        await self.session_manager.transition_session_state(
            session.session_id, ConversationState.COLLECTING, "error_recovery", db
        )
        
        # Process as if in collecting state
        return await self._handle_collecting_state(session, message, db)
    
    async def _handle_paused_state(
        self, 
        session: ConversationSession, 
        message: str, 
        db: Session
    ) -> Dict[str, Any]:
        """
        Handle message in PAUSED state
        """
        # Resume session
        await self.session_manager.transition_session_state(
            session.session_id, ConversationState.COLLECTING, "session_resumed", db
        )
        
        # Process as if in collecting state
        return await self._handle_collecting_state(session, message, db)
    
    async def _get_llm_response(self, llm_request: LLMRequest) -> LLMResponse:
        """
        Get LLM response using AI service
        """
        try:
            # Convert conversation history to the format expected by AI service
            conversation_history = []
            for msg in llm_request.conversation_history:
                if isinstance(msg, dict):
                    conversation_history.append({
                        "role": "user" if msg.get("message_type") == "incoming" else "assistant",
                        "content": msg.get("content", "")
                    })
            
            # Use AI service to extract request information
            extracted_info = self.ai_service.extract_request_info(
                message=llm_request.message,
                conversation_history=conversation_history
            )
            
            # Map AI service response to LLMResponse format
            action_code = ActionCode.DATA_COLLECTION if not extracted_info.get("is_complete") else ActionCode.DATA_VALIDATION
            
            logger.info(f"Creating LLMResponse with action_code: {action_code}")
            
            return LLMResponse(
                action_code=action_code,
                client_message=extracted_info.get("response_message", "Merci pour votre message."),
                extracted_data=extracted_info,
                session_update={},
                next_state=ConversationState.COLLECTING if not extracted_info.get("is_complete") else ConversationState.VALIDATING,
                confidence=0.8,
                metadata={"ai_service_response": extracted_info}
            )
            
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            
            # Return fallback response
            return LLMResponse(
                action_code=ActionCode.ERROR_HANDLING,
                client_message="Désolé, une erreur s'est produite. Pouvez-vous répéter votre demande ?",
                extracted_data={},
                session_update={},
                next_state=ConversationState.ERROR,
                confidence=0.5,
                metadata={"error": str(e)}
            )
    
    async def get_session_info(self, session_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get session information
        """
        return await self.session_manager.get_session_summary(session_id, db)
    
    async def get_user_session_info(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get user's active session information
        """
        session = await self.session_manager.get_user_active_session(user_id, db)
        if session:
            return session.get_session_summary()
        return None
    
    async def pause_session(self, session_id: str, db: Session) -> bool:
        """
        Pause a session
        """
        return await self.session_manager.transition_session_state(
            session_id, ConversationState.PAUSED, "user_request", db
        )
    
    async def resume_session(self, session_id: str, db: Session) -> bool:
        """
        Resume a paused session
        """
        return await self.session_manager.transition_session_state(
            session_id, ConversationState.COLLECTING, "user_request", db
        )
    
    async def cancel_session(self, session_id: str, db: Session) -> bool:
        """
        Cancel a session
        """
        return await self.session_manager.transition_session_state(
            session_id, ConversationState.CANCELLED, "user_request", db
        )
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics
        """
        success_rate = (self.successful_conversations / self.total_conversations * 100) if self.total_conversations > 0 else 0
        
        return {
            'total_conversations': self.total_conversations,
            'successful_conversations': self.successful_conversations,
            'success_rate': success_rate,
            'session_creations': self.session_creations,
            'state_transitions': self.state_transitions,
            'active_sessions': await self.session_manager.get_active_sessions_count() if self.session_manager else 0
        }
    
    async def cleanup_expired_sessions(self, db: Session) -> int:
        """
        Cleanup expired sessions
        """
        if self.session_manager:
            return await self.session_manager.cleanup_expired_sessions(db)
        return 0