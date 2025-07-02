"""
Analytics API for tracking user interactions and page metrics
Simple endpoint to prevent 404 errors and collect basic analytics
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
from datetime import datetime

router = APIRouter()

class AnalyticsEvent(BaseModel):
    event: str
    data: Dict[str, Any] = {}
    timestamp: Optional[str] = None
    user_agent: Optional[str] = None

@router.post("/api/analytics")
async def track_analytics(event: AnalyticsEvent, request: Request):
    """
    Track analytics events from the frontend
    
    Args:
        event: Analytics event data
        request: HTTP request for getting client info
    
    Returns:
        Dict: Success response
    """
    try:
        # Add request metadata
        event_data = {
            "event": event.event,
            "data": event.data,
            "timestamp": event.timestamp or datetime.now().isoformat(),
            "user_agent": event.user_agent or request.headers.get("User-Agent"),
            "client_ip": request.client.host if request.client else None,
            "referer": request.headers.get("Referer")
        }
        
        # For now, just log the event (could be saved to database later)
        print(f"Analytics Event: {event.event} - {json.dumps(event.data, default=str)}")
        
        return {"status": "success", "message": "Event tracked"}
        
    except Exception as e:
        print(f"Analytics error: {str(e)}")
        return {"status": "error", "message": "Failed to track event"}

@router.get("/api/analytics/health")
async def analytics_health():
    """Health check for analytics service"""
    return {"status": "ok", "service": "analytics"}