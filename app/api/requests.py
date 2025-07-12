"""
Requests API endpoints for Djobea AI
Implements comprehensive request management functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging
import uuid

from app.database import get_db
from app.models.database_models import (
    ServiceRequest, User, Provider, RequestStatus
)
from app.models.dynamic_services import Service, Zone
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Requests"])

# Pydantic models
class AssignProviderRequest(BaseModel):
    providerId: int = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)

class CancelRequestRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)
    refundAmount: Optional[float] = Field(None, ge=0)

class UpdateStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|assigned|in_progress|completed|cancelled)$")
    notes: Optional[str] = Field(None, max_length=500)

class GenerateInvoiceRequest(BaseModel):
    finalCost: float = Field(..., gt=0)
    description: str = Field(..., min_length=10, max_length=500)
    materials: Optional[List[str]] = []
    laborHours: Optional[float] = Field(None, ge=0)

@router.get("/")
async def get_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    dateFrom: Optional[str] = Query(None),
    dateTo: Optional[str] = Query(None),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/requests - Get requests list
    Retrieve paginated list of service requests with filtering and sorting
    """
    try:
        logger.info(f"Fetching requests - Page {page}, Limit {limit}")
        
        # Build base query
        query = db.query(ServiceRequest).join(User, ServiceRequest.user_id == User.id)
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    User.name.ilike(f"%{search}%"),
                    ServiceRequest.service_type.ilike(f"%{search}%"),
                    ServiceRequest.location.ilike(f"%{search}%"),
                    ServiceRequest.description.ilike(f"%{search}%")
                )
            )
        
        if status:
            status_mapping = {
                "pending": RequestStatus.PENDING,
                "assigned": RequestStatus.ASSIGNED,
                "in_progress": RequestStatus.IN_PROGRESS,
                "completed": RequestStatus.COMPLETED,
                "cancelled": RequestStatus.CANCELLED
            }
            if status in status_mapping:
                query = query.filter(ServiceRequest.status == status_mapping[status])
        
        if priority:
            query = query.filter(ServiceRequest.urgency == priority)
        
        if service:
            query = query.filter(ServiceRequest.service_type.ilike(f"%{service}%"))
        
        if location:
            query = query.filter(ServiceRequest.location.ilike(f"%{location}%"))
        
        # Date filters
        if dateFrom:
            try:
                from_date = datetime.fromisoformat(dateFrom.replace('Z', '+00:00'))
                query = query.filter(ServiceRequest.created_at >= from_date)
            except ValueError:
                pass
        
        if dateTo:
            try:
                to_date = datetime.fromisoformat(dateTo.replace('Z', '+00:00'))
                query = query.filter(ServiceRequest.created_at <= to_date)
            except ValueError:
                pass
        
        # Sorting
        if sortBy == "createdAt":
            if sortOrder == "desc":
                query = query.order_by(desc(ServiceRequest.created_at))
            else:
                query = query.order_by(ServiceRequest.created_at)
        elif sortBy == "status":
            if sortOrder == "desc":
                query = query.order_by(desc(ServiceRequest.status))
            else:
                query = query.order_by(ServiceRequest.status)
        elif sortBy == "priority":
            if sortOrder == "desc":
                query = query.order_by(desc(ServiceRequest.urgency))
            else:
                query = query.order_by(ServiceRequest.urgency)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        requests = query.offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit
        has_next_page = page < total_pages
        has_prev_page = page > 1
        
        # Format requests
        formatted_requests = []
        for req in requests:
            # Get user info
            user = db.query(User).filter(User.id == req.user_id).first()
            
            # Get provider info if assigned
            provider = None
            if req.provider_id:
                provider = db.query(Provider).filter(Provider.id == req.provider_id).first()
            
            # Map status to French
            status_mapping = {
                "PENDING": "en attente",
                "PROVIDER_NOTIFIED": "prestataire notifié",
                "ASSIGNED": "assigné",
                "IN_PROGRESS": "en cours",
                "COMPLETED": "terminé",
                "CANCELLED": "annulé"
            }
            
            status_fr = status_mapping.get(req.status.value if req.status else "PENDING", "en attente")
            
            # Map priority to French
            priority_mapping = {
                "urgent": "urgent",
                "normal": "normal",
                "flexible": "flexible"
            }
            
            priority = priority_mapping.get(req.urgency, "normal")
            
            # Calculate coordinates (simple approach)
            coordinates = {"lat": 4.0511, "lng": 9.7679}
            if "makepe" in req.location.lower():
                coordinates = {"lat": 4.0612, "lng": 9.7580}
            elif "akwa" in req.location.lower():
                coordinates = {"lat": 4.0483, "lng": 9.7043}
            
            formatted_request = {
                "id": req.id,
                "client": {
                    "name": user.name if user else "Client inconnu",
                    "phone": user.phone_number if user else "",
                    "email": getattr(user, 'email', '') if user else ""
                },
                "service": {
                    "type": req.service_type,
                    "description": req.description
                },
                "location": {
                    "address": req.location,
                    "zone": "Bonamoussadi" if "bonamoussadi" in req.location.lower() else "Douala",
                    "coordinates": coordinates
                },
                "provider": {
                    "id": provider.id if provider else None,
                    "name": provider.name if provider else None,
                    "phone": provider.phone_number if provider else None,
                    "rating": provider.rating if provider else None
                } if provider else None,
                "status": status_fr,
                "priority": priority,
                "createdAt": req.created_at.isoformat() + "Z",
                "updatedAt": (req.updated_at or req.created_at).isoformat() + "Z",
                "scheduledAt": req.scheduled_at.isoformat() + "Z" if req.scheduled_at else None,
                "completedAt": req.completed_at.isoformat() + "Z" if req.completed_at else None,
                "cost": {
                    "estimated": req.estimated_cost or 0,
                    "final": req.final_cost or 0,
                    "currency": "FCFA"
                }
            }
            
            formatted_requests.append(formatted_request)
        
        # Get status statistics
        status_stats = {
            "pending": db.query(ServiceRequest).filter(ServiceRequest.status == RequestStatus.PENDING).count(),
            "assigned": db.query(ServiceRequest).filter(ServiceRequest.status.in_([RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS])).count(),
            "completed": db.query(ServiceRequest).filter(ServiceRequest.status == RequestStatus.COMPLETED).count(),
            "cancelled": db.query(ServiceRequest).filter(ServiceRequest.status == RequestStatus.CANCELLED).count()
        }
        
        response = {
            "requests": formatted_requests,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasNextPage": has_next_page,
                "hasPrevPage": has_prev_page
            },
            "stats": status_stats
        }
        
        logger.info(f"Retrieved {len(formatted_requests)} requests (page {page}/{total_pages})")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des demandes")


@router.get("/{request_id}")
async def get_request_details(
    request_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/requests/{id} - Get request details
    Retrieve detailed information about a specific request
    """
    try:
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        # Get user info
        user = db.query(User).filter(User.id == request.user_id).first()
        
        # Get provider info if assigned
        provider = None
        if request.provider_id:
            provider = db.query(Provider).filter(Provider.id == request.provider_id).first()
        
        # Map status to French
        status_mapping = {
            "PENDING": "en attente",
            "PROVIDER_NOTIFIED": "prestataire notifié",
            "ASSIGNED": "assigné",
            "IN_PROGRESS": "en cours",
            "COMPLETED": "terminé",
            "CANCELLED": "annulé"
        }
        
        status_fr = status_mapping.get(request.status.value if request.status else "PENDING", "en attente")
        
        # Calculate coordinates
        coordinates = {"lat": 4.0511, "lng": 9.7679}
        if "makepe" in request.location.lower():
            coordinates = {"lat": 4.0612, "lng": 9.7580}
        elif "akwa" in request.location.lower():
            coordinates = {"lat": 4.0483, "lng": 9.7043}
        
        # Create timeline
        timeline = []
        timeline.append({
            "event": "created",
            "title": "Demande créée",
            "description": f"Demande de {request.service_type} créée par {user.name if user else 'Client'}",
            "timestamp": request.created_at.isoformat() + "Z"
        })
        
        if request.accepted_at:
            timeline.append({
                "event": "assigned",
                "title": "Prestataire assigné",
                "description": f"Demande assignée à {provider.name if provider else 'Prestataire'}",
                "timestamp": request.accepted_at.isoformat() + "Z"
            })
        
        if request.completed_at:
            timeline.append({
                "event": "completed",
                "title": "Service terminé",
                "description": "Service terminé avec succès",
                "timestamp": request.completed_at.isoformat() + "Z"
            })
        
        response = {
            "id": request.id,
            "client": {
                "name": user.name if user else "Client inconnu",
                "phone": user.phone_number if user else "",
                "email": getattr(user, 'email', '') if user else ""
            },
            "service": {
                "type": request.service_type,
                "description": request.description,
                "priority": request.urgency
            },
            "location": {
                "address": request.location,
                "zone": "Bonamoussadi" if "bonamoussadi" in request.location.lower() else "Douala",
                "coordinates": coordinates,
                "landmark": request.landmark_references
            },
            "provider": {
                "id": provider.id if provider else None,
                "name": provider.name if provider else None,
                "phone": provider.phone_number if provider else None,
                "rating": provider.rating if provider else None,
                "serviceType": provider.service_type if provider else None
            } if provider else None,
            "status": status_fr,
            "timeline": timeline,
            "dates": {
                "createdAt": request.created_at.isoformat() + "Z",
                "updatedAt": (request.updated_at or request.created_at).isoformat() + "Z",
                "scheduledAt": request.scheduled_at.isoformat() + "Z" if request.scheduled_at else None,
                "acceptedAt": request.accepted_at.isoformat() + "Z" if request.accepted_at else None,
                "completedAt": request.completed_at.isoformat() + "Z" if request.completed_at else None
            },
            "cost": {
                "estimated": request.estimated_cost or 0,
                "final": request.final_cost or 0,
                "commission": request.commission_amount or 0,
                "currency": "FCFA"
            }
        }
        
        logger.info(f"Retrieved request details: {request.id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des détails de la demande")


@router.post("/{request_id}/assign")
async def assign_request_to_provider(
    request_id: int,
    assign_data: AssignProviderRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/requests/{id}/assign - Assign request to provider
    Assign a service request to a specific provider
    """
    try:
        # Get request
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        # Check if request is already assigned
        if request.status in [RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED]:
            raise HTTPException(
                status_code=400, 
                detail="Cette demande est déjà assignée ou terminée"
            )
        
        # Get provider
        provider = db.query(Provider).filter(Provider.id == assign_data.providerId).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Prestataire non trouvé")
        
        # Check if provider is available
        if provider.status not in [ProviderStatus.ACTIVE, ProviderStatus.AVAILABLE]:
            raise HTTPException(
                status_code=400, 
                detail="Ce prestataire n'est pas disponible"
            )
        
        # Assign request
        request.provider_id = assign_data.providerId
        request.status = RequestStatus.ASSIGNED
        request.accepted_at = datetime.utcnow()
        request.updated_at = datetime.utcnow()
        
        # Update provider status
        provider.status = ProviderStatus.BUSY
        provider.updated_at = datetime.utcnow()
        
        db.commit()
        
        response = {
            "message": "Demande assignée avec succès",
            "request": {
                "id": request.id,
                "status": "assigné",
                "assignedAt": request.accepted_at.isoformat() + "Z"
            },
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "phone": provider.phone_number,
                "rating": provider.rating
            }
        }
        
        logger.info(f"Assigned request {request_id} to provider {provider.name}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'assignation de la demande")


@router.post("/{request_id}/cancel")
async def cancel_request(
    request_id: int,
    cancel_data: CancelRequestRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/requests/{id}/cancel - Cancel request
    Cancel a service request
    """
    try:
        # Get request
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        # Check if request can be cancelled
        if request.status == RequestStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail="Impossible d'annuler une demande terminée"
            )
        
        if request.status == RequestStatus.CANCELLED:
            raise HTTPException(
                status_code=400, 
                detail="Cette demande est déjà annulée"
            )
        
        # Cancel request
        request.status = RequestStatus.CANCELLED
        request.updated_at = datetime.utcnow()
        
        # Free up provider if assigned
        if request.provider_id:
            provider = db.query(Provider).filter(Provider.id == request.provider_id).first()
            if provider:
                provider.status = ProviderStatus.AVAILABLE
                provider.updated_at = datetime.utcnow()
        
        db.commit()
        
        response = {
            "message": "Demande annulée avec succès",
            "request": {
                "id": request.id,
                "status": "annulé",
                "cancelledAt": request.updated_at.isoformat() + "Z"
            },
            "cancellation": {
                "reason": cancel_data.reason,
                "refundAmount": cancel_data.refundAmount or 0,
                "currency": "FCFA"
            }
        }
        
        logger.info(f"Cancelled request {request_id}: {cancel_data.reason}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'annulation de la demande")


@router.put("/{request_id}/status")
async def update_request_status(
    request_id: int,
    status_data: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/requests/{id}/status - Update request status
    Update the status of a service request
    """
    try:
        # Get request
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        # Map status
        status_mapping = {
            "pending": RequestStatus.PENDING,
            "assigned": RequestStatus.ASSIGNED,
            "in_progress": RequestStatus.IN_PROGRESS,
            "completed": RequestStatus.COMPLETED,
            "cancelled": RequestStatus.CANCELLED
        }
        
        new_status = status_mapping.get(status_data.status)
        if not new_status:
            raise HTTPException(status_code=400, detail="Statut invalide")
        
        # Update status
        old_status = request.status
        request.status = new_status
        request.updated_at = datetime.utcnow()
        
        # Handle status-specific actions
        if new_status == RequestStatus.COMPLETED and old_status != RequestStatus.COMPLETED:
            request.completed_at = datetime.utcnow()
            
            # Free up provider
            if request.provider_id:
                provider = db.query(Provider).filter(Provider.id == request.provider_id).first()
                if provider:
                    provider.status = ProviderStatus.AVAILABLE
                    provider.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Map status to French
        status_mapping_fr = {
            "pending": "en attente",
            "assigned": "assigné",
            "in_progress": "en cours",
            "completed": "terminé",
            "cancelled": "annulé"
        }
        
        response = {
            "message": "Statut mis à jour avec succès",
            "request": {
                "id": request.id,
                "status": status_mapping_fr.get(status_data.status, status_data.status),
                "updatedAt": request.updated_at.isoformat() + "Z"
            }
        }
        
        logger.info(f"Updated request {request_id} status to {status_data.status}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating request status {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du statut")


@router.post("/{request_id}/invoice")
async def generate_invoice(
    request_id: int,
    invoice_data: GenerateInvoiceRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/requests/{id}/invoice - Generate invoice
    Generate an invoice for a completed service request
    """
    try:
        # Get request
        request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if not request:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        # Check if request is completed
        if request.status != RequestStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail="Seules les demandes terminées peuvent être facturées"
            )
        
        # Update final cost
        request.final_cost = invoice_data.finalCost
        request.commission_amount = invoice_data.finalCost * 0.15  # 15% commission
        request.updated_at = datetime.utcnow()
        
        # Generate invoice ID
        invoice_id = f"INV-{request_id}-{datetime.utcnow().strftime('%Y%m%d')}"
        
        # Get user and provider info
        user = db.query(User).filter(User.id == request.user_id).first()
        provider = None
        if request.provider_id:
            provider = db.query(Provider).filter(Provider.id == request.provider_id).first()
        
        db.commit()
        
        # Create invoice data
        invoice = {
            "invoiceId": invoice_id,
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "request": {
                "id": request.id,
                "serviceType": request.service_type,
                "description": invoice_data.description,
                "completedAt": request.completed_at.isoformat() + "Z" if request.completed_at else None
            },
            "client": {
                "name": user.name if user else "Client inconnu",
                "phone": user.phone_number if user else "",
                "email": getattr(user, 'email', '') if user else ""
            },
            "provider": {
                "name": provider.name if provider else "Prestataire inconnu",
                "phone": provider.phone_number if provider else "",
                "serviceType": provider.service_type if provider else ""
            } if provider else None,
            "cost": {
                "subtotal": invoice_data.finalCost,
                "commission": request.commission_amount,
                "total": invoice_data.finalCost,
                "currency": "FCFA"
            },
            "details": {
                "materials": invoice_data.materials,
                "laborHours": invoice_data.laborHours,
                "description": invoice_data.description
            }
        }
        
        logger.info(f"Generated invoice {invoice_id} for request {request_id}")
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating invoice for request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de la facture")