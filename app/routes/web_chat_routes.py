"""
Web Chat Routes for Djobea AI
Handles web chat notifications and real-time updates
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from loguru import logger

from app.database import get_db
from app.services.web_chat_notification_service import web_chat_notification_service
from app.models.database_models import User, ServiceRequest

router = APIRouter()


@router.get("/notifications/{user_id}")
async def get_user_notifications(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get active notifications for a user"""
    try:
        notifications = await web_chat_notification_service.get_user_notifications(user_id)
        return {
            "status": "success",
            "notifications": notifications,
            "count": len(notifications),
            "unread_count": len([n for n in notifications if not n.get("read", False)])
        }
    except Exception as e:
        logger.error(f"Error getting notifications for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving notifications")


@router.post("/notifications/{user_id}/mark-read")
async def mark_notification_read(
    user_id: str,
    notification_id: int,
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    try:
        success = await web_chat_notification_service.mark_notification_read(user_id, notification_id)
        if success:
            return {"status": "success", "message": "Notification marked as read"}
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Error updating notification")


@router.post("/notifications/{user_id}/clear")
async def clear_user_notifications(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Clear all notifications for a user"""
    try:
        success = await web_chat_notification_service.clear_user_notifications(user_id)
        if success:
            return {"status": "success", "message": "All notifications cleared"}
        else:
            raise HTTPException(status_code=500, detail="Error clearing notifications")
    except Exception as e:
        logger.error(f"Error clearing notifications: {e}")
        raise HTTPException(status_code=500, detail="Error clearing notifications")


@router.get("/notifications/poll/{user_id}")
async def poll_notifications(
    user_id: str,
    last_check: str = Query(None, description="Last check timestamp"),
    db: Session = Depends(get_db)
):
    """Poll for new notifications (for real-time updates)"""
    try:
        # Get all notifications for user
        notifications = await web_chat_notification_service.get_user_notifications(user_id)
        
        # Filter new notifications if last_check provided
        if last_check:
            try:
                from datetime import datetime
                last_check_dt = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                new_notifications = [
                    n for n in notifications 
                    if datetime.fromisoformat(n['timestamp'].replace('Z', '+00:00')) > last_check_dt
                ]
            except:
                new_notifications = notifications
        else:
            new_notifications = notifications
        
        return {
            "status": "success",
            "notifications": new_notifications,
            "count": len(new_notifications),
            "has_new": len(new_notifications) > 0
        }
    except Exception as e:
        logger.error(f"Error polling notifications: {e}")
        raise HTTPException(status_code=500, detail="Error polling notifications")


@router.post("/test-notification/{user_id}")
async def test_notification(
    user_id: str,
    message: str = "Test notification",
    notification_type: str = "info",
    db: Session = Depends(get_db)
):
    """Test notification system (for debugging)"""
    try:
        # Check if user exists first
        if user_id.startswith('237'):  # Phone number format
            user = db.query(User).filter(User.phone_number == user_id).first()
            if not user:
                return {"status": "error", "message": f"User with phone number {user_id} not found"}
            logger.info(f"Found user {user.id} for phone number {user_id}")
        
        success = await web_chat_notification_service.send_web_chat_notification(
            user_id, message, notification_type
        )
        if success:
            return {"status": "success", "message": "Test notification sent"}
        else:
            raise HTTPException(status_code=500, detail="Error sending test notification")
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail="Error sending test notification")