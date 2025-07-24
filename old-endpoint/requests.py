"""
Requests API v1 - Unified Requests Domain
Combines requests_complete.py, request_management_api.py, tracking_api.py, escalation_detection_api.py, human_escalation_api.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models.database_models import ServiceRequest, User, Provider, AdminUser
from app.utils.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# ==== REQUEST MANAGEMENT ====
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
        
        # Get assigned provider if exists
        provider = None
        if request.assigned_provider_id:
            provider = db.query(Provider).filter(Provider.id == request.assigned_provider_id).first()
        
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
                "assignedProvider": {
                    "id": provider.id,
                    "name": provider.name,
                    "phone": provider.phone_number,
                    "rating": provider.rating or 4.5
                } if provider else None,
                "timeline": [
                    {
                        "status": "created",
                        "timestamp": request.created_at.isoformat() if request.created_at else None,
                        "description": "Demande créée"
                    },
                    {
                        "status": request.status,
                        "timestamp": datetime.now().isoformat(),
                        "description": f"Statut: {request.status}"
                    }
                ]
            }
        }
    except Exception as e:
        logger.error(f"Get request error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la demande")

@router.post("/")
async def create_request(
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Create new request"""
    try:
        new_request = ServiceRequest(
            user_id=request_data.get("userId"),
            service_type=request_data.get("serviceType"),
            location=request_data.get("location"),
            description=request_data.get("description"),
            status="pending",
            urgency=request_data.get("urgency", "normal"),
            created_at=datetime.now()
        )
        
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        return {
            "success": True,
            "message": "Demande créée avec succès",
            "data": {
                "id": new_request.id,
                "requestId": f"REQ-{new_request.id:03d}"
            }
        }
    except Exception as e:
        logger.error(f"Create request error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la demande")

@router.put("/{request_id}/status")
async def update_request_status(
    request_id: int = Path(..., description="Request ID"),
    status_data: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update request status"""
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        new_status = status_data.get("status")
        if new_status:
            request.status = new_status
            if new_status == "completed":
                request.completed_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Statut mis à jour avec succès"
        }
    except Exception as e:
        logger.error(f"Update request status error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du statut")

@router.post("/{request_id}/assign")
async def assign_provider(
    request_id: int = Path(..., description="Request ID"),
    assignment_data: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Assign provider to request"""
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        provider_id = assignment_data.get("providerId")
        if provider_id:
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                request.assigned_provider_id = provider_id
                request.status = "assigned"
                request.assigned_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Prestataire assigné avec succès"
        }
    except Exception as e:
        logger.error(f"Assign provider error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de l'assignation du prestataire")

# ==== TRACKING & MONITORING ====
@router.get("/{request_id}/tracking")
async def get_request_tracking(
    request_id: int = Path(..., description="Request ID"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get request tracking information"""
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        return {
            "success": True,
            "data": {
                "requestId": request.id,
                "status": request.status,
                "progress": {
                    "current": request.status,
                    "percentage": _get_progress_percentage(request.status),
                    "estimatedCompletion": _get_estimated_completion(request.created_at)
                },
                "timeline": [
                    {
                        "step": "created",
                        "status": "completed",
                        "timestamp": request.created_at.isoformat() if request.created_at else None,
                        "description": "Demande créée"
                    },
                    {
                        "step": "assigned",
                        "status": "completed" if request.assigned_provider_id else "pending",
                        "timestamp": request.assigned_at.isoformat() if hasattr(request, 'assigned_at') and request.assigned_at else None,
                        "description": "Prestataire assigné"
                    },
                    {
                        "step": "in_progress",
                        "status": "completed" if request.status == "in_progress" else "pending",
                        "timestamp": None,
                        "description": "Service en cours"
                    },
                    {
                        "step": "completed",
                        "status": "completed" if request.status == "completed" else "pending",
                        "timestamp": request.completed_at.isoformat() if hasattr(request, 'completed_at') and request.completed_at else None,
                        "description": "Service terminé"
                    }
                ]
            }
        }
    except Exception as e:
        logger.error(f"Get request tracking error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du suivi")

@router.get("/tracking/analytics")
async def get_tracking_analytics(
    period: str = Query("7d", description="Time period"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get tracking analytics"""
    try:
        # Calculate date range
        end_date = datetime.now()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)
        
        # Get requests in period
        requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date,
            ServiceRequest.created_at <= end_date
        ).all()
        
        # Calculate metrics
        total_requests = len(requests)
        completed_requests = len([r for r in requests if r.status == "completed"])
        in_progress_requests = len([r for r in requests if r.status == "in_progress"])
        pending_requests = len([r for r in requests if r.status == "pending"])
        
        completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "success": True,
            "data": {
                "period": period,
                "summary": {
                    "totalRequests": total_requests,
                    "completedRequests": completed_requests,
                    "inProgressRequests": in_progress_requests,
                    "pendingRequests": pending_requests,
                    "completionRate": round(completion_rate, 1)
                },
                "trends": {
                    "dailyRequests": _get_daily_trends(requests),
                    "statusDistribution": {
                        "pending": pending_requests,
                        "assigned": len([r for r in requests if r.status == "assigned"]),
                        "in_progress": in_progress_requests,
                        "completed": completed_requests
                    }
                }
            }
        }
    except Exception as e:
        logger.error(f"Get tracking analytics error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des analyses de suivi")

# ==== ESCALATION MANAGEMENT ====
@router.post("/{request_id}/escalate")
async def escalate_request(
    request_id: int = Path(..., description="Request ID"),
    escalation_data: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Escalate request to human agent"""
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        # Update request with escalation info
        request.escalated = True
        request.escalation_reason = escalation_data.get("reason", "Manual escalation")
        request.escalated_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Demande escaladée avec succès",
            "data": {
                "requestId": request.id,
                "escalationReason": escalation_data.get("reason"),
                "escalatedAt": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Escalate request error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de l'escalade de la demande")

@router.get("/escalations")
async def get_escalated_requests(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get escalated requests"""
    try:
        # Build query for escalated requests
        query = db.query(ServiceRequest).filter(ServiceRequest.escalated == True)
        
        # Pagination
        total = query.count()
        requests = query.offset((page - 1) * limit).limit(limit).all()
        
        escalated_list = []
        for request in requests:
            escalated_list.append({
                "id": request.id,
                "requestId": f"REQ-{request.id:03d}",
                "serviceType": request.service_type or "Général",
                "location": request.location or "Bonamoussadi",
                "status": request.status or "pending",
                "escalationReason": getattr(request, 'escalation_reason', 'Raison non spécifiée'),
                "escalatedAt": request.escalated_at.isoformat() if hasattr(request, 'escalated_at') and request.escalated_at else None,
                "priority": "high"
            })
        
        return {
            "success": True,
            "data": escalated_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get escalated requests error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des demandes escaladées")

# ==== UTILITY FUNCTIONS ====
def _get_progress_percentage(status: str) -> int:
    """Get progress percentage based on status"""
    status_map = {
        "pending": 10,
        "assigned": 30,
        "in_progress": 70,
        "completed": 100,
        "cancelled": 0
    }
    return status_map.get(status, 0)

def _get_estimated_completion(created_at: datetime) -> str:
    """Get estimated completion time"""
    if not created_at:
        return "N/A"
    
    # Simple estimation: 2 hours from creation
    estimated = created_at + timedelta(hours=2)
    return estimated.isoformat()

def _get_daily_trends(requests: List[ServiceRequest]) -> List[Dict]:
    """Get daily request trends"""
    # Group requests by day
    daily_counts = {}
    for request in requests:
        if request.created_at:
            day = request.created_at.date().isoformat()
            daily_counts[day] = daily_counts.get(day, 0) + 1
    
    # Convert to list format
    return [
        {"date": date, "requests": count}
        for date, count in sorted(daily_counts.items())
    ]