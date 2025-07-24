"""
System API endpoints for Djobea AI
Implements system metrics, monitoring, and zone management functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
import time

from app.database import get_db
from app.models.database_models import (
    ServiceRequest, Provider, User, RequestStatus
)
from app.models.dynamic_services import Service, Zone
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["System"])

@router.get("/zones")
async def get_zones_list(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/zones - Get zones list
    Retrieve list of all service zones with statistics
    """
    try:
        logger.info("Fetching zones list")
        
        # Get all zones
        zones = db.query(Zone).all()
        
        formatted_zones = []
        for zone in zones:
            # Get request statistics for this zone
            total_requests = db.query(ServiceRequest).filter(
                ServiceRequest.location.ilike(f"%{zone.name}%")
            ).count()
            
            active_requests = db.query(ServiceRequest).filter(
                ServiceRequest.location.ilike(f"%{zone.name}%"),
                ServiceRequest.status.in_([RequestStatus.PENDING, RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS])
            ).count()
            
            completed_requests = db.query(ServiceRequest).filter(
                ServiceRequest.location.ilike(f"%{zone.name}%"),
                ServiceRequest.status == RequestStatus.COMPLETED
            ).count()
            
            # Get provider count for this zone
            providers_count = db.query(Provider).filter(
                Provider.coverage_zone.ilike(f"%{zone.name}%")
            ).count()
            
            # Calculate success rate
            success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            formatted_zone = {
                "id": zone.id,
                "name": zone.name,
                "nameEn": zone.name_en or zone.name,
                "nameFr": zone.name_fr or zone.name,
                "description": zone.description or "",
                "coordinates": {
                    "lat": zone.latitude or 4.0511,
                    "lng": zone.longitude or 9.7679
                },
                "parentZone": zone.parent_zone_id,
                "zoneType": zone.zone_type or "district",
                "isActive": zone.is_active if zone.is_active is not None else True,
                "statistics": {
                    "totalRequests": total_requests,
                    "activeRequests": active_requests,
                    "completedRequests": completed_requests,
                    "providersCount": providers_count,
                    "successRate": round(success_rate, 2)
                },
                "createdAt": zone.created_at.isoformat() + "Z" if zone.created_at else None,
                "updatedAt": zone.updated_at.isoformat() + "Z" if zone.updated_at else None
            }
            
            formatted_zones.append(formatted_zone)
        
        # Sort by total requests (most active zones first)
        formatted_zones.sort(key=lambda x: x['statistics']['totalRequests'], reverse=True)
        
        # Get zone hierarchy (parent zones)
        parent_zones = [zone for zone in formatted_zones if zone.get('parentZone') is None]
        child_zones = [zone for zone in formatted_zones if zone.get('parentZone') is not None]
        
        response = {
            "zones": formatted_zones,
            "hierarchy": {
                "parentZones": parent_zones,
                "childZones": child_zones
            },
            "summary": {
                "totalZones": len(formatted_zones),
                "activeZones": len([z for z in formatted_zones if z['isActive']]),
                "totalRequests": sum(z['statistics']['totalRequests'] for z in formatted_zones),
                "totalProviders": sum(z['statistics']['providersCount'] for z in formatted_zones)
            }
        }
        
        logger.info(f"Retrieved {len(formatted_zones)} zones")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching zones: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des zones")


@router.get("/metrics/system")
async def get_system_metrics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/metrics/system - Get system metrics
    Retrieve comprehensive system performance and health metrics
    """
    try:
        logger.info("Fetching system metrics")
        
        # Get current timestamp
        current_time = datetime.utcnow()
        
        # Database metrics
        try:
            # Test database connection and get basic stats
            db_start_time = time.time()
            total_users = db.query(User).count()
            total_providers = db.query(Provider).count()
            total_requests = db.query(ServiceRequest).count()
            total_services = db.query(Service).count()
            db_response_time = round((time.time() - db_start_time) * 1000, 2)  # in milliseconds
            
            # Get database size (PostgreSQL specific)
            try:
                db_size_result = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).fetchone()
                db_size = db_size_result[0] if db_size_result else "Unknown"
            except:
                db_size = "Unknown"
            
            # Active connections
            try:
                active_connections_result = db.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                ).fetchone()
                active_connections = active_connections_result[0] if active_connections_result else 0
            except:
                active_connections = 0
            
            db_metrics = {
                "status": "healthy",
                "responseTime": db_response_time,
                "size": db_size,
                "activeConnections": active_connections,
                "tables": {
                    "users": total_users,
                    "providers": total_providers,
                    "requests": total_requests,
                    "services": total_services
                }
            }
        except Exception as e:
            logger.error(f"Database metrics error: {str(e)}")
            db_metrics = {
                "status": "error",
                "error": str(e),
                "responseTime": None
            }
        
        # System resource metrics
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_total = round(memory.total / (1024**3), 2)  # GB
            memory_used = round(memory.used / (1024**3), 2)  # GB
            memory_available = round(memory.available / (1024**3), 2)  # GB
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_total = round(disk.total / (1024**3), 2)  # GB
            disk_used = round(disk.used / (1024**3), 2)  # GB
            disk_free = round(disk.free / (1024**3), 2)  # GB
            
            # System uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = current_time - boot_time
            uptime_hours = round(uptime.total_seconds() / 3600, 1)
            
            system_metrics = {
                "status": "healthy",
                "uptime": {
                    "hours": uptime_hours,
                    "bootTime": boot_time.isoformat() + "Z"
                },
                "cpu": {
                    "usage": cpu_percent,
                    "cores": cpu_count
                },
                "memory": {
                    "usage": memory_percent,
                    "total": memory_total,
                    "used": memory_used,
                    "available": memory_available,
                    "unit": "GB"
                },
                "disk": {
                    "usage": disk_percent,
                    "total": disk_total,
                    "used": disk_used,
                    "free": disk_free,
                    "unit": "GB"
                }
            }
        except Exception as e:
            logger.error(f"System metrics error: {str(e)}")
            system_metrics = {
                "status": "error",
                "error": str(e)
            }
        
        # Application metrics
        try:
            # Recent activity (last 24 hours)
            last_24h = current_time - timedelta(hours=24)
            
            requests_24h = db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= last_24h
            ).count()
            
            completed_24h = db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= last_24h,
                ServiceRequest.status == RequestStatus.COMPLETED
            ).count()
            
            new_users_24h = db.query(User).filter(
                User.created_at >= last_24h
            ).count()
            
            # Error rate calculation (simplified)
            cancelled_24h = db.query(ServiceRequest).filter(
                ServiceRequest.created_at >= last_24h,
                ServiceRequest.status == RequestStatus.CANCELLED
            ).count()
            
            error_rate = (cancelled_24h / requests_24h * 100) if requests_24h > 0 else 0
            success_rate = (completed_24h / requests_24h * 100) if requests_24h > 0 else 0
            
            # Average response time (simplified calculation)
            avg_response_time = db.query(
                func.avg(
                    func.extract('epoch', ServiceRequest.accepted_at - ServiceRequest.created_at)
                )
            ).filter(
                ServiceRequest.created_at >= last_24h,
                ServiceRequest.accepted_at.isnot(None)
            ).scalar() or 0
            
            app_metrics = {
                "status": "healthy",
                "performance": {
                    "avgResponseTime": round(avg_response_time / 60, 2) if avg_response_time else 0,  # minutes
                    "successRate": round(success_rate, 2),
                    "errorRate": round(error_rate, 2)
                },
                "activity": {
                    "requests24h": requests_24h,
                    "completions24h": completed_24h,
                    "newUsers24h": new_users_24h
                }
            }
        except Exception as e:
            logger.error(f"Application metrics error: {str(e)}")
            app_metrics = {
                "status": "error",
                "error": str(e)
            }
        
        # Overall system health
        overall_status = "healthy"
        if (db_metrics.get("status") == "error" or 
            system_metrics.get("status") == "error" or 
            app_metrics.get("status") == "error"):
            overall_status = "degraded"
        
        # Check for warning conditions
        warnings = []
        if system_metrics.get("cpu", {}).get("usage", 0) > 80:
            warnings.append("High CPU usage detected")
        if system_metrics.get("memory", {}).get("usage", 0) > 80:
            warnings.append("High memory usage detected")
        if system_metrics.get("disk", {}).get("usage", 0) > 80:
            warnings.append("High disk usage detected")
        if db_metrics.get("responseTime", 0) > 1000:
            warnings.append("Slow database response time")
        
        if warnings:
            overall_status = "warning"
        
        response = {
            "timestamp": current_time.isoformat() + "Z",
            "status": overall_status,
            "warnings": warnings,
            "database": db_metrics,
            "system": system_metrics,
            "application": app_metrics,
            "summary": {
                "componentsHealthy": sum(1 for m in [db_metrics, system_metrics, app_metrics] if m.get("status") == "healthy"),
                "totalComponents": 3,
                "overallHealth": round((sum(1 for m in [db_metrics, system_metrics, app_metrics] if m.get("status") == "healthy") / 3) * 100, 1)
            }
        }
        
        logger.info(f"System metrics retrieved - Status: {overall_status}")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des métriques système")