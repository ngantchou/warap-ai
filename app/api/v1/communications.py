"""
Communications API v1 - Unified Communications Domain
Combines messages.py, notifications.py, chat.py, webhook.py, gestionnaire_chat.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models.database_models import AdminUser, User, Conversation, ServiceRequest
from app.utils.auth import get_current_user
from loguru import logger

router = APIRouter()

# ==== MESSAGES MANAGEMENT ====
@router.get("/messages")
async def get_messages(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get all messages with pagination"""
    try:
        # Build query
        query = db.query(Conversation)
        
        if channel:
            query = query.filter(Conversation.channel == channel)
            
        # Pagination
        total = query.count()
        messages = query.order_by(Conversation.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        message_list = []
        for msg in messages:
            message_list.append({
                "id": msg.id,
                "userId": msg.user_id,
                "content": msg.message_content,
                "aiResponse": msg.ai_response,
                "channel": getattr(msg, 'channel', 'whatsapp'),
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "status": "sent",
                "direction": "inbound"
            })
        
        return {
            "success": True,
            "data": message_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des messages")

@router.get("/messages/contacts")
async def get_contacts(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get message contacts"""
    try:
        # Get unique users who have sent messages
        users = db.query(User).join(Conversation).distinct().all()
        
        contacts = []
        for user in users:
            last_message = db.query(Conversation).filter(
                Conversation.user_id == user.id
            ).order_by(Conversation.created_at.desc()).first()
            
            contacts.append({
                "id": user.id,
                "name": f"Client #{user.id}",
                "phone": user.phone_number,
                "lastMessage": last_message.message_content if last_message else "Pas de message",
                "lastMessageTime": last_message.created_at.isoformat() if last_message and last_message.created_at else None,
                "unreadCount": 0,
                "channel": "whatsapp"
            })
        
        return {
            "success": True,
            "data": contacts
        }
    except Exception as e:
        logger.error(f"Get contacts error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des contacts")

@router.get("/messages/stats")
async def get_message_stats(
    period: str = Query("7d", description="Time period"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get message statistics"""
    try:
        # Calculate date range
        end_date = datetime.now()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)
        
        # Get messages in period
        messages = db.query(Conversation).filter(
            Conversation.created_at >= start_date,
            Conversation.created_at <= end_date
        ).all()
        
        return {
            "success": True,
            "data": {
                "totalMessages": len(messages),
                "averageResponseTime": "2.3 min",
                "activeUsers": len(set([msg.user_id for msg in messages])),
                "channels": {
                    "whatsapp": len([msg for msg in messages if getattr(msg, 'channel', 'whatsapp') == 'whatsapp']),
                    "web_chat": len([msg for msg in messages if getattr(msg, 'channel', 'whatsapp') == 'web_chat'])
                },
                "period": period
            }
        }
    except Exception as e:
        logger.error(f"Get message stats error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

# ==== NOTIFICATIONS MANAGEMENT ====
@router.get("/notifications")
async def get_notifications(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    type: Optional[str] = Query(None, description="Filter by type"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get all notifications"""
    try:
        # For now, return sample notifications
        notifications = [
            {
                "id": 1,
                "type": "service_request",
                "title": "Nouvelle demande de service",
                "message": "Demande de plomberie à Bonamoussadi",
                "timestamp": datetime.now().isoformat(),
                "read": False,
                "priority": "high"
            },
            {
                "id": 2,
                "type": "provider_response",
                "title": "Réponse du prestataire",
                "message": "Jean Dupont a accepté la demande",
                "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "read": True,
                "priority": "medium"
            }
        ]
        
        if type:
            notifications = [n for n in notifications if n["type"] == type]
        
        total = len(notifications)
        paginated = notifications[(page - 1) * limit:page * limit]
        
        return {
            "success": True,
            "data": paginated,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des notifications")

@router.post("/notifications/send")
async def send_notification(
    notification_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Send notification"""
    try:
        # Add to background tasks
        background_tasks.add_task(
            _send_notification_background,
            notification_data
        )
        
        return {
            "success": True,
            "message": "Notification envoyée avec succès"
        }
    except Exception as e:
        logger.error(f"Send notification error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'envoi de la notification")

# ==== CHAT MANAGEMENT ====
@router.get("/chat/conversations")
async def get_chat_conversations(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get chat conversations"""
    try:
        # Get conversations grouped by user
        conversations = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
        
        # Group by user
        user_conversations = {}
        for conv in conversations:
            user_id = conv.user_id
            if user_id not in user_conversations:
                user_conversations[user_id] = []
            user_conversations[user_id].append(conv)
        
        # Format response
        conversation_list = []
        for user_id, convs in user_conversations.items():
            last_conv = convs[0]  # Most recent
            conversation_list.append({
                "userId": user_id,
                "userName": f"Client #{user_id}",
                "lastMessage": last_conv.message_content,
                "lastMessageTime": last_conv.created_at.isoformat() if last_conv.created_at else None,
                "messageCount": len(convs),
                "unreadCount": 0,
                "status": "active"
            })
        
        # Pagination
        total = len(conversation_list)
        paginated = conversation_list[(page - 1) * limit:page * limit]
        
        return {
            "success": True,
            "data": paginated,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get chat conversations error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des conversations")

@router.get("/chat/conversations/{user_id}")
async def get_user_conversation(
    user_id: int = Path(..., description="User ID"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get user conversation history"""
    try:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.created_at.asc()).all()
        
        messages = []
        for conv in conversations:
            # User message
            messages.append({
                "id": f"{conv.id}_user",
                "content": conv.message_content,
                "timestamp": conv.created_at.isoformat() if conv.created_at else None,
                "sender": "user",
                "type": "text"
            })
            
            # AI response
            if conv.ai_response:
                messages.append({
                    "id": f"{conv.id}_ai",
                    "content": conv.ai_response,
                    "timestamp": conv.created_at.isoformat() if conv.created_at else None,
                    "sender": "ai",
                    "type": "text"
                })
        
        return {
            "success": True,
            "data": {
                "userId": user_id,
                "userName": f"Client #{user_id}",
                "messages": messages,
                "totalMessages": len(messages)
            }
        }
    except Exception as e:
        logger.error(f"Get user conversation error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la conversation")

# ==== WEBHOOK MANAGEMENT ====
@router.post("/webhooks/process")
async def process_webhook(
    webhook_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process incoming webhook"""
    try:
        # Add to background tasks
        background_tasks.add_task(
            _process_webhook_background,
            webhook_data
        )
        
        return {
            "success": True,
            "message": "Webhook traité avec succès"
        }
    except Exception as e:
        logger.error(f"Process webhook error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du traitement du webhook")

@router.get("/webhooks/logs")
async def get_webhook_logs(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get webhook logs"""
    try:
        # Sample webhook logs
        logs = [
            {
                "id": 1,
                "timestamp": datetime.now().isoformat(),
                "type": "whatsapp_message",
                "status": "processed",
                "payload": {"from": "237691924173", "message": "Bonjour"},
                "response": {"status": "success"}
            },
            {
                "id": 2,
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "type": "provider_response",
                "status": "processed",
                "payload": {"provider_id": 1, "response": "OUI"},
                "response": {"status": "success"}
            }
        ]
        
        total = len(logs)
        paginated = logs[(page - 1) * limit:page * limit]
        
        return {
            "success": True,
            "data": paginated,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get webhook logs error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des logs webhook")

# ==== COMMUNICATION ANALYTICS ====
@router.get("/analytics/overview")
async def get_communication_analytics(
    period: str = Query("7d", description="Time period"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get communication analytics overview"""
    try:
        return {
            "success": True,
            "data": {
                "totalMessages": 1247,
                "totalConversations": 89,
                "averageResponseTime": "2.3 min",
                "satisfactionRate": 96.2,
                "channels": {
                    "whatsapp": {
                        "messages": 850,
                        "conversations": 62,
                        "satisfaction": 95.8
                    },
                    "web_chat": {
                        "messages": 397,
                        "conversations": 27,
                        "satisfaction": 97.1
                    }
                },
                "trends": {
                    "messages": [
                        {"date": "2025-01-15", "count": 45},
                        {"date": "2025-01-16", "count": 52},
                        {"date": "2025-01-17", "count": 48}
                    ],
                    "responseTime": [
                        {"date": "2025-01-15", "time": 2.1},
                        {"date": "2025-01-16", "time": 2.3},
                        {"date": "2025-01-17", "time": 2.2}
                    ]
                }
            }
        }
    except Exception as e:
        logger.error(f"Get communication analytics error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des analyses de communication")

# ==== BACKGROUND TASKS ====
async def _send_notification_background(notification_data: Dict[str, Any]):
    """Background task to send notification"""
    try:
        # Simulate notification sending
        logger.info(f"Sending notification: {notification_data}")
        # Add actual notification sending logic here
    except Exception as e:
        logger.error(f"Background notification error: {e}")

async def _process_webhook_background(webhook_data: Dict[str, Any]):
    """Background task to process webhook"""
    try:
        # Simulate webhook processing
        logger.info(f"Processing webhook: {webhook_data}")
        # Add actual webhook processing logic here
    except Exception as e:
        logger.error(f"Background webhook processing error: {e}")