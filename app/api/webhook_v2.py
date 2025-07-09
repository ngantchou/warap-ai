"""
Enhanced Webhook V2 with Action Code System
Implements 99% automation through structured Agent-LLM communication
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
from datetime import datetime
from loguru import logger

from app.services.enhanced_conversation_manager_v2 import enhanced_conversation_manager_v2
from app.services.whatsapp_service import WhatsAppService
from app.models.action_codes import ActionCode, ConversationState
from app.database import get_db
from app.config import get_settings
from sqlalchemy.orm import Session

router = APIRouter()
settings = get_settings()
whatsapp_service = WhatsAppService()


class WhatsAppMessage(BaseModel):
    """WhatsApp message model"""
    Body: str
    From: str
    To: str
    MessageSid: Optional[str] = None
    AccountSid: Optional[str] = None
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None
    NumMedia: Optional[str] = "0"


class ChatMessage(BaseModel):
    """Chat widget message model"""
    message: str
    phone_number: str
    session_id: Optional[str] = None


@router.post("/whatsapp-v2")
async def whatsapp_webhook_v2(request: Request, db: Session = Depends(get_db)):
    """
    Enhanced WhatsApp webhook with action code system
    Processes messages using structured Agent-LLM communication
    """
    try:
        # Get form data
        form_data = await request.form()
        logger.info(f"Received WhatsApp webhook V2: {dict(form_data)}")
        
        # Extract message data
        message_body = form_data.get("Body", "").strip()
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        to_number = form_data.get("To", "").replace("whatsapp:", "")
        message_sid = form_data.get("MessageSid", "")
        
        # Validate required fields
        if not message_body or not from_number:
            logger.warning("Missing required fields in WhatsApp webhook")
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields"}
            )
        
        # Clean phone number
        phone_number = from_number.replace("+", "").replace(" ", "")
        
        # Log incoming message
        logger.info(f"Processing WhatsApp message V2 from {phone_number}: {message_body}")
        
        # Process message through enhanced conversation manager
        response_message = await enhanced_conversation_manager_v2.process_message(
            phone_number, message_body, db
        )
        
        # Send response via WhatsApp
        if response_message:
            await whatsapp_service.send_message(phone_number, response_message)
            logger.info(f"Sent WhatsApp response to {phone_number}: {response_message}")
        
        # Get conversation stats for monitoring
        stats = enhanced_conversation_manager_v2.get_conversation_stats()
        
        # Log system performance metrics
        logger.info(f"Conversation stats: {stats}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Message processed successfully",
                "automation_rate": stats.get("automation_rate", 0),
                "total_conversations": stats.get("total_conversations", 0)
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook V2: {str(e)}")
        
        # Send error response to user
        try:
            if 'phone_number' in locals():
                await whatsapp_service.send_message(
                    phone_number,
                    "Désolé, une erreur technique s'est produite. Veuillez réessayer dans quelques instants."
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {str(send_error)}")
        
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


@router.post("/chat-v2")
async def chat_webhook_v2(message: ChatMessage, db: Session = Depends(get_db)):
    """
    Enhanced chat widget webhook with action code system
    Processes chat messages using structured Agent-LLM communication
    """
    try:
        logger.info(f"Received chat message V2 from {message.phone_number}: {message.message}")
        
        # Validate phone number
        if not message.phone_number or len(message.phone_number) < 10:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid phone number"}
            )
        
        # Clean phone number
        phone_number = message.phone_number.replace("+", "").replace(" ", "")
        
        # Process message through enhanced conversation manager
        response_message = await enhanced_conversation_manager_v2.process_message(
            phone_number, message.message, db
        )
        
        # Get conversation stats
        stats = enhanced_conversation_manager_v2.get_conversation_stats()
        
        # Get current session state for frontend
        session = enhanced_conversation_manager_v2.active_sessions.get(phone_number, {})
        current_state = session.get("conversation_state", ConversationState.INITIAL)
        
        logger.info(f"Sent chat response to {phone_number}: {response_message}")
        
        return JSONResponse(
            status_code=200,
            content={
                "response": response_message,
                "conversation_state": current_state.value if isinstance(current_state, ConversationState) else str(current_state),
                "automation_rate": stats.get("automation_rate", 0),
                "session_data": session.get("session_data", {})
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message V2: {str(e)}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Une erreur technique s'est produite. Veuillez réessayer.",
                "response": "Désolé, une erreur technique s'est produite. Veuillez réessayer dans quelques instants."
            }
        )


@router.get("/system-stats")
async def get_system_stats():
    """
    Get system statistics for monitoring
    """
    try:
        # Get conversation stats
        conversation_stats = enhanced_conversation_manager_v2.get_conversation_stats()
        
        # Get active sessions info
        active_sessions = len(enhanced_conversation_manager_v2.active_sessions)
        
        # Calculate performance metrics
        automation_rate = conversation_stats.get("automation_rate", 0)
        success_rate = conversation_stats.get("success_rate", 0)
        
        return JSONResponse(
            status_code=200,
            content={
                "system_status": "operational",
                "conversation_stats": conversation_stats,
                "active_sessions": active_sessions,
                "performance_metrics": {
                    "automation_rate": automation_rate,
                    "success_rate": success_rate,
                    "target_automation": 99.0,
                    "target_success": 95.0
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get system statistics"}
        )


@router.post("/test-action-code")
async def test_action_code(
    action_code: str,
    phone_number: str,
    test_message: str,
    db: Session = Depends(get_db)
):
    """
    Test specific action code execution
    Development and testing endpoint
    """
    try:
        # Validate action code
        if not ActionCode.is_valid_code(action_code):
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid action code: {action_code}"}
            )
        
        # Get or create session
        session = enhanced_conversation_manager_v2.get_or_create_session(phone_number, db)
        
        # Create mock LLM response with specified action code
        from app.models.action_codes import LLMResponse
        
        test_response = LLMResponse(
            action_code=ActionCode(action_code),
            client_message=f"Test response for {action_code}",
            extracted_data={"test": True},
            session_update={"test_mode": True},
            next_state=ConversationState.COLLECTING,
            confidence=0.9,
            metadata={"test_execution": True}
        )
        
        # Execute action
        action_result = await enhanced_conversation_manager_v2.code_executor.execute_action(
            test_response, phone_number, session, db
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "action_code": action_code,
                "execution_result": action_result.to_dict(),
                "test_message": test_message,
                "session_state": session.get("conversation_state", ConversationState.INITIAL).value
            }
        )
        
    except Exception as e:
        logger.error(f"Error testing action code: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Action code test failed: {str(e)}"}
        )


@router.get("/action-codes")
async def get_action_codes():
    """
    Get all available action codes with descriptions
    """
    try:
        codes_info = {}
        
        for code in ActionCode:
            codes_info[code.value] = {
                "description": ActionCode.get_description(code),
                "category": ActionCode.get_category(code)
            }
        
        # Group by category
        categories = {}
        for code_value, info in codes_info.items():
            category = info["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append({
                "code": code_value,
                "description": info["description"]
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "total_codes": len(ActionCode),
                "categories": categories,
                "codes": codes_info
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting action codes: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get action codes"}
        )


@router.post("/session-cleanup")
async def cleanup_sessions():
    """
    Clean up expired sessions
    Administrative endpoint
    """
    try:
        # Get initial session count
        initial_count = len(enhanced_conversation_manager_v2.active_sessions)
        
        # Clean up expired sessions
        enhanced_conversation_manager_v2.cleanup_expired_sessions()
        
        # Get final session count
        final_count = len(enhanced_conversation_manager_v2.active_sessions)
        
        cleaned_count = initial_count - final_count
        
        return JSONResponse(
            status_code=200,
            content={
                "initial_sessions": initial_count,
                "final_sessions": final_count,
                "cleaned_sessions": cleaned_count,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to cleanup sessions"}
        )


@router.get("/session/{phone_number}")
async def get_session_info(phone_number: str):
    """
    Get session information for a specific phone number
    """
    try:
        # Clean phone number
        phone_number = phone_number.replace("+", "").replace(" ", "")
        
        # Get session
        session = enhanced_conversation_manager_v2.active_sessions.get(phone_number)
        
        if not session:
            return JSONResponse(
                status_code=404,
                content={"error": "Session not found"}
            )
        
        # Convert datetime objects to strings
        session_info = {
            "user_id": session.get("user_id"),
            "conversation_state": session.get("conversation_state", ConversationState.INITIAL).value,
            "session_data": session.get("session_data", {}),
            "turn_count": session.get("turn_count", 0),
            "created_at": session.get("created_at", datetime.now()).isoformat(),
            "last_activity": session.get("last_activity", datetime.now()).isoformat()
        }
        
        return JSONResponse(
            status_code=200,
            content=session_info
        )
        
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get session information"}
        )


@router.delete("/session/{phone_number}")
async def delete_session(phone_number: str):
    """
    Delete a specific session
    Administrative endpoint
    """
    try:
        # Clean phone number
        phone_number = phone_number.replace("+", "").replace(" ", "")
        
        # Check if session exists
        if phone_number not in enhanced_conversation_manager_v2.active_sessions:
            return JSONResponse(
                status_code=404,
                content={"error": "Session not found"}
            )
        
        # Delete session
        del enhanced_conversation_manager_v2.active_sessions[phone_number]
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Session deleted successfully",
                "phone_number": phone_number,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to delete session"}
        )


@router.get("/health-v2")
async def health_check_v2():
    """
    Enhanced health check for V2 system
    """
    try:
        # Check conversation manager
        stats = enhanced_conversation_manager_v2.get_conversation_stats()
        
        # Check code executor
        executor_stats = enhanced_conversation_manager_v2.code_executor.get_execution_stats()
        
        # System health indicators
        health_status = {
            "system_version": "v2",
            "status": "healthy",
            "conversation_manager": "operational",
            "code_executor": "operational",
            "active_sessions": len(enhanced_conversation_manager_v2.active_sessions),
            "automation_rate": stats.get("automation_rate", 0),
            "success_rate": stats.get("success_rate", 0),
            "total_executions": executor_stats.get("total_executions", 0),
            "execution_success_rate": executor_stats.get("success_rate", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(
            status_code=200,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check V2 failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )