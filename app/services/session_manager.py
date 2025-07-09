"""
Session Manager Service
Manages conversation sessions with state persistence and Redis caching
"""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from app.models.database_models import ConversationSession as DBSession, User, Conversation
from app.models.conversation_session import (
    ConversationSession, ConversationState, SessionPhase, ConversationMessage,
    CollectedData, SessionMetrics, TransitionRule
)
from app.database import get_db
from app.config import get_settings

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages conversation sessions with state persistence and caching
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        self.cache_enabled = False
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.max_sessions_in_memory = 100
        self.cleanup_task = None
        
        # Initialize Redis if available
        self._initialize_redis()
    
    async def start_cleanup_task(self):
        """Start the cleanup task"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
    
    def _initialize_redis(self):
        """Initialize Redis connection if available"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory session storage")
            return
        
        try:
            self.redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                decode_responses=True,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis session cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}, using in-memory storage")
            self.redis_client = None
            self.cache_enabled = False
    
    async def create_session(
        self, 
        user_id: str, 
        phone_number: str, 
        initial_state: ConversationState = ConversationState.INITIAL,
        db: Session = None
    ) -> ConversationSession:
        """
        Create new conversation session
        """
        session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create session object
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            phone_number=phone_number,
            initial_state=initial_state
        )
        
        # Store in database
        if db:
            await self._save_session_to_db(session, db)
        
        # Cache in Redis/memory
        await self._cache_session(session)
        
        # Add to active sessions
        self.active_sessions[session_id] = session
        self.session_locks[session_id] = asyncio.Lock()
        
        logger.info(f"Created new session: {session_id} for user {user_id}")
        return session
    
    async def get_session(self, session_id: str, db: Session = None) -> Optional[ConversationSession]:
        """
        Get session by ID from cache or database
        """
        # Check active sessions first
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if not session.is_expired():
                return session
            else:
                # Remove expired session
                await self._remove_session(session_id)
                return None
        
        # Try cache
        session = await self._get_cached_session(session_id)
        if session:
            if not session.is_expired():
                self.active_sessions[session_id] = session
                self.session_locks[session_id] = asyncio.Lock()
                return session
            else:
                await self._remove_session(session_id)
                return None
        
        # Load from database
        if db:
            session = await self._load_session_from_db(session_id, db)
            if session and not session.is_expired():
                await self._cache_session(session)
                self.active_sessions[session_id] = session
                self.session_locks[session_id] = asyncio.Lock()
                return session
            elif session:
                # Mark as expired in database
                await self._mark_session_expired(session_id, db)
        
        return None
    
    async def get_user_active_session(self, user_id: int, db: Session = None) -> Optional[ConversationSession]:
        """
        Get active session for user
        """
        # Check active sessions
        for session in self.active_sessions.values():
            if session.user_id == user_id and not session.is_expired():
                return session
        
        # Check database
        if db:
            db_session = db.query(DBSession).filter(
                DBSession.user_id == user_id,
                DBSession.is_active == True,
                DBSession.is_expired == False,
                DBSession.expires_at > datetime.now()
            ).order_by(DBSession.created_at.desc()).first()
            
            if db_session:
                session = await self._convert_db_to_session(db_session, db)
                if session:
                    await self._cache_session(session)
                    self.active_sessions[session.session_id] = session
                    self.session_locks[session.session_id] = asyncio.Lock()
                    return session
        
        return None
    
    async def update_session(self, session: ConversationSession, db: Session = None) -> bool:
        """
        Update session in cache and database
        """
        session_id = session.session_id
        
        # Get lock for session
        if session_id not in self.session_locks:
            self.session_locks[session_id] = asyncio.Lock()
        
        async with self.session_locks[session_id]:
            # Update timestamp
            session.updated_at = datetime.now()
            
            # Update in active sessions
            self.active_sessions[session_id] = session
            
            # Update cache
            await self._cache_session(session)
            
            # Update database
            if db:
                await self._save_session_to_db(session, db)
            
            logger.debug(f"Updated session: {session_id}")
            return True
    
    async def transition_session_state(
        self, 
        session_id: str, 
        new_state: ConversationState, 
        reason: str = "", 
        db: Session = None
    ) -> bool:
        """
        Transition session to new state
        """
        session = await self.get_session(session_id, db)
        if not session:
            return False
        
        # Validate transition
        if not TransitionRule.is_valid_transition(session.current_state, new_state):
            logger.warning(f"Invalid transition from {session.current_state} to {new_state}")
            return False
        
        # Perform transition
        success = session.transition_to(new_state, reason)
        if success:
            await self.update_session(session, db)
            logger.info(f"Session {session_id} transitioned to {new_state.value}")
        
        return success
    
    async def add_message_to_session(
        self, 
        session_id: str, 
        message: ConversationMessage, 
        db: Session = None
    ) -> bool:
        """
        Add message to session
        """
        session = await self.get_session(session_id, db)
        if not session:
            return False
        
        # Add message to session
        session.add_message(message)
        
        # Update session
        await self.update_session(session, db)
        
        # Also save to database conversations table
        if db:
            await self._save_message_to_db(session_id, message, db)
        
        return True
    
    async def update_collected_data(
        self, 
        session_id: str, 
        field: str, 
        value: Any, 
        confidence: float = None, 
        db: Session = None
    ) -> bool:
        """
        Update collected data in session
        """
        session = await self.get_session(session_id, db)
        if not session:
            return False
        
        # Update data
        session.update_collected_data(field, value, confidence)
        
        # Update session
        await self.update_session(session, db)
        
        return True
    
    async def complete_session(self, session_id: str, db: Session = None) -> bool:
        """
        Mark session as completed
        """
        session = await self.get_session(session_id, db)
        if not session:
            return False
        
        # Transition to completed state
        success = await self.transition_session_state(
            session_id, ConversationState.COMPLETED, "session_completed", db
        )
        
        if success:
            session.metrics.end_time = datetime.now()
            await self.update_session(session, db)
            
            # Mark as completed in database
            if db:
                await self._mark_session_completed(session_id, db)
            
            logger.info(f"Session {session_id} completed")
        
        return success
    
    async def expire_session(self, session_id: str, db: Session = None) -> bool:
        """
        Mark session as expired
        """
        session = await self.get_session(session_id, db)
        if not session:
            return False
        
        # Transition to expired state
        success = await self.transition_session_state(
            session_id, ConversationState.EXPIRED, "session_expired", db
        )
        
        if success:
            # Remove from active sessions
            await self._remove_session(session_id)
            
            # Mark as expired in database
            if db:
                await self._mark_session_expired(session_id, db)
            
            logger.info(f"Session {session_id} expired")
        
        return success
    
    async def get_session_metrics(self, session_id: str, db: Session = None) -> Optional[SessionMetrics]:
        """
        Get session performance metrics
        """
        session = await self.get_session(session_id, db)
        if not session:
            return None
        
        return session.metrics
    
    async def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions
        """
        return len(self.active_sessions)
    
    async def get_session_summary(self, session_id: str, db: Session = None) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive session summary
        """
        session = await self.get_session(session_id, db)
        if not session:
            return None
        
        return session.get_session_summary()
    
    async def cleanup_expired_sessions(self, db: Session = None) -> int:
        """
        Cleanup expired sessions
        """
        cleaned_count = 0
        
        # Clean active sessions
        expired_sessions = []
        for session_id, session in self.active_sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self._remove_session(session_id)
            cleaned_count += 1
        
        # Clean database sessions
        if db:
            expired_db_sessions = db.query(DBSession).filter(
                DBSession.expires_at < datetime.now(),
                DBSession.is_expired == False
            ).all()
            
            for db_session in expired_db_sessions:
                db_session.is_expired = True
                db_session.is_active = False
                cleaned_count += 1
            
            db.commit()
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
        
        return cleaned_count
    
    async def _cache_session(self, session: ConversationSession):
        """Cache session in Redis or memory"""
        if self.cache_enabled and self.redis_client:
            try:
                session_data = session.to_dict()
                cache_key = f"session:{session.session_id}"
                self.redis_client.setex(
                    cache_key,
                    int(self.settings.session_cache_ttl),
                    json.dumps(session_data, default=str)
                )
            except Exception as e:
                logger.warning(f"Failed to cache session in Redis: {e}")
    
    async def _get_cached_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session from cache"""
        if self.cache_enabled and self.redis_client:
            try:
                cache_key = f"session:{session_id}"
                cached_data = self.redis_client.get(cache_key)
                
                if cached_data:
                    session_data = json.loads(cached_data)
                    return ConversationSession.from_dict(session_data)
                    
            except Exception as e:
                logger.warning(f"Failed to get cached session: {e}")
        
        return None
    
    async def _remove_session(self, session_id: str):
        """Remove session from cache and memory"""
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        if session_id in self.session_locks:
            del self.session_locks[session_id]
        
        # Remove from cache
        if self.cache_enabled and self.redis_client:
            try:
                cache_key = f"session:{session_id}"
                self.redis_client.delete(cache_key)
            except Exception as e:
                logger.warning(f"Failed to remove session from cache: {e}")
    
    async def _save_session_to_db(self, session: ConversationSession, db: Session):
        """Save session to database"""
        try:
            # Check if session exists
            db_session = db.query(DBSession).filter(
                DBSession.session_id == session.session_id
            ).first()
            
            if db_session:
                # Update existing session
                db_session.current_state = session.current_state.value
                db_session.previous_state = session.previous_state.value if session.previous_state else None
                db_session.current_phase = session.current_phase.value if session.current_phase else None
                db_session.state_history = session.state_history
                db_session.collected_data = session.collected_data.to_dict()
                db_session.session_metadata = session.session_metadata
                db_session.metrics = session.metrics.to_dict()
                db_session.expires_at = session.expires_at
                db_session.is_active = not session.is_expired()
                db_session.is_expired = session.is_expired()
            else:
                # Create new session
                db_session = DBSession(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    phone_number=session.phone_number,
                    current_state=session.current_state.value,
                    previous_state=session.previous_state.value if session.previous_state else None,
                    current_phase=session.current_phase.value if session.current_phase else None,
                    state_history=session.state_history,
                    collected_data=session.collected_data.to_dict(),
                    session_metadata=session.session_metadata,
                    metrics=session.metrics.to_dict(),
                    expires_at=session.expires_at,
                    is_active=not session.is_expired(),
                    is_expired=session.is_expired()
                )
                db.add(db_session)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
            db.rollback()
    
    async def _load_session_from_db(self, session_id: str, db: Session) -> Optional[ConversationSession]:
        """Load session from database"""
        try:
            db_session = db.query(DBSession).filter(
                DBSession.session_id == session_id
            ).first()
            
            if db_session:
                return await self._convert_db_to_session(db_session, db)
                
        except Exception as e:
            logger.error(f"Failed to load session from database: {e}")
        
        return None
    
    async def _convert_db_to_session(self, db_session: DBSession, db: Session) -> Optional[ConversationSession]:
        """Convert database session to ConversationSession object"""
        try:
            # Create session object
            session = ConversationSession(
                session_id=db_session.session_id,
                user_id=db_session.user_id,
                phone_number=db_session.phone_number,
                initial_state=ConversationState(db_session.current_state)
            )
            
            # Restore session data
            session.created_at = db_session.created_at
            session.updated_at = db_session.updated_at
            session.expires_at = db_session.expires_at
            session.current_state = ConversationState(db_session.current_state)
            session.previous_state = ConversationState(db_session.previous_state) if db_session.previous_state else None
            session.current_phase = SessionPhase(db_session.current_phase) if db_session.current_phase else None
            session.state_history = db_session.state_history or []
            
            # Restore collected data
            if db_session.collected_data:
                session.collected_data = CollectedData.from_dict(db_session.collected_data)
            
            # Restore metadata
            session.session_metadata = db_session.session_metadata or {}
            
            # Restore metrics
            if db_session.metrics:
                session.metrics = SessionMetrics.from_dict(db_session.metrics)
            
            # Load recent conversation history
            recent_messages = db.query(Conversation).filter(
                Conversation.session_id == session.session_id
            ).order_by(Conversation.created_at.desc()).limit(10).all()
            
            for db_message in reversed(recent_messages):
                message = ConversationMessage(
                    id=str(db_message.id),
                    timestamp=db_message.created_at,
                    message_type=db_message.message_type,
                    content=db_message.message_content,
                    action_code=db_message.action_code,
                    confidence_score=db_message.confidence_score,
                    extracted_data=db_message.extracted_data or {},
                    metadata=db_message.action_metadata or {}
                )
                session.conversation_history.append(message)
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to convert database session: {e}")
            return None
    
    async def _save_message_to_db(self, session_id: str, message: ConversationMessage, db: Session):
        """Save message to database"""
        try:
            # Get user ID from session
            db_session = db.query(DBSession).filter(
                DBSession.session_id == session_id
            ).first()
            
            if db_session:
                db_message = Conversation(
                    user_id=db_session.user_id,
                    session_id=session_id,
                    message_type=message.message_type,
                    message_content=message.content,
                    action_code=message.action_code,
                    confidence_score=message.confidence_score,
                    extracted_data=message.extracted_data,
                    action_metadata=message.metadata
                )
                
                db.add(db_message)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")
            db.rollback()
    
    async def _mark_session_completed(self, session_id: str, db: Session):
        """Mark session as completed in database"""
        try:
            db_session = db.query(DBSession).filter(
                DBSession.session_id == session_id
            ).first()
            
            if db_session:
                db_session.is_active = False
                db_session.completed_at = datetime.now()
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to mark session as completed: {e}")
            db.rollback()
    
    async def _mark_session_expired(self, session_id: str, db: Session):
        """Mark session as expired in database"""
        try:
            db_session = db.query(DBSession).filter(
                DBSession.session_id == session_id
            ).first()
            
            if db_session:
                db_session.is_expired = True
                db_session.is_active = False
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to mark session as expired: {e}")
            db.rollback()
    
    async def _cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired_sessions()
                
                # Clean up memory if too many sessions
                if len(self.active_sessions) > self.max_sessions_in_memory:
                    oldest_sessions = sorted(
                        self.active_sessions.items(),
                        key=lambda x: x[1].updated_at
                    )[:len(self.active_sessions) - self.max_sessions_in_memory]
                    
                    for session_id, _ in oldest_sessions:
                        await self._remove_session(session_id)
                        
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")


# Global session manager instance
session_manager = SessionManager()


async def get_session_manager() -> SessionManager:
    """Get session manager instance"""
    return session_manager