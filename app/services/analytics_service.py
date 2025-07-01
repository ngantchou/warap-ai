"""
Sprint 4 - Analytics Service
Business metrics and performance analytics for admin dashboard
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from datetime import datetime, timedelta

from app.models.database_models import ServiceRequest, Provider, User, Conversation, RequestStatus
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnalyticsService:
    """Service for generating business analytics and metrics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get real-time dashboard metrics"""
        try:
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Basic counts
            total_requests = self.db.query(ServiceRequest).count()
            total_providers = self.db.query(Provider).count()
            total_users = self.db.query(User).count()
            
            # Status distribution
            status_counts = {}
            for status in RequestStatus:
                count = self.db.query(ServiceRequest).filter(ServiceRequest.status == status.value).count()
                status_counts[status.value] = count
            
            # Active metrics
            active_providers = self.db.query(Provider).filter(
                and_(Provider.is_active == True, Provider.is_available == True)
            ).count()
            
            pending_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status.in_([RequestStatus.PENDING.value, RequestStatus.PROVIDER_NOTIFIED.value])
            ).count()
            
            # Success rate
            completed_requests = status_counts.get(RequestStatus.COMPLETED.value, 0)
            success_rate = (completed_requests / max(total_requests, 1)) * 100
            
            # Recent activity (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            recent_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= yesterday
            ).count()
            
            # Average response time (for completed requests)
            completed_with_times = self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.status == RequestStatus.COMPLETED.value,
                    ServiceRequest.accepted_at.isnot(None),
                    ServiceRequest.completed_at.isnot(None)
                )
            ).all()
            
            avg_completion_time = None
            if completed_with_times:
                total_time = sum([
                    (req.completed_at - req.created_at).total_seconds() / 3600  # Convert to hours
                    for req in completed_with_times
                    if req.completed_at and req.created_at
                ])
                avg_completion_time = total_time / len(completed_with_times)
            
            return {
                "overview": {
                    "total_requests": total_requests,
                    "total_providers": total_providers,
                    "total_users": total_users,
                    "active_providers": active_providers,
                    "pending_requests": pending_requests,
                    "success_rate": round(success_rate, 1),
                    "recent_requests_24h": recent_requests,
                    "avg_completion_time_hours": round(avg_completion_time, 2) if avg_completion_time else None
                },
                "status_distribution": status_counts,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("dashboard_metrics_error", extra={"error": str(e)})
            return {
                "overview": {
                    "total_requests": 0,
                    "total_providers": 0,
                    "total_users": 0,
                    "active_providers": 0,
                    "pending_requests": 0,
                    "success_rate": 0.0,
                    "recent_requests_24h": 0,
                    "avg_completion_time_hours": None
                },
                "status_distribution": {},
                "last_updated": datetime.now().isoformat(),
                "error": "Failed to load metrics"
            }
    
    def get_success_rate_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get success rate analytics over time"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Daily success rates
            daily_data = []
            for i in range(days):
                day = start_date + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                day_requests = self.db.query(ServiceRequest).filter(
                    and_(
                        ServiceRequest.created_at >= day_start,
                        ServiceRequest.created_at < day_end
                    )
                ).all()
                
                total_day = len(day_requests)
                completed_day = len([r for r in day_requests if r.status == RequestStatus.COMPLETED.value])
                
                success_rate = (completed_day / max(total_day, 1)) * 100
                
                daily_data.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "total_requests": total_day,
                    "completed_requests": completed_day,
                    "success_rate": round(success_rate, 1)
                })
            
            # Overall period metrics
            period_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= start_date
            ).all()
            
            total_period = len(period_requests)
            completed_period = len([r for r in period_requests if r.status == RequestStatus.COMPLETED.value])
            overall_success_rate = (completed_period / max(total_period, 1)) * 100
            
            return {
                "period_days": days,
                "overall_success_rate": round(overall_success_rate, 1),
                "total_requests": total_period,
                "completed_requests": completed_period,
                "daily_data": daily_data
            }
            
        except Exception as e:
            logger.error("success_rate_analytics_error", extra={"error": str(e), "days": days})
            return {
                "period_days": days,
                "overall_success_rate": 0.0,
                "total_requests": 0,
                "completed_requests": 0,
                "daily_data": [],
                "error": "Failed to load success rate analytics"
            }
    
    def get_response_time_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get response time analytics"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get requests with response times
            requests_with_times = self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.created_at >= start_date,
                    ServiceRequest.accepted_at.isnot(None)
                )
            ).all()
            
            if not requests_with_times:
                return {
                    "period_days": days,
                    "total_requests_analyzed": 0,
                    "average_response_time_minutes": None,
                    "median_response_time_minutes": None,
                    "response_time_distribution": {},
                    "provider_performance": []
                }
            
            # Calculate response times in minutes
            response_times = []
            provider_times = {}
            
            for request in requests_with_times:
                if request.accepted_at and request.created_at:
                    response_time = (request.accepted_at - request.created_at).total_seconds() / 60
                    response_times.append(response_time)
                    
                    # Track by provider
                    if request.provider_id:
                        if request.provider_id not in provider_times:
                            provider_times[request.provider_id] = []
                        provider_times[request.provider_id].append(response_time)
            
            # Calculate statistics
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            response_times_sorted = sorted(response_times)
            median_response_time = (
                response_times_sorted[len(response_times_sorted) // 2]
                if response_times_sorted else 0
            )
            
            # Response time distribution
            distribution = {
                "under_10_min": len([t for t in response_times if t < 10]),
                "10_to_30_min": len([t for t in response_times if 10 <= t < 30]),
                "30_to_60_min": len([t for t in response_times if 30 <= t < 60]),
                "over_60_min": len([t for t in response_times if t >= 60])
            }
            
            # Provider performance
            provider_performance = []
            for provider_id, times in provider_times.items():
                provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
                if provider:
                    avg_time = sum(times) / len(times)
                    provider_performance.append({
                        "provider_id": provider_id,
                        "provider_name": provider.name,
                        "avg_response_time_minutes": round(avg_time, 1),
                        "total_responses": len(times)
                    })
            
            # Sort by response time
            provider_performance.sort(key=lambda x: x["avg_response_time_minutes"])
            
            return {
                "period_days": days,
                "total_requests_analyzed": len(requests_with_times),
                "average_response_time_minutes": round(avg_response_time, 1),
                "median_response_time_minutes": round(median_response_time, 1),
                "response_time_distribution": distribution,
                "provider_performance": provider_performance[:10]  # Top 10
            }
            
        except Exception as e:
            logger.error("response_time_analytics_error", extra={"error": str(e), "days": days})
            return {
                "period_days": days,
                "total_requests_analyzed": 0,
                "average_response_time_minutes": None,
                "median_response_time_minutes": None,
                "response_time_distribution": {},
                "provider_performance": [],
                "error": "Failed to load response time analytics"
            }
    
    def get_service_type_analytics(self) -> Dict[str, Any]:
        """Get analytics by service type"""
        try:
            # Service type distribution
            service_counts = {}
            service_completion_rates = {}
            
            all_requests = self.db.query(ServiceRequest).all()
            
            for request in all_requests:
                service = request.service_type
                if service not in service_counts:
                    service_counts[service] = {"total": 0, "completed": 0}
                
                service_counts[service]["total"] += 1
                if request.status == RequestStatus.COMPLETED.value:
                    service_counts[service]["completed"] += 1
            
            # Calculate completion rates
            for service, counts in service_counts.items():
                completion_rate = (counts["completed"] / max(counts["total"], 1)) * 100
                service_completion_rates[service] = {
                    "total_requests": counts["total"],
                    "completed_requests": counts["completed"],
                    "completion_rate": round(completion_rate, 1)
                }
            
            return {
                "service_distribution": service_completion_rates,
                "most_requested": max(service_counts.items(), key=lambda x: x[1]["total"])[0] if service_counts else None,
                "highest_completion_rate": max(
                    service_completion_rates.items(),
                    key=lambda x: x[1]["completion_rate"]
                )[0] if service_completion_rates else None
            }
            
        except Exception as e:
            logger.error("service_type_analytics_error", extra={"error": str(e)})
            return {
                "service_distribution": {},
                "most_requested": None,
                "highest_completion_rate": None,
                "error": "Failed to load service type analytics"
            }
    
    def get_geographic_analytics(self) -> Dict[str, Any]:
        """Get analytics by location/geography"""
        try:
            # Location distribution
            location_counts = {}
            
            all_requests = self.db.query(ServiceRequest).all()
            
            for request in all_requests:
                # Extract main location keyword
                location = request.location.lower()
                main_location = "autre"
                
                # Check for main areas
                if "bonamoussadi" in location:
                    main_location = "bonamoussadi"
                elif "makepe" in location:
                    main_location = "makepe"
                elif "akwa" in location:
                    main_location = "akwa"
                elif "deido" in location:
                    main_location = "deido"
                elif "bonapriso" in location:
                    main_location = "bonapriso"
                
                if main_location not in location_counts:
                    location_counts[main_location] = {"total": 0, "completed": 0}
                
                location_counts[main_location]["total"] += 1
                if request.status == RequestStatus.COMPLETED.value:
                    location_counts[main_location]["completed"] += 1
            
            # Calculate completion rates by location
            location_analytics = {}
            for location, counts in location_counts.items():
                completion_rate = (counts["completed"] / max(counts["total"], 1)) * 100
                location_analytics[location] = {
                    "total_requests": counts["total"],
                    "completed_requests": counts["completed"],
                    "completion_rate": round(completion_rate, 1)
                }
            
            return {
                "location_distribution": location_analytics,
                "most_served_area": max(location_counts.items(), key=lambda x: x[1]["total"])[0] if location_counts else None
            }
            
        except Exception as e:
            logger.error("geographic_analytics_error", extra={"error": str(e)})
            return {
                "location_distribution": {},
                "most_served_area": None,
                "error": "Failed to load geographic analytics"
            }
    
    def get_provider_rankings(self) -> List[Dict[str, Any]]:
        """Get provider performance rankings"""
        try:
            providers = self.db.query(Provider).all()
            provider_stats = []
            
            for provider in providers:
                # Get provider's requests
                provider_requests = self.db.query(ServiceRequest).filter(
                    ServiceRequest.provider_id == provider.id
                ).all()
                
                total_requests = len(provider_requests)
                completed_requests = len([r for r in provider_requests if r.status == RequestStatus.COMPLETED.value])
                
                # Calculate average response time
                response_times = []
                for request in provider_requests:
                    if request.accepted_at and request.created_at:
                        response_time = (request.accepted_at - request.created_at).total_seconds() / 60
                        response_times.append(response_time)
                
                avg_response_time = sum(response_times) / len(response_times) if response_times else None
                completion_rate = (completed_requests / max(total_requests, 1)) * 100
                
                provider_stats.append({
                    "provider_id": provider.id,
                    "name": provider.name,
                    "phone_number": provider.phone_number,
                    "services": provider.services,
                    "rating": provider.rating,
                    "total_jobs": provider.total_jobs,
                    "total_requests": total_requests,
                    "completed_requests": completed_requests,
                    "completion_rate": round(completion_rate, 1),
                    "avg_response_time_minutes": round(avg_response_time, 1) if avg_response_time else None,
                    "is_active": provider.is_active,
                    "is_available": provider.is_available
                })
            
            # Sort by completion rate then by response time
            provider_stats.sort(key=lambda x: (-x["completion_rate"], x["avg_response_time_minutes"] or 999))
            
            return provider_stats
            
        except Exception as e:
            logger.error("provider_rankings_error", extra={"error": str(e)})
            return []