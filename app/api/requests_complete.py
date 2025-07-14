"""
Complete Requests API Module - Fixed Version
All request management endpoints with proper field mappings
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models.database_models import ServiceRequest, User, Provider
from app.utils.auth import get_current_user
from app.models.database_models import AdminUser

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def get_requests(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get all requests with pagination"""
    try:
        # Build query
        query = db.query(ServiceRequest).join(User, ServiceRequest.user_id == User.id, isouter=True)
        
        if status:
            query = query.filter(ServiceRequest.status == status)
        if service_type:
            query = query.filter(ServiceRequest.service_type == service_type)
            
        # Pagination
        total = query.count()
        requests = query.offset((page - 1) * limit).limit(limit).all()
        
        request_list = []
        for request in requests:
            request_list.append({
                "id": request.id,
                "requestId": f"REQ-{request.id:03d}",
                "clientName": f"Client #{request.user_id}" if request.user_id else "Client inconnu",
                "serviceType": request.service_type or "Général",
                "location": request.location or "Bonamoussadi",
                "description": request.description or "Pas de description",
                "status": request.status or "pending",
                "priority": getattr(request, 'priority', 'normal'),
                "createdAt": request.created_at.isoformat() if request.created_at else None,
                "estimatedPrice": getattr(request, 'estimated_price', 0),
                "assignedProviderId": getattr(request, 'assigned_provider_id', None)
            })
        
        return {
            "success": True,
            "data": request_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get requests error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des demandes")

@router.get("/{request_id}")
async def get_request(
    request_id: int = Path(..., description="Request ID"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get request details"""
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        return {
            "success": True,
            "data": {
                "id": request.id,
                "requestId": f"REQ-{request.id:03d}",
                "clientName": f"Client #{request.user_id}" if request.user_id else "Client inconnu",
                "serviceType": request.service_type or "Général",
                "location": request.location or "Bonamoussadi",
                "description": request.description or "Pas de description",
                "status": request.status or "pending",
                "priority": getattr(request, 'priority', 'normal'),
                "createdAt": request.created_at.isoformat() if request.created_at else None,
                "estimatedPrice": getattr(request, 'estimated_price', 0),
                "estimatedDuration": getattr(request, 'estimated_duration', 60),
                "assignedProviderId": getattr(request, 'assigned_provider_id', None),
                "assignedAt": getattr(request, 'assigned_at', None),
                "completedAt": getattr(request, 'completed_at', None)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get request error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la demande")

@router.get("/stats")
async def get_request_stats(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get request statistics"""
    try:
        # Basic stats
        total_requests = db.query(ServiceRequest).count()
        pending_requests = db.query(ServiceRequest).filter(ServiceRequest.status == "pending").count()
        completed_requests = db.query(ServiceRequest).filter(ServiceRequest.status == "completed").count()
        
        # Status distribution
        status_counts = db.query(
            ServiceRequest.status,
            func.count(ServiceRequest.id).label('count')
        ).group_by(ServiceRequest.status).all()
        
        status_distribution = {status: count for status, count in status_counts}
        
        # Service type distribution
        service_counts = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('count')
        ).group_by(ServiceRequest.service_type).all()
        
        service_distribution = {service_type: count for service_type, count in service_counts}
        
        return {
            "success": True,
            "data": {
                "totalRequests": total_requests,
                "pendingRequests": pending_requests,
                "completedRequests": completed_requests,
                "statusDistribution": status_distribution,
                "serviceDistribution": service_distribution,
                "completionRate": (completed_requests / total_requests * 100) if total_requests > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Get request stats error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

@router.get("/analytics")
async def get_request_analytics(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get request analytics"""
    try:
        # Calculate date range
        now = datetime.now()
        if period == "24h":
            start_date = now - timedelta(hours=24)
        elif period == "7d":
            start_date = now - timedelta(days=7)
        elif period == "30d":
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=7)
        
        # Requests over time
        requests_over_time = db.query(
            func.date(ServiceRequest.created_at).label('date'),
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= start_date
        ).group_by(
            func.date(ServiceRequest.created_at)
        ).all()
        
        # Service type trends
        service_trends = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('count')
        ).filter(
            ServiceRequest.created_at >= start_date
        ).group_by(ServiceRequest.service_type).all()
        
        return {
            "success": True,
            "data": {
                "period": period,
                "requestsOverTime": [
                    {"date": str(date), "count": count}
                    for date, count in requests_over_time
                ],
                "serviceTrends": [
                    {"service": service_type, "count": count}
                    for service_type, count in service_trends
                ],
                "totalRequests": sum(count for _, count in requests_over_time)
            }
        }
    except Exception as e:
        logger.error(f"Get request analytics error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des analytiques")

@router.put("/{request_id}/status")
async def update_request_status(
    request_id: int = Path(..., description="Request ID"),
    status: str = Query(..., description="New status"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update request status"""
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        request.status = status
        if status == "completed":
            request.completed_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Statut mis à jour avec succès",
            "data": {
                "id": request.id,
                "status": request.status,
                "updatedAt": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update request status error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du statut")

@router.delete("/{request_id}")
async def delete_request(
    request_id: int = Path(..., description="Request ID"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Delete a request"""
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        db.delete(request)
        db.commit()
        
        return {
            "success": True,
            "message": "Demande supprimée avec succès"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete request error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression")