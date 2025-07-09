"""
Code Executor for Agent-LLM Communication System
Handles execution of action codes returned by LLM
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from app.models.action_codes import (
    ActionCode, ActionResult, ConversationState, 
    LLMResponse, ACTION_CODE_MAPPING
)
from app.models.database_models import User, ServiceRequest, Conversation
from app.services.provider_service import ProviderService
from app.services.whatsapp_service import WhatsAppService
from app.services.ai_service import AIService
from app.database import get_db
from app.config import get_settings
from sqlalchemy.orm import Session


class CodeExecutor:
    """
    Executes action codes returned by LLM with comprehensive error handling
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.whatsapp_service = WhatsAppService()
        self.ai_service = AIService()
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "execution_times": []
        }
    
    async def execute_action(
        self, 
        llm_response: LLMResponse, 
        user_id: str, 
        session_context: Dict[str, Any],
        db: Session
    ) -> ActionResult:
        """
        Execute an action code with comprehensive error handling
        """
        start_time = datetime.now()
        
        try:
            self.execution_stats["total_executions"] += 1
            
            # Get execution method
            method_name = ACTION_CODE_MAPPING.get(llm_response.action_code)
            if not method_name:
                return ActionResult(
                    success=False,
                    action_code=llm_response.action_code,
                    result_data={},
                    error_message=f"Méthode d'exécution non trouvée pour {llm_response.action_code.value}"
                )
            
            # Get method from class
            method = getattr(self, method_name, None)
            if not method:
                return ActionResult(
                    success=False,
                    action_code=llm_response.action_code,
                    result_data={},
                    error_message=f"Méthode {method_name} non implémentée"
                )
            
            # Execute method
            result = await method(llm_response, user_id, session_context, db)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            self.execution_stats["execution_times"].append(execution_time)
            
            if result.success:
                self.execution_stats["successful_executions"] += 1
                logger.info(f"Action {llm_response.action_code.value} executed successfully in {execution_time:.2f}s")
            else:
                self.execution_stats["failed_executions"] += 1
                logger.error(f"Action {llm_response.action_code.value} failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.execution_stats["failed_executions"] += 1
            logger.error(f"Erreur lors de l'exécution de {llm_response.action_code.value}: {str(e)}")
            
            return ActionResult(
                success=False,
                action_code=llm_response.action_code,
                result_data={},
                error_message=f"Erreur d'exécution: {str(e)}",
                execution_time=execution_time
            )
    
    # === COLLECTION METHODS ===
    
    async def collect_service_need(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect initial service need"""
        extracted_data = llm_response.extracted_data
        
        # Update session with detected service type
        session_update = {
            "service_type": extracted_data.get("service_type"),
            "service_hint": extracted_data.get("service_hint"),
            "confidence": llm_response.confidence,
            "collection_phase": "service_need"
        }
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_BESOIN,
            result_data={
                "message_sent": True,
                "session_updated": True,
                "next_phase": "location_collection"
            }
        )
    
    async def collect_location(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect location information"""
        extracted_data = llm_response.extracted_data
        
        # Validate location is in coverage area
        location = extracted_data.get("location", "").lower()
        if "bonamoussadi" not in location and "douala" not in location:
            return ActionResult(
                success=False,
                action_code=ActionCode.COLLECTE_LOCALISATION,
                result_data={"coverage_error": True},
                error_message="Zone non couverte"
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_LOCALISATION,
            result_data={
                "location_validated": True,
                "location": location,
                "next_phase": "description_collection"
            }
        )
    
    async def collect_description(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect problem description"""
        extracted_data = llm_response.extracted_data
        
        description = extracted_data.get("description", "")
        urgency = extracted_data.get("urgency", "normal")
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_DESCRIPTION,
            result_data={
                "description": description,
                "urgency": urgency,
                "next_phase": "timing_collection"
            }
        )
    
    async def collect_timing(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect timing preferences"""
        extracted_data = llm_response.extracted_data
        
        timing = extracted_data.get("time_preference", "flexible")
        urgency = extracted_data.get("urgency", "normal")
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_DELAI,
            result_data={
                "timing": timing,
                "urgency": urgency,
                "next_phase": "validation"
            }
        )
    
    async def collect_budget(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect budget information (optional)"""
        extracted_data = llm_response.extracted_data
        
        budget = extracted_data.get("budget")
        service_type = session_context.get("service_type")
        
        # Provide pricing information
        pricing_info = self.settings.service_pricing.get(service_type, {})
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_BUDGET,
            result_data={
                "budget": budget,
                "pricing_info": pricing_info,
                "next_phase": "contact_collection"
            }
        )
    
    async def collect_contact(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect contact information"""
        extracted_data = llm_response.extracted_data
        
        # Contact info should already be available from user registration
        user = db.query(User).filter(User.phone_number == user_id).first()
        if not user:
            return ActionResult(
                success=False,
                action_code=ActionCode.COLLECTE_CONTACT,
                result_data={},
                error_message="Utilisateur non trouvé"
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_CONTACT,
            result_data={
                "contact_available": True,
                "phone": user.phone_number,
                "next_phase": "validation"
            }
        )
    
    async def collect_urgency(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect urgency level"""
        extracted_data = llm_response.extracted_data
        
        urgency = extracted_data.get("urgency", "normal")
        urgency_indicators = extracted_data.get("urgency_indicators", [])
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_URGENCE,
            result_data={
                "urgency": urgency,
                "indicators": urgency_indicators,
                "next_phase": "service_creation"
            }
        )
    
    async def collect_availability(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect client availability"""
        extracted_data = llm_response.extracted_data
        
        availability = extracted_data.get("availability", "flexible")
        time_slots = extracted_data.get("time_slots", [])
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_DISPONIBILITE,
            result_data={
                "availability": availability,
                "time_slots": time_slots,
                "next_phase": "validation"
            }
        )
    
    async def collect_access(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect access information"""
        extracted_data = llm_response.extracted_data
        
        access_info = extracted_data.get("access_info", "")
        special_instructions = extracted_data.get("special_instructions", "")
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_ACCES,
            result_data={
                "access_info": access_info,
                "special_instructions": special_instructions,
                "next_phase": "service_creation"
            }
        )
    
    async def collect_materials(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Collect material requirements"""
        extracted_data = llm_response.extracted_data
        
        materials = extracted_data.get("materials", [])
        client_provides = extracted_data.get("client_provides", False)
        
        return ActionResult(
            success=True,
            action_code=ActionCode.COLLECTE_MATERIEL,
            result_data={
                "materials": materials,
                "client_provides": client_provides,
                "next_phase": "service_creation"
            }
        )
    
    # === VALIDATION METHODS ===
    
    async def validate_service(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Validate service request"""
        extracted_data = llm_response.extracted_data
        
        # Check required fields
        required_fields = ["service_type", "location", "description"]
        missing_fields = []
        
        for field in required_fields:
            if not session_context.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            return ActionResult(
                success=False,
                action_code=ActionCode.VALIDATE_SERVICE,
                result_data={"missing_fields": missing_fields},
                error_message=f"Champs manquants: {', '.join(missing_fields)}"
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.VALIDATE_SERVICE,
            result_data={
                "validation_passed": True,
                "next_phase": "service_creation"
            }
        )
    
    async def validate_location(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Validate location"""
        location = session_context.get("location", "").lower()
        
        # Check if location is in coverage area
        coverage_areas = ["bonamoussadi", "douala"]
        is_covered = any(area in location for area in coverage_areas)
        
        if not is_covered:
            return ActionResult(
                success=False,
                action_code=ActionCode.VALIDATE_LOCATION,
                result_data={"coverage_error": True},
                error_message="Zone non couverte par nos services"
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.VALIDATE_LOCATION,
            result_data={"location_valid": True}
        )
    
    async def validate_timing(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Validate timing preferences"""
        timing = session_context.get("timing", "flexible")
        urgency = session_context.get("urgency", "normal")
        
        # Check if timing is realistic
        if urgency == "urgent" and timing == "flexible":
            return ActionResult(
                success=False,
                action_code=ActionCode.VALIDATE_TIMING,
                result_data={"timing_conflict": True},
                error_message="Conflit entre urgence et flexibilité"
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.VALIDATE_TIMING,
            result_data={"timing_valid": True}
        )
    
    async def validate_budget(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Validate budget"""
        budget = session_context.get("budget")
        service_type = session_context.get("service_type")
        
        if budget and service_type:
            pricing = self.settings.service_pricing.get(service_type, {})
            min_price = pricing.get("min", 0)
            max_price = pricing.get("max", 100000)
            
            if budget < min_price:
                return ActionResult(
                    success=False,
                    action_code=ActionCode.VALIDATE_BUDGET,
                    result_data={"budget_too_low": True, "min_price": min_price},
                    error_message=f"Budget insuffisant, minimum {min_price} XAF"
                )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.VALIDATE_BUDGET,
            result_data={"budget_valid": True}
        )
    
    async def validate_contact(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Validate contact information"""
        user = db.query(User).filter(User.phone_number == user_id).first()
        
        if not user:
            return ActionResult(
                success=False,
                action_code=ActionCode.VALIDATE_CONTACT,
                result_data={},
                error_message="Informations de contact manquantes"
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.VALIDATE_CONTACT,
            result_data={"contact_valid": True}
        )
    
    async def validate_complete(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Complete validation of all collected data"""
        # Run all validation checks
        validation_results = []
        
        # Validate service
        service_result = await self.validate_service(llm_response, user_id, session_context, db)
        validation_results.append(service_result)
        
        # Validate location
        location_result = await self.validate_location(llm_response, user_id, session_context, db)
        validation_results.append(location_result)
        
        # Validate contact
        contact_result = await self.validate_contact(llm_response, user_id, session_context, db)
        validation_results.append(contact_result)
        
        # Check if all validations passed
        all_valid = all(result.success for result in validation_results)
        
        if not all_valid:
            failed_validations = [result.error_message for result in validation_results if not result.success]
            return ActionResult(
                success=False,
                action_code=ActionCode.VALIDATE_COMPLETE,
                result_data={"validation_errors": failed_validations},
                error_message="Validation échouée: " + "; ".join(failed_validations)
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.VALIDATE_COMPLETE,
            result_data={
                "all_validations_passed": True,
                "ready_for_creation": True
            }
        )
    
    # === SERVICE ACTION METHODS ===
    
    async def create_service(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Create new service request"""
        try:
            # Get user
            user = db.query(User).filter(User.phone_number == user_id).first()
            if not user:
                return ActionResult(
                    success=False,
                    action_code=ActionCode.CREATE_SERVICE,
                    result_data={},
                    error_message="Utilisateur non trouvé"
                )
            
            # Create service request
            service_request = ServiceRequest(
                user_id=user.id,
                service_type=session_context.get("service_type"),
                location=session_context.get("location"),
                description=session_context.get("description"),
                urgency=session_context.get("urgency", "normal"),
                status="PENDING"
            )
            
            db.add(service_request)
            db.commit()
            db.refresh(service_request)
            
            return ActionResult(
                success=True,
                action_code=ActionCode.CREATE_SERVICE,
                result_data={
                    "service_id": service_request.id,
                    "status": "PENDING",
                    "next_phase": "provider_search"
                }
            )
            
        except Exception as e:
            db.rollback()
            return ActionResult(
                success=False,
                action_code=ActionCode.CREATE_SERVICE,
                result_data={},
                error_message=f"Erreur de création: {str(e)}"
            )
    
    async def create_urgent_service(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Create urgent service request"""
        # Set urgency to urgent
        session_context["urgency"] = "urgent"
        
        # Create service with urgent flag
        result = await self.create_service(llm_response, user_id, session_context, db)
        
        if result.success:
            result.result_data["urgent_priority"] = True
            
        return result
    
    async def search_providers(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Search available providers"""
        service_type = session_context.get("service_type")
        location = session_context.get("location")
        urgency = session_context.get("urgency", "normal")
        
        # Create provider service instance with database session
        provider_service = ProviderService(db)
        providers = provider_service.find_available_providers(
            service_type=service_type,
            location=location
        )
        
        if not providers:
            return ActionResult(
                success=False,
                action_code=ActionCode.SEARCH_PROVIDERS,
                result_data={"no_providers": True},
                error_message="Aucun prestataire disponible"
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.SEARCH_PROVIDERS,
            result_data={
                "providers_found": len(providers),
                "providers": [{"id": p.id, "name": p.name, "rating": p.rating} for p in providers],
                "next_phase": "provider_notification"
            }
        )
    
    async def notify_providers(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Notify selected providers"""
        service_id = session_context.get("service_id")
        
        if not service_id:
            return ActionResult(
                success=False,
                action_code=ActionCode.NOTIFY_PROVIDERS,
                result_data={},
                error_message="ID de service manquant"
            )
        
        # Get service request
        service_request = db.query(ServiceRequest).filter(ServiceRequest.id == service_id).first()
        if not service_request:
            return ActionResult(
                success=False,
                action_code=ActionCode.NOTIFY_PROVIDERS,
                result_data={},
                error_message="Demande de service non trouvée"
            )
        
        # Notify providers using existing service
        try:
            notification_result = await self.provider_service.notify_providers(service_request, db)
            
            return ActionResult(
                success=True,
                action_code=ActionCode.NOTIFY_PROVIDERS,
                result_data={
                    "notifications_sent": notification_result.get("sent", 0),
                    "next_phase": "awaiting_response"
                }
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                action_code=ActionCode.NOTIFY_PROVIDERS,
                result_data={},
                error_message=f"Erreur de notification: {str(e)}"
            )
    
    # === INFORMATION METHODS ===
    
    async def provide_general_info(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Provide general information"""
        info_type = llm_response.extracted_data.get("info_type", "general")
        
        info_data = {
            "app_name": self.settings.app_name,
            "services": self.settings.supported_services,
            "coverage_area": f"{self.settings.target_city}, {self.settings.target_district}",
            "contact_info": "WhatsApp uniquement"
        }
        
        return ActionResult(
            success=True,
            action_code=ActionCode.INFO_GENERALE,
            result_data=info_data
        )
    
    async def provide_pricing_info(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Provide pricing information"""
        service_type = llm_response.extracted_data.get("service_type")
        
        if service_type and service_type in self.settings.service_pricing:
            pricing = self.settings.service_pricing[service_type]
            return ActionResult(
                success=True,
                action_code=ActionCode.INFO_TARIFS,
                result_data=pricing
            )
        
        return ActionResult(
            success=True,
            action_code=ActionCode.INFO_TARIFS,
            result_data={"all_pricing": self.settings.service_pricing}
        )
    
    async def provide_timing_info(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Provide timing information"""
        timing_info = {
            "urgent": "Moins de 2 heures",
            "normal": "Moins de 24 heures",
            "flexible": "Moins de 48 heures",
            "service_hours": "7h-20h en semaine, 8h-18h weekend"
        }
        
        return ActionResult(
            success=True,
            action_code=ActionCode.INFO_DELAIS,
            result_data=timing_info
        )
    
    async def provide_services_info(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Provide services information"""
        services_info = {
            "available_services": self.settings.supported_services,
            "service_details": {
                "plomberie": "Réparations, installations, fuites",
                "électricité": "Pannes, installations, diagnostic",
                "réparation électroménager": "Tous appareils électroménagers"
            }
        }
        
        return ActionResult(
            success=True,
            action_code=ActionCode.INFO_SERVICES,
            result_data=services_info
        )
    
    # === ERROR HANDLING METHODS ===
    
    async def handle_error(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Handle general errors"""
        error_type = llm_response.extracted_data.get("error_type", "unknown")
        
        return ActionResult(
            success=True,
            action_code=ActionCode.ERROR_HANDLING,
            result_data={
                "error_handled": True,
                "error_type": error_type,
                "recovery_action": "clarification"
            }
        )
    
    async def request_clarification(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Request clarification from user"""
        clarification_type = llm_response.extracted_data.get("clarification_type", "general")
        
        return ActionResult(
            success=True,
            action_code=ActionCode.CLARIFICATION,
            result_data={
                "clarification_requested": True,
                "clarification_type": clarification_type
            }
        )
    
    async def escalate_to_human(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Escalate to human agent"""
        escalation_reason = llm_response.extracted_data.get("escalation_reason", "complex_issue")
        
        # Log escalation
        logger.warning(f"Escalation to human for user {user_id}: {escalation_reason}")
        
        return ActionResult(
            success=True,
            action_code=ActionCode.ESCALATE_HUMAN,
            result_data={
                "escalated": True,
                "escalation_reason": escalation_reason,
                "next_action": "await_human_agent"
            }
        )
    
    # === FLOW CONTROL METHODS ===
    
    async def continue_conversation(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """Continue conversation flow"""
        return ActionResult(
            success=True,
            action_code=ActionCode.FLOW_CONTINUE,
            result_data={"flow_continued": True}
        )
    
    async def end_conversation(self, llm_response: LLMResponse, user_id: str, session_context: Dict[str, Any], db: Session) -> ActionResult:
        """End conversation"""
        return ActionResult(
            success=True,
            action_code=ActionCode.FLOW_END,
            result_data={"conversation_ended": True}
        )
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        avg_execution_time = 0
        if self.execution_stats["execution_times"]:
            avg_execution_time = sum(self.execution_stats["execution_times"]) / len(self.execution_stats["execution_times"])
        
        success_rate = 0
        if self.execution_stats["total_executions"] > 0:
            success_rate = self.execution_stats["successful_executions"] / self.execution_stats["total_executions"]
        
        return {
            "total_executions": self.execution_stats["total_executions"],
            "successful_executions": self.execution_stats["successful_executions"],
            "failed_executions": self.execution_stats["failed_executions"],
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time
        }