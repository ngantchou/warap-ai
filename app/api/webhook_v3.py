"""
Webhook Router V3 - Session Management Integration
Handles WhatsApp webhooks with full session management support
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.database import get_db
from app.models.database_models import User, ConversationSession as DBSession
from app.services.enhanced_conversation_manager_v3 import EnhancedConversationManagerV3
from app.services.whatsapp_service import WhatsAppService
from app.middleware.security import limiter
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
conversation_manager = EnhancedConversationManagerV3()
whatsapp_service = WhatsAppService()
settings = get_settings()

@router.post("/whatsapp-v3")
@limiter.limit("100/minute")
async def whatsapp_webhook_v3(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enhanced WhatsApp webhook with session management
    """
    try:
        # Get request data
        data = await request.json()
        
        # Validate webhook signature
        if not whatsapp_service.validate_webhook_signature(request.headers, await request.body()):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
        
        # Process webhook events
        if data.get("entry"):
            for entry in data["entry"]:
                changes = entry.get("changes", [])
                
                for change in changes:
                    if change.get("field") == "messages":
                        message_data = change.get("value", {})
                        
                        # Process incoming messages
                        messages = message_data.get("messages", [])
                        for message in messages:
                            await process_whatsapp_message_v3(message, message_data, db, background_tasks)
        
        return JSONResponse({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook V3: {e}")
        return JSONResponse({"error": "Internal server error"}, status_code=500)

@router.post("/chat-v3")
@limiter.limit("200/minute")
async def chat_webhook_v3(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enhanced chat webhook with session management
    """
    try:
        data = await request.json()
        message = data.get("message", "")
        phone_number = data.get("phone_number", "")
        
        if not message or not phone_number:
            raise HTTPException(status_code=400, detail="Message and phone number required")
        
        logger.info(f"Received chat message V3 from {phone_number}: {message}")
        
        # Get or create user
        user = get_or_create_user(phone_number, db)
        user_id = str(user.id)
        
        # Process message with session management
        response = await conversation_manager.process_message(
            message=message,
            phone_number=phone_number,
            user_id=user_id,
            db=db
        )
        
        # Log response
        logger.info(f"Sent chat response to {phone_number}: {response.get('response')}")
        
        return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"Error processing chat webhook V3: {e}")
        return JSONResponse({
            "response": "Désolé, une erreur technique s'est produite. Veuillez réessayer.",
            "conversation_state": "ERROR",
            "automation_rate": 0.0,
            "session_data": {
                "error_handled": True,
                "error_type": "system_error",
                "recovery_action": "retry"
            }
        })

@router.get("/webhook/session-stats")
async def get_session_stats(db: Session = Depends(get_db)):
    """
    Get session management statistics
    """
    try:
        # Get performance stats from conversation manager
        performance_stats = await conversation_manager.get_performance_stats()
        
        # Get database statistics
        total_sessions = db.query(DBSession).count()
        active_sessions = db.query(DBSession).filter(
            DBSession.is_active == True,
            DBSession.is_expired == False
        ).count()
        completed_sessions = db.query(DBSession).filter(
            DBSession.current_state == "COMPLETED"
        ).count()
        expired_sessions = db.query(DBSession).filter(
            DBSession.is_expired == True
        ).count()
        
        return {
            "system_status": "operational",
            "session_management": {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "completed_sessions": completed_sessions,
                "expired_sessions": expired_sessions,
                "completion_rate": (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
            },
            "conversation_performance": performance_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting session stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/webhook/session/{session_id}")
async def get_session_info(session_id: str, db: Session = Depends(get_db)):
    """
    Get detailed session information
    """
    try:
        session_info = await conversation_manager.get_session_info(session_id, db)
        
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/webhook/user-session/{user_id}")
async def get_user_session_info(user_id: str, db: Session = Depends(get_db)):
    """
    Get user's active session information
    """
    try:
        session_info = await conversation_manager.get_user_session_info(user_id, db)
        
        if not session_info:
            return {"message": "No active session found"}
        
        return session_info
        
    except Exception as e:
        logger.error(f"Error getting user session info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook/session/{session_id}/pause")
async def pause_session(session_id: str, db: Session = Depends(get_db)):
    """
    Pause a session
    """
    try:
        success = await conversation_manager.pause_session(session_id, db)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to pause session")
        
        return {"message": "Session paused successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook/session/{session_id}/resume")
async def resume_session(session_id: str, db: Session = Depends(get_db)):
    """
    Resume a paused session
    """
    try:
        success = await conversation_manager.resume_session(session_id, db)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to resume session")
        
        return {"message": "Session resumed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook/session/{session_id}/cancel")
async def cancel_session(session_id: str, db: Session = Depends(get_db)):
    """
    Cancel a session
    """
    try:
        success = await conversation_manager.cancel_session(session_id, db)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel session")
        
        return {"message": "Session cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook/cleanup-sessions")
async def cleanup_expired_sessions(db: Session = Depends(get_db)):
    """
    Cleanup expired sessions
    """
    try:
        cleaned_count = await conversation_manager.cleanup_expired_sessions(db)
        
        return {
            "message": f"Cleaned up {cleaned_count} expired sessions",
            "cleaned_sessions": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_whatsapp_message_v3(
    message: Dict[str, Any],
    message_data: Dict[str, Any],
    db: Session,
    background_tasks: BackgroundTasks
):
    """
    Process individual WhatsApp message with session management
    """
    try:
        # Extract message information
        phone_number = message.get("from", "")
        message_text = ""
        
        # Handle different message types
        if message.get("type") == "text":
            message_text = message.get("text", {}).get("body", "")
        elif message.get("type") == "interactive":
            # Handle interactive messages (buttons, quick replies)
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                message_text = interactive.get("button_reply", {}).get("title", "")
            elif interactive.get("type") == "list_reply":
                message_text = interactive.get("list_reply", {}).get("title", "")
        
        if not message_text or not phone_number:
            logger.warning(f"Skipping message with missing data: {message}")
            return
        
        logger.info(f"Processing WhatsApp message V3 from {phone_number}: {message_text}")
        
        # Get or create user
        user = get_or_create_user(phone_number, db)
        user_id = str(user.id)
        
        # Process message with session management
        response = await conversation_manager.process_message(
            message=message_text,
            phone_number=phone_number,
            user_id=user_id,
            db=db
        )
        
        # Send response via WhatsApp
        if response.get("response"):
            success = whatsapp_service.send_message(
                to=phone_number,
                message=response["response"]
            )
            
            if success:
                logger.info(f"Sent WhatsApp response to {phone_number}: {response['response']}")
            else:
                logger.error(f"Failed to send WhatsApp response to {phone_number}")
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message V3: {e}")
        
        # Send error message
        error_response = "Désolé, une erreur technique s'est produite. Veuillez réessayer."
        whatsapp_service.send_message(to=phone_number, message=error_response)

@router.post("/test-session")
async def test_session_management(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Test endpoint for session management functionality
    """
    try:
        data = await request.json()
        message = data.get("message", "")
        phone_number = data.get("phone_number", "")
        
        if not message or not phone_number:
            raise HTTPException(status_code=400, detail="Message and phone number required")
        
        logger.info(f"Testing session management with message: {message}")
        
        # Get or create user
        user = get_or_create_user(phone_number, db)
        user_id = str(user.id)
        
        # Process message with session management
        result = await conversation_manager.process_message(
            message=message,
            phone_number=phone_number,
            user_id=user_id,
            db=db
        )
        
        return JSONResponse({
            "status": "success",
            "result": result,
            "session_stats": {
                "total_conversations": conversation_manager.total_conversations,
                "successful_conversations": conversation_manager.successful_conversations,
                "session_creations": conversation_manager.session_creations,
                "state_transitions": conversation_manager.state_transitions
            }
        })
        
    except Exception as e:
        logger.error(f"Error testing session management: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

def get_or_create_user(phone_number: str, db: Session) -> User:
    """
    Get existing user or create new one
    """
    # Normalize phone number
    normalized_phone = phone_number.replace("+", "").replace(" ", "").replace("-", "")
    
    # Try to find existing user
    user = db.query(User).filter(
        User.phone_number == normalized_phone
    ).first()
    
    if not user:
        # Create new user
        user = User(
            whatsapp_id=normalized_phone,
            phone_number=normalized_phone,
            name=f"User {normalized_phone[-4:]}"  # Use last 4 digits as name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {user.phone_number}")
    
    return user

# Session management endpoints for testing
@router.post("/webhook/test-session")
async def test_session_management(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Test session management functionality
    """
    try:
        data = await request.json()
        message = data.get("message", "J'ai un problème de plomberie")
        phone_number = data.get("phone_number", "237691924172")
        
        # Get or create user
        user = get_or_create_user(phone_number, db)
        user_id = str(user.id)
        
        # Process message
        response = await conversation_manager.process_message(
            message=message,
            phone_number=phone_number,
            user_id=user_id,
            db=db
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in test session: {e}")
        return {
            "error": str(e),
            "response": "Erreur de test"
        }