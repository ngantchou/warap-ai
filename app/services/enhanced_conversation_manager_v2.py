"""
Enhanced Conversation Manager V2 with Action Code Integration
Implements 99% automation through structured Agent-LLM communication
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger

from app.models.action_codes import (
    ActionCode, LLMRequest, LLMResponse, ConversationState, 
    ActionResult, ActionCodeValidator
)
from app.models.database_models import User, ServiceRequest, Conversation
from app.services.code_executor import CodeExecutor
from app.services.ai_service import AIService
from app.services.whatsapp_service import WhatsAppService
from app.database import get_db
from app.config import get_settings
from sqlalchemy.orm import Session


class EnhancedConversationManagerV2:
    """
    Enhanced conversation manager with structured Agent-LLM communication
    Achieves 99% automation through systematic code-based actions
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.code_executor = CodeExecutor()
        self.ai_service = AIService()
        self.whatsapp_service = WhatsAppService()
        self.conversation_stats = {
            "total_conversations": 0,
            "automated_resolutions": 0,
            "human_escalations": 0,
            "average_turns": 0,
            "success_rate": 0.0
        }
        
        # Session storage for conversation context
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def process_message(self, phone_number: str, message: str, db: Session) -> str:
        """
        Process incoming message using structured Agent-LLM communication
        """
        try:
            self.conversation_stats["total_conversations"] += 1
            
            # Get or create session
            session_context = self.get_or_create_session(phone_number, db)
            
            # Create LLM request
            llm_request = self.create_llm_request(
                phone_number, message, session_context, db
            )
            
            # Get LLM response with action code
            llm_response = await self.get_llm_response(llm_request)
            
            # Validate LLM response
            is_valid, validation_error = ActionCodeValidator.validate_llm_response(
                llm_response.to_dict()
            )
            
            if not is_valid:
                logger.error(f"Invalid LLM response: {validation_error}")
                # Use fallback
                llm_response = self.create_fallback_response(
                    validation_error, session_context
                )
            
            # Execute action code
            action_result = await self.code_executor.execute_action(
                llm_response, phone_number, session_context, db
            )
            
            # Update session context
            self.update_session_context(
                phone_number, llm_response, action_result, db
            )
            
            # Log interaction
            await self.log_conversation_interaction(
                phone_number, message, llm_response, action_result, db
            )
            
            # Update statistics
            self.update_conversation_stats(llm_response, action_result)
            
            return llm_response.client_message
            
        except Exception as e:
            logger.error(f"Error processing message for {phone_number}: {str(e)}")
            return "Désolé, une erreur technique s'est produite. Veuillez réessayer."
    
    def get_or_create_session(self, phone_number: str, db: Session) -> Dict[str, Any]:
        """Get or create conversation session"""
        if phone_number not in self.active_sessions:
            # Get or create user
            user = db.query(User).filter(User.phone_number == phone_number).first()
            if not user:
                user = User(
                    whatsapp_id=phone_number,
                    phone_number=phone_number,
                    created_at=datetime.now()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            # Create new session
            self.active_sessions[phone_number] = {
                "user_id": user.id,
                "conversation_state": ConversationState.INITIAL,
                "session_data": {},
                "conversation_history": [],
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "turn_count": 0
            }
        
        # Update last activity
        self.active_sessions[phone_number]["last_activity"] = datetime.now()
        self.active_sessions[phone_number]["turn_count"] += 1
        
        return self.active_sessions[phone_number]
    
    def create_llm_request(
        self, 
        phone_number: str, 
        message: str, 
        session_context: Dict[str, Any], 
        db: Session
    ) -> LLMRequest:
        """Create structured LLM request"""
        
        # Get conversation history from database
        conversation_history = self.get_conversation_history(phone_number, db)
        
        # Create dynamic context
        dynamic_context = {
            "current_time": datetime.now().isoformat(),
            "turn_count": session_context["turn_count"],
            "available_services": self.settings.supported_services,
            "coverage_area": f"{self.settings.target_city}, {self.settings.target_district}",
            "service_hours": "7h-20h en semaine, 8h-18h weekend",
            "pricing_info": self.settings.service_pricing
        }
        
        return LLMRequest(
            message=message,
            user_id=phone_number,
            session_context=session_context,
            dynamic_context=dynamic_context,
            conversation_history=conversation_history,
            current_state=session_context["conversation_state"],
            timestamp=datetime.now()
        )
    
    async def get_llm_response(self, llm_request: LLMRequest) -> LLMResponse:
        """Get structured response from LLM with action code"""
        
        # Create comprehensive prompt for LLM
        prompt = self.create_structured_prompt(llm_request)
        
        try:
            # Get AI response
            ai_response = await self.ai_service.process_message_with_context(
                llm_request.message,
                llm_request.conversation_history,
                llm_request.session_context
            )
            
            # Parse response to extract action code and structured data
            parsed_response = self.parse_llm_response(ai_response, llm_request)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            return self.create_fallback_response("llm_error", llm_request.session_context)
    
    def create_structured_prompt(self, llm_request: LLMRequest) -> str:
        """Create structured prompt for LLM with action code instructions"""
        
        prompt = f"""
SYSTÈME DE COMMUNICATION AGENT-LLM DJOBEA AI

CONTEXTE:
- Utilisateur: {llm_request.user_id}
- Message: {llm_request.message}
- État conversation: {llm_request.current_state.value}
- Tour de conversation: {llm_request.session_context.get('turn_count', 1)}
- Données session: {json.dumps(llm_request.session_context.get('session_data', {}), indent=2)}

HISTORIQUE CONVERSATION:
{self.format_conversation_history(llm_request.conversation_history)}

INSTRUCTIONS:
1. Analysez le message et le contexte
2. Déterminez l'action appropriée parmi ces codes:

CODES DE COLLECTE:
- COLLECTE_BESOIN: Identifier le service initial
- COLLECTE_LOCALISATION: Préciser la localisation
- COLLECTE_DESCRIPTION: Détails du problème
- COLLECTE_DELAI: Délai d'intervention
- COLLECTE_URGENCE: Niveau d'urgence
- COLLECTE_CONTACT: Informations de contact

CODES DE VALIDATION:
- VALIDATE_SERVICE: Valider la demande
- VALIDATE_COMPLETE: Validation complète

CODES D'ACTION:
- CREATE_SERVICE: Créer demande de service
- SEARCH_PROVIDERS: Rechercher prestataires
- NOTIFY_PROVIDERS: Notifier prestataires

CODES D'INFORMATION:
- INFO_GENERALE: Informations générales
- INFO_TARIFS: Informations tarifaires
- INFO_SERVICES: Services disponibles

CODES DE GESTION:
- STATUS_CHECK: Vérifier statut
- CANCEL_SERVICE: Annuler service
- MODIFY_SERVICE: Modifier service

CODES D'ERREUR:
- CLARIFICATION: Demander clarification
- ESCALATE_HUMAN: Escalader vers humain
- ERROR_HANDLING: Gestion d'erreur

RÉPONSE REQUISE (FORMAT JSON):
{{
    "action_code": "CODE_ACTION",
    "client_message": "Message à envoyer au client",
    "extracted_data": {{
        "service_type": "...",
        "location": "...",
        "description": "...",
        "urgency": "...",
        "autres_données": "..."
    }},
    "session_update": {{
        "champs_à_mettre_à_jour": "valeurs"
    }},
    "next_state": "ÉTAT_SUIVANT",
    "confidence": 0.95,
    "metadata": {{
        "reasoning": "Explication du choix",
        "missing_info": ["info_manquante1", "info_manquante2"]
    }},
    "requires_followup": true/false
}}

CONTEXTE MÉTIER:
- Services: {llm_request.dynamic_context['available_services']}
- Zone: {llm_request.dynamic_context['coverage_area']}
- Horaires: {llm_request.dynamic_context['service_hours']}
- Tarifs: {json.dumps(llm_request.dynamic_context['pricing_info'], indent=2)}

OBJECTIF: 99% d'automatisation - Évitez l'escalade humaine sauf cas extrême.
"""
        
        return prompt
    
    def parse_llm_response(self, ai_response: str, llm_request: LLMRequest) -> LLMResponse:
        """Parse AI response to extract structured data"""
        
        try:
            # Try to extract JSON from response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                response_data = json.loads(json_str)
                
                # Validate and create LLMResponse
                is_valid, error = ActionCodeValidator.validate_llm_response(response_data)
                
                if is_valid:
                    return LLMResponse.from_dict(response_data)
                else:
                    logger.warning(f"Invalid LLM response structure: {error}")
                    
            # If JSON parsing fails, create response from text
            return self.create_response_from_text(ai_response, llm_request)
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return self.create_fallback_response("parse_error", llm_request.session_context)
    
    def create_response_from_text(self, text: str, llm_request: LLMRequest) -> LLMResponse:
        """Create LLMResponse from plain text when JSON parsing fails"""
        
        # Analyze text to determine appropriate action
        text_lower = text.lower()
        
        # Determine action based on text content
        if any(word in text_lower for word in ["service", "problème", "besoin"]):
            if any(word in text_lower for word in ["où", "localisation", "adresse"]):
                action_code = ActionCode.COLLECTE_LOCALISATION
            elif any(word in text_lower for word in ["description", "détails", "expliquer"]):
                action_code = ActionCode.COLLECTE_DESCRIPTION
            else:
                action_code = ActionCode.COLLECTE_BESOIN
        elif any(word in text_lower for word in ["prix", "tarif", "coût"]):
            action_code = ActionCode.INFO_TARIFS
        elif any(word in text_lower for word in ["urgent", "emergency", "rapidement"]):
            action_code = ActionCode.COLLECTE_URGENCE
        else:
            action_code = ActionCode.CLARIFICATION
        
        return LLMResponse(
            action_code=action_code,
            client_message=text,
            extracted_data={},
            session_update={},
            next_state=ConversationState.COLLECTING,
            confidence=0.6,
            metadata={"fallback_parsing": True},
            requires_followup=True
        )
    
    def create_fallback_response(self, error_type: str, session_context: Dict[str, Any]) -> LLMResponse:
        """Create fallback response for errors"""
        
        fallback_action = ActionCodeValidator.get_fallback_action(error_type)
        
        fallback_messages = {
            "validation_error": "Je n'ai pas bien compris votre demande. Pouvez-vous la reformuler ?",
            "llm_error": "Une erreur technique s'est produite. Pouvez-vous répéter votre demande ?",
            "parse_error": "Désolé, j'ai des difficultés à traiter votre message. Pouvez-vous être plus précis ?",
            "timeout": "Le traitement prend plus de temps que prévu. Pouvez-vous patienter ?",
            "system_error": "Une erreur système s'est produite. Nous allons résoudre cela rapidement."
        }
        
        message = fallback_messages.get(error_type, "Une erreur s'est produite. Veuillez réessayer.")
        
        return LLMResponse(
            action_code=fallback_action,
            client_message=message,
            extracted_data={"error_type": error_type},
            session_update={},
            next_state=ConversationState.ERROR,
            confidence=0.5,
            metadata={"fallback_response": True, "error_type": error_type},
            requires_followup=True
        )
    
    def update_session_context(
        self, 
        phone_number: str, 
        llm_response: LLMResponse, 
        action_result: ActionResult, 
        db: Session
    ):
        """Update session context with response and result data"""
        
        if phone_number not in self.active_sessions:
            return
        
        session = self.active_sessions[phone_number]
        
        # Update conversation state
        session["conversation_state"] = llm_response.next_state
        
        # Update session data with LLM session update
        session["session_data"].update(llm_response.session_update)
        
        # Update with action result data
        if action_result.success:
            session["session_data"].update(action_result.result_data)
        
        # Update with extracted data
        session["session_data"].update(llm_response.extracted_data)
        
        # Update last activity
        session["last_activity"] = datetime.now()
    
    async def log_conversation_interaction(
        self, 
        phone_number: str, 
        message: str, 
        llm_response: LLMResponse, 
        action_result: ActionResult, 
        db: Session
    ):
        """Log conversation interaction for audit and improvement"""
        
        try:
            # Get user
            user = db.query(User).filter(User.phone_number == phone_number).first()
            if not user:
                return
            
            # Create conversation log
            conversation = Conversation(
                user_id=user.id,
                message_content=message,
                ai_response=llm_response.client_message,
                action_code=llm_response.action_code.value,
                conversation_state=llm_response.next_state.value,
                confidence_score=llm_response.confidence,
                action_success=action_result.success,
                execution_time=action_result.execution_time,
                metadata={
                    "extracted_data": llm_response.extracted_data,
                    "session_update": llm_response.session_update,
                    "action_result": action_result.result_data,
                    "error_message": action_result.error_message
                },
                created_at=datetime.now()
            )
            
            db.add(conversation)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging conversation: {str(e)}")
    
    def get_conversation_history(self, phone_number: str, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history from database"""
        
        try:
            user = db.query(User).filter(User.phone_number == phone_number).first()
            if not user:
                return []
            
            conversations = db.query(Conversation)\
                .filter(Conversation.user_id == user.id)\
                .order_by(Conversation.created_at.desc())\
                .limit(limit)\
                .all()
            
            history = []
            for conv in reversed(conversations):
                history.append({
                    "message": conv.message_content,
                    "response": conv.ai_response,
                    "action_code": conv.action_code,
                    "timestamp": conv.created_at.isoformat(),
                    "confidence": conv.confidence_score
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    def format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for LLM prompt"""
        
        if not history:
            return "Aucun historique de conversation"
        
        formatted_history = []
        for i, conv in enumerate(history[-5:]):  # Last 5 conversations
            formatted_history.append(
                f"Tour {i+1}:\n"
                f"Client: {conv['message']}\n"
                f"Assistant: {conv['response']}\n"
                f"Action: {conv['action_code']}\n"
                f"Confiance: {conv.get('confidence', 0):.2f}\n"
            )
        
        return "\n".join(formatted_history)
    
    def update_conversation_stats(self, llm_response: LLMResponse, action_result: ActionResult):
        """Update conversation statistics"""
        
        if llm_response.action_code == ActionCode.ESCALATE_HUMAN:
            self.conversation_stats["human_escalations"] += 1
        elif action_result.success:
            self.conversation_stats["automated_resolutions"] += 1
        
        # Calculate success rate
        total = self.conversation_stats["total_conversations"]
        if total > 0:
            success_rate = (self.conversation_stats["automated_resolutions"] / total) * 100
            self.conversation_stats["success_rate"] = success_rate
    
    def cleanup_expired_sessions(self, max_inactive_hours: int = 1):
        """Clean up expired sessions"""
        
        current_time = datetime.now()
        expired_sessions = []
        
        for phone_number, session in self.active_sessions.items():
            inactive_time = current_time - session["last_activity"]
            if inactive_time.total_seconds() > (max_inactive_hours * 3600):
                expired_sessions.append(phone_number)
        
        for phone_number in expired_sessions:
            del self.active_sessions[phone_number]
            logger.info(f"Cleaned up expired session for {phone_number}")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        
        automation_rate = 0
        if self.conversation_stats["total_conversations"] > 0:
            automation_rate = (
                (self.conversation_stats["total_conversations"] - self.conversation_stats["human_escalations"]) /
                self.conversation_stats["total_conversations"]
            ) * 100
        
        return {
            "total_conversations": self.conversation_stats["total_conversations"],
            "automated_resolutions": self.conversation_stats["automated_resolutions"],
            "human_escalations": self.conversation_stats["human_escalations"],
            "automation_rate": automation_rate,
            "success_rate": self.conversation_stats["success_rate"],
            "active_sessions": len(self.active_sessions),
            "code_executor_stats": self.code_executor.get_execution_stats()
        }


# Global instance
enhanced_conversation_manager_v2 = EnhancedConversationManagerV2()