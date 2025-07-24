"""
Analytics Insights API for Djobea AI
Provides AI-generated insights and recommendations based on system performance data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
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

class InsightType(str, Enum):
    POSITIVE = "positive"
    WARNING = "warning"
    CRITICAL = "critical"
    NEUTRAL = "neutral"

class InsightPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class InsightCategory(str, Enum):
    PERFORMANCE = "performance"
    SATISFACTION = "satisfaction"
    REVENUE = "revenue"
    EFFICIENCY = "efficiency"
    GROWTH = "growth"
    QUALITY = "quality"

def get_time_range(period: str) -> tuple[datetime, datetime]:
    """Get start and end datetime for the specified period"""
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
    else:
        start_date = end_date - timedelta(days=30)  # Default to 30 days
    
    return start_date, end_date

def calculate_performance_metrics(db: Session, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Calculate performance metrics for the specified period"""
    try:
        # Current period metrics
        current_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).all()
        
        # Previous period for comparison
        period_length = end_date - start_date
        prev_start = start_date - period_length
        prev_end = start_date
        
        previous_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= prev_start,
            ServiceRequest.created_at < prev_end
        ).all()
        
        # Calculate metrics
        current_count = len(current_requests)
        previous_count = len(previous_requests)
        
        completed_current = [r for r in current_requests if r.status == "completed"]
        completed_previous = [r for r in previous_requests if r.status == "completed"]
        
        current_completion_rate = (len(completed_current) / current_count * 100) if current_count > 0 else 0
        previous_completion_rate = (len(completed_previous) / previous_count * 100) if previous_count > 0 else 0
        
        # Calculate average response time (mock calculation)
        current_avg_response = 12.1  # minutes
        previous_avg_response = 14.2  # minutes
        
        # Calculate satisfaction score (mock calculation)
        current_satisfaction = 4.7
        previous_satisfaction = 4.5
        
        return {
            "current_requests": current_count,
            "previous_requests": previous_count,
            "current_completion_rate": current_completion_rate,
            "previous_completion_rate": previous_completion_rate,
            "current_avg_response": current_avg_response,
            "previous_avg_response": previous_avg_response,
            "current_satisfaction": current_satisfaction,
            "previous_satisfaction": previous_satisfaction
        }
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        return {
            "current_requests": 0,
            "previous_requests": 0,
            "current_completion_rate": 0,
            "previous_completion_rate": 0,
            "current_avg_response": 0,
            "previous_avg_response": 0,
            "current_satisfaction": 0,
            "previous_satisfaction": 0
        }

def generate_insights(metrics: Dict[str, Any], period: str) -> List[Dict[str, Any]]:
    """Generate AI insights based on performance metrics"""
    insights = []
    
    # Performance insight - Response time improvement
    if metrics["current_avg_response"] < metrics["previous_avg_response"]:
        improvement = ((metrics["previous_avg_response"] - metrics["current_avg_response"]) / metrics["previous_avg_response"]) * 100
        insights.append({
            "id": "insight_001",
            "type": InsightType.POSITIVE,
            "priority": InsightPriority.HIGH if improvement > 10 else InsightPriority.MEDIUM,
            "category": InsightCategory.PERFORMANCE,
            "title": "Amélioration significative du temps de réponse",
            "description": f"Le temps de réponse moyen a diminué de {improvement:.1f}% cette période, passant de {metrics['previous_avg_response']:.1f} à {metrics['current_avg_response']:.1f} minutes.",
            "impact": "high" if improvement > 10 else "medium",
            "confidence": 0.92,
            "metrics": {
                "previousValue": metrics["previous_avg_response"],
                "currentValue": metrics["current_avg_response"],
                "improvement": improvement,
                "unit": "minutes"
            },
            "recommendations": [
                "Maintenir les pratiques actuelles d'optimisation",
                "Étendre ces améliorations aux autres régions"
            ],
            "createdAt": datetime.now().isoformat()
        })
    
    # Satisfaction insight
    if metrics["current_satisfaction"] != metrics["previous_satisfaction"]:
        change = metrics["current_satisfaction"] - metrics["previous_satisfaction"]
        change_percent = (change / metrics["previous_satisfaction"]) * 100
        
        if change > 0:
            insights.append({
                "id": "insight_002",
                "type": InsightType.POSITIVE,
                "priority": InsightPriority.MEDIUM,
                "category": InsightCategory.SATISFACTION,
                "title": "Amélioration de la satisfaction client",
                "description": f"La satisfaction client a augmenté de {change_percent:.1f}%, passant de {metrics['previous_satisfaction']:.1f} à {metrics['current_satisfaction']:.1f}/5.",
                "impact": "medium",
                "confidence": 0.87,
                "metrics": {
                    "previousValue": metrics["previous_satisfaction"],
                    "currentValue": metrics["current_satisfaction"],
                    "improvement": change_percent,
                    "unit": "rating"
                },
                "recommendations": [
                    "Identifier les facteurs de cette amélioration",
                    "Partager les bonnes pratiques avec tous les prestataires"
                ],
                "createdAt": datetime.now().isoformat()
            })
        else:
            insights.append({
                "id": "insight_003",
                "type": InsightType.WARNING,
                "priority": InsightPriority.HIGH if abs(change_percent) > 5 else InsightPriority.MEDIUM,
                "category": InsightCategory.SATISFACTION,
                "title": "Baisse de satisfaction client détectée",
                "description": f"La satisfaction client a diminué de {abs(change_percent):.1f}%, passant de {metrics['previous_satisfaction']:.1f} à {metrics['current_satisfaction']:.1f}/5.",
                "impact": "high" if abs(change_percent) > 5 else "medium",
                "confidence": 0.89,
                "metrics": {
                    "previousValue": metrics["previous_satisfaction"],
                    "currentValue": metrics["current_satisfaction"],
                    "decline": abs(change_percent),
                    "unit": "rating"
                },
                "recommendations": [
                    "Analyser les commentaires clients récents",
                    "Organiser une formation pour les prestataires",
                    "Mettre en place un suivi renforcé"
                ],
                "createdAt": datetime.now().isoformat()
            })
    
    # Volume insight
    if metrics["current_requests"] != metrics["previous_requests"]:
        change = metrics["current_requests"] - metrics["previous_requests"]
        change_percent = (change / metrics["previous_requests"]) * 100 if metrics["previous_requests"] > 0 else 0
        
        if change > 0:
            insights.append({
                "id": "insight_004",
                "type": InsightType.POSITIVE,
                "priority": InsightPriority.MEDIUM,
                "category": InsightCategory.GROWTH,
                "title": "Croissance du volume de demandes",
                "description": f"Le nombre de demandes a augmenté de {change_percent:.1f}%, passant de {metrics['previous_requests']} à {metrics['current_requests']} demandes.",
                "impact": "medium",
                "confidence": 0.95,
                "metrics": {
                    "previousValue": metrics["previous_requests"],
                    "currentValue": metrics["current_requests"],
                    "growth": change_percent,
                    "unit": "requests"
                },
                "recommendations": [
                    "Préparer la capacité pour gérer l'augmentation",
                    "Recruter des prestataires supplémentaires si nécessaire"
                ],
                "createdAt": datetime.now().isoformat()
            })
    
    # Efficiency insight
    completion_change = metrics["current_completion_rate"] - metrics["previous_completion_rate"]
    if abs(completion_change) > 1:  # Only if change is significant
        if completion_change > 0:
            insights.append({
                "id": "insight_005",
                "type": InsightType.POSITIVE,
                "priority": InsightPriority.MEDIUM,
                "category": InsightCategory.EFFICIENCY,
                "title": "Amélioration du taux de completion",
                "description": f"Le taux de completion a augmenté de {completion_change:.1f}%, atteignant {metrics['current_completion_rate']:.1f}%.",
                "impact": "medium",
                "confidence": 0.88,
                "metrics": {
                    "previousValue": metrics["previous_completion_rate"],
                    "currentValue": metrics["current_completion_rate"],
                    "improvement": completion_change,
                    "unit": "percentage"
                },
                "recommendations": [
                    "Analyser les processus qui ont contribué à cette amélioration",
                    "Standardiser les bonnes pratiques"
                ],
                "createdAt": datetime.now().isoformat()
            })
    
    return insights

@router.get("/analytics/insights")
async def get_analytics_insights(
    period: str = Query("30d", description="Time period for insights (24h, 7d, 30d, 90d, 1y)"),
    category: Optional[str] = Query(None, description="Filter by insight category"),
    priority: Optional[str] = Query(None, description="Filter by priority level"),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated insights and recommendations"""
    try:
        # Get time range
        start_date, end_date = get_time_range(period)
        
        # Calculate performance metrics
        metrics = calculate_performance_metrics(db, start_date, end_date)
        
        # Generate insights
        insights = generate_insights(metrics, period)
        
        # Apply filters
        if category:
            insights = [i for i in insights if i["category"] == category]
        
        if priority:
            insights = [i for i in insights if i["priority"] == priority]
        
        # Calculate summary
        total_insights = len(insights)
        priority_counts = {
            "high": len([i for i in insights if i["priority"] == "high"]),
            "medium": len([i for i in insights if i["priority"] == "medium"]),
            "low": len([i for i in insights if i["priority"] == "low"])
        }
        
        category_counts = {}
        for category_enum in InsightCategory:
            count = len([i for i in insights if i["category"] == category_enum.value])
            if count > 0:
                category_counts[category_enum.value] = count
        
        summary = {
            "totalInsights": total_insights,
            "highPriority": priority_counts["high"],
            "mediumPriority": priority_counts["medium"],
            "lowPriority": priority_counts["low"],
            "categories": category_counts
        }
        
        return {
            "success": True,
            "data": insights,
            "summary": summary,
            "message": "Analytics insights retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving analytics insights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")