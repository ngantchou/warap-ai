"""
Conversation Context Manager for Djobea AI
Manages conversation context and memory across interactions
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from dataclasses import dataclass, asdict

from app.models.database_models import User, Conversation, ServiceRequest
from loguru import logger


@dataclass
class ConversationContext:
    """Complete conversation context for a user"""
    user_id: int
    conversation_history: List[Dict[str, Any]]
    active_requests: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    session_data: Dict[str, Any]
    last_interaction: datetime
    total_messages: int


class ConversationContextManager:
    """
    Manages conversation context and memory
    Provides seamless conversation continuity across sessions
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.context_cache: Dict[str, ConversationContext] = {}
        self.cache_timeout_minutes = 30
    
    async def get_or_create_context(self, user_identifier: str) -> Dict[str, Any]:
        """Get existing conversation context or create new one"""
        
        # Check cache first
        if user_identifier in self.context_cache:
            context = self.context_cache[user_identifier]
            if self._is_context_fresh(context):
                return self._format_context_data(context)
        
        # Load from database
        user = await self._get_user_by_identifier(user_identifier)
        if not user:
            # New user - create minimal context
            return self._create_new_user_context()
        
        # Build context from database
        context = await self._build_context_from_database(user)
        
        # Cache context
        self.context_cache[user_identifier] = context
        
        return self._format_context_data(context)
    
    async def add_message(
        self, 
        user_identifier: str, 
        message: str, 
        sender: str,
        analysis_data: Optional[Dict[str, Any]] = None
    ):
        """Add new message to conversation context"""
        
        user = await self._get_user_by_identifier(user_identifier)
        if not user:
            return
        
        # Create conversation record
        conversation = Conversation(
            user_id=user.id,
            message_content=message,
            message_type="incoming",
            ai_response="",  # Will be updated later
            created_at=datetime.utcnow()
        )
        
        self.db.add(conversation)
        self.db.commit()
        
        # Update cache if exists
        if user_identifier in self.context_cache:
            context = self.context_cache[user_identifier]
            context.conversation_history.append({
                "message": message,
                "sender": sender,
                "timestamp": datetime.utcnow().isoformat(),
                "analysis": analysis_data
            })
            context.total_messages += 1
            context.last_interaction = datetime.utcnow()
    
    async def update_response(self, user_identifier: str, response: str):
        """Update the AI response for the last conversation"""
        
        user = await self._get_user_by_identifier(user_identifier)
        if not user:
            return
        
        # Get the most recent conversation
        latest_conversation = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
            .first()
        )
        
        if latest_conversation:
            # Update conversation response
            self.db.query(Conversation).filter(
                Conversation.id == latest_conversation.id
            ).update({"ai_response": response})
            self.db.commit()
    
    async def get_conversation_history(
        self, 
        user_identifier: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        
        user = await self._get_user_by_identifier(user_identifier)
        if not user:
            return []
        
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .all()
        )
        
        history = []
        for conv in reversed(conversations):  # Reverse to get chronological order
            history.extend([
                {
                    "content": conv.message_content,
                    "sender": "user",
                    "timestamp": conv.created_at.isoformat()
                },
                {
                    "content": conv.ai_response,
                    "sender": "assistant",
                    "timestamp": conv.created_at.isoformat()
                }
            ])
        
        return history
    
    async def get_active_requests(self, user_identifier: str) -> List[Dict[str, Any]]:
        """Get user's active service requests"""
        
        user = await self._get_user_by_identifier(user_identifier)
        if not user:
            return []
        
        active_requests = (
            self.db.query(ServiceRequest)
            .filter(ServiceRequest.user_id == user.id)
            .filter(ServiceRequest.status.in_([
                "PENDING", "PROVIDER_NOTIFIED", "ASSIGNED", "IN_PROGRESS"
            ]))
            .order_by(ServiceRequest.created_at.desc())
            .all()
        )
        
        return [
            {
                "id": req.id,
                "service_type": req.service_type,
                "description": req.description,
                "location": req.location,
                "status": req.status,
                "created_at": req.created_at.isoformat(),
                "urgency": req.urgency
            }
            for req in active_requests
        ]
    
    async def update_user_preferences(
        self, 
        user_identifier: str, 
        preferences: Dict[str, Any]
    ):
        """Update user preferences in context"""
        
        if user_identifier in self.context_cache:
            context = self.context_cache[user_identifier]
            context.user_preferences.update(preferences)
    
    async def set_session_data(
        self, 
        user_identifier: str, 
        key: str, 
        value: Any
    ):
        """Set session-specific data"""
        
        if user_identifier in self.context_cache:
            context = self.context_cache[user_identifier]
            context.session_data[key] = value
    
    async def get_session_data(
        self, 
        user_identifier: str, 
        key: str, 
        default: Any = None
    ) -> Any:
        """Get session-specific data"""
        
        if user_identifier in self.context_cache:
            context = self.context_cache[user_identifier]
            return context.session_data.get(key, default)
        
        return default
    
    async def clear_context(self, user_identifier: str):
        """Clear context for user (new session)"""
        
        if user_identifier in self.context_cache:
            del self.context_cache[user_identifier]
    
    def cleanup_expired_contexts(self):
        """Remove expired contexts from cache"""
        
        current_time = datetime.utcnow()
        expired_keys = []
        
        for user_id, context in self.context_cache.items():
            if current_time - context.last_interaction > timedelta(minutes=self.cache_timeout_minutes):
                expired_keys.append(user_id)
        
        for key in expired_keys:
            del self.context_cache[key]
    
    async def _get_user_by_identifier(self, user_identifier: str) -> Optional[User]:
        """Get user by identifier (phone number or session ID)"""
        
        # Try phone number format first
        if user_identifier.startswith("237") or user_identifier.startswith("+237"):
            phone = user_identifier.replace("+", "")
            user = self.db.query(User).filter(User.whatsapp_id == phone).first()
            if user:
                return user
        
        # Try session format
        user = self.db.query(User).filter(User.whatsapp_id == user_identifier).first()
        return user
    
    async def _build_context_from_database(self, user: User) -> ConversationContext:
        """Build complete context from database"""
        
        # Get conversation history
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
            .limit(20)
            .all()
        )
        
        conversation_history = []
        for conv in reversed(conversations):
            conversation_history.extend([
                {
                    "message": conv.message_content,
                    "sender": "user",
                    "timestamp": conv.created_at.isoformat()
                },
                {
                    "message": conv.ai_response,
                    "sender": "assistant", 
                    "timestamp": conv.created_at.isoformat()
                }
            ])
        
        # Get active requests
        active_requests = await self.get_active_requests(user.whatsapp_id)
        
        # Build user preferences from conversation history
        user_preferences = self._extract_user_preferences(conversations)
        
        return ConversationContext(
            user_id=user.id,
            conversation_history=conversation_history,
            active_requests=active_requests,
            user_preferences=user_preferences,
            session_data={},
            last_interaction=datetime.utcnow(),
            total_messages=len(conversations)
        )
    
    def _create_new_user_context(self) -> Dict[str, Any]:
        """Create context for new user"""
        
        return {
            "conversation_history": [],
            "active_requests": [],
            "user_preferences": {
                "language": "french",
                "communication_style": "polite",
                "service_preferences": {}
            },
            "session_data": {},
            "is_new_user": True
        }
    
    def _format_context_data(self, context: ConversationContext) -> Dict[str, Any]:
        """Format context data for use"""
        
        return {
            "conversation_history": context.conversation_history[-10:],  # Last 10 messages
            "active_requests": context.active_requests,
            "user_preferences": context.user_preferences,
            "session_data": context.session_data,
            "total_messages": context.total_messages
        }
    
    def _is_context_fresh(self, context: ConversationContext) -> bool:
        """Check if context is still fresh (not expired)"""
        
        time_diff = datetime.utcnow() - context.last_interaction
        return time_diff < timedelta(minutes=self.cache_timeout_minutes)
    
    def _extract_user_preferences(self, conversations: List[Conversation]) -> Dict[str, Any]:
        """Extract user preferences from conversation history"""
        
        preferences = {
            "language": "french",
            "communication_style": "polite",
            "service_preferences": {},
            "urgency_patterns": [],
            "location_patterns": []
        }
        
        # Analyze conversation patterns to extract preferences
        for conv in conversations:
            # Extract service preferences from message content patterns
            if conv.message_content:
                # Simple pattern matching for service types
                content_lower = conv.message_content.lower()
                if "plomberie" in content_lower:
                    service_type = "plomberie"
                    if service_type not in preferences["service_preferences"]:
                        preferences["service_preferences"][service_type] = 0
                    preferences["service_preferences"][service_type] += 1
                elif "électricité" in content_lower or "électrique" in content_lower:
                    service_type = "électricité"
                    if service_type not in preferences["service_preferences"]:
                        preferences["service_preferences"][service_type] = 0
                    preferences["service_preferences"][service_type] += 1
                elif "électroménager" in content_lower:
                    service_type = "électroménager"
                    if service_type not in preferences["service_preferences"]:
                        preferences["service_preferences"][service_type] = 0
                    preferences["service_preferences"][service_type] += 1
        
        return preferences