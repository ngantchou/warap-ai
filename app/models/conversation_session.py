"""
Conversation Session Models
Advanced session management for Agent-LLM communication
"""
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import json
import uuid


class ConversationState(Enum):
    """
    Conversation state machine with valid transitions
    """
    INITIAL = "INITIAL"
    COLLECTING = "COLLECTING"
    VALIDATING = "VALIDATING"
    CONFIRMING = "CONFIRMING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"
    ESCALATED = "ESCALATED"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"


class SessionPhase(Enum):
    """
    Collection phases within COLLECTING state
    """
    SERVICE_TYPE = "SERVICE_TYPE"
    LOCATION = "LOCATION"
    DESCRIPTION = "DESCRIPTION"
    TIMING = "TIMING"
    URGENCY = "URGENCY"
    BUDGET = "BUDGET"
    CONTACT = "CONTACT"
    ACCESS = "ACCESS"
    MATERIALS = "MATERIALS"
    COMPLETE = "COMPLETE"


class TransitionRule:
    """
    Defines valid state transitions
    """
    VALID_TRANSITIONS = {
        ConversationState.INITIAL: [
            ConversationState.COLLECTING,
            ConversationState.ERROR,
            ConversationState.ESCALATED
        ],
        ConversationState.COLLECTING: [
            ConversationState.VALIDATING,
            ConversationState.ERROR,
            ConversationState.ESCALATED,
            ConversationState.PAUSED,
            ConversationState.CANCELLED
        ],
        ConversationState.VALIDATING: [
            ConversationState.CONFIRMING,
            ConversationState.COLLECTING,  # Back to collection if invalid
            ConversationState.ERROR,
            ConversationState.ESCALATED
        ],
        ConversationState.CONFIRMING: [
            ConversationState.PROCESSING,
            ConversationState.COLLECTING,  # Back to collection if changes needed
            ConversationState.CANCELLED,
            ConversationState.ERROR
        ],
        ConversationState.PROCESSING: [
            ConversationState.COMPLETED,
            ConversationState.ERROR,
            ConversationState.ESCALATED
        ],
        ConversationState.COMPLETED: [],  # Terminal state
        ConversationState.CANCELLED: [],  # Terminal state
        ConversationState.ERROR: [
            ConversationState.COLLECTING,
            ConversationState.ESCALATED,
            ConversationState.EXPIRED
        ],
        ConversationState.ESCALATED: [],  # Terminal state
        ConversationState.PAUSED: [
            ConversationState.COLLECTING,
            ConversationState.EXPIRED,
            ConversationState.CANCELLED
        ],
        ConversationState.EXPIRED: []  # Terminal state
    }
    
    @classmethod
    def is_valid_transition(cls, from_state: ConversationState, to_state: ConversationState) -> bool:
        """Check if transition is valid"""
        return to_state in cls.VALID_TRANSITIONS.get(from_state, [])
    
    @classmethod
    def get_valid_transitions(cls, from_state: ConversationState) -> List[ConversationState]:
        """Get all valid transitions from current state"""
        return cls.VALID_TRANSITIONS.get(from_state, [])
    
    @classmethod
    def is_terminal_state(cls, state: ConversationState) -> bool:
        """Check if state is terminal"""
        return len(cls.VALID_TRANSITIONS.get(state, [])) == 0


@dataclass
class ConversationMessage:
    """
    Individual message in conversation history
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: str = "incoming"  # incoming, outgoing, system
    content: str = ""
    action_code: Optional[str] = None
    confidence_score: Optional[float] = None
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type,
            "content": self.content,
            "action_code": self.action_code,
            "confidence_score": self.confidence_score,
            "extracted_data": self.extracted_data,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class CollectedData:
    """
    Data collected during conversation
    """
    service_type: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    timing: Optional[str] = None
    urgency: Optional[str] = None
    budget: Optional[float] = None
    contact_info: Optional[str] = None
    access_info: Optional[str] = None
    materials: Optional[List[str]] = None
    
    # Metadata
    location_confidence: Optional[float] = None
    service_confidence: Optional[float] = None
    urgency_indicators: List[str] = field(default_factory=list)
    collection_progress: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "service_type": self.service_type,
            "location": self.location,
            "description": self.description,
            "timing": self.timing,
            "urgency": self.urgency,
            "budget": self.budget,
            "contact_info": self.contact_info,
            "access_info": self.access_info,
            "materials": self.materials,
            "location_confidence": self.location_confidence,
            "service_confidence": self.service_confidence,
            "urgency_indicators": self.urgency_indicators,
            "collection_progress": self.collection_progress
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollectedData':
        """Create from dictionary"""
        return cls(**data)
    
    def is_complete(self) -> bool:
        """Check if required data is collected"""
        required_fields = ["service_type", "location", "description"]
        return all(getattr(self, field) is not None for field in required_fields)
    
    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields"""
        required_fields = ["service_type", "location", "description"]
        return [field for field in required_fields if getattr(self, field) is None]
    
    def update_progress(self):
        """Update collection progress percentage"""
        total_fields = 9  # Total possible fields
        filled_fields = sum(1 for field in [
            self.service_type, self.location, self.description, self.timing,
            self.urgency, self.budget, self.contact_info, self.access_info, self.materials
        ] if field is not None)
        
        self.collection_progress = (filled_fields / total_fields) * 100


@dataclass
class SessionMetrics:
    """
    Performance metrics for conversation session
    """
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Interaction metrics
    total_messages: int = 0
    user_messages: int = 0
    ai_responses: int = 0
    
    # Performance metrics
    average_response_time: float = 0.0
    total_response_time: float = 0.0
    action_executions: int = 0
    successful_actions: int = 0
    
    # State metrics
    state_changes: int = 0
    rollbacks: int = 0
    errors: int = 0
    
    # Automation metrics
    automation_score: float = 0.0
    escalation_triggered: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_messages": self.total_messages,
            "user_messages": self.user_messages,
            "ai_responses": self.ai_responses,
            "average_response_time": self.average_response_time,
            "total_response_time": self.total_response_time,
            "action_executions": self.action_executions,
            "successful_actions": self.successful_actions,
            "state_changes": self.state_changes,
            "rollbacks": self.rollbacks,
            "errors": self.errors,
            "automation_score": self.automation_score,
            "escalation_triggered": self.escalation_triggered
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetrics':
        """Create from dictionary"""
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        if data.get("end_time"):
            data["end_time"] = datetime.fromisoformat(data["end_time"])
        return cls(**data)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def record_action(self, success: bool, execution_time: float):
        """Record action execution"""
        self.action_executions += 1
        if success:
            self.successful_actions += 1
        
        self.total_response_time += execution_time
        self.average_response_time = self.total_response_time / self.action_executions
    
    def calculate_automation_score(self) -> float:
        """Calculate automation score based on performance"""
        if self.action_executions == 0:
            return 0.0
        
        success_rate = self.successful_actions / self.action_executions
        error_penalty = min(self.errors * 0.1, 0.3)  # Max 30% penalty
        escalation_penalty = 0.5 if self.escalation_triggered else 0.0
        
        score = (success_rate - error_penalty - escalation_penalty) * 100
        return max(0.0, min(100.0, score))
    
    def get_session_duration(self) -> timedelta:
        """Get total session duration"""
        end = self.end_time or datetime.now()
        return end - self.start_time


class ConversationSession:
    """
    Complete conversation session with state management
    """
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        phone_number: str,
        initial_state: ConversationState = ConversationState.INITIAL
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.phone_number = phone_number
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(hours=2)  # Default 2 hours
        
        # State management
        self.current_state = initial_state
        self.previous_state: Optional[ConversationState] = None
        self.current_phase: Optional[SessionPhase] = None
        self.state_history: List[Dict[str, Any]] = []
        
        # Data management
        self.collected_data = CollectedData()
        self.conversation_history: List[ConversationMessage] = []
        self.session_metadata: Dict[str, Any] = {}
        
        # Performance tracking
        self.metrics = SessionMetrics(session_id)
        
        # Timeouts and limits
        self.max_history_size = 10
        self.timeout_minutes = 120
        self.max_collection_attempts = 3
        
        # Add initial state to history
        self._record_state_change(initial_state, "session_created")
    
    def transition_to(self, new_state: ConversationState, reason: str = "") -> bool:
        """
        Transition to new state with validation
        """
        if not TransitionRule.is_valid_transition(self.current_state, new_state):
            return False
        
        self.previous_state = self.current_state
        self.current_state = new_state
        self.updated_at = datetime.now()
        
        # Record transition
        self._record_state_change(new_state, reason)
        
        # Update metrics
        self.metrics.state_changes += 1
        self.metrics.update_activity()
        
        return True
    
    def rollback_state(self, reason: str = "error_recovery") -> bool:
        """
        Rollback to previous state
        """
        if self.previous_state is None:
            return False
        
        target_state = self.previous_state
        self.previous_state = self.current_state
        self.current_state = target_state
        self.updated_at = datetime.now()
        
        # Record rollback
        self._record_state_change(target_state, f"rollback_{reason}")
        
        # Update metrics
        self.metrics.rollbacks += 1
        self.metrics.update_activity()
        
        return True
    
    def add_message(self, message: ConversationMessage):
        """
        Add message to conversation history
        """
        self.conversation_history.append(message)
        
        # Maintain history size limit
        if len(self.conversation_history) > self.max_history_size:
            self.conversation_history = self.conversation_history[-self.max_history_size:]
        
        # Update metrics
        self.metrics.total_messages += 1
        if message.message_type == "incoming":
            self.metrics.user_messages += 1
        elif message.message_type == "outgoing":
            self.metrics.ai_responses += 1
        
        self.metrics.update_activity()
        self.updated_at = datetime.now()
    
    def update_collected_data(self, field: str, value: Any, confidence: float = None):
        """
        Update collected data with confidence tracking
        """
        if hasattr(self.collected_data, field):
            setattr(self.collected_data, field, value)
            
            # Update confidence if provided
            if confidence is not None:
                confidence_field = f"{field}_confidence"
                if hasattr(self.collected_data, confidence_field):
                    setattr(self.collected_data, confidence_field, confidence)
            
            # Update progress
            self.collected_data.update_progress()
            self.updated_at = datetime.now()
    
    def get_recent_history(self, limit: int = 5) -> List[ConversationMessage]:
        """
        Get recent conversation history
        """
        return self.conversation_history[-limit:]
    
    def is_expired(self) -> bool:
        """
        Check if session is expired
        """
        try:
            now = datetime.now()
            # Ensure both datetime objects are timezone-naive
            expires_at = self.expires_at
            if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            return now > expires_at
        except Exception:
            # If comparison fails, assume not expired
            return False
    
    def extend_expiration(self, minutes: int = 60):
        """
        Extend session expiration
        """
        self.expires_at = datetime.now() + timedelta(minutes=minutes)
        self.updated_at = datetime.now()
    
    def is_data_complete(self) -> bool:
        """
        Check if required data collection is complete
        """
        return self.collected_data.is_complete()
    
    def get_missing_data(self) -> List[str]:
        """
        Get list of missing required data
        """
        return self.collected_data.get_missing_fields()
    
    def can_proceed_to_validation(self) -> bool:
        """
        Check if session can proceed to validation
        """
        return (
            self.current_state == ConversationState.COLLECTING and
            self.is_data_complete()
        )
    
    def record_error(self, error_type: str, error_message: str):
        """
        Record error in session
        """
        self.metrics.errors += 1
        self.session_metadata.setdefault("errors", []).append({
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def record_escalation(self, reason: str):
        """
        Record escalation event
        """
        self.metrics.escalation_triggered = True
        self.session_metadata["escalation"] = {
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive session summary
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "phone_number": self.phone_number,
            "current_state": self.current_state.value,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired(),
            "collected_data": self.collected_data.to_dict(),
            "data_complete": self.is_data_complete(),
            "missing_data": self.get_missing_data(),
            "conversation_history": [msg.to_dict() for msg in self.conversation_history],
            "metrics": self.metrics.to_dict(),
            "session_metadata": self.session_metadata,
            "automation_score": self.metrics.calculate_automation_score()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary for persistence
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "phone_number": self.phone_number,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "state_history": self.state_history,
            "collected_data": self.collected_data.to_dict(),
            "conversation_history": [msg.to_dict() for msg in self.conversation_history],
            "session_metadata": self.session_metadata,
            "metrics": self.metrics.to_dict(),
            "max_history_size": self.max_history_size,
            "timeout_minutes": self.timeout_minutes,
            "max_collection_attempts": self.max_collection_attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """
        Create session from dictionary
        """
        session = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            phone_number=data["phone_number"],
            initial_state=ConversationState(data["current_state"])
        )
        
        # Restore timestamps
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.updated_at = datetime.fromisoformat(data["updated_at"])
        session.expires_at = datetime.fromisoformat(data["expires_at"])
        
        # Restore state
        session.current_state = ConversationState(data["current_state"])
        session.previous_state = ConversationState(data["previous_state"]) if data.get("previous_state") else None
        session.current_phase = SessionPhase(data["current_phase"]) if data.get("current_phase") else None
        session.state_history = data.get("state_history", [])
        
        # Restore data
        session.collected_data = CollectedData.from_dict(data["collected_data"])
        session.conversation_history = [
            ConversationMessage.from_dict(msg) for msg in data.get("conversation_history", [])
        ]
        session.session_metadata = data.get("session_metadata", {})
        session.metrics = SessionMetrics.from_dict(data["metrics"])
        
        # Restore settings
        session.max_history_size = data.get("max_history_size", 10)
        session.timeout_minutes = data.get("timeout_minutes", 120)
        session.max_collection_attempts = data.get("max_collection_attempts", 3)
        
        return session
    
    def _record_state_change(self, new_state: ConversationState, reason: str):
        """
        Record state change in history
        """
        self.state_history.append({
            "timestamp": datetime.now().isoformat(),
            "from_state": self.previous_state.value if self.previous_state else None,
            "to_state": new_state.value,
            "reason": reason
        })
        
        # Maintain history size
        if len(self.state_history) > 20:  # Keep last 20 state changes
            self.state_history = self.state_history[-20:]