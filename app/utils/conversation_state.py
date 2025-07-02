"""
Conversation State Management for Djobea AI
Manages conversation phases and state transitions for natural flow
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field


class ConversationPhase(Enum):
    """Different phases of conversation flow"""
    GREETING = "greeting"
    INFORMATION_GATHERING = "information_gathering"
    REQUEST_PROCESSING = "request_processing"
    PROVIDER_MATCHING = "provider_matching"
    PROVIDER_COMMUNICATION = "provider_communication"
    SERVICE_COORDINATION = "service_coordination"
    STATUS_TRACKING = "status_tracking"
    COMPLETION = "completion"
    EMERGENCY_PROCESSING = "emergency_processing"
    CANCELLATION = "cancellation"
    FOLLOW_UP = "follow_up"


class ConversationMood(Enum):
    """User mood/tone detection for adaptive responses"""
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    FRUSTRATED = "frustrated"
    SATISFIED = "satisfied"
    CONFUSED = "confused"


@dataclass
class ConversationState:
    """Complete conversation state for seamless user experience"""
    
    # Core identification
    user_identifier: str
    session_id: Optional[str] = None
    
    # Conversation flow
    current_phase: ConversationPhase = ConversationPhase.GREETING
    previous_phase: Optional[ConversationPhase] = None
    phase_start_time: datetime = field(default_factory=datetime.utcnow)
    
    # Context and memory
    context_data: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Current request tracking
    active_request_id: Optional[int] = None
    pending_request_data: Optional[Dict[str, Any]] = None
    
    # User preferences and mood
    detected_mood: ConversationMood = ConversationMood.NEUTRAL
    language_preference: str = "french"
    communication_style: str = "polite"
    
    # Conversation metrics
    message_count: int = 0
    total_session_time: int = 0  # in seconds
    last_interaction_time: datetime = field(default_factory=datetime.utcnow)
    
    # Response tracking
    last_message: Optional[str] = None
    last_response: Optional[str] = None
    last_intent: Optional[str] = None
    
    # System flags
    requires_follow_up: bool = False
    is_emergency_session: bool = False
    needs_human_intervention: bool = False
    
    def transition_to_phase(self, new_phase: ConversationPhase):
        """Transition to a new conversation phase"""
        self.previous_phase = self.current_phase
        self.current_phase = new_phase
        self.phase_start_time = datetime.utcnow()
    
    def update_mood(self, detected_mood: ConversationMood):
        """Update detected user mood"""
        self.detected_mood = detected_mood
    
    def add_to_history(self, message: str, sender: str, metadata: Optional[Dict[str, Any]] = None):
        """Add message to conversation history"""
        entry = {
            "message": message,
            "sender": sender,
            "timestamp": datetime.utcnow().isoformat(),
            "phase": self.current_phase.value,
            "metadata": metadata or {}
        }
        self.conversation_history.append(entry)
        
        # Keep history manageable (last 20 entries)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        return self.conversation_history[-limit:] if self.conversation_history else []
    
    def set_context_data(self, key: str, value: Any):
        """Set context data"""
        self.context_data[key] = value
    
    def get_context_data(self, key: str, default: Any = None) -> Any:
        """Get context data"""
        return self.context_data.get(key, default)
    
    def update_interaction_time(self):
        """Update last interaction time"""
        self.last_interaction_time = datetime.utcnow()
        self.message_count += 1
    
    def get_session_duration(self) -> int:
        """Get current session duration in seconds"""
        if self.conversation_history:
            start_time = datetime.fromisoformat(self.conversation_history[0]["timestamp"])
            return int((datetime.utcnow() - start_time).total_seconds())
        return 0
    
    def is_new_session(self) -> bool:
        """Check if this is a new conversation session"""
        return self.message_count <= 1
    
    def is_long_running_session(self) -> bool:
        """Check if session has been running for a long time"""
        return self.get_session_duration() > 1800  # 30 minutes
    
    def needs_proactive_update(self) -> bool:
        """Check if conversation needs proactive status update"""
        # If waiting in provider matching phase for too long
        if (self.current_phase == ConversationPhase.PROVIDER_MATCHING and
            (datetime.utcnow() - self.phase_start_time).total_seconds() > 300):  # 5 minutes
            return True
        
        # If request processing is taking too long
        if (self.current_phase == ConversationPhase.REQUEST_PROCESSING and
            (datetime.utcnow() - self.phase_start_time).total_seconds() > 180):  # 3 minutes
            return True
        
        return False
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation state"""
        return {
            "user_identifier": self.user_identifier,
            "current_phase": self.current_phase.value,
            "mood": self.detected_mood.value,
            "message_count": self.message_count,
            "session_duration": self.get_session_duration(),
            "active_request": self.active_request_id,
            "last_intent": self.last_intent,
            "needs_follow_up": self.requires_follow_up,
            "is_emergency": self.is_emergency_session
        }


class ConversationStateManager:
    """
    Manages conversation state transitions and business logic
    """
    
    def __init__(self):
        self.state_transitions = {
            ConversationPhase.GREETING: [
                ConversationPhase.INFORMATION_GATHERING,
                ConversationPhase.EMERGENCY_PROCESSING
            ],
            ConversationPhase.INFORMATION_GATHERING: [
                ConversationPhase.REQUEST_PROCESSING,
                ConversationPhase.EMERGENCY_PROCESSING,
                ConversationPhase.CANCELLATION
            ],
            ConversationPhase.REQUEST_PROCESSING: [
                ConversationPhase.PROVIDER_MATCHING,
                ConversationPhase.EMERGENCY_PROCESSING,
                ConversationPhase.CANCELLATION
            ],
            ConversationPhase.PROVIDER_MATCHING: [
                ConversationPhase.PROVIDER_COMMUNICATION,
                ConversationPhase.CANCELLATION,
                ConversationPhase.INFORMATION_GATHERING  # If need more info
            ],
            ConversationPhase.PROVIDER_COMMUNICATION: [
                ConversationPhase.SERVICE_COORDINATION,
                ConversationPhase.CANCELLATION,
                ConversationPhase.PROVIDER_MATCHING  # If provider rejects
            ],
            ConversationPhase.SERVICE_COORDINATION: [
                ConversationPhase.STATUS_TRACKING,
                ConversationPhase.COMPLETION,
                ConversationPhase.CANCELLATION
            ],
            ConversationPhase.STATUS_TRACKING: [
                ConversationPhase.COMPLETION,
                ConversationPhase.CANCELLATION,
                ConversationPhase.FOLLOW_UP
            ],
            ConversationPhase.EMERGENCY_PROCESSING: [
                ConversationPhase.PROVIDER_COMMUNICATION,
                ConversationPhase.SERVICE_COORDINATION
            ],
            ConversationPhase.CANCELLATION: [
                ConversationPhase.COMPLETION,
                ConversationPhase.GREETING  # New request
            ],
            ConversationPhase.COMPLETION: [
                ConversationPhase.FOLLOW_UP,
                ConversationPhase.GREETING  # New request
            ],
            ConversationPhase.FOLLOW_UP: [
                ConversationPhase.GREETING,
                ConversationPhase.INFORMATION_GATHERING  # New request
            ]
        }
    
    def can_transition(self, current_phase: ConversationPhase, target_phase: ConversationPhase) -> bool:
        """Check if transition between phases is valid"""
        allowed_transitions = self.state_transitions.get(current_phase, [])
        return target_phase in allowed_transitions
    
    def get_next_phase_for_intent(self, current_phase: ConversationPhase, intent: str) -> ConversationPhase:
        """Determine next phase based on current phase and detected intent"""
        
        # Emergency can happen from any phase
        if intent == "emergency":
            return ConversationPhase.EMERGENCY_PROCESSING
        
        # Cancellation can happen from most phases
        if intent == "cancel_request" and current_phase in [
            ConversationPhase.INFORMATION_GATHERING,
            ConversationPhase.REQUEST_PROCESSING,
            ConversationPhase.PROVIDER_MATCHING,
            ConversationPhase.PROVIDER_COMMUNICATION
        ]:
            return ConversationPhase.CANCELLATION
        
        # Phase-specific transitions
        if current_phase == ConversationPhase.GREETING:
            if intent == "new_service_request":
                return ConversationPhase.INFORMATION_GATHERING
        
        elif current_phase == ConversationPhase.INFORMATION_GATHERING:
            if intent == "continue_previous":
                return ConversationPhase.INFORMATION_GATHERING  # Continue gathering
            elif intent == "new_service_request":
                return ConversationPhase.REQUEST_PROCESSING  # If complete
        
        elif current_phase == ConversationPhase.REQUEST_PROCESSING:
            return ConversationPhase.PROVIDER_MATCHING
        
        elif current_phase == ConversationPhase.PROVIDER_MATCHING:
            if intent == "status_inquiry":
                return ConversationPhase.STATUS_TRACKING
        
        elif current_phase == ConversationPhase.STATUS_TRACKING:
            if intent == "general_inquiry":
                return ConversationPhase.FOLLOW_UP
        
        # Default: stay in current phase
        return current_phase
    
    def should_escalate_to_human(self, state: ConversationState) -> bool:
        """Determine if conversation should be escalated to human intervention"""
        
        # Too many failed attempts
        if state.message_count > 15 and state.current_phase == ConversationPhase.INFORMATION_GATHERING:
            return True
        
        # User explicitly frustrated
        if state.detected_mood == ConversationMood.FRUSTRATED and state.message_count > 5:
            return True
        
        # Emergency that can't be handled automatically
        if (state.is_emergency_session and 
            state.current_phase == ConversationPhase.EMERGENCY_PROCESSING and
            (datetime.utcnow() - state.phase_start_time).total_seconds() > 600):  # 10 minutes
            return True
        
        return False
    
    def get_proactive_message_type(self, state: ConversationState) -> Optional[str]:
        """Determine if a proactive message should be sent"""
        
        if state.current_phase == ConversationPhase.PROVIDER_MATCHING:
            phase_duration = (datetime.utcnow() - state.phase_start_time).total_seconds()
            
            if 120 <= phase_duration < 180:  # 2-3 minutes
                return "provider_search_update"
            elif 300 <= phase_duration < 360:  # 5-6 minutes
                return "extended_search_notification"
            elif phase_duration >= 600:  # 10 minutes
                return "search_timeout_warning"
        
        elif state.current_phase == ConversationPhase.SERVICE_COORDINATION:
            phase_duration = (datetime.utcnow() - state.phase_start_time).total_seconds()
            
            if phase_duration >= 3600:  # 1 hour
                return "service_progress_check"
        
        return None