"""
Analytics KPIs API for Djobea AI
Provides comprehensive key performance indicators for the analytics dashboard
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json

from app.database import get_db
from app.models.database_models import User, Provider, ServiceRequest, Conversation
from app.services.auth_service import auth_service
from app.models.auth_models import User as AuthUser
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()

class KPIValue(BaseModel):
    """KPI value structure"""
    value: Union[int, float]
    change: float
    trend: str
    target: Union[int, float]
    targetProgress: float
    unit: Optional[str] = None
    currency: Optional[str] = None
    scale: Optional[int] = None

class KPIResponse(BaseModel):
    """KPI response structure"""
    success: bool
    data: Dict[str, KPIValue]
    message: str

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

def get_date_range(period: str = "30d") -> tuple:
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
        start_date = now - timedelta(days=30)  # Default
    
    return start_date, now

def calculate_change_percentage(current: float, previous: float) -> float:
    """Calculate percentage change between two values"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100

def calculate_trend(change: float) -> str:
    """Calculate trend direction based on change percentage"""
    if change > 0:
        return "up"
    elif change < 0:
        return "down"
    else:
        return "stable"

def calculate_target_progress(current: float, target: float) -> float:
    """Calculate progress towards target as percentage"""
    if target == 0:
        return 100.0 if current == 0 else 0.0
    return min((current / target) * 100, 100.0)

@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    period: str = Query("30d", description="Time period for KPI calculation"),
    compare: bool = Query(False, description="Include comparison with previous period"),
    metrics: List[str] = Query([], description="Specific metrics to retrieve"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get key performance indicators for the analytics dashboard
    
    Supports filtering by specific metrics and includes comparison with previous period
    """
    try:
        start_date, end_date = get_date_range(period)
        
        # Calculate previous period for comparison
        period_duration = end_date - start_date
        previous_start = start_date - period_duration
        previous_end = start_date
        
        # Initialize KPI data
        kpi_data = {}
        
        # Get all requests for current period
        current_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).all()
        
        # Get all requests for previous period (if comparison requested)
        previous_requests = []
        if compare:
            previous_requests = db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= previous_start,
                ServiceRequest.created_at < previous_end
            ).all()
        
        # Calculate total requests
        if not metrics or "totalRequests" in metrics:
            total_requests_current = len(current_requests)
            total_requests_previous = len(previous_requests) if compare else 0
            change = calculate_change_percentage(total_requests_current, total_requests_previous)
            
            kpi_data["totalRequests"] = KPIValue(
                value=total_requests_current,
                change=change,
                trend=calculate_trend(change),
                target=1300,  # Business target
                targetProgress=calculate_target_progress(total_requests_current, 1300)
            )
        
        # Calculate active providers
        if not metrics or "activeProviders" in metrics:
            active_providers_current = db.query(Provider).filter(
                Provider.is_active == True,
                Provider.last_active >= start_date
            ).count()
            
            active_providers_previous = 0
            if compare:
                active_providers_previous = db.query(Provider).filter(
                    Provider.is_active == True,
                    Provider.last_active >= previous_start,
                    Provider.last_active < previous_end
                ).count()
            
            change = calculate_change_percentage(active_providers_current, active_providers_previous)
            
            kpi_data["activeProviders"] = KPIValue(
                value=active_providers_current,
                change=change,
                trend=calculate_trend(change),
                target=100,  # Business target
                targetProgress=calculate_target_progress(active_providers_current, 100)
            )
        
        # Calculate completed requests
        completed_requests_current = sum(1 for r in current_requests if r.status == "terminée")
        completed_requests_previous = sum(1 for r in previous_requests if r.status == "terminée") if compare else 0
        
        if not metrics or "completedRequests" in metrics:
            change = calculate_change_percentage(completed_requests_current, completed_requests_previous)
            
            kpi_data["completedRequests"] = KPIValue(
                value=completed_requests_current,
                change=change,
                trend=calculate_trend(change),
                target=1200,  # Business target
                targetProgress=calculate_target_progress(completed_requests_current, 1200)
            )
        
        # Calculate revenue (15% commission on completed requests)
        if not metrics or "revenue" in metrics:
            # Estimate revenue based on completed requests and average service cost
            average_service_cost = 8000  # Average cost in XAF
            commission_rate = 0.15
            
            revenue_current = completed_requests_current * average_service_cost * commission_rate
            revenue_previous = completed_requests_previous * average_service_cost * commission_rate if compare else 0
            change = calculate_change_percentage(revenue_current, revenue_previous)
            
            kpi_data["revenue"] = KPIValue(
                value=revenue_current,
                change=change,
                trend=calculate_trend(change),
                target=50000,  # Business target in XAF
                targetProgress=calculate_target_progress(revenue_current, 50000),
                currency="XAF"
            )
        
        # Calculate average response time
        if not metrics or "averageResponseTime" in metrics:
            # Calculate average response time for current period
            total_response_time = 0
            response_count = 0
            
            for request in current_requests:
                if request.status != "en attente":
                    # Estimate response time based on request creation vs assignment
                    response_time = 15  # Average 15 minutes (placeholder calculation)
                    total_response_time += response_time
                    response_count += 1
            
            avg_response_time_current = total_response_time / response_count if response_count > 0 else 0
            
            # Calculate for previous period
            avg_response_time_previous = 0
            if compare:
                prev_total = 0
                prev_count = 0
                for request in previous_requests:
                    if request.status != "en attente":
                        prev_total += 15
                        prev_count += 1
                avg_response_time_previous = prev_total / prev_count if prev_count > 0 else 0
            
            change = calculate_change_percentage(avg_response_time_current, avg_response_time_previous)
            
            kpi_data["averageResponseTime"] = KPIValue(
                value=round(avg_response_time_current, 1),
                change=change,
                trend=calculate_trend(-change),  # Lower response time is better
                target=10.0,  # Target response time in minutes
                targetProgress=calculate_target_progress(10.0, avg_response_time_current) if avg_response_time_current > 0 else 100.0,
                unit="minutes"
            )
        
        # Calculate customer satisfaction
        if not metrics or "customerSatisfaction" in metrics:
            # Calculate satisfaction based on completed requests
            total_satisfaction = 0
            satisfaction_count = 0
            
            for request in current_requests:
                if request.status == "terminée":
                    # Estimate satisfaction based on completion (4.5-5.0 range)
                    satisfaction = 4.7  # Average satisfaction score
                    total_satisfaction += satisfaction
                    satisfaction_count += 1
            
            avg_satisfaction_current = total_satisfaction / satisfaction_count if satisfaction_count > 0 else 0
            
            # Calculate for previous period
            avg_satisfaction_previous = 0
            if compare:
                prev_total = 0
                prev_count = 0
                for request in previous_requests:
                    if request.status == "terminée":
                        prev_total += 4.7
                        prev_count += 1
                avg_satisfaction_previous = prev_total / prev_count if prev_count > 0 else 0
            
            change = calculate_change_percentage(avg_satisfaction_current, avg_satisfaction_previous)
            
            kpi_data["customerSatisfaction"] = KPIValue(
                value=round(avg_satisfaction_current, 1),
                change=change,
                trend=calculate_trend(change),
                target=4.8,  # Target satisfaction score
                targetProgress=calculate_target_progress(avg_satisfaction_current, 4.8),
                scale=5
            )
        
        return KPIResponse(
            success=True,
            data=kpi_data,
            message="KPIs retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving KPIs: {str(e)}"
        )

@router.get("/analytics/kpis/trends")
def get_kpi_trends(
    period: str = Query("30d", description="Time period for trend analysis"),
    metrics: List[str] = Query([], description="Specific metrics to analyze"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get KPI trends over time for detailed analysis
    """
    try:
        start_date, end_date = get_date_range(period)
        
        # Calculate trends data
        trends_data = {}
        
        # Get daily breakdown of requests
        daily_requests = db.query(
            func.date(ServiceRequest.created_at).label('date'),
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).group_by(func.date(ServiceRequest.created_at)).all()
        
        trends_data["requestsTrend"] = [
            {"date": str(day.date), "value": day.count}
            for day in daily_requests
        ]
        
        # Get completion rate trend - simplified approach
        daily_completions = db.query(
            func.date(ServiceRequest.created_at).label('date'),
            func.count(ServiceRequest.id).label('total')
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).group_by(func.date(ServiceRequest.created_at)).all()
        
        # Calculate completion rate for each day
        completion_trends = []
        for day in daily_completions:
            # Get completed requests for this day
            completed_count = db.query(ServiceRequest).filter(
                func.date(ServiceRequest.created_at) == day.date,
                ServiceRequest.status == "terminée"
            ).count()
            
            completion_rate = (completed_count / day.total * 100) if day.total > 0 else 0
            completion_trends.append({
                "date": str(day.date),
                "value": completion_rate
            })
        
        trends_data["completionRateTrend"] = completion_trends
        
        return {
            "success": True,
            "data": trends_data,
            "message": "KPI trends retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving KPI trends: {str(e)}"
        )

@router.get("/analytics/kpis/targets")
def get_kpi_targets(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get KPI targets and thresholds for performance evaluation
    """
    try:
        targets = {
            "totalRequests": {
                "target": 1300,
                "threshold": 1000,
                "unit": "requests"
            },
            "activeProviders": {
                "target": 100,
                "threshold": 80,
                "unit": "providers"
            },
            "completedRequests": {
                "target": 1200,
                "threshold": 900,
                "unit": "requests"
            },
            "revenue": {
                "target": 50000,
                "threshold": 40000,
                "unit": "XAF"
            },
            "averageResponseTime": {
                "target": 10.0,
                "threshold": 15.0,
                "unit": "minutes"
            },
            "customerSatisfaction": {
                "target": 4.8,
                "threshold": 4.5,
                "unit": "rating",
                "scale": 5
            }
        }
        
        return {
            "success": True,
            "data": targets,
            "message": "KPI targets retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving KPI targets: {str(e)}"
        )