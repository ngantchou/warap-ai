"""
Direct User-to-Gestionnaire Communication API
Bypasses LLM for direct human-to-human conversation
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid
import json

from app.database import get_db
from app.models.database_models import (
    User, AdminUser, SupportTicket, SupportTicketStatus, 
    Conversation, ConversationSession
)
from app.services.whatsapp_service import WhatsAppService
from app.services.auth_service import AuthService
from app.api.auth import get_current_admin_user

router = APIRouter(prefix="/api/v1/gestionnaire", tags=["gestionnaire"])

# Pydantic models
class DirectMessageRequest(BaseModel):
    user_phone: str = Field(..., description="User's phone number")
    message: str = Field(..., description="Message content")
    agent_id: Optional[str] = Field(None, description="Specific agent ID (optional)")

class DirectMessageResponse(BaseModel):
    success: bool
    message_id: str
    agent_id: str
    agent_name: str
    timestamp: datetime
    delivered: bool

class AgentMessageRequest(BaseModel):
    message: str = Field(..., description="Agent's response message")
    user_phone: str = Field(..., description="User's phone number")
    
class AgentMessageResponse(BaseModel):
    success: bool
    message_id: str
    timestamp: datetime
    sent_to_user: bool

class ConversationHistory(BaseModel):
    conversation_id: str
    user_phone: str
    agent_id: str
    agent_name: str
    messages: List[dict]
    status: str
    created_at: datetime
    last_message_at: datetime

class AssignAgentRequest(BaseModel):
    user_phone: str = Field(..., description="User's phone number")
    agent_id: str = Field(..., description="Agent ID to assign")
    priority: str = Field("medium", description="Priority level")
    title: str = Field("Contact direct avec gestionnaire", description="Support ticket title")
    description: str = Field("L'utilisateur a demandé un contact direct avec un gestionnaire")

class ActiveConversation(BaseModel):
    conversation_id: str
    user_phone: str
    user_name: str
    agent_id: str
    agent_name: str
    last_message: str
    last_message_time: datetime
    status: str
    priority: str
    unread_count: int

# Storage for direct conversations (in production, use Redis or database)
direct_conversations = {}

@router.post("/send-message", response_model=DirectMessageResponse)
async def send_direct_message(
    request: DirectMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Send direct message from user to gestionnaire (bypasses LLM)
    """
    try:
        # Get or create user
        user = db.query(User).filter(User.phone_number == request.user_phone).first()
        if not user:
            # Create new user for direct communication
            user = User(
                whatsapp_id=request.user_phone,
                phone_number=request.user_phone,
                name=f"Direct User {request.user_phone[-4:]}",
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Find available agent
        available_agent = None
        if request.agent_id:
            # Check if specific agent is available
            try:
                agent_info = await get_agent_info(request.agent_id, db)
                if agent_info and agent_info.get("availability_status") == "available":
                    available_agent = agent_info
            except Exception as e:
                print(f"Error getting agent info: {e}")
        
        if not available_agent:
            # Find any available agent
            try:
                available_agent = await find_available_agent(db)
            except Exception as e:
                print(f"Error finding available agent: {e}")
                print(f"Traceback: {__import__('traceback').format_exc()}")
        
        if not available_agent:
            raise HTTPException(
                status_code=503, 
                detail="Aucun gestionnaire disponible pour le moment"
            )
        
        # Create or get conversation session
        conversation_id = f"direct_{user.id}_{available_agent['agent_id']}"
        
        # Create support ticket for tracking
        support_ticket = SupportTicket(
            user_id=user.id,
            title="Contact direct avec gestionnaire",
            description=f"Message direct: {request.message[:100]}...",
            status=SupportTicketStatus.OPEN,
            priority="medium",
            assigned_to=None  # Will be updated when agent responds
        )
        db.add(support_ticket)
        db.commit()
        db.refresh(support_ticket)
        
        # Store conversation in memory (for real-time access)
        if conversation_id not in direct_conversations:
            direct_conversations[conversation_id] = {
                "user_phone": request.user_phone,
                "user_id": user.id,
                "agent_id": available_agent['agent_id'],
                "agent_name": available_agent['name'],
                "messages": [],
                "status": "active",
                "created_at": datetime.utcnow(),
                "support_ticket_id": support_ticket.id
            }
        
        # Add user message
        message_id = str(uuid.uuid4())
        message_entry = {
            "message_id": message_id,
            "sender": "user",
            "content": request.message,
            "timestamp": datetime.utcnow(),
            "delivered": True
        }
        
        direct_conversations[conversation_id]["messages"].append(message_entry)
        direct_conversations[conversation_id]["last_message_at"] = datetime.utcnow()
        
        # Log to database
        conversation_log = Conversation(
            user_id=user.id,
            message_type="incoming",
            message_content=request.message,
            ai_response=None,
            extracted_data={"conversation_type": "direct_gestionnaire", "agent_id": available_agent['agent_id']},
            created_at=datetime.utcnow()
        )
        db.add(conversation_log)
        db.commit()
        
        # Notify agent (in production, use WebSocket or push notification)
        await notify_agent_new_message(
            available_agent['agent_id'], 
            user.phone_number, 
            request.message,
            conversation_id
        )
        
        return DirectMessageResponse(
            success=True,
            message_id=message_id,
            agent_id=available_agent['agent_id'],
            agent_name=available_agent['name'],
            timestamp=datetime.utcnow(),
            delivered=True
        )
        
    except Exception as e:
        import traceback
        print(f"Error in send_direct_message: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'envoi du message: {str(e)}"
        )

@router.post("/agent-reply", response_model=AgentMessageResponse)
async def agent_reply(
    request: AgentMessageRequest,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Agent sends reply to user (bypasses LLM)
    """
    try:
        # Find conversation
        conversation_id = None
        for conv_id, conv_data in direct_conversations.items():
            if conv_data["user_phone"] == request.user_phone:
                conversation_id = conv_id
                break
        
        if not conversation_id:
            raise HTTPException(
                status_code=404,
                detail="Conversation non trouvée"
            )
        
        # Get user
        user = db.query(User).filter(User.phone_number == request.user_phone).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Add agent message
        message_id = str(uuid.uuid4())
        message_entry = {
            "message_id": message_id,
            "sender": "agent",
            "sender_name": current_user.username,
            "content": request.message,
            "timestamp": datetime.utcnow(),
            "delivered": False
        }
        
        direct_conversations[conversation_id]["messages"].append(message_entry)
        direct_conversations[conversation_id]["last_message_at"] = datetime.utcnow()
        
        # Log to database
        conversation_log = Conversation(
            user_id=user.id,
            message_type="outgoing",
            message_content=request.message,
            ai_response=request.message,
            extracted_data={
                "conversation_type": "direct_gestionnaire_reply",
                "agent_id": current_user.username,
                "agent_name": current_user.username
            },
            created_at=datetime.utcnow()
        )
        db.add(conversation_log)
        db.commit()
        
        # Send via WhatsApp
        whatsapp_service = WhatsAppService()
        sent_success = False
        
        try:
            # Format message for WhatsApp
            formatted_message = f"👨‍💼 *{current_user.username}* (Gestionnaire Djobea AI):\n\n{request.message}"
            
            whatsapp_service.send_message(request.user_phone, formatted_message)
            sent_success = True
            message_entry["delivered"] = True
            
        except Exception as whatsapp_error:
            print(f"WhatsApp sending error: {whatsapp_error}")
            # Message logged but not delivered
        
        return AgentMessageResponse(
            success=True,
            message_id=message_id,
            timestamp=datetime.utcnow(),
            sent_to_user=sent_success
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'envoi de la réponse: {str(e)}"
        )

@router.get("/conversations", response_model=List[ActiveConversation])
async def get_active_conversations(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get all active conversations for current agent
    """
    try:
        active_conversations = []
        
        for conv_id, conv_data in direct_conversations.items():
            if conv_data["status"] == "active":
                # Get user info
                user = db.query(User).filter(User.id == conv_data["user_id"]).first()
                user_name = user.name if user else f"User {conv_data['user_phone'][-4:]}"
                
                # Get last message
                last_message = ""
                unread_count = 0
                if conv_data["messages"]:
                    last_message = conv_data["messages"][-1]["content"]
                    # Count unread messages from user
                    unread_count = len([
                        msg for msg in conv_data["messages"]
                        if msg["sender"] == "user" and msg["timestamp"] > datetime.utcnow() - timedelta(minutes=30)
                    ])
                
                active_conversations.append(ActiveConversation(
                    conversation_id=conv_id,
                    user_phone=conv_data["user_phone"],
                    user_name=user_name,
                    agent_id=conv_data["agent_id"],
                    agent_name=conv_data["agent_name"],
                    last_message=last_message,
                    last_message_time=conv_data.get("last_message_at", conv_data["created_at"]),
                    status=conv_data["status"],
                    priority="medium",
                    unread_count=unread_count
                ))
        
        return active_conversations
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des conversations: {str(e)}"
        )

@router.get("/conversation/{conversation_id}", response_model=ConversationHistory)
async def get_conversation_history(
    conversation_id: str,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed conversation history
    """
    try:
        if conversation_id not in direct_conversations:
            raise HTTPException(
                status_code=404,
                detail="Conversation non trouvée"
            )
        
        conv_data = direct_conversations[conversation_id]
        
        return ConversationHistory(
            conversation_id=conversation_id,
            user_phone=conv_data["user_phone"],
            agent_id=conv_data["agent_id"],
            agent_name=conv_data["agent_name"],
            messages=conv_data["messages"],
            status=conv_data["status"],
            created_at=conv_data["created_at"],
            last_message_at=conv_data.get("last_message_at", conv_data["created_at"])
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'historique: {str(e)}"
        )

@router.post("/assign-agent", response_model=dict)
async def assign_agent_to_user(
    request: AssignAgentRequest,
    db: Session = Depends(get_db)
):
    """
    Assign specific agent to user and create direct conversation
    """
    try:
        # Get user
        user = db.query(User).filter(User.phone_number == request.user_phone).first()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Verify agent exists
        agent_info = await get_agent_info(request.agent_id, db)
        if not agent_info:
            raise HTTPException(status_code=404, detail="Agent non trouvé")
        
        # Create support ticket
        support_ticket = SupportTicket(
            user_id=user.id,
            title=request.title,
            description=request.description,
            status=SupportTicketStatus.OPEN,
            priority=request.priority,
            assigned_to=None
        )
        db.add(support_ticket)
        db.commit()
        db.refresh(support_ticket)
        
        # Create direct conversation
        conversation_id = f"assigned_{user.id}_{request.agent_id}"
        direct_conversations[conversation_id] = {
            "user_phone": request.user_phone,
            "user_id": user.id,
            "agent_id": request.agent_id,
            "agent_name": agent_info['name'],
            "messages": [],
            "status": "active",
            "created_at": datetime.utcnow(),
            "support_ticket_id": support_ticket.id,
            "assignment_type": "manual"
        }
        
        # Send notification to user
        whatsapp_service = WhatsAppService()
        try:
            notification_message = f"👨‍💼 *{agent_info['name']}* a été assigné(e) comme votre gestionnaire personnel.\n\nVous pouvez maintenant communiquer directement avec votre gestionnaire. Tapez votre message pour commencer."
            whatsapp_service.send_message(request.user_phone, notification_message)
        except Exception as whatsapp_error:
            print(f"WhatsApp notification error: {whatsapp_error}")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "agent_id": request.agent_id,
            "agent_name": agent_info['name'],
            "support_ticket_id": support_ticket.id,
            "message": "Agent assigné avec succès"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'assignation: {str(e)}"
        )

@router.delete("/conversation/{conversation_id}")
async def close_conversation(
    conversation_id: str,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Close direct conversation
    """
    try:
        if conversation_id not in direct_conversations:
            raise HTTPException(
                status_code=404,
                detail="Conversation non trouvée"
            )
        
        conv_data = direct_conversations[conversation_id]
        
        # Update status
        direct_conversations[conversation_id]["status"] = "closed"
        direct_conversations[conversation_id]["closed_at"] = datetime.utcnow()
        direct_conversations[conversation_id]["closed_by"] = current_user.username
        
        # Update support ticket
        if "support_ticket_id" in conv_data:
            support_ticket = db.query(SupportTicket).filter(
                SupportTicket.id == conv_data["support_ticket_id"]
            ).first()
            if support_ticket:
                support_ticket.status = SupportTicketStatus.RESOLVED
                support_ticket.resolved_at = datetime.utcnow()
                support_ticket.resolution_notes = f"Conversation fermée par {current_user.username}"
                db.commit()
        
        # Send closure notification to user
        whatsapp_service = WhatsAppService()
        try:
            closure_message = f"🏁 Votre conversation avec le gestionnaire {conv_data['agent_name']} a été fermée.\n\nMerci d'avoir utilisé Djobea AI. N'hésitez pas à nous contacter si vous avez besoin d'aide à nouveau."
            whatsapp_service.send_message(conv_data["user_phone"], closure_message)
        except Exception as whatsapp_error:
            print(f"WhatsApp closure notification error: {whatsapp_error}")
        
        return {"success": True, "message": "Conversation fermée avec succès"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la fermeture: {str(e)}"
        )

# Helper functions
async def get_agent_info(agent_id: str, db: Session) -> dict:
    """Get agent information"""
    # In production, this would query the agent database
    # For now, we'll simulate with the escalation API
    try:
        import requests
        response = requests.get(f"http://localhost:5000/api/v1/escalation/agents/{agent_id}/dashboard")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                return data.get("agent", {})
    except:
        pass
    return None

async def find_available_agent(db: Session) -> dict:
    """Find available agent"""
    try:
        import requests
        response = requests.get("http://localhost:5000/api/v1/escalation/agents")
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                agents = data.get("agents", [])
                # Find first available agent
                for agent in agents:
                    if agent.get("availability_status") == "available":
                        return agent
    except:
        pass
    return None

async def notify_agent_new_message(agent_id: str, user_phone: str, message: str, conversation_id: str):
    """Notify agent of new message (in production, use WebSocket/push notifications)"""
    # For now, just log
    print(f"NOTIFICATION: Agent {agent_id} has new message from {user_phone} in conversation {conversation_id}")
    print(f"Message: {message}")