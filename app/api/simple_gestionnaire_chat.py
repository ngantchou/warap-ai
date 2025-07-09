"""
Simple Direct User-to-Gestionnaire Communication API
Minimal implementation to test the core functionality
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import json

router = APIRouter(prefix="/api/v1/simple-gestionnaire", tags=["simple-gestionnaire"])

# Simple storage for testing
conversations = {}
agents = [
    {
        "agent_id": "agent_001",
        "name": "Marie Douala",
        "status": "available",
        "department": "technical"
    },
    {
        "agent_id": "agent_002", 
        "name": "Jean-Baptiste Nkomo",
        "status": "available",
        "department": "support"
    }
]

# Pydantic models
class SimpleMessageRequest(BaseModel):
    user_phone: str = Field(..., description="User's phone number")
    message: str = Field(..., description="Message content")

class SimpleMessageResponse(BaseModel):
    success: bool
    message_id: str
    agent_name: str
    timestamp: datetime
    conversation_id: str

class ConversationMessage(BaseModel):
    message_id: str
    sender: str
    content: str
    timestamp: datetime

class SimpleConversationHistory(BaseModel):
    conversation_id: str
    user_phone: str
    agent_name: str
    messages: List[ConversationMessage]
    status: str

@router.post("/send-message", response_model=SimpleMessageResponse)
async def send_simple_message(request: SimpleMessageRequest):
    """Send direct message from user to gestionnaire (simple version)"""
    try:
        # Find available agent
        available_agent = None
        for agent in agents:
            if agent["status"] == "available":
                available_agent = agent
                break
        
        if not available_agent:
            raise HTTPException(
                status_code=503,
                detail="Aucun gestionnaire disponible pour le moment"
            )
        
        # Create conversation ID
        conversation_id = f"simple_{request.user_phone}_{available_agent['agent_id']}"
        
        # Create or get conversation
        if conversation_id not in conversations:
            conversations[conversation_id] = {
                "user_phone": request.user_phone,
                "agent_id": available_agent["agent_id"],
                "agent_name": available_agent["name"],
                "messages": [],
                "status": "active",
                "created_at": datetime.utcnow()
            }
        
        # Add message
        message_id = str(uuid.uuid4())
        message = {
            "message_id": message_id,
            "sender": "user",
            "content": request.message,
            "timestamp": datetime.utcnow()
        }
        
        conversations[conversation_id]["messages"].append(message)
        
        return SimpleMessageResponse(
            success=True,
            message_id=message_id,
            agent_name=available_agent["name"],
            timestamp=datetime.utcnow(),
            conversation_id=conversation_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )

@router.get("/conversations", response_model=List[SimpleConversationHistory])
async def get_simple_conversations():
    """Get all conversations"""
    try:
        result = []
        for conv_id, conv_data in conversations.items():
            messages = [
                ConversationMessage(
                    message_id=msg["message_id"],
                    sender=msg["sender"],
                    content=msg["content"],
                    timestamp=msg["timestamp"]
                )
                for msg in conv_data["messages"]
            ]
            
            result.append(SimpleConversationHistory(
                conversation_id=conv_id,
                user_phone=conv_data["user_phone"],
                agent_name=conv_data["agent_name"],
                messages=messages,
                status=conv_data["status"]
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )

@router.get("/agents")
async def get_simple_agents():
    """Get available agents"""
    return {"success": True, "agents": agents}

@router.post("/agent-reply")
async def agent_simple_reply(request: dict):
    """Agent sends reply to user"""
    try:
        conversation_id = request.get("conversation_id")
        message = request.get("message")
        
        if not conversation_id or not message:
            raise HTTPException(
                status_code=400,
                detail="conversation_id et message requis"
            )
        
        if conversation_id not in conversations:
            raise HTTPException(
                status_code=404,
                detail="Conversation non trouvée"
            )
        
        # Add agent message
        message_id = str(uuid.uuid4())
        agent_message = {
            "message_id": message_id,
            "sender": "agent",
            "content": message,
            "timestamp": datetime.utcnow()
        }
        
        conversations[conversation_id]["messages"].append(agent_message)
        
        return {
            "success": True,
            "message_id": message_id,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )

@router.get("/conversation/{conversation_id}")
async def get_simple_conversation(conversation_id: str):
    """Get specific conversation"""
    try:
        if conversation_id not in conversations:
            raise HTTPException(
                status_code=404,
                detail="Conversation non trouvée"
            )
        
        conv_data = conversations[conversation_id]
        messages = [
            ConversationMessage(
                message_id=msg["message_id"],
                sender=msg["sender"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
            for msg in conv_data["messages"]
        ]
        
        return SimpleConversationHistory(
            conversation_id=conversation_id,
            user_phone=conv_data["user_phone"],
            agent_name=conv_data["agent_name"],
            messages=messages,
            status=conv_data["status"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )

@router.get("/health")
async def simple_health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "service": "simple-gestionnaire-chat",
        "conversations_count": len(conversations),
        "agents_count": len(agents)
    }