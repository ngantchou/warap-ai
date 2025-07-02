"""
Enhanced Conversation Manager for Djobea AI
Integrates multi-LLM orchestration with advanced state management and proactive engagement
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import User, ServiceRequest, Conversation
from app.services.multi_llm_orchestrator import (
    MultiLLMOrchestrator, ConversationContext, ProcessingResult
)
from app.services.conversation_state_machine import (
    ConversationStateMachine, ConversationState, TriggerEvent
)
from app.services.proactive_engagement_service import (
    ProactiveEngagementService, EngagementTrigger
)
from app.services.whatsapp_service import WhatsAppService
from app.services.request_service import RequestService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class EnhancedConversationManager:
    """
    Enhanced conversation manager integrating multi-LLM orchestration,
    advanced state management, and proactive engagement
    """
    
    def __init__(self):
        self.llm_orchestrator = MultiLLMOrchestrator()
        self.state_machine = ConversationStateMachine()
        self.proactive_service = ProactiveEngagementService()
        self.whatsapp_service = WhatsAppService()
        # Services will be injected when methods are called
        self.request_service = None
        
    async def process_message(
        self,
        phone_number: str,
        message: str,
        media_url: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Main message processing pipeline with enhanced multi-LLM capabilities
        """
        try:
            if not db:
                db = next(get_db())
            
            # Initialize services with database session if needed
            if not self.request_service:
                from app.services.request_service import RequestService
                self.request_service = RequestService(db)
            
            logger.info(f"Processing enhanced message from {phone_number}")
            
            # Step 1: Get or create user and conversation context
            user = await self._get_or_create_user(phone_number, db)
            conversation_history = await self._load_conversation_history(user.id, db)
            current_state = await self._get_current_conversation_state(user.id, db)
            
            # Step 2: Create comprehensive conversation context
            context = ConversationContext(
                user_id=str(user.id),
                phone_number=phone_number,
                message=message,
                conversation_history=conversation_history,
                current_state=current_state,
                requires_multimodal=bool(media_url)
            )
            
            # Step 3: Multi-LLM processing
            processing_result = await self.llm_orchestrator.process_conversation(context)
            
            # Step 4: Determine state transition
            trigger_event = self._determine_trigger_event(
                current_state, 
                processing_result,
                context
            )
            
            # Step 5: Execute state transition and system actions
            new_state, system_messages = await self.state_machine.handle_state_transition(
                ConversationState(current_state),
                trigger_event,
                self._build_transition_context(context, processing_result),
                db
            )
            
            # Step 6: Handle proactive engagement scheduling
            await self._schedule_proactive_engagement(
                context,
                new_state,
                processing_result
            )
            
            # Step 7: Store conversation and update state
            await self._store_conversation_turn(
                user.id,
                message,
                processing_result.response,
                new_state.value,
                processing_result.extracted_data,
                db
            )
            
            # Step 8: Prepare enhanced response
            response = await self._prepare_enhanced_response(
                processing_result,
                system_messages,
                new_state,
                context
            )
            
            logger.info(f"Enhanced conversation processing completed for {phone_number}")
            
            return {
                "response": response,
                "confidence": processing_result.confidence,
                "state": new_state.value,
                "extracted_data": processing_result.extracted_data,
                "system_actions": processing_result.system_actions,
                "llm_provider": processing_result.provider.value
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced conversation processing: {e}")
            return await self._generate_fallback_response(phone_number, message)

    async def _get_or_create_user(self, phone_number: str, db: Session) -> User:
        """Get existing user or create new one"""
        try:
            user = db.query(User).filter(User.phone_number == phone_number).first()
            
            if not user:
                user = User(
                    phone_number=phone_number,
                    first_name="Client",
                    created_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Created new user for {phone_number}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error getting/creating user: {e}")
            db.rollback()
            raise

    async def _load_conversation_history(self, user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Load recent conversation history for context"""
        try:
            conversations = db.query(Conversation)\
                .filter(Conversation.user_id == user_id)\
                .order_by(Conversation.created_at.desc())\
                .limit(10)\
                .all()
            
            history = []
            for conv in reversed(conversations):
                history.append({
                    "timestamp": conv.created_at.isoformat(),
                    "message": conv.message_content,
                    "ai_response": conv.ai_response,
                    "confidence": conv.confidence_score or 0.8
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return []

    async def _get_current_conversation_state(self, user_id: int, db: Session) -> str:
        """Get current conversation state"""
        try:
            # Check for active service requests
            active_request = db.query(ServiceRequest)\
                .filter(ServiceRequest.user_id == user_id)\
                .filter(ServiceRequest.status.in_([
                    "PENDING", "PROVIDER_NOTIFIED", "ASSIGNED", "IN_PROGRESS"
                ]))\
                .order_by(ServiceRequest.created_at.desc())\
                .first()
            
            if active_request:
                if active_request.status == "PENDING":
                    return "SEARCHING_PROVIDERS"
                elif active_request.status in ["PROVIDER_NOTIFIED", "ASSIGNED"]:
                    return "PROVIDER_ASSIGNED"
                elif active_request.status == "IN_PROGRESS":
                    return "SERVICE_IN_PROGRESS"
            
            # Check recent conversations for state indicators
            recent_conv = db.query(Conversation)\
                .filter(Conversation.user_id == user_id)\
                .order_by(Conversation.created_at.desc())\
                .first()
            
            if recent_conv and recent_conv.conversation_state:
                return recent_conv.conversation_state
            
            return "INITIAL"
            
        except Exception as e:
            logger.error(f"Error getting conversation state: {e}")
            return "INITIAL"

    def _determine_trigger_event(
        self,
        current_state: str,
        processing_result: ProcessingResult,
        context: ConversationContext
    ) -> TriggerEvent:
        """Determine appropriate trigger event based on processing results"""
        try:
            extracted_data = processing_result.extracted_data or {}
            intention = extracted_data.get("intention_primaire", "")
            entities = extracted_data.get("entities", {})
            
            # High-priority triggers
            if "annuler" in context.message.lower() or intention == "annulation":
                return TriggerEvent.CANCELLATION_REQUESTED
            
            if "urgence" in context.message.lower() or intention == "urgence":
                return TriggerEvent.ESCALATION_REQUIRED
            
            # State-specific logic
            if current_state == "INITIAL":
                return TriggerEvent.NEW_MESSAGE
            
            elif current_state == "COLLECTING_INFO":
                if self._has_complete_info(entities):
                    return TriggerEvent.INFO_COMPLETE
                return TriggerEvent.NEW_MESSAGE
            
            elif current_state == "CONFIRMING_REQUEST":
                if any(word in context.message.lower() for word in ["oui", "confirme", "ok", "d'accord"]):
                    return TriggerEvent.REQUEST_CONFIRMED
                return TriggerEvent.NEW_MESSAGE
            
            elif current_state == "PRESENTING_OPTIONS":
                if "automatique" in context.message.lower():
                    return TriggerEvent.AUTO_ASSIGN
                elif any(word in context.message.lower() for word in ["1", "2", "3", "choisir"]):
                    return TriggerEvent.PROVIDER_SELECTED
                return TriggerEvent.NEW_MESSAGE
            
            elif current_state == "SERVICE_IN_PROGRESS":
                if "terminé" in context.message.lower() or "fini" in context.message.lower():
                    return TriggerEvent.SERVICE_COMPLETED
                return TriggerEvent.NEW_MESSAGE
            
            elif current_state == "PAYMENT_PENDING":
                if "payé" in context.message.lower() or "paiement" in context.message.lower():
                    return TriggerEvent.PAYMENT_COMPLETED
                return TriggerEvent.NEW_MESSAGE
            
            # Default
            return TriggerEvent.NEW_MESSAGE
            
        except Exception as e:
            logger.error(f"Error determining trigger event: {e}")
            return TriggerEvent.NEW_MESSAGE

    def _has_complete_info(self, entities: Dict[str, Any]) -> bool:
        """Check if all required information is collected"""
        required_fields = ["service_type", "location", "description"]
        return all(entities.get(field) for field in required_fields)

    def _build_transition_context(
        self,
        conversation_context: ConversationContext,
        processing_result: ProcessingResult
    ) -> Dict[str, Any]:
        """Build context for state transitions"""
        return {
            "user_id": conversation_context.user_id,
            "phone_number": conversation_context.phone_number,
            "conversation_id": f"{conversation_context.user_id}_{datetime.utcnow().strftime('%Y%m%d')}",
            "extracted_entities": processing_result.extracted_data or {},
            "confidence": processing_result.confidence,
            "conversation_history": conversation_context.conversation_history,
            "current_message": conversation_context.message
        }

    async def _schedule_proactive_engagement(
        self,
        context: ConversationContext,
        new_state: ConversationState,
        processing_result: ProcessingResult
    ):
        """Schedule appropriate proactive engagement based on state"""
        try:
            engagement_mapping = {
                ConversationState.SEARCHING_PROVIDERS: EngagementTrigger.REQUEST_CREATED,
                ConversationState.PROVIDER_ASSIGNED: EngagementTrigger.PROVIDER_ASSIGNED,
                ConversationState.SERVICE_IN_PROGRESS: EngagementTrigger.SERVICE_IN_PROGRESS,
                ConversationState.PAYMENT_PENDING: EngagementTrigger.PAYMENT_PENDING
            }
            
            if new_state in engagement_mapping:
                trigger = engagement_mapping[new_state]
                
                engagement_context = {
                    "user_profile": context.user_profile,
                    "extracted_entities": processing_result.extracted_data,
                    "confidence": processing_result.confidence,
                    "phone_number": context.phone_number
                }
                
                await self.proactive_service.schedule_engagement(
                    user_id=context.user_id,
                    phone_number=context.phone_number,
                    trigger=trigger,
                    context=engagement_context
                )
                
                logger.info(f"Scheduled proactive engagement: {trigger.value}")
            
        except Exception as e:
            logger.error(f"Error scheduling proactive engagement: {e}")

    async def _store_conversation_turn(
        self,
        user_id: int,
        message: str,
        ai_response: str,
        state: str,
        extracted_data: Optional[Dict[str, Any]],
        db: Session
    ):
        """Store conversation turn in database"""
        try:
            conversation = Conversation(
                user_id=user_id,
                message_content=message,
                message_type="incoming",
                ai_response=ai_response,
                conversation_state=state,
                confidence_score=extracted_data.get("confidence") if extracted_data else None,
                extracted_entities=json.dumps(extracted_data) if extracted_data else None,
                created_at=datetime.utcnow()
            )
            
            db.add(conversation)
            db.commit()
            
            logger.info(f"Stored conversation turn for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            db.rollback()

    async def _prepare_enhanced_response(
        self,
        processing_result: ProcessingResult,
        system_messages: List[str],
        new_state: ConversationState,
        context: ConversationContext
    ) -> str:
        """Prepare enhanced response with system actions integration"""
        try:
            base_response = processing_result.response
            
            # Add system messages if any
            if system_messages:
                additional_info = "\n\n".join(system_messages)
                base_response = f"{base_response}\n\n{additional_info}"
            
            # Add state-specific enhancements
            state_enhancements = {
                ConversationState.SEARCHING_PROVIDERS: "🔍 Recherche en cours...",
                ConversationState.PROVIDER_ASSIGNED: "✅ Prestataire assigné !",
                ConversationState.SERVICE_IN_PROGRESS: "🔧 Service en cours",
                ConversationState.PAYMENT_PENDING: "💳 Paiement requis",
                ConversationState.COMPLETED: "✅ Service terminé avec succès !"
            }
            
            if new_state in state_enhancements:
                enhancement = state_enhancements[new_state]
                base_response = f"{enhancement}\n\n{base_response}"
            
            return base_response
            
        except Exception as e:
            logger.error(f"Error preparing enhanced response: {e}")
            return processing_result.response

    async def _generate_fallback_response(
        self,
        phone_number: str,
        message: str
    ) -> Dict[str, Any]:
        """Generate fallback response when main processing fails"""
        fallback_responses = [
            "Merci pour votre message. Je traite votre demande et vous réponds rapidement.",
            "J'ai bien reçu votre message. Un conseiller analyse votre situation.",
            "Merci de me faire confiance. Je m'occupe de votre demande en priorité."
        ]
        
        import random
        response = random.choice(fallback_responses)
        
        return {
            "response": response,
            "confidence": 0.6,
            "state": "INITIAL",
            "extracted_data": {},
            "system_actions": ["fallback_response"],
            "llm_provider": "fallback"
        }

    async def handle_provider_response(
        self,
        provider_phone: str,
        message: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """Handle provider responses (OUI/NON) with enhanced processing"""
        try:
            if not db:
                db = next(get_db())
            
            logger.info(f"Processing provider response from {provider_phone}")
            
            # Create context for provider response
            context = ConversationContext(
                user_id="provider",
                phone_number=provider_phone,
                message=message,
                conversation_history=[],
                current_state="PROVIDER_RESPONDING"
            )
            
            # Use LLM to analyze provider response
            processing_result = await self.llm_orchestrator.process_conversation(context)
            
            # Determine if response is acceptance or decline
            response_lower = message.lower().strip()
            is_acceptance = any(word in response_lower for word in [
                "oui", "yes", "ok", "d'accord", "accepte", "j'accepte"
            ])
            
            if is_acceptance:
                trigger = TriggerEvent.PROVIDER_ACCEPTED
            else:
                trigger = TriggerEvent.PROVIDER_DECLINED
            
            # Process the provider response through system
            # This would integrate with existing provider notification logic
            
            return {
                "response": "Réponse prestataire traitée",
                "acceptance": is_acceptance,
                "confidence": processing_result.confidence,
                "trigger": trigger.value
            }
            
        except Exception as e:
            logger.error(f"Error handling provider response: {e}")
            return {"response": "Erreur traitement réponse", "acceptance": False}

    async def get_conversation_status(
        self,
        phone_number: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get current conversation status and analytics"""
        try:
            if not db:
                db = next(get_db())
            
            user = db.query(User).filter(User.phone_number == phone_number).first()
            if not user:
                return {"status": "no_conversation", "state": "INITIAL"}
            
            current_state = await self._get_current_conversation_state(user.id, db)
            recent_conversations = await self._load_conversation_history(user.id, db)
            
            # Get active service request if any
            active_request = db.query(ServiceRequest)\
                .filter(ServiceRequest.user_id == user.id)\
                .filter(ServiceRequest.status.in_([
                    "PENDING", "PROVIDER_NOTIFIED", "ASSIGNED", "IN_PROGRESS"
                ]))\
                .order_by(ServiceRequest.created_at.desc())\
                .first()
            
            # Get proactive engagement status
            engagement_status = self.proactive_service.get_engagement_status(str(user.id))
            
            return {
                "status": "active",
                "state": current_state,
                "user_id": user.id,
                "conversation_turns": len(recent_conversations),
                "active_request": {
                    "id": active_request.id,
                    "status": active_request.status,
                    "service_type": active_request.service_type
                } if active_request else None,
                "proactive_engagements": engagement_status
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation status: {e}")
            return {"status": "error", "state": "UNKNOWN"}

# Global enhanced conversation manager instance
enhanced_conversation_manager = EnhancedConversationManager()