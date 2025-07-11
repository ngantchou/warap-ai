"""
Analytics API endpoints for Djobea AI
Implements comprehensive analytics and reporting functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case, text
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models.database_models import (
    ServiceRequest, User, Provider, RequestStatus
)
from app.models.dynamic_services import Service, Zone
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/")
async def get_analytics_overview(
    period: str = Query("7d", pattern="^(24h|7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/analytics - Get analytics overview
    Retrieve comprehensive analytics data for the specified period
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Get total requests in period
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date
        ).count()
        
        # Get completed requests
        completed_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).count()
        
        # Calculate success rate
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Get active providers
        active_providers = db.query(Provider).filter(
            Provider.status == ProviderStatus.ACTIVE
        ).count()
        
        # Get revenue (sum of completed request costs)
        revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).scalar() or 0
        
        # Get request trend data
        request_trend = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            count = db.query(ServiceRequest).filter(
                func.date(ServiceRequest.created_at) == date.date()
            ).count()
            request_trend.append({
                "date": date.strftime("%Y-%m-%d"),
                "requests": count
            })
        
        # Get service distribution
        service_distribution = []
        services = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= start_date
        ).group_by(ServiceRequest.service_type).all()
        
        for service_type, count in services:
            service_distribution.append({
                "service": service_type,
                "count": count,
                "percentage": (count / total_requests * 100) if total_requests > 0 else 0
            })
        
        # Get top zones
        top_zones = []
        zones = db.query(
            ServiceRequest.location,
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= start_date
        ).group_by(ServiceRequest.location).order_by(desc('count')).limit(5).all()
        
        for location, count in zones:
            top_zones.append({
                "zone": location,
                "requests": count
            })
        
        response = {
            "period": period,
            "overview": {
                "totalRequests": total_requests,
                "completedRequests": completed_requests,
                "successRate": round(success_rate, 2),
                "activeProviders": active_providers,
                "revenue": round(revenue, 2),
                "currency": "FCFA"
            },
            "trends": {
                "requestTrend": request_trend,
                "serviceDistribution": service_distribution,
                "topZones": top_zones
            }
        }
        
        logger.info(f"Analytics overview retrieved for period: {period}")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving analytics overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des données analytiques")


@router.get("/kpis")
async def get_kpi_metrics(
    period: str = Query("7d", pattern="^(24h|7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/analytics/kpis - Get KPI metrics
    Retrieve key performance indicators for the specified period
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Calculate KPIs
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date
        ).count()
        
        completed_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).count()
        
        cancelled_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.CANCELLED
        ).count()
        
        # Average response time (in minutes)
        avg_response_time = db.query(
            func.avg(
                func.extract('epoch', ServiceRequest.accepted_at - ServiceRequest.created_at) / 60
            )
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.accepted_at.isnot(None)
        ).scalar() or 0
        
        # Average completion time (in hours)
        avg_completion_time = db.query(
            func.avg(
                func.extract('epoch', ServiceRequest.completed_at - ServiceRequest.created_at) / 3600
            )
        ).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.completed_at.isnot(None)
        ).scalar() or 0
        
        # Customer satisfaction (assuming 4.5 as average)
        customer_satisfaction = 4.5
        
        # Revenue metrics
        total_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).scalar() or 0
        
        avg_order_value = total_revenue / completed_requests if completed_requests > 0 else 0
        
        # Provider metrics
        total_providers = db.query(Provider).count()
        active_providers = db.query(Provider).filter(
            Provider.status == ProviderStatus.ACTIVE
        ).count()
        
        response = {
            "period": period,
            "kpis": {
                "performance": {
                    "totalRequests": total_requests,
                    "completedRequests": completed_requests,
                    "completionRate": round((completed_requests / total_requests * 100) if total_requests > 0 else 0, 2),
                    "cancellationRate": round((cancelled_requests / total_requests * 100) if total_requests > 0 else 0, 2)
                },
                "efficiency": {
                    "avgResponseTime": round(avg_response_time, 2),
                    "avgCompletionTime": round(avg_completion_time, 2),
                    "customerSatisfaction": customer_satisfaction
                },
                "financial": {
                    "totalRevenue": round(total_revenue, 2),
                    "avgOrderValue": round(avg_order_value, 2),
                    "currency": "FCFA"
                },
                "providers": {
                    "totalProviders": total_providers,
                    "activeProviders": active_providers,
                    "utilizationRate": round((active_providers / total_providers * 100) if total_providers > 0 else 0, 2)
                }
            }
        }
        
        logger.info(f"KPI metrics retrieved for period: {period}")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving KPI metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des KPIs")


@router.get("/performance")
async def get_performance_metrics(
    period: str = Query("7d", pattern="^(24h|7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/analytics/performance - Get performance metrics
    Retrieve performance analytics over time
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Get performance data by day
        performance_data = []
        days = 7 if period == "7d" else 30 if period == "30d" else 7
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            
            # Daily metrics
            daily_requests = db.query(ServiceRequest).filter(
                func.date(ServiceRequest.created_at) == date.date()
            ).count()
            
            daily_completed = db.query(ServiceRequest).filter(
                func.date(ServiceRequest.created_at) == date.date(),
                ServiceRequest.status == RequestStatus.COMPLETED
            ).count()
            
            daily_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
                func.date(ServiceRequest.created_at) == date.date(),
                ServiceRequest.status == RequestStatus.COMPLETED
            ).scalar() or 0
            
            performance_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "requests": daily_requests,
                "completed": daily_completed,
                "revenue": round(daily_revenue, 2),
                "successRate": round((daily_completed / daily_requests * 100) if daily_requests > 0 else 0, 2)
            })
        
        # Overall performance metrics
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date
        ).count()
        
        total_completed = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).count()
        
        total_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).scalar() or 0
        
        response = {
            "period": period,
            "performance": {
                "overview": {
                    "totalRequests": total_requests,
                    "totalCompleted": total_completed,
                    "totalRevenue": round(total_revenue, 2),
                    "avgSuccessRate": round((total_completed / total_requests * 100) if total_requests > 0 else 0, 2)
                },
                "timeline": performance_data
            }
        }
        
        logger.info(f"Performance metrics retrieved for period: {period}")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des métriques de performance")


@router.get("/services")
async def get_services_analytics(
    period: str = Query("7d", pattern="^(24h|7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/analytics/services - Get services analytics
    Retrieve service distribution and performance analytics
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Get service distribution
        service_stats = []
        services = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('total'),
            func.sum(case((ServiceRequest.status == RequestStatus.COMPLETED, 1), else_=0)).label('completed'),
            func.avg(ServiceRequest.final_cost).label('avg_cost')
        ).filter(
            ServiceRequest.created_at >= start_date
        ).group_by(ServiceRequest.service_type).all()
        
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date
        ).count()
        
        for service_type, total, completed, avg_cost in services:
            service_stats.append({
                "service": service_type,
                "totalRequests": total,
                "completedRequests": completed,
                "successRate": round((completed / total * 100) if total > 0 else 0, 2),
                "marketShare": round((total / total_requests * 100) if total_requests > 0 else 0, 2),
                "avgCost": round(avg_cost or 0, 2),
                "revenue": round((avg_cost or 0) * completed, 2)
            })
        
        # Sort by total requests
        service_stats.sort(key=lambda x: x['totalRequests'], reverse=True)
        
        response = {
            "period": period,
            "services": {
                "distribution": service_stats,
                "summary": {
                    "totalServices": len(service_stats),
                    "totalRequests": total_requests,
                    "mostPopular": service_stats[0]['service'] if service_stats else None,
                    "currency": "FCFA"
                }
            }
        }
        
        logger.info(f"Services analytics retrieved for period: {period}")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving services analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des analyses de services")


@router.get("/geographic")
async def get_geographic_analytics(
    period: str = Query("7d", pattern="^(24h|7d|30d|90d|1y)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/analytics/geographic - Get geographic analytics
    Retrieve geographic distribution of services and providers
    """
    try:
        # Calculate date range
        now = datetime.utcnow()
        period_mapping = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
            "1y": timedelta(days=365)
        }
        
        start_date = now - period_mapping[period]
        
        # Get geographic distribution
        geographic_stats = []
        locations = db.query(
            ServiceRequest.location,
            func.count(ServiceRequest.id).label('total'),
            func.sum(case((ServiceRequest.status == RequestStatus.COMPLETED, 1), else_=0)).label('completed'),
            func.avg(ServiceRequest.final_cost).label('avg_cost')
        ).filter(
            ServiceRequest.created_at >= start_date
        ).group_by(ServiceRequest.location).all()
        
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date
        ).count()
        
        for location, total, completed, avg_cost in locations:
            # Extract zone from location (simple approach)
            zone = "Bonamoussadi" if "bonamoussadi" in location.lower() else "Douala"
            
            geographic_stats.append({
                "zone": zone,
                "location": location,
                "totalRequests": total,
                "completedRequests": completed,
                "successRate": round((completed / total * 100) if total > 0 else 0, 2),
                "marketShare": round((total / total_requests * 100) if total_requests > 0 else 0, 2),
                "avgCost": round(avg_cost or 0, 2),
                "revenue": round((avg_cost or 0) * completed, 2)
            })
        
        # Sort by total requests
        geographic_stats.sort(key=lambda x: x['totalRequests'], reverse=True)
        
        # Get provider distribution by zone
        provider_distribution = []
        providers = db.query(
            Provider.coverage_zone,
            func.count(Provider.id).label('count')
        ).group_by(Provider.coverage_zone).all()
        
        for zone, count in providers:
            provider_distribution.append({
                "zone": zone,
                "providers": count
            })
        
        response = {
            "period": period,
            "geographic": {
                "requestDistribution": geographic_stats,
                "providerDistribution": provider_distribution,
                "summary": {
                    "totalZones": len(geographic_stats),
                    "totalRequests": total_requests,
                    "topZone": geographic_stats[0]['zone'] if geographic_stats else None,
                    "currency": "FCFA"
                }
            }
        }
        
        logger.info(f"Geographic analytics retrieved for period: {period}")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving geographic analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des analyses géographiques")


@router.get("/insights")
async def get_ai_insights(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/analytics/insights - Get AI insights
    Retrieve AI-generated insights and recommendations
    """
    try:
        # Get recent data for insights
        now = datetime.utcnow()
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)
        
        # Calculate insights
        insights = []
        
        # Request trend insight
        weekly_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= last_week
        ).count()
        
        monthly_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= last_month
        ).count()
        
        if weekly_requests > 0 and monthly_requests > 0:
            growth_rate = ((weekly_requests / (monthly_requests / 4)) - 1) * 100
            
            insights.append({
                "type": "trend",
                "category": "requests",
                "title": "Tendance des demandes",
                "description": f"Les demandes ont {'augmenté' if growth_rate > 0 else 'diminué'} de {abs(growth_rate):.1f}% cette semaine",
                "impact": "high" if abs(growth_rate) > 20 else "medium" if abs(growth_rate) > 10 else "low",
                "recommendation": "Ajuster la capacité des prestataires" if growth_rate > 20 else "Continuer le suivi"
            })
        
        # Service performance insight
        top_service = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= last_week
        ).group_by(ServiceRequest.service_type).order_by(desc('count')).first()
        
        if top_service:
            insights.append({
                "type": "performance",
                "category": "services",
                "title": "Service le plus demandé",
                "description": f"{top_service[0]} représente {top_service[1]} demandes cette semaine",
                "impact": "medium",
                "recommendation": "Recruter plus de prestataires spécialisés"
            })
        
        # Provider availability insight
        total_providers = db.query(Provider).count()
        active_providers = db.query(Provider).filter(
            Provider.status == ProviderStatus.ACTIVE
        ).count()
        
        if total_providers > 0:
            availability_rate = (active_providers / total_providers) * 100
            insights.append({
                "type": "capacity",
                "category": "providers",
                "title": "Disponibilité des prestataires",
                "description": f"{availability_rate:.1f}% des prestataires sont actifs",
                "impact": "high" if availability_rate < 70 else "medium" if availability_rate < 85 else "low",
                "recommendation": "Activer plus de prestataires" if availability_rate < 70 else "Niveau optimal"
            })
        
        # Revenue insight
        weekly_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= last_week,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).scalar() or 0
        
        monthly_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.created_at >= last_month,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).scalar() or 0
        
        if weekly_revenue > 0 and monthly_revenue > 0:
            revenue_growth = ((weekly_revenue / (monthly_revenue / 4)) - 1) * 100
            insights.append({
                "type": "financial",
                "category": "revenue",
                "title": "Croissance du chiffre d'affaires",
                "description": f"Revenus {'en hausse' if revenue_growth > 0 else 'en baisse'} de {abs(revenue_growth):.1f}% cette semaine",
                "impact": "high" if abs(revenue_growth) > 20 else "medium",
                "recommendation": "Optimiser les tarifs" if revenue_growth < -10 else "Maintenir la stratégie"
            })
        
        response = {
            "insights": insights,
            "generatedAt": now.isoformat() + "Z",
            "summary": {
                "totalInsights": len(insights),
                "highImpact": len([i for i in insights if i["impact"] == "high"]),
                "mediumImpact": len([i for i in insights if i["impact"] == "medium"]),
                "lowImpact": len([i for i in insights if i["impact"] == "low"])
            }
        }
        
        logger.info(f"AI insights generated: {len(insights)} insights")
        return response
        
    except Exception as e:
        logger.error(f"Error generating AI insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération des insights IA")


@router.get("/leaderboard")
async def get_provider_leaderboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/analytics/leaderboard - Get provider leaderboard
    Retrieve top performing providers
    """
    try:
        # Get provider performance data
        provider_stats = db.query(
            Provider.id,
            Provider.name,
            Provider.service_type,
            Provider.rating,
            Provider.coverage_zone,
            func.count(ServiceRequest.id).label('total_requests'),
            func.sum(case((ServiceRequest.status == RequestStatus.COMPLETED, 1), else_=0)).label('completed_requests'),
            func.avg(ServiceRequest.final_cost).label('avg_cost')
        ).join(
            ServiceRequest, Provider.id == ServiceRequest.provider_id, isouter=True
        ).group_by(
            Provider.id, Provider.name, Provider.service_type, Provider.rating, Provider.coverage_zone
        ).all()
        
        # Calculate performance scores and format leaderboard
        leaderboard = []
        for provider in provider_stats:
            total_requests = provider.total_requests or 0
            completed_requests = provider.completed_requests or 0
            success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Performance score calculation
            score = (
                (provider.rating or 0) * 20 +  # Rating weight: 20%
                success_rate * 0.4 +            # Success rate weight: 40%
                min(total_requests * 2, 40)     # Request volume weight: 40% (capped at 40)
            )
            
            leaderboard.append({
                "id": provider.id,
                "name": provider.name,
                "serviceType": provider.service_type,
                "zone": provider.coverage_zone,
                "rating": provider.rating or 0,
                "totalRequests": total_requests,
                "completedRequests": completed_requests,
                "successRate": round(success_rate, 2),
                "avgCost": round(provider.avg_cost or 0, 2),
                "revenue": round((provider.avg_cost or 0) * completed_requests, 2),
                "performanceScore": round(score, 2),
                "rank": 0  # Will be set after sorting
            })
        
        # Sort by performance score and assign ranks
        leaderboard.sort(key=lambda x: x['performanceScore'], reverse=True)
        for i, provider in enumerate(leaderboard):
            provider['rank'] = i + 1
        
        # Get top 10 providers
        top_providers = leaderboard[:10]
        
        response = {
            "leaderboard": top_providers,
            "summary": {
                "totalProviders": len(leaderboard),
                "topPerformer": top_providers[0]['name'] if top_providers else None,
                "avgPerformanceScore": round(sum(p['performanceScore'] for p in leaderboard) / len(leaderboard), 2) if leaderboard else 0,
                "currency": "FCFA"
            }
        }
        
        logger.info(f"Provider leaderboard retrieved: {len(top_providers)} top providers")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving provider leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du classement des prestataires")