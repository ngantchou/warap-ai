"""
Action codes for Agent-LLM communication in Djobea AI
Comprehensive system for 99% automation of client interactions
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

class ActionCode(Enum):
    """
    Comprehensive action codes for Agent-LLM communication
    Organized by category for systematic interaction management
    """
    
    # === COLLECTION CODES (COLLECTE_*) ===
    COLLECTE_BESOIN = "COLLECTE_BESOIN"  # Initial service need identification
    COLLECTE_LOCALISATION = "COLLECTE_LOCALISATION"  # Location precision
    COLLECTE_DESCRIPTION = "COLLECTE_DESCRIPTION"  # Problem details
    COLLECTE_DELAI = "COLLECTE_DELAI"  # Intervention timing
    COLLECTE_BUDGET = "COLLECTE_BUDGET"  # Budget estimation (optional)
    COLLECTE_CONTACT = "COLLECTE_CONTACT"  # Contact information
    COLLECTE_URGENCE = "COLLECTE_URGENCE"  # Urgency level assessment
    COLLECTE_DISPONIBILITE = "COLLECTE_DISPONIBILITE"  # Client availability
    COLLECTE_ACCES = "COLLECTE_ACCES"  # Access information
    COLLECTE_MATERIEL = "COLLECTE_MATERIEL"  # Material requirements
    
    # === VALIDATION CODES (VALIDATE_*) ===
    VALIDATE_SERVICE = "VALIDATE_SERVICE"  # Service request validation
    VALIDATE_LOCATION = "VALIDATE_LOCATION"  # Location validation
    VALIDATE_TIMING = "VALIDATE_TIMING"  # Timing validation
    VALIDATE_BUDGET = "VALIDATE_BUDGET"  # Budget validation
    VALIDATE_CONTACT = "VALIDATE_CONTACT"  # Contact validation
    VALIDATE_COMPLETE = "VALIDATE_COMPLETE"  # Complete request validation
    
    # === ACTION CODES (CREATE_*, SEARCH_*, NOTIFY_*) ===
    CREATE_SERVICE = "CREATE_SERVICE"  # Create complete service request
    CREATE_URGENT = "CREATE_URGENT"  # Create urgent service request
    SEARCH_PROVIDERS = "SEARCH_PROVIDERS"  # Search available providers
    NOTIFY_PROVIDERS = "NOTIFY_PROVIDERS"  # Notify selected providers
    CONFIRM_MATCH = "CONFIRM_MATCH"  # Confirm provider matching
    ASSIGN_PROVIDER = "ASSIGN_PROVIDER"  # Assign specific provider
    
    # === MANAGEMENT CODES (STATUS_*, CANCEL_*, MODIFY_*) ===
    STATUS_CHECK = "STATUS_CHECK"  # Check request status
    STATUS_DETAIL = "STATUS_DETAIL"  # Detailed status information
    CANCEL_SERVICE = "CANCEL_SERVICE"  # Cancel service request
    MODIFY_SERVICE = "MODIFY_SERVICE"  # Modify existing request
    COMPLETE_SERVICE = "COMPLETE_SERVICE"  # Complete service
    RESCHEDULE_SERVICE = "RESCHEDULE_SERVICE"  # Reschedule service
    
    # === INFORMATION CODES (INFO_*) ===
    INFO_GENERALE = "INFO_GENERALE"  # General information
    INFO_TARIFS = "INFO_TARIFS"  # Pricing information
    INFO_DELAIS = "INFO_DELAIS"  # Timing information
    INFO_SERVICES = "INFO_SERVICES"  # Available services
    INFO_ZONE = "INFO_ZONE"  # Coverage area information
    INFO_CONTACT = "INFO_CONTACT"  # Contact information
    INFO_PROCESS = "INFO_PROCESS"  # Process explanation
    
    # === HELP AND NAVIGATION CODES (HELP_*, MENU_*) ===
    HELP_NAVIGATION = "HELP_NAVIGATION"  # Navigation assistance
    HELP_SERVICE = "HELP_SERVICE"  # Service-specific help
    MENU_PRINCIPAL = "MENU_PRINCIPAL"  # Main menu
    MENU_ACTIONS = "MENU_ACTIONS"  # Available actions menu
    MENU_QUICK = "MENU_QUICK"  # Quick actions menu
    
    # === ERROR HANDLING CODES (ERROR_*, FALLBACK_*) ===
    ERROR_HANDLING = "ERROR_HANDLING"  # General error handling
    ERROR_VALIDATION = "ERROR_VALIDATION"  # Validation error
    ERROR_SYSTEM = "ERROR_SYSTEM"  # System error
    FALLBACK = "FALLBACK"  # Fallback action
    CLARIFICATION = "CLARIFICATION"  # Request clarification
    
    # === ESCALATION CODES (ESCALATE_*) ===
    ESCALATE_HUMAN = "ESCALATE_HUMAN"  # Escalate to human agent
    ESCALATE_TECHNICAL = "ESCALATE_TECHNICAL"  # Technical escalation
    ESCALATE_MANAGER = "ESCALATE_MANAGER"  # Manager escalation
    
    # === CONVERSATION FLOW CODES (FLOW_*) ===
    FLOW_CONTINUE = "FLOW_CONTINUE"  # Continue conversation
    FLOW_RESTART = "FLOW_RESTART"  # Restart conversation
    FLOW_END = "FLOW_END"  # End conversation
    FLOW_PAUSE = "FLOW_PAUSE"  # Pause conversation
    
    @classmethod
    def get_category(cls, code: 'ActionCode') -> str:
        """Get the category of an action code"""
        code_name = code.value
        if code_name.startswith('COLLECTE_'):
            return 'COLLECTION'
        elif code_name.startswith('VALIDATE_'):
            return 'VALIDATION'
        elif code_name.startswith(('CREATE_', 'SEARCH_', 'NOTIFY_', 'CONFIRM_', 'ASSIGN_')):
            return 'ACTION'
        elif code_name.startswith(('STATUS_', 'CANCEL_', 'MODIFY_', 'COMPLETE_', 'RESCHEDULE_')):
            return 'MANAGEMENT'
        elif code_name.startswith('INFO_'):
            return 'INFORMATION'
        elif code_name.startswith(('HELP_', 'MENU_')):
            return 'NAVIGATION'
        elif code_name.startswith(('ERROR_', 'FALLBACK', 'CLARIFICATION')):
            return 'ERROR'
        elif code_name.startswith('ESCALATE_'):
            return 'ESCALATION'
        elif code_name.startswith('FLOW_'):
            return 'FLOW'
        return 'UNKNOWN'
    
    @classmethod
    def get_description(cls, code: 'ActionCode') -> str:
        """Get human-readable description of action code"""
        descriptions = {
            cls.COLLECTE_BESOIN: "Identifier le besoin initial du client",
            cls.COLLECTE_LOCALISATION: "Préciser la localisation du service",
            cls.COLLECTE_DESCRIPTION: "Collecter les détails du problème",
            cls.COLLECTE_DELAI: "Déterminer le délai d'intervention souhaité",
            cls.COLLECTE_BUDGET: "Estimer le budget disponible",
            cls.COLLECTE_CONTACT: "Recueillir les informations de contact",
            cls.COLLECTE_URGENCE: "Évaluer le niveau d'urgence",
            cls.COLLECTE_DISPONIBILITE: "Vérifier la disponibilité du client",
            cls.COLLECTE_ACCES: "Obtenir les informations d'accès",
            cls.COLLECTE_MATERIEL: "Identifier les besoins matériels",
            
            cls.VALIDATE_SERVICE: "Valider la demande de service",
            cls.VALIDATE_LOCATION: "Valider la localisation",
            cls.VALIDATE_TIMING: "Valider les créneaux horaires",
            cls.VALIDATE_BUDGET: "Valider le budget",
            cls.VALIDATE_CONTACT: "Valider les informations de contact",
            cls.VALIDATE_COMPLETE: "Validation complète de la demande",
            
            cls.CREATE_SERVICE: "Créer une nouvelle demande de service",
            cls.CREATE_URGENT: "Créer une demande urgente",
            cls.SEARCH_PROVIDERS: "Rechercher des prestataires disponibles",
            cls.NOTIFY_PROVIDERS: "Notifier les prestataires sélectionnés",
            cls.CONFIRM_MATCH: "Confirmer le matching prestataire-client",
            cls.ASSIGN_PROVIDER: "Assigner un prestataire spécifique",
            
            cls.STATUS_CHECK: "Vérifier le statut de la demande",
            cls.STATUS_DETAIL: "Fournir des détails de statut",
            cls.CANCEL_SERVICE: "Annuler la demande de service",
            cls.MODIFY_SERVICE: "Modifier la demande existante",
            cls.COMPLETE_SERVICE: "Finaliser le service",
            cls.RESCHEDULE_SERVICE: "Reprogrammer le service",
            
            cls.INFO_GENERALE: "Fournir des informations générales",
            cls.INFO_TARIFS: "Fournir des informations tarifaires",
            cls.INFO_DELAIS: "Fournir des informations sur les délais",
            cls.INFO_SERVICES: "Lister les services disponibles",
            cls.INFO_ZONE: "Informations sur la zone de couverture",
            cls.INFO_CONTACT: "Informations de contact",
            cls.INFO_PROCESS: "Explication du processus",
            
            cls.HELP_NAVIGATION: "Aide à la navigation",
            cls.HELP_SERVICE: "Aide spécifique au service",
            cls.MENU_PRINCIPAL: "Afficher le menu principal",
            cls.MENU_ACTIONS: "Afficher les actions disponibles",
            cls.MENU_QUICK: "Afficher les actions rapides",
            
            cls.ERROR_HANDLING: "Gestion d'erreur générale",
            cls.ERROR_VALIDATION: "Erreur de validation",
            cls.ERROR_SYSTEM: "Erreur système",
            cls.FALLBACK: "Action de secours",
            cls.CLARIFICATION: "Demander une clarification",
            
            cls.ESCALATE_HUMAN: "Escalader vers un agent humain",
            cls.ESCALATE_TECHNICAL: "Escalade technique",
            cls.ESCALATE_MANAGER: "Escalade managériale",
            
            cls.FLOW_CONTINUE: "Continuer la conversation",
            cls.FLOW_RESTART: "Redémarrer la conversation",
            cls.FLOW_END: "Terminer la conversation",
            cls.FLOW_PAUSE: "Mettre en pause la conversation",
        }
        return descriptions.get(code, "Description non disponible")
    
    @classmethod
    def is_valid_code(cls, code_str: str) -> bool:
        """Check if a code string is valid"""
        try:
            cls(code_str)
            return True
        except ValueError:
            return False
    
    @classmethod
    def get_codes_by_category(cls, category: str) -> List['ActionCode']:
        """Get all codes in a specific category"""
        return [code for code in cls if cls.get_category(code) == category.upper()]


class ConversationState(Enum):
    """States of the conversation flow"""
    INITIAL = "INITIAL"  # Initial state
    COLLECTING = "COLLECTING"  # Collecting information
    VALIDATING = "VALIDATING"  # Validating collected data
    PROCESSING = "PROCESSING"  # Processing request
    MATCHING = "MATCHING"  # Matching with providers
    CONFIRMED = "CONFIRMED"  # Request confirmed
    IN_PROGRESS = "IN_PROGRESS"  # Service in progress
    COMPLETED = "COMPLETED"  # Service completed
    CANCELLED = "CANCELLED"  # Request cancelled
    ERROR = "ERROR"  # Error state
    ESCALATED = "ESCALATED"  # Escalated to human
    PAUSED = "PAUSED"  # Conversation paused


@dataclass
class LLMRequest:
    """
    Structured request to LLM with context and session data
    """
    message: str
    user_id: str
    session_context: Dict[str, Any]
    dynamic_context: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    current_state: ConversationState
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM processing"""
        return {
            "message": self.message,
            "user_id": self.user_id,
            "session_context": self.session_context,
            "dynamic_context": self.dynamic_context,
            "conversation_history": self.conversation_history,
            "current_state": self.current_state.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }


@dataclass
class LLMResponse:
    """
    Structured response from LLM with action code and data
    """
    action_code: ActionCode
    client_message: str
    extracted_data: Dict[str, Any]
    session_update: Dict[str, Any]
    next_state: ConversationState
    confidence: float
    metadata: Dict[str, Any]
    requires_followup: bool = False
    escalation_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action_code": self.action_code.value,
            "client_message": self.client_message,
            "extracted_data": self.extracted_data,
            "session_update": self.session_update,
            "next_state": self.next_state.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "requires_followup": self.requires_followup,
            "escalation_reason": self.escalation_reason
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMResponse':
        """Create from dictionary"""
        return cls(
            action_code=ActionCode(data["action_code"]),
            client_message=data["client_message"],
            extracted_data=data["extracted_data"],
            session_update=data["session_update"],
            next_state=ConversationState(data["next_state"]),
            confidence=data["confidence"],
            metadata=data["metadata"],
            requires_followup=data.get("requires_followup", False),
            escalation_reason=data.get("escalation_reason")
        )


@dataclass
class ActionResult:
    """
    Result of action execution
    """
    success: bool
    action_code: ActionCode
    result_data: Dict[str, Any]
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    side_effects: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "action_code": self.action_code.value,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "side_effects": self.side_effects or []
        }


class ActionCodeValidator:
    """
    Validator for action codes with comprehensive validation logic
    """
    
    @staticmethod
    def validate_code(code_str: str) -> tuple[bool, str]:
        """
        Validate action code string
        Returns (is_valid, error_message)
        """
        if not code_str:
            return False, "Code d'action vide"
        
        if not ActionCode.is_valid_code(code_str):
            return False, f"Code d'action invalide: {code_str}"
        
        return True, ""
    
    @staticmethod
    def validate_llm_response(response_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate LLM response structure
        Returns (is_valid, error_message)
        """
        required_fields = [
            "action_code", "client_message", "extracted_data",
            "session_update", "next_state", "confidence", "metadata"
        ]
        
        for field in required_fields:
            if field not in response_data:
                return False, f"Champ requis manquant: {field}"
        
        # Validate action code
        is_valid, error = ActionCodeValidator.validate_code(response_data["action_code"])
        if not is_valid:
            return False, error
        
        # Validate confidence
        confidence = response_data.get("confidence", 0)
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            return False, "Confiance doit être entre 0 et 1"
        
        # Validate state
        try:
            ConversationState(response_data["next_state"])
        except ValueError:
            return False, f"État de conversation invalide: {response_data['next_state']}"
        
        return True, ""
    
    @staticmethod
    def get_fallback_action(error_type: str) -> ActionCode:
        """
        Get appropriate fallback action based on error type
        """
        fallback_map = {
            "invalid_code": ActionCode.ERROR_HANDLING,
            "validation_error": ActionCode.ERROR_VALIDATION,
            "system_error": ActionCode.ERROR_SYSTEM,
            "unclear_intent": ActionCode.CLARIFICATION,
            "timeout": ActionCode.FALLBACK,
            "escalation": ActionCode.ESCALATE_HUMAN
        }
        return fallback_map.get(error_type, ActionCode.ERROR_HANDLING)


# Action code mapping for execution
ACTION_CODE_MAPPING = {
    # Collection actions
    ActionCode.COLLECTE_BESOIN: "collect_service_need",
    ActionCode.COLLECTE_LOCALISATION: "collect_location",
    ActionCode.COLLECTE_DESCRIPTION: "collect_description",
    ActionCode.COLLECTE_DELAI: "collect_timing",
    ActionCode.COLLECTE_BUDGET: "collect_budget",
    ActionCode.COLLECTE_CONTACT: "collect_contact",
    ActionCode.COLLECTE_URGENCE: "collect_urgency",
    ActionCode.COLLECTE_DISPONIBILITE: "collect_availability",
    ActionCode.COLLECTE_ACCES: "collect_access",
    ActionCode.COLLECTE_MATERIEL: "collect_materials",
    
    # Validation actions
    ActionCode.VALIDATE_SERVICE: "validate_service",
    ActionCode.VALIDATE_LOCATION: "validate_location",
    ActionCode.VALIDATE_TIMING: "validate_timing",
    ActionCode.VALIDATE_BUDGET: "validate_budget",
    ActionCode.VALIDATE_CONTACT: "validate_contact",
    ActionCode.VALIDATE_COMPLETE: "validate_complete",
    
    # Service actions
    ActionCode.CREATE_SERVICE: "create_service",
    ActionCode.CREATE_URGENT: "create_urgent_service",
    ActionCode.SEARCH_PROVIDERS: "search_providers",
    ActionCode.NOTIFY_PROVIDERS: "notify_providers",
    ActionCode.CONFIRM_MATCH: "confirm_provider_match",
    ActionCode.ASSIGN_PROVIDER: "assign_provider",
    
    # Management actions
    ActionCode.STATUS_CHECK: "check_status",
    ActionCode.STATUS_DETAIL: "get_status_detail",
    ActionCode.CANCEL_SERVICE: "cancel_service",
    ActionCode.MODIFY_SERVICE: "modify_service",
    ActionCode.COMPLETE_SERVICE: "complete_service",
    ActionCode.RESCHEDULE_SERVICE: "reschedule_service",
    
    # Information actions
    ActionCode.INFO_GENERALE: "provide_general_info",
    ActionCode.INFO_TARIFS: "provide_pricing_info",
    ActionCode.INFO_DELAIS: "provide_timing_info",
    ActionCode.INFO_SERVICES: "provide_services_info",
    ActionCode.INFO_ZONE: "provide_zone_info",
    ActionCode.INFO_CONTACT: "provide_contact_info",
    ActionCode.INFO_PROCESS: "provide_process_info",
    
    # Navigation actions
    ActionCode.HELP_NAVIGATION: "provide_navigation_help",
    ActionCode.HELP_SERVICE: "provide_service_help",
    ActionCode.MENU_PRINCIPAL: "show_main_menu",
    ActionCode.MENU_ACTIONS: "show_actions_menu",
    ActionCode.MENU_QUICK: "show_quick_menu",
    
    # Error handling
    ActionCode.ERROR_HANDLING: "handle_error",
    ActionCode.ERROR_VALIDATION: "handle_validation_error",
    ActionCode.ERROR_SYSTEM: "handle_system_error",
    ActionCode.FALLBACK: "execute_fallback",
    ActionCode.CLARIFICATION: "request_clarification",
    
    # Escalation
    ActionCode.ESCALATE_HUMAN: "escalate_to_human",
    ActionCode.ESCALATE_TECHNICAL: "escalate_technical",
    ActionCode.ESCALATE_MANAGER: "escalate_to_manager",
    
    # Flow control
    ActionCode.FLOW_CONTINUE: "continue_conversation",
    ActionCode.FLOW_RESTART: "restart_conversation",
    ActionCode.FLOW_END: "end_conversation",
    ActionCode.FLOW_PAUSE: "pause_conversation"
}