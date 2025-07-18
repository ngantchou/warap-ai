"""
Geographic Analytics API for Djobea AI
Provides analytics data broken down by geographic regions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models.database_models import ServiceRequest, Provider, User
from app.services.auth_service import auth_service
from app.models.auth_models import User as AuthUser
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
logger = logging.getLogger(__name__)
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

@router.get("/analytics/geographic")
async def get_geographic_analytics(
    period: Optional[str] = Query("30d", description="Time period for data"),
    region: Optional[str] = Query(None, description="Filter by specific region"),
    level: Optional[str] = Query("city", description="Geographic level (city, region, country)"),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get geographic analytics data broken down by regions
    
    Args:
        period: Time period for data (24h, 7d, 30d, 90d, 1y)
        region: Filter by specific region
        level: Geographic level (city, region, country)
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Geographic analytics data with regional breakdowns
    """
    try:
        # Parse time period
        period_map = {
            "24h": 1,
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "1y": 365
        }
        
        days = period_map.get(period, 30)
        start_date = datetime.now() - timedelta(days=days)
        
        # Get geographic data from service requests
        query = db.query(
            ServiceRequest.location,
            func.count(ServiceRequest.id).label('requests'),
            func.count(func.distinct(ServiceRequest.provider_id)).label('providers'),
            func.sum(ServiceRequest.estimated_price).label('revenue'),
            func.avg(ServiceRequest.rating).label('satisfaction'),
            func.avg(
                func.extract('epoch', ServiceRequest.updated_at - ServiceRequest.created_at) / 3600
            ).label('response_time')
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.location.isnot(None)
        ).group_by(ServiceRequest.location)
        
        # Apply region filter if specified
        if region:
            query = query.filter(ServiceRequest.location.ilike(f"%{region}%"))
        
        results = query.all()
        
        # Process results and add geographic data
        geographic_data = []
        total_requests = 0
        total_providers = 0
        total_revenue = 0
        total_satisfaction = 0
        satisfaction_count = 0
        
        # Cameroon cities with coordinates (focusing on major cities)
        city_coordinates = {
            "douala": [4.0511, 9.7679],
            "yaoundé": [3.8480, 11.5021],
            "bamenda": [5.9597, 10.1480],
            "bafoussam": [5.4781, 10.4167],
            "garoua": [9.3265, 13.3978],
            "maroua": [10.5906, 14.3156],
            "ngaoundéré": [7.3167, 13.5833],
            "bertoua": [4.5833, 13.6833],
            "buea": [4.1553, 9.2918],
            "kumba": [4.6333, 9.4500],
            "bonamoussadi": [4.0669, 9.7370],
            "akwa": [4.0496, 9.7069],
            "bonapriso": [4.0595, 9.7155],
            "new bell": [4.0449, 9.7370],
            "deido": [4.0611, 9.7070]
        }
        
        for result in results:
            location = result.location.lower() if result.location else "unknown"
            
            # Find coordinates for the location
            coordinates = None
            for city, coords in city_coordinates.items():
                if city in location:
                    coordinates = coords
                    break
            
            if not coordinates:
                coordinates = [4.0511, 9.7679]  # Default to Douala
            
            requests_count = result.requests or 0
            providers_count = result.providers or 0
            revenue = float(result.revenue or 0)
            satisfaction = float(result.satisfaction or 0) if result.satisfaction else 0
            response_time = float(result.response_time or 0) if result.response_time else 0
            
            # Calculate growth (simplified calculation)
            growth = min(max(-50, (requests_count - 10) * 2), 100)  # Simulated growth
            
            total_requests += requests_count
            total_providers += providers_count
            total_revenue += revenue
            
            if satisfaction > 0:
                total_satisfaction += satisfaction
                satisfaction_count += 1
            
            geographic_data.append({
                "region": result.location or "Unknown",
                "requests": requests_count,
                "providers": providers_count,
                "revenue": revenue,
                "satisfaction": round(satisfaction, 1),
                "responseTime": round(response_time, 1),
                "coordinates": coordinates,
                "growth": round(growth, 1),
                "marketShare": 0  # Will be calculated after we have totals
            })
        
        # Calculate market share for each region
        for region_data in geographic_data:
            if total_requests > 0:
                region_data["marketShare"] = round(
                    (region_data["requests"] / total_requests) * 100, 1
                )
        
        # Sort by requests (descending)
        geographic_data.sort(key=lambda x: x["requests"], reverse=True)
        
        # Calculate summary
        avg_satisfaction = (total_satisfaction / satisfaction_count) if satisfaction_count > 0 else 0
        
        summary = {
            "totalRegions": len(geographic_data),
            "totalRequests": total_requests,
            "totalProviders": total_providers,
            "totalRevenue": round(total_revenue, 2),
            "averageSatisfaction": round(avg_satisfaction, 1)
        }
        
        logger.info(f"Geographic analytics retrieved: {len(geographic_data)} regions, {total_requests} requests")
        
        return {
            "success": True,
            "data": geographic_data,
            "summary": summary,
            "message": "Geographic analytics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving geographic analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving geographic analytics: {str(e)}"
        )

@router.get("/analytics/geographic/regions")
async def get_available_regions(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get list of available regions for filtering
    
    Args:
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        List of available regions
    """
    try:
        # Get unique locations from service requests
        regions = db.query(
            ServiceRequest.location,
            func.count(ServiceRequest.id).label('request_count')
        ).filter(
            ServiceRequest.location.isnot(None)
        ).group_by(
            ServiceRequest.location
        ).order_by(
            func.count(ServiceRequest.id).desc()
        ).all()
        
        region_list = []
        for region in regions:
            region_list.append({
                "name": region.location,
                "requestCount": region.request_count,
                "key": region.location.lower().replace(" ", "_")
            })
        
        return {
            "success": True,
            "data": region_list,
            "message": "Available regions retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving available regions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving available regions: {str(e)}"
        )

@router.get("/analytics/geographic/heatmap")
async def get_geographic_heatmap(
    period: Optional[str] = Query("30d", description="Time period for data"),
    metric: Optional[str] = Query("requests", description="Metric for heatmap (requests, revenue, satisfaction)"),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Get geographic heatmap data for visualization
    
    Args:
        period: Time period for data
        metric: Metric for heatmap visualization
        db: Database session
        current_user: Current authenticated user
    
    Returns:
        Heatmap data with coordinates and values
    """
    try:
        # Parse time period
        period_map = {
            "24h": 1,
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "1y": 365
        }
        
        days = period_map.get(period, 30)
        start_date = datetime.now() - timedelta(days=days)
        
        # Get heatmap data
        if metric == "revenue":
            query = db.query(
                ServiceRequest.location,
                func.sum(ServiceRequest.estimated_price).label('value')
            )
        elif metric == "satisfaction":
            query = db.query(
                ServiceRequest.location,
                func.avg(ServiceRequest.rating).label('value')
            )
        else:  # requests
            query = db.query(
                ServiceRequest.location,
                func.count(ServiceRequest.id).label('value')
            )
        
        query = query.filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.location.isnot(None)
        ).group_by(ServiceRequest.location)
        
        results = query.all()
        
        # Cameroon cities with coordinates
        city_coordinates = {
            "douala": [4.0511, 9.7679],
            "yaoundé": [3.8480, 11.5021],
            "bamenda": [5.9597, 10.1480],
            "bafoussam": [5.4781, 10.4167],
            "garoua": [9.3265, 13.3978],
            "maroua": [10.5906, 14.3156],
            "ngaoundéré": [7.3167, 13.5833],
            "bertoua": [4.5833, 13.6833],
            "buea": [4.1553, 9.2918],
            "kumba": [4.6333, 9.4500],
            "bonamoussadi": [4.0669, 9.7370],
            "akwa": [4.0496, 9.7069],
            "bonapriso": [4.0595, 9.7155],
            "new bell": [4.0449, 9.7370],
            "deido": [4.0611, 9.7070]
        }
        
        heatmap_data = []
        for result in results:
            location = result.location.lower() if result.location else "unknown"
            
            # Find coordinates for the location
            coordinates = None
            for city, coords in city_coordinates.items():
                if city in location:
                    coordinates = coords
                    break
            
            if coordinates:
                value = float(result.value or 0)
                heatmap_data.append({
                    "lat": coordinates[0],
                    "lng": coordinates[1],
                    "value": value,
                    "location": result.location
                })
        
        return {
            "success": True,
            "data": heatmap_data,
            "metric": metric,
            "period": period,
            "message": "Geographic heatmap data retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving geographic heatmap: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving geographic heatmap: {str(e)}"
        )