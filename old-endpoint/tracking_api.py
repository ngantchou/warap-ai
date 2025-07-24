"""
Real-time Tracking API for Djobea AI
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.services.tracking_service import TrackingService
from app.services.notification_service import NotificationService, EscalationService
from app.services.analytics_service import AnalyticsService

router = APIRouter()

# Request Models
class StatusUpdateRequest(BaseModel):
    request_id: str = Field(..., description="Request ID")
    new_status: str = Field(..., description="New status")
    user_id: str = Field(..., description="User ID")
    provider_id: Optional[str] = Field(None, description="Provider ID")
    reason: Optional[str] = Field(None, description="Reason for status change")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class UserPreferencesRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    preferences: Dict[str, Any] = Field(..., description="User preferences")

class NotificationRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    message: str = Field(..., description="Notification message")
    channels: Optional[List[str]] = Field(None, description="Notification channels")
    urgency: Optional[str] = Field('normal', description="Urgency level")

class NotificationRuleRequest(BaseModel):
    rule_name: str = Field(..., description="Rule name")
    trigger_status: Optional[str] = Field('all', description="Trigger status")
    trigger_delay_minutes: Optional[int] = Field(0, description="Delay in minutes")
    notification_channels: Optional[List[str]] = Field(['whatsapp'], description="Notification channels")
    notification_template: Optional[str] = Field('default', description="Template name")
    notification_frequency: Optional[str] = Field('immediate', description="Frequency")
    max_notifications: Optional[int] = Field(5, description="Max notifications")

class EscalationRuleRequest(BaseModel):
    rule_name: str = Field(..., description="Rule name")
    status_trigger: Optional[str] = Field('all', description="Status trigger")
    delay_threshold_minutes: Optional[int] = Field(30, description="Delay threshold")
    escalation_type: Optional[str] = Field('manager_alert', description="Escalation type")
    escalation_target: Optional[str] = Field('manager', description="Escalation target")
    escalation_message: Optional[str] = Field('Escalation required', description="Escalation message")
    escalation_channels: Optional[List[str]] = Field(['whatsapp'], description="Escalation channels")

# Tracking Endpoints
@router.post("/api/v1/tracking/status/update")
async def update_request_status(
    request: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update request status with real-time tracking"""
    try:
        tracking_service = TrackingService(db)
        
        result = tracking_service.update_request_status(
            request_id=request.request_id,
            new_status=request.new_status,
            user_id=request.user_id,
            provider_id=request.provider_id,
            reason=request.reason,
            metadata=request.metadata
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/request/{request_id}")
async def get_request_tracking(
    request_id: str,
    db: Session = Depends(get_db)
):
    """Get comprehensive tracking information for a request"""
    try:
        tracking_service = TrackingService(db)
        
        result = tracking_service.get_request_tracking(request_id)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/user/{user_id}/requests")
async def get_user_requests_tracking(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get tracking information for all user requests"""
    try:
        tracking_service = TrackingService(db)
        
        # Get all requests for user
        from app.models.tracking_models import RequestStatus
        requests = db.query(RequestStatus).filter(
            RequestStatus.user_id == user_id
        ).all()
        
        results = []
        for request in requests:
            tracking = tracking_service.get_request_tracking(request.request_id)
            if tracking['success']:
                results.append(tracking['data'])
        
        return {
            'success': True,
            'user_id': user_id,
            'requests': results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User Preferences Endpoints
@router.post("/api/v1/tracking/preferences")
async def set_user_preferences(
    request: UserPreferencesRequest,
    db: Session = Depends(get_db)
):
    """Set user notification preferences"""
    try:
        tracking_service = TrackingService(db)
        
        result = tracking_service.set_user_preferences(
            user_id=request.user_id,
            preferences=request.preferences
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user notification preferences"""
    try:
        tracking_service = TrackingService(db)
        
        result = tracking_service.get_user_preferences(user_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Notification Endpoints
@router.post("/api/v1/tracking/notifications/send")
async def send_immediate_notification(
    request: NotificationRequest,
    db: Session = Depends(get_db)
):
    """Send immediate notification to user"""
    try:
        notification_service = NotificationService(db)
        
        result = notification_service.send_immediate_notification(
            user_id=request.user_id,
            message=request.message,
            channels=request.channels,
            urgency=request.urgency
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/tracking/notifications/rules")
async def create_notification_rule(
    request: NotificationRuleRequest,
    db: Session = Depends(get_db)
):
    """Create a new notification rule"""
    try:
        notification_service = NotificationService(db)
        
        result = notification_service.create_notification_rule(request.dict())
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/notifications/rules")
async def get_notification_rules(
    active_only: bool = Query(True, description="Get only active rules"),
    db: Session = Depends(get_db)
):
    """Get all notification rules"""
    try:
        notification_service = NotificationService(db)
        
        result = notification_service.get_notification_rules(active_only)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/v1/tracking/notifications/rules/{rule_id}")
async def update_notification_rule(
    rule_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update a notification rule"""
    try:
        notification_service = NotificationService(db)
        
        result = notification_service.update_notification_rule(rule_id, updates)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/notifications/history")
async def get_notification_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    limit: int = Query(50, description="Number of notifications to return"),
    db: Session = Depends(get_db)
):
    """Get notification history"""
    try:
        notification_service = NotificationService(db)
        
        result = notification_service.get_notification_history(
            user_id=user_id,
            request_id=request_id,
            limit=limit
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/notifications/analytics")
async def get_notification_analytics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get notification analytics"""
    try:
        notification_service = NotificationService(db)
        
        result = notification_service.get_notification_analytics(days)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/tracking/notifications/test/{user_id}")
async def test_notification_system(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Test notification system with a user"""
    try:
        notification_service = NotificationService(db)
        
        result = notification_service.test_notification_system(user_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Escalation Endpoints
@router.post("/api/v1/tracking/escalations/rules")
async def create_escalation_rule(
    request: EscalationRuleRequest,
    db: Session = Depends(get_db)
):
    """Create a new escalation rule"""
    try:
        escalation_service = EscalationService(db)
        
        result = escalation_service.create_escalation_rule(request.dict())
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/escalations/rules")
async def get_escalation_rules(
    active_only: bool = Query(True, description="Get only active rules"),
    db: Session = Depends(get_db)
):
    """Get all escalation rules"""
    try:
        escalation_service = EscalationService(db)
        
        result = escalation_service.get_escalation_rules(active_only)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/escalations/history")
async def get_escalation_history(
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    limit: int = Query(50, description="Number of escalations to return"),
    db: Session = Depends(get_db)
):
    """Get escalation history"""
    try:
        escalation_service = EscalationService(db)
        
        result = escalation_service.get_escalation_history(
            request_id=request_id,
            limit=limit
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/escalations/analytics")
async def get_escalation_analytics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get escalation analytics"""
    try:
        escalation_service = EscalationService(db)
        
        result = escalation_service.get_escalation_analytics(days)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Endpoints
@router.get("/api/v1/tracking/analytics/performance")
async def get_performance_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get comprehensive performance metrics"""
    try:
        analytics_service = AnalyticsService(db)
        
        result = analytics_service.get_performance_metrics(days)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/analytics/dashboard")
async def get_real_time_dashboard(
    db: Session = Depends(get_db)
):
    """Get real-time dashboard data"""
    try:
        analytics_service = AnalyticsService(db)
        
        result = analytics_service.get_real_time_dashboard()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/analytics/service")
async def get_service_analytics(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    zone: Optional[str] = Query(None, description="Filter by zone"),
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get service-specific analytics"""
    try:
        analytics_service = AnalyticsService(db)
        
        result = analytics_service.get_service_analytics(
            service_type=service_type,
            zone=zone,
            days=days
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/analytics/user/{user_id}")
async def get_user_analytics(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user-specific analytics"""
    try:
        analytics_service = AnalyticsService(db)
        
        result = analytics_service.get_user_analytics(user_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/tracking/analytics/optimization")
async def get_optimization_report(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Generate optimization recommendations"""
    try:
        analytics_service = AnalyticsService(db)
        
        result = analytics_service.generate_optimization_report(days)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health Check
@router.get("/api/v1/tracking/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check for tracking system"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Test services
        tracking_service = TrackingService(db)
        notification_service = NotificationService(db)
        analytics_service = AnalyticsService(db)
        
        return {
            'success': True,
            'status': 'healthy',
            'services': {
                'tracking': 'operational',
                'notifications': 'operational',
                'analytics': 'operational'
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }