"""
Notifications API Module
Implementation of notification endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models.database_models import AdminUser
from app.utils.auth import get_current_user
from loguru import logger

router = APIRouter()

@router.get("/")
async def get_notifications(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status: read, unread"),
    type: Optional[str] = Query(None, description="Filter by type: system, request, payment"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get notifications with pagination"""
    try:
        # Sample notifications data
        notifications = [
            {
                "id": 1,
                "type": "system",
                "title": "Système Opérationnel",
                "message": "Le système fonctionne normalement",
                "status": "unread",
                "priority": "info",
                "createdAt": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                "data": {
                    "systemLoad": 45.2,
                    "activeRequests": 23
                }
            },
            {
                "id": 2,
                "type": "request",
                "title": "Nouvelle Demande",
                "message": "Nouvelle demande de plomberie reçue",
                "status": "unread",
                "priority": "medium",
                "createdAt": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                "data": {
                    "requestId": "REQ-045",
                    "serviceType": "plomberie",
                    "location": "Bonamoussadi Centre"
                }
            },
            {
                "id": 3,
                "type": "payment",
                "title": "Paiement Reçu",
                "message": "Paiement de 15,000 XAF reçu",
                "status": "read",
                "priority": "high",
                "createdAt": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "data": {
                    "amount": 15000,
                    "currency": "XAF",
                    "transactionId": "TXN-000123"
                }
            },
            {
                "id": 4,
                "type": "system",
                "title": "Maintenance Programmée",
                "message": "Maintenance système prévue demain à 02:00",
                "status": "unread",
                "priority": "warning",
                "createdAt": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
                "data": {
                    "scheduledTime": "2025-07-16T02:00:00Z",
                    "duration": 60,
                    "impact": "minimal"
                }
            }
        ]
        
        # Apply filters
        if status:
            notifications = [n for n in notifications if n["status"] == status]
        if type:
            notifications = [n for n in notifications if n["type"] == type]
        
        # Apply pagination
        total = len(notifications)
        start = (page - 1) * limit
        end = start + limit
        paginated_notifications = notifications[start:end]
        
        return {
            "success": True,
            "data": paginated_notifications,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit,
                "hasNext": end < total,
                "hasPrevious": page > 1
            }
        }
    except Exception as e:
        logger.error(f"Get notifications error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des notifications")

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int = Path(..., description="Notification ID"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Mark notification as read"""
    try:
        # In production, update notification status in database
        logger.info(f"Marking notification {notification_id} as read for user {current_user.id}")
        
        return {
            "success": True,
            "data": {
                "id": notification_id,
                "status": "read",
                "markedAt": datetime.utcnow().isoformat(),
                "markedBy": current_user.username
            },
            "message": "Notification marquée comme lue"
        }
    except Exception as e:
        logger.error(f"Mark notification read error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du marquage de la notification")

@router.put("/read-all")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Mark all notifications as read"""
    try:
        # In production, update all unread notifications in database
        logger.info(f"Marking all notifications as read for user {current_user.id}")
        
        return {
            "success": True,
            "data": {
                "totalMarked": 8,
                "markedAt": datetime.utcnow().isoformat(),
                "markedBy": current_user.username
            },
            "message": "Toutes les notifications marquées comme lues"
        }
    except Exception as e:
        logger.error(f"Mark all notifications read error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du marquage des notifications")