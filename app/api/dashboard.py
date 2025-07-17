"""
Dashboard API for Djobea AI
Dashboard API - Real Data Implementation
Provides comprehensive dashboard data including stats, charts, and activity
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from app.database import get_db
from app.models.database_models import User, Provider, ServiceRequest, Conversation
from app.services.auth_service import auth_service
from app.models.auth_models import User as AuthUser
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)):
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401,
                            detail="Invalid authentication credentials")
    return user

def get_date_range(period: str = "7d") -> tuple:
    """Get date range based on period parameter"""
    now = datetime.now()
    
    if period == "24h":
        start_date = now - timedelta(hours=24)
    elif period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    elif period == "90d":
        start_date = now - timedelta(days=90)
    elif period == "1y":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=7)  # Default
    
    return start_date, now

def calculate_change_percentage(current: float, previous: float) -> float:
    """Calculate percentage change between two values"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100

@router.get("/dashboard")
def get_dashboard_data(
    period: str = Query("7d", description="Period for data analysis"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve complete dashboard data including stats, charts, and activity
    
    Args:
        period: Time period for analysis (24h, 7d, 30d, 90d, 1y)
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Complete dashboard data structure
    """
    try:
        start_date, end_date = get_date_range(period)
        
        # Get stats from database
        stats = get_dashboard_stats(db, start_date, end_date, period)
        
        # Get charts data
        charts = get_dashboard_charts(db, start_date, end_date, period)
        
        # Get activity data
        activity = get_dashboard_activity(db, start_date, end_date)
        
        # Get recent activity
        recent_activity = get_recent_activity(db, limit=10)
        
        # Get quick actions
        quick_actions = get_quick_actions(current_user)
        
        return {
            "success": True,
            "data": {
                "stats": stats,
                "charts": charts,
                "activity": activity,
                "recentActivity": recent_activity,
                "quickActions": quick_actions
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard data error: {str(e)}")

@router.get("/dashboard/stats")
def get_dashboard_stats_endpoint(
    period: str = Query("7d", description="Period for data analysis"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics
    
    Args:
        period: Time period for analysis (24h, 7d, 30d, 90d, 1y)
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Dashboard statistics
    """
    try:
        start_date, end_date = get_date_range(period)
        
        # Get stats from database
        stats = get_dashboard_stats(db, start_date, end_date, period)
        
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

def get_dashboard_stats(db: Session, start_date: datetime, end_date: datetime, period: str) -> dict:
    """Get dashboard statistics from database"""
    try:
        # Get total service requests
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).count()
        
        # Get completed requests
        completed_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date,
            ServiceRequest.status.in_(['completed', 'COMPLETED'])
        ).count()
        
        # Get pending requests
        pending_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date,
            ServiceRequest.status.in_(['pending', 'PENDING'])
        ).count()
        
        # Get active providers
        active_providers = db.query(Provider).filter(
            Provider.is_active == True
        ).count()
        
        # Calculate success rate
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate completion rate
        completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate revenue (assuming 15% commission)
        revenue = completed_requests * 5000  # Average service cost
        
        # Get previous period stats for comparison
        previous_period_start = start_date - (end_date - start_date)
        previous_total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= previous_period_start,
            ServiceRequest.created_at < start_date
        ).count()
        
        previous_providers = db.query(Provider).filter(
            Provider.created_at >= previous_period_start,
            Provider.created_at < start_date
        ).count()
        
        # Calculate changes
        requests_change = calculate_change_percentage(total_requests, previous_total_requests)
        providers_change = calculate_change_percentage(active_providers, previous_providers)
        
        return {
            "totalRequests": total_requests,
            "completedRequests": completed_requests,
            "pendingRequests": pending_requests,
            "activeProviders": active_providers,
            "successRate": round(success_rate, 2),
            "completionRate": round(completion_rate, 2),
            "revenue": revenue,
            "requestsChange": round(requests_change, 2),
            "providersChange": round(providers_change, 2),
            "period": period
        }
        
    except Exception as e:
        # Return default data if database query fails
        return {
            "totalRequests": 0,
            "completedRequests": 0,
            "pendingRequests": 0,
            "activeProviders": 0,
            "successRate": 0.0,
            "completionRate": 0.0,
            "revenue": 0,
            "requestsChange": 0.0,
            "providersChange": 0.0,
            "period": period
        }

def get_dashboard_charts(db: Session, start_date: datetime, end_date: datetime, period: str) -> dict:
    """Get dashboard charts data from database"""
    try:
        # Activity chart - requests per day
        activity_data = []
        activity_labels = []
        
        # Generate labels and data for the period
        current_date = start_date
        while current_date <= end_date:
            requests_count = db.query(ServiceRequest).filter(
                func.date(ServiceRequest.created_at) == current_date.date()
            ).count()
            
            activity_data.append(requests_count)
            activity_labels.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        # Services chart - requests by service type
        service_stats = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).group_by(ServiceRequest.service_type).all()
        
        service_labels = [stat[0] for stat in service_stats]
        service_data = [stat[1] for stat in service_stats]
        
        return {
            "activity": {
                "labels": activity_labels,
                "data": activity_data
            },
            "services": {
                "labels": service_labels,
                "data": service_data
            }
        }
        
    except Exception as e:
        # Return default data if database query fails
        return {
            "activity": {
                "labels": [],
                "data": []
            },
            "services": {
                "labels": [],
                "data": []
            }
        }

def get_dashboard_activity(db: Session, start_date: datetime, end_date: datetime) -> dict:
    """Get dashboard activity data from database"""
    try:
        # Get activity metrics
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).count()
        
        completed_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date,
            ServiceRequest.status.in_(['completed', 'COMPLETED'])
        ).count()
        
        return {
            "totalRequests": total_requests,
            "completedRequests": completed_requests,
            "successRate": (completed_requests / total_requests * 100) if total_requests > 0 else 0
        }
        
    except Exception as e:
        return {
            "totalRequests": 0,
            "completedRequests": 0,
            "successRate": 0.0
        }

def get_recent_activity(db: Session, limit: int = 10) -> List[dict]:
    """Get recent activity from database"""
    try:
        # Get recent service requests
        recent_requests = db.query(ServiceRequest).order_by(
            desc(ServiceRequest.created_at)
        ).limit(limit).all()
        
        activity = []
        for request in recent_requests:
            activity.append({
                "id": request.id,
                "title": f"Service Request #{request.id}",
                "description": f"{request.service_type} - {request.location}",
                "timestamp": request.created_at.isoformat(),
                "type": "request",
                "status": request.status
            })
        
        return activity
        
    except Exception as e:
        return []

def get_quick_actions(current_user: AuthUser) -> List[dict]:
    """Get quick actions based on user role"""
    actions = [
        {
            "title": "View Requests",
            "icon": "📋",
            "action": "view_requests",
            "description": "View all service requests"
        },
        {
            "title": "Providers",
            "icon": "👥",
            "action": "view_providers",
            "description": "Manage service providers"
        },
        {
            "title": "Analytics",
            "icon": "📊",
            "action": "view_analytics",
            "description": "View detailed analytics"
        },
        {
            "title": "Settings",
            "icon": "⚙️",
            "action": "settings",
            "description": "System settings"
        }
    ]
    
    # Add admin-only actions
    if hasattr(current_user, 'role') and current_user.role == 'admin':
        actions.append({
            "title": "System Health",
            "icon": "🔧",
            "action": "system_health",
            "description": "Check system health"
        })
    
    return actions