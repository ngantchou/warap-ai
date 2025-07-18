"""
Analytics Leaderboard API
Provides leaderboard data for providers, services, and regions
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.database import get_db
from app.models.database_models import Provider, ServiceRequest, User
from app.services.auth_service import auth_service
from app.models.auth_models import User as AuthUser
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AuthUser:
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

@router.get("/leaderboard")
async def get_leaderboard(
    category: str = Query(..., description="Leaderboard category", regex="^(providers|services|regions)$"),
    period: str = Query("30d", description="Time period", regex="^(24h|7d|30d|90d|1y|all)$"),
    limit: int = Query(10, ge=1, le=50, description="Number of entries to return"),
    metric: str = Query("rating", description="Ranking metric", regex="^(rating|requests|revenue|responseTime)$"),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get leaderboard data for providers, services, or regions"""
    
    try:
        # Calculate date range
        end_date = datetime.now()
        if period == "24h":
            start_date = end_date - timedelta(hours=24)
        elif period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        else:  # all
            start_date = datetime(2020, 1, 1)
        
        if category == "providers":
            leaderboard_data = await _get_providers_leaderboard(
                db, start_date, end_date, limit, metric
            )
        elif category == "services":
            leaderboard_data = await _get_services_leaderboard(
                db, start_date, end_date, limit, metric
            )
        elif category == "regions":
            leaderboard_data = await _get_regions_leaderboard(
                db, start_date, end_date, limit, metric
            )
        
        # Calculate total entries
        total_entries = len(leaderboard_data)
        
        # Apply limit
        leaderboard_data = leaderboard_data[:limit]
        
        # Add ranking
        for i, entry in enumerate(leaderboard_data):
            entry["rank"] = i + 1
        
        return {
            "success": True,
            "data": leaderboard_data,
            "metadata": {
                "totalEntries": total_entries,
                "period": period,
                "category": category,
                "metric": metric,
                "lastUpdated": datetime.now().isoformat()
            },
            "message": "Leaderboard retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving leaderboard: {str(e)}")


async def _get_providers_leaderboard(
    db: Session, 
    start_date: datetime, 
    end_date: datetime, 
    limit: int, 
    metric: str
) -> List[Dict[str, Any]]:
    """Get providers leaderboard data"""
    
    try:
        # Get all providers
        providers = db.query(Provider).all()
        
        leaderboard_data = []
        
        for provider in providers:
            # Get request statistics for this provider
            requests_query = db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider.id,
                ServiceRequest.created_at >= start_date,
                ServiceRequest.created_at <= end_date
            )
            
            total_requests = requests_query.count()
            completed_requests = requests_query.filter(ServiceRequest.status == "completed").count()
            completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Mock response time and revenue data
            avg_response_time = 4.5 if total_requests > 0 else 0
            total_revenue = completed_requests * 15000  # 15000 XAF per completed request
            
            # Calculate score based on metric
            if metric == "rating":
                score = float(provider.rating or 0)
            elif metric == "requests":
                score = total_requests
            elif metric == "revenue":
                score = total_revenue
            elif metric == "responseTime":
                score = -avg_response_time if avg_response_time > 0 else 0  # Negative for better ranking
            else:
                score = float(provider.rating or 0)
            
            # Determine badges
            badges = []
            if completion_rate >= 95:
                badges.append("Top Performer")
            if avg_response_time <= 2:
                badges.append("Quick Response")
            if provider.rating and provider.rating >= 4.5:
                badges.append("Customer Favorite")
            if total_requests >= 50:
                badges.append("Experienced")
            if total_revenue >= 50000:
                badges.append("High Earner")
            
            # Calculate change (mock data for now)
            change = 0
            if total_requests > 10:
                change = 1 if provider.rating and provider.rating > 4.0 else -1
            
            leaderboard_data.append({
                "id": str(provider.id),
                "name": provider.name or "Prestataire",
                "avatar": f"https://ui-avatars.com/api/?name={provider.name or 'Provider'}&size=64&background=0D8ABC&color=fff",
                "score": round(score, 1),
                "missions": total_requests,
                "rating": round(float(provider.rating or 0), 1),
                "responseTime": round(avg_response_time, 1),
                "completionRate": round(completion_rate, 1),
                "revenue": round(total_revenue, 2),
                "change": change,
                "category": provider.service_type or "Service",
                "location": provider.location or "Douala",
                "joinDate": provider.created_at.strftime("%Y-%m-%d") if provider.created_at else "2024-01-01",
                "badges": badges
            })
        
        # Sort by score descending
        leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
        
        return leaderboard_data
        
    except Exception as e:
        raise Exception(f"Error calculating providers leaderboard: {str(e)}")


async def _get_services_leaderboard(
    db: Session, 
    start_date: datetime, 
    end_date: datetime, 
    limit: int, 
    metric: str
) -> List[Dict[str, Any]]:
    """Get services leaderboard data"""
    
    try:
        # Get distinct service types
        service_types = db.query(ServiceRequest.service_type).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).distinct().all()
        
        leaderboard_data = []
        
        for service_type_row in service_types:
            service_type = service_type_row.service_type
            
            # Get statistics for this service type
            service_requests = db.query(ServiceRequest).filter(
                ServiceRequest.service_type == service_type,
                ServiceRequest.created_at >= start_date,
                ServiceRequest.created_at <= end_date
            )
            
            total_requests = service_requests.count()
            completed_requests = service_requests.filter(ServiceRequest.status == "completed").count()
            completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Mock average rating and revenue
            avg_rating = 4.5 if total_requests > 0 else 0
            total_revenue = completed_requests * 15000  # 15000 XAF per completed request
            
            # Calculate score based on metric
            if metric == "rating":
                score = avg_rating
            elif metric == "requests":
                score = total_requests
            elif metric == "revenue":
                score = total_revenue
            else:
                score = total_requests
            
            # Service name mapping
            service_names = {
                "plomberie": "Plomberie",
                "electricite": "Électricité", 
                "electromenager": "Électroménager",
                "menage": "Ménage",
                "jardinage": "Jardinage"
            }
            
            service_name = service_names.get(service_type, service_type.title())
            
            leaderboard_data.append({
                "id": f"service_{service_type}",
                "name": service_name,
                "avatar": f"https://ui-avatars.com/api/?name={service_name}&size=64&background=28A745&color=fff",
                "score": round(score, 1),
                "missions": total_requests,
                "rating": round(avg_rating, 1),
                "responseTime": 0,  # Not applicable for services
                "completionRate": round(completion_rate, 1),
                "revenue": round(total_revenue, 2),
                "change": 0,
                "category": service_name,
                "location": "Douala",
                "joinDate": "2024-01-01",
                "badges": ["Service populaire" if total_requests > 20 else "Service"]
            })
        
        # Sort by score descending
        leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
        
        return leaderboard_data
        
    except Exception as e:
        raise Exception(f"Error calculating services leaderboard: {str(e)}")


async def _get_regions_leaderboard(
    db: Session, 
    start_date: datetime, 
    end_date: datetime, 
    limit: int, 
    metric: str
) -> List[Dict[str, Any]]:
    """Get regions leaderboard data"""
    
    try:
        # Get distinct regions/locations
        regions = db.query(ServiceRequest.location).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date,
            ServiceRequest.location.isnot(None)
        ).distinct().all()
        
        leaderboard_data = []
        
        for region_row in regions:
            region_name = region_row.location
            
            # Get statistics for this region
            region_requests = db.query(ServiceRequest).filter(
                ServiceRequest.location == region_name,
                ServiceRequest.created_at >= start_date,
                ServiceRequest.created_at <= end_date
            )
            
            total_requests = region_requests.count()
            completed_requests = region_requests.filter(ServiceRequest.status == "completed").count()
            completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Mock average rating and revenue
            avg_rating = 4.3 if total_requests > 0 else 0
            total_revenue = completed_requests * 15000  # 15000 XAF per completed request
            
            # Calculate score based on metric
            if metric == "rating":
                score = avg_rating
            elif metric == "requests":
                score = total_requests
            elif metric == "revenue":
                score = total_revenue
            else:
                score = total_requests
            
            leaderboard_data.append({
                "id": f"region_{region_name.lower().replace(' ', '_')}",
                "name": region_name,
                "avatar": f"https://ui-avatars.com/api/?name={region_name}&size=64&background=DC3545&color=fff",
                "score": round(score, 1),
                "missions": total_requests,
                "rating": round(avg_rating, 1),
                "responseTime": 0,  # Not applicable for regions
                "completionRate": round(completion_rate, 1),
                "revenue": round(total_revenue, 2),
                "change": 0,
                "category": "Région",
                "location": region_name,
                "joinDate": "2024-01-01",
                "badges": ["Zone active" if total_requests > 15 else "Zone"]
            })
        
        # Sort by score descending
        leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
        
        return leaderboard_data
        
    except Exception as e:
        raise Exception(f"Error calculating regions leaderboard: {str(e)}")