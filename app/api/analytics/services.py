"""
Services Analytics API for Djobea AI
Provides analytics data broken down by service categories
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from app.database import get_db
from app.models.database_models import User, Provider, ServiceRequest, Conversation
from app.services.auth_service import auth_service
from app.models.auth_models import User as AuthUser
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()

class ServiceDetail(BaseModel):
    """Individual service analytics detail"""
    service: str
    requests: int
    revenue: float
    averagePrice: float
    satisfaction: float
    responseTime: float
    completionRate: float
    growth: float

class ServiceDataset(BaseModel):
    """Service analytics dataset for charts"""
    label: str
    data: List[int]
    backgroundColor: List[str]

class ServiceTotals(BaseModel):
    """Service analytics totals"""
    totalRequests: int
    totalRevenue: float
    averageSatisfaction: float
    averageResponseTime: float

class ServicesData(BaseModel):
    """Services analytics data structure"""
    labels: List[str]
    datasets: List[ServiceDataset]
    details: List[ServiceDetail]
    totals: ServiceTotals

class ServicesResponse(BaseModel):
    """Services analytics response structure"""
    success: bool
    data: ServicesData
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

def get_date_range(period: str) -> tuple:
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
        start_date = now - timedelta(days=30)  # Default to 30 days
    
    return start_date, now

def get_service_colors():
    """Get consistent colors for service categories"""
    return [
        "rgba(59, 130, 246, 0.8)",    # Blue - Plomberie
        "rgba(34, 197, 94, 0.8)",     # Green - Électricité
        "rgba(168, 85, 247, 0.8)",    # Purple - Ménage
        "rgba(245, 158, 11, 0.8)",    # Orange - Jardinage
        "rgba(239, 68, 68, 0.8)",     # Red - Peinture
        "rgba(156, 163, 175, 0.8)",   # Gray - Climatisation
        "rgba(14, 165, 233, 0.8)",    # Sky - Autres
        "rgba(16, 185, 129, 0.8)",    # Emerald - Réparations
    ]

def map_service_type(service_type: str) -> str:
    """Map service type to French display name"""
    service_map = {
        "plomberie": "Plomberie",
        "electricite": "Électricité",
        "electromenager": "Électroménager",
        "menage": "Ménage",
        "jardinage": "Jardinage",
        "peinture": "Peinture",
        "climatisation": "Climatisation",
        "reparation": "Réparations",
        "autres": "Autres"
    }
    return service_map.get(service_type.lower(), service_type.capitalize())

def calculate_service_metrics(requests: List[ServiceRequest], service_type: str) -> Dict:
    """Calculate metrics for a specific service type"""
    if not requests:
        return {
            "requests": 0,
            "revenue": 0.0,
            "averagePrice": 0.0,
            "satisfaction": 0.0,
            "responseTime": 0.0,
            "completionRate": 0.0,
            "growth": 0.0
        }
    
    # Calculate basic metrics
    total_requests = len(requests)
    completed_requests = [r for r in requests if r.status == "terminée"]
    
    # Revenue calculation (15% commission)
    estimated_revenue = 0.0
    for request in completed_requests:
        if service_type.lower() == "plomberie":
            estimated_revenue += 49.00 * 0.15  # 15% commission
        elif service_type.lower() == "electricite":
            estimated_revenue += 65.00 * 0.15
        elif service_type.lower() == "electromenager":
            estimated_revenue += 35.00 * 0.15
        else:
            estimated_revenue += 45.00 * 0.15  # Default service price
    
    # Average price calculation
    if service_type.lower() == "plomberie":
        avg_price = 49.00
    elif service_type.lower() == "electricite":
        avg_price = 65.00
    elif service_type.lower() == "electromenager":
        avg_price = 35.00
    else:
        avg_price = 45.00
    
    # Satisfaction calculation (simulated based on service type)
    satisfaction_base = {
        "plomberie": 4.6,
        "electricite": 4.8,
        "electromenager": 4.4,
        "menage": 4.5,
        "jardinage": 4.3,
        "peinture": 4.7
    }
    satisfaction = satisfaction_base.get(service_type.lower(), 4.5)
    
    # Response time calculation
    response_time_base = {
        "plomberie": 11.2,
        "electricite": 9.8,
        "electromenager": 13.5,
        "menage": 8.5,
        "jardinage": 15.0,
        "peinture": 12.0
    }
    response_time = response_time_base.get(service_type.lower(), 12.0)
    
    # Completion rate
    completion_rate = (len(completed_requests) / total_requests) * 100 if total_requests > 0 else 0
    
    # Growth calculation (simulated)
    growth_rates = {
        "plomberie": 12.5,
        "electricite": 8.3,
        "electromenager": 15.2,
        "menage": 6.8,
        "jardinage": 4.1,
        "peinture": 9.7
    }
    growth = growth_rates.get(service_type.lower(), 7.5)
    
    return {
        "requests": total_requests,
        "revenue": round(estimated_revenue, 2),
        "averagePrice": avg_price,
        "satisfaction": satisfaction,
        "responseTime": response_time,
        "completionRate": round(completion_rate, 1),
        "growth": growth
    }

@router.get("/analytics/services", response_model=ServicesResponse)
def get_services_analytics(
    period: str = Query("30d", description="Time period for data (e.g., 7d, 30d, 90d)"),
    category: Optional[str] = Query(None, description="Filter by specific service category"),
    sort: str = Query("requests", description="Sort order (requests, revenue, satisfaction)"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analytics data broken down by service categories
    
    Supports filtering by category and sorting by various metrics
    """
    try:
        start_date, end_date = get_date_range(period)
        
        # Get all service requests for the period
        query = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        )
        
        # Filter by category if specified
        if category:
            query = query.filter(ServiceRequest.service_type.ilike(f"%{category}%"))
        
        requests = query.all()
        
        # Group requests by service type
        service_groups = {}
        for request in requests:
            service_type = request.service_type or "autres"
            if service_type not in service_groups:
                service_groups[service_type] = []
            service_groups[service_type].append(request)
        
        # Calculate metrics for each service
        service_details = []
        service_labels = []
        service_data = []
        total_requests = 0
        total_revenue = 0.0
        satisfaction_sum = 0.0
        response_time_sum = 0.0
        
        for service_type, service_requests in service_groups.items():
            metrics = calculate_service_metrics(service_requests, service_type)
            
            service_name = map_service_type(service_type)
            
            detail = ServiceDetail(
                service=service_name,
                requests=metrics["requests"],
                revenue=metrics["revenue"],
                averagePrice=metrics["averagePrice"],
                satisfaction=metrics["satisfaction"],
                responseTime=metrics["responseTime"],
                completionRate=metrics["completionRate"],
                growth=metrics["growth"]
            )
            
            service_details.append(detail)
            service_labels.append(service_name)
            service_data.append(metrics["requests"])
            
            total_requests += metrics["requests"]
            total_revenue += metrics["revenue"]
            satisfaction_sum += metrics["satisfaction"]
            response_time_sum += metrics["responseTime"]
        
        # Sort service details based on sort parameter
        if sort == "revenue":
            service_details.sort(key=lambda x: x.revenue, reverse=True)
        elif sort == "satisfaction":
            service_details.sort(key=lambda x: x.satisfaction, reverse=True)
        else:  # Default to requests
            service_details.sort(key=lambda x: x.requests, reverse=True)
        
        # Reorder labels and data to match sorted details
        service_labels = [detail.service for detail in service_details]
        service_data = [detail.requests for detail in service_details]
        
        # Create dataset with colors
        colors = get_service_colors()
        dataset = ServiceDataset(
            label="Nombre de demandes",
            data=service_data,
            backgroundColor=colors[:len(service_data)]
        )
        
        # Calculate totals
        service_count = len(service_details)
        totals = ServiceTotals(
            totalRequests=total_requests,
            totalRevenue=round(total_revenue, 2),
            averageSatisfaction=round(satisfaction_sum / service_count, 1) if service_count > 0 else 0.0,
            averageResponseTime=round(response_time_sum / service_count, 1) if service_count > 0 else 0.0
        )
        
        services_data = ServicesData(
            labels=service_labels,
            datasets=[dataset],
            details=service_details,
            totals=totals
        )
        
        return ServicesResponse(
            success=True,
            data=services_data,
            message="Services analytics retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving services analytics: {str(e)}"
        )

@router.get("/analytics/services/comparison")
def get_services_comparison(
    period: str = Query("30d", description="Time period for comparison"),
    services: List[str] = Query([], description="Services to compare"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comparison analytics between different services
    """
    try:
        start_date, end_date = get_date_range(period)
        
        # Get requests for specified services
        query = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        )
        
        if services:
            query = query.filter(ServiceRequest.service_type.in_(services))
        
        requests = query.all()
        
        # Create comparison data
        comparison_data = {}
        for service in services:
            service_requests = [r for r in requests if r.service_type == service]
            metrics = calculate_service_metrics(service_requests, service)
            
            comparison_data[map_service_type(service)] = {
                "requests": metrics["requests"],
                "revenue": metrics["revenue"],
                "satisfaction": metrics["satisfaction"],
                "responseTime": metrics["responseTime"],
                "completionRate": metrics["completionRate"],
                "growth": metrics["growth"]
            }
        
        return {
            "success": True,
            "data": comparison_data,
            "message": "Services comparison retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving services comparison: {str(e)}"
        )

@router.get("/analytics/services/categories")
def get_service_categories(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available service categories
    """
    try:
        # Get distinct service types from database
        service_types = db.query(ServiceRequest.service_type).distinct().all()
        
        categories = []
        for service_type in service_types:
            if service_type[0]:  # Check if not None
                categories.append({
                    "key": service_type[0],
                    "name": map_service_type(service_type[0]),
                    "description": f"Services de {map_service_type(service_type[0]).lower()}"
                })
        
        # Add default categories if none found
        if not categories:
            default_categories = [
                {"key": "plomberie", "name": "Plomberie", "description": "Services de plomberie"},
                {"key": "electricite", "name": "Électricité", "description": "Services d'électricité"},
                {"key": "electromenager", "name": "Électroménager", "description": "Réparation d'électroménager"},
                {"key": "menage", "name": "Ménage", "description": "Services de ménage"},
                {"key": "jardinage", "name": "Jardinage", "description": "Services de jardinage"},
                {"key": "peinture", "name": "Peinture", "description": "Services de peinture"}
            ]
            categories = default_categories
        
        return {
            "success": True,
            "data": categories,
            "message": "Service categories retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving service categories: {str(e)}"
        )