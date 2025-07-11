"""
AI API endpoints for Djobea AI
Implements AI predictions and insights functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models.database_models import (
    ServiceRequest, Provider, User, RequestStatus
)
from app.models.dynamic_services import Service, Zone
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ai", tags=["AI"])

@router.get("/predictions")
async def get_ai_predictions(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/ai/predictions - Get AI predictions
    Retrieve AI-generated predictions and forecasts
    """
    try:
        logger.info("Generating AI predictions")
        
        # Get historical data for predictions
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        
        # Request volume prediction
        weekly_requests = []
        for i in range(4):  # Last 4 weeks
            week_start = now - timedelta(weeks=i+1)
            week_end = now - timedelta(weeks=i)
            
            week_count = db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= week_start,
                ServiceRequest.created_at < week_end
            ).count()
            
            weekly_requests.append(week_count)
        
        # Calculate trend
        if len(weekly_requests) >= 2:
            recent_avg = sum(weekly_requests[:2]) / 2
            older_avg = sum(weekly_requests[2:]) / 2 if len(weekly_requests) > 2 else weekly_requests[-1]
            growth_rate = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        else:
            growth_rate = 0
        
        # Predict next week's requests
        current_week_requests = weekly_requests[0] if weekly_requests else 0
        predicted_requests = round(current_week_requests * (1 + growth_rate / 100))
        
        # Service demand prediction
        service_demand = []
        services = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('recent_count')
        ).filter(
            ServiceRequest.created_at >= last_7_days
        ).group_by(ServiceRequest.service_type).all()
        
        total_recent = sum(count for _, count in services)
        
        for service_type, recent_count in services:
            # Get historical average
            historical_count = db.query(ServiceRequest).filter(
                ServiceRequest.service_type == service_type,
                ServiceRequest.created_at >= last_30_days,
                ServiceRequest.created_at < last_7_days
            ).count()
            
            historical_avg_weekly = historical_count / 3  # 3 weeks of historical data
            
            # Predict growth
            if historical_avg_weekly > 0:
                service_growth = ((recent_count - historical_avg_weekly) / historical_avg_weekly * 100)
            else:
                service_growth = 0
            
            # Predict next week demand
            predicted_demand = round(recent_count * (1 + service_growth / 100))
            
            service_demand.append({
                "serviceType": service_type,
                "currentWeekDemand": recent_count,
                "predictedDemand": predicted_demand,
                "growthRate": round(service_growth, 2),
                "marketShare": round((recent_count / total_recent * 100) if total_recent > 0 else 0, 2),
                "trend": "increasing" if service_growth > 5 else "decreasing" if service_growth < -5 else "stable"
            })
        
        # Sort by predicted demand
        service_demand.sort(key=lambda x: x['predictedDemand'], reverse=True)
        
        # Provider capacity prediction
        active_providers = db.query(Provider).filter(
            Provider.status.in_([ProviderStatus.ACTIVE, ProviderStatus.AVAILABLE])
        ).count()
        
        # Calculate average requests per provider
        recent_requests_total = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= last_7_days
        ).count()
        
        requests_per_provider = recent_requests_total / active_providers if active_providers > 0 else 0
        
        # Predict capacity needs
        capacity_utilization = min((predicted_requests / active_providers / 5) * 100, 100) if active_providers > 0 else 100  # Assuming 5 requests per provider per week is full capacity
        
        provider_predictions = {
            "currentCapacity": active_providers,
            "currentUtilization": round((recent_requests_total / active_providers / 5) * 100 if active_providers > 0 else 0, 2),
            "predictedUtilization": round(capacity_utilization, 2),
            "recommendedProviders": max(0, round(predicted_requests / 5) - active_providers),
            "status": "sufficient" if capacity_utilization < 80 else "strained" if capacity_utilization < 100 else "overloaded"
        }
        
        # Zone demand prediction
        zone_predictions = []
        zones = db.query(
            ServiceRequest.location,
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= last_7_days
        ).group_by(ServiceRequest.location).order_by(desc('count')).limit(5).all()
        
        for location, count in zones:
            # Simple zone classification
            if "bonamoussadi" in location.lower():
                zone = "Bonamoussadi"
            elif "makepe" in location.lower():
                zone = "Makepe"
            elif "akwa" in location.lower():
                zone = "Akwa"
            else:
                zone = "Douala Centre"
            
            # Get providers in this zone
            zone_providers = db.query(Provider).filter(
                Provider.coverage_zone.ilike(f"%{zone}%"),
                Provider.status.in_([ProviderStatus.ACTIVE, ProviderStatus.AVAILABLE])
            ).count()
            
            predicted_zone_demand = round(count * (1 + growth_rate / 100))
            
            zone_predictions.append({
                "zone": zone,
                "location": location,
                "currentDemand": count,
                "predictedDemand": predicted_zone_demand,
                "availableProviders": zone_providers,
                "demandPerProvider": round(predicted_zone_demand / zone_providers, 2) if zone_providers > 0 else predicted_zone_demand,
                "recommendation": "recruit_providers" if zone_providers < predicted_zone_demand / 3 else "optimal"
            })
        
        # Success rate prediction
        completed_recent = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= last_7_days,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).count()
        
        current_success_rate = (completed_recent / recent_requests_total * 100) if recent_requests_total > 0 else 0
        
        # Get historical success rate
        historical_total = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= last_30_days,
            ServiceRequest.created_at < last_7_days
        ).count()
        
        historical_completed = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= last_30_days,
            ServiceRequest.created_at < last_7_days,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).count()
        
        historical_success_rate = (historical_completed / historical_total * 100) if historical_total > 0 else 0
        
        success_rate_trend = current_success_rate - historical_success_rate
        predicted_success_rate = min(100, max(0, current_success_rate + success_rate_trend))
        
        # Revenue prediction
        recent_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= last_7_days,
            ServiceRequest.status == RequestStatus.COMPLETED,
            ServiceRequest.final_cost.isnot(None)
        ).scalar() or 0
        
        avg_order_value = recent_revenue / completed_recent if completed_recent > 0 else 0
        predicted_revenue = predicted_requests * predicted_success_rate / 100 * avg_order_value
        
        response = {
            "generatedAt": now.isoformat() + "Z",
            "predictionHorizon": "7 days",
            "confidence": "medium",  # Could be calculated based on data quality
            "requests": {
                "currentWeek": recent_requests_total,
                "predictedNextWeek": predicted_requests,
                "growthRate": round(growth_rate, 2),
                "trend": "increasing" if growth_rate > 5 else "decreasing" if growth_rate < -5 else "stable"
            },
            "services": {
                "demandForecast": service_demand,
                "topGrowingService": service_demand[0]['serviceType'] if service_demand else None,
                "emergingTrends": [s for s in service_demand if s['growthRate'] > 20]
            },
            "capacity": provider_predictions,
            "geography": {
                "zoneDemand": zone_predictions,
                "highDemandZones": [z['zone'] for z in zone_predictions if z['demandPerProvider'] > 3]
            },
            "performance": {
                "currentSuccessRate": round(current_success_rate, 2),
                "predictedSuccessRate": round(predicted_success_rate, 2),
                "trend": "improving" if success_rate_trend > 1 else "declining" if success_rate_trend < -1 else "stable"
            },
            "revenue": {
                "currentWeek": round(recent_revenue, 2),
                "predictedNextWeek": round(predicted_revenue, 2),
                "avgOrderValue": round(avg_order_value, 2),
                "currency": "FCFA"
            },
            "recommendations": [
                {
                    "category": "capacity",
                    "priority": "high" if provider_predictions['status'] == "overloaded" else "medium",
                    "action": f"Recruit {provider_predictions['recommendedProviders']} additional providers" if provider_predictions['recommendedProviders'] > 0 else "Current capacity is sufficient",
                    "impact": "Improve service availability and reduce wait times"
                },
                {
                    "category": "market",
                    "priority": "medium",
                    "action": f"Focus marketing efforts on {service_demand[0]['serviceType'] if service_demand else 'general services'}",
                    "impact": "Capitalize on growing demand trends"
                },
                {
                    "category": "operations",
                    "priority": "medium",
                    "action": "Monitor success rate trends and investigate causes of any decline",
                    "impact": "Maintain high service quality and customer satisfaction"
                }
            ]
        }
        
        logger.info(f"AI predictions generated: {predicted_requests} requests predicted for next week")
        return response
        
    except Exception as e:
        logger.error(f"Error generating AI predictions: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération des prédictions IA")