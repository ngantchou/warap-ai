"""
Providers API endpoints for Djobea AI
Implements comprehensive provider management functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.models.database_models import (
    Provider, ServiceRequest, RequestStatus
)
from app.models.dynamic_services import Service, Zone
from app.api.auth import get_current_admin_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/providers", tags=["Providers"])

# Pydantic models
class CreateProviderRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r'^\+237[0-9]{9}$')
    serviceType: str = Field(..., min_length=2, max_length=50)
    coverageZone: str = Field(..., min_length=2, max_length=100)
    specialties: Optional[List[str]] = []
    yearsExperience: Optional[int] = Field(default=0, ge=0, le=50)
    bio: Optional[str] = Field(default="", max_length=500)
    certifications: Optional[List[str]] = []

class UpdateProviderRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+237[0-9]{9}$')
    serviceType: Optional[str] = Field(None, min_length=2, max_length=50)
    coverageZone: Optional[str] = Field(None, min_length=2, max_length=100)
    specialties: Optional[List[str]] = None
    yearsExperience: Optional[int] = Field(None, ge=0, le=50)
    bio: Optional[str] = Field(None, max_length=500)
    certifications: Optional[List[str]] = None
    status: Optional[str] = None

class ContactProviderRequest(BaseModel):
    message: str = Field(..., min_length=10, max_length=500)
    urgency: str = Field(default="normal", pattern="^(urgent|normal|low)$")

@router.get("/")
async def get_providers(
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    minRating: Optional[float] = Query(None, ge=0, le=5),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/providers - Get providers list
    Retrieve paginated list of service providers with filtering
    """
    try:
        logger.info(f"Fetching providers - Page {page}, Limit {limit}")
        
        # Build base query
        query = db.query(Provider)
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    Provider.name.ilike(f"%{search}%"),
                    Provider.service_type.ilike(f"%{search}%"),
                    Provider.coverage_zone.ilike(f"%{search}%")
                )
            )
        
        if status:
            status_mapping = {
                "active": ProviderStatus.ACTIVE,
                "inactive": ProviderStatus.INACTIVE,
                "new": ProviderStatus.NEW,
                "available": ProviderStatus.AVAILABLE,
                "busy": ProviderStatus.BUSY
            }
            if status in status_mapping:
                query = query.filter(Provider.status == status_mapping[status])
        
        if specialty:
            query = query.filter(Provider.service_type.ilike(f"%{specialty}%"))
        
        if zone:
            query = query.filter(Provider.coverage_zone.ilike(f"%{zone}%"))
        
        if minRating is not None:
            query = query.filter(Provider.rating >= minRating)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        providers = query.offset(offset).limit(limit).all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit
        has_next_page = page < total_pages
        has_prev_page = page > 1
        
        # Format providers
        formatted_providers = []
        for provider in providers:
            # Get provider statistics
            total_requests = db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider.id
            ).count()
            
            completed_requests = db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider.id,
                ServiceRequest.status == RequestStatus.COMPLETED
            ).count()
            
            success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Get recent activity
            last_activity = db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider.id
            ).order_by(desc(ServiceRequest.created_at)).first()
            
            formatted_provider = {
                "id": provider.id,
                "name": provider.name,
                "phone": provider.phone_number,
                "serviceType": provider.service_type,
                "coverageZone": provider.coverage_zone,
                "status": "active" if provider.is_active else "inactive",
                "availability": "available" if provider.is_available else "busy",
                "rating": provider.rating or 0,
                "yearsExperience": provider.years_experience or 0,
                "bio": provider.bio or "",
                "specialties": provider.specialties or [],
                "certifications": provider.certifications or [],
                "verificationStatus": provider.verification_status or "unverified",
                "trustScore": provider.trust_score or 0,
                "stats": {
                    "totalRequests": total_requests,
                    "completedRequests": completed_requests,
                    "successRate": round(success_rate, 2),
                    "lastActivity": last_activity.created_at.isoformat() + "Z" if last_activity else None
                },
                "joinedAt": provider.created_at.isoformat() + "Z" if provider.created_at else None,
                "updatedAt": provider.updated_at.isoformat() + "Z" if provider.updated_at else None
            }
            
            formatted_providers.append(formatted_provider)
        
        response = {
            "providers": formatted_providers,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasNextPage": has_next_page,
                "hasPrevPage": has_prev_page
            }
        }
        
        logger.info(f"Retrieved {len(formatted_providers)} providers (page {page}/{total_pages})")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching providers: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des prestataires")


@router.post("/")
async def create_provider(
    provider_data: CreateProviderRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/providers - Create new provider
    Add a new service provider to the system
    """
    try:
        logger.info(f"Creating new provider: {provider_data.name}")
        
        # Check if provider already exists
        existing_provider = db.query(Provider).filter(
            Provider.phone_number == provider_data.phone
        ).first()
        
        if existing_provider:
            raise HTTPException(
                status_code=400, 
                detail="Un prestataire avec ce numéro de téléphone existe déjà"
            )
        
        # Create new provider
        new_provider = Provider(
            name=provider_data.name,
            phone_number=provider_data.phone,
            service_type=provider_data.serviceType,
            coverage_zone=provider_data.coverageZone,
            specialties=provider_data.specialties,
            years_experience=provider_data.yearsExperience,
            bio=provider_data.bio,
            certifications=provider_data.certifications,
            status=ProviderStatus.NEW,
            rating=0.0,
            trust_score=0.0,
            verification_status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_provider)
        db.commit()
        db.refresh(new_provider)
        
        # Format response
        response = {
            "id": new_provider.id,
            "name": new_provider.name,
            "phone": new_provider.phone_number,
            "serviceType": new_provider.service_type,
            "coverageZone": new_provider.coverage_zone,
            "status": new_provider.status.value,
            "rating": new_provider.rating,
            "yearsExperience": new_provider.years_experience,
            "bio": new_provider.bio,
            "specialties": new_provider.specialties,
            "certifications": new_provider.certifications,
            "verificationStatus": new_provider.verification_status,
            "trustScore": new_provider.trust_score,
            "joinedAt": new_provider.created_at.isoformat() + "Z",
            "updatedAt": new_provider.updated_at.isoformat() + "Z"
        }
        
        logger.info(f"Created provider: {new_provider.name} (ID: {new_provider.id})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating provider: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création du prestataire")


@router.get("/{provider_id}")
async def get_provider_by_id(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/providers/{id} - Get provider by ID
    Retrieve detailed information about a specific provider
    """
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Prestataire non trouvé")
        
        # Get provider statistics
        total_requests = db.query(ServiceRequest).filter(
            ServiceRequest.provider_id == provider.id
        ).count()
        
        completed_requests = db.query(ServiceRequest).filter(
            ServiceRequest.provider_id == provider.id,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).count()
        
        cancelled_requests = db.query(ServiceRequest).filter(
            ServiceRequest.provider_id == provider.id,
            ServiceRequest.status == RequestStatus.CANCELLED
        ).count()
        
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Get recent requests
        recent_requests = db.query(ServiceRequest).filter(
            ServiceRequest.provider_id == provider.id
        ).order_by(desc(ServiceRequest.created_at)).limit(5).all()
        
        formatted_requests = []
        for req in recent_requests:
            formatted_requests.append({
                "id": req.id,
                "serviceType": req.service_type,
                "location": req.location,
                "status": req.status.value if req.status else "pending",
                "createdAt": req.created_at.isoformat() + "Z",
                "completedAt": req.completed_at.isoformat() + "Z" if req.completed_at else None,
                "cost": req.final_cost or req.estimated_cost or 0
            })
        
        # Calculate total revenue
        total_revenue = db.query(func.sum(ServiceRequest.final_cost)).filter(
            ServiceRequest.provider_id == provider.id,
            ServiceRequest.status == RequestStatus.COMPLETED
        ).scalar() or 0
        
        response = {
            "id": provider.id,
            "name": provider.name,
            "phone": provider.phone_number,
            "serviceType": provider.service_type,
            "coverageZone": provider.coverage_zone,
            "status": provider.status.value if provider.status else "inactive",
            "rating": provider.rating or 0,
            "yearsExperience": provider.years_experience or 0,
            "bio": provider.bio or "",
            "specialties": provider.specialties or [],
            "certifications": provider.certifications or [],
            "verificationStatus": provider.verification_status or "unverified",
            "trustScore": provider.trust_score or 0,
            "stats": {
                "totalRequests": total_requests,
                "completedRequests": completed_requests,
                "cancelledRequests": cancelled_requests,
                "successRate": round(success_rate, 2),
                "totalRevenue": round(total_revenue, 2),
                "avgOrderValue": round(total_revenue / completed_requests, 2) if completed_requests > 0 else 0,
                "currency": "FCFA"
            },
            "recentRequests": formatted_requests,
            "joinedAt": provider.created_at.isoformat() + "Z" if provider.created_at else None,
            "updatedAt": provider.updated_at.isoformat() + "Z" if provider.updated_at else None
        }
        
        logger.info(f"Retrieved provider details: {provider.name} (ID: {provider.id})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving provider {provider_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du prestataire")


@router.put("/{provider_id}")
async def update_provider(
    provider_id: int,
    provider_data: UpdateProviderRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/providers/{id} - Update provider
    Update provider information
    """
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Prestataire non trouvé")
        
        # Update fields if provided
        if provider_data.name is not None:
            provider.name = provider_data.name
        if provider_data.phone is not None:
            # Check if phone number is already used by another provider
            existing_provider = db.query(Provider).filter(
                Provider.phone_number == provider_data.phone,
                Provider.id != provider_id
            ).first()
            if existing_provider:
                raise HTTPException(
                    status_code=400, 
                    detail="Ce numéro de téléphone est déjà utilisé par un autre prestataire"
                )
            provider.phone_number = provider_data.phone
        if provider_data.serviceType is not None:
            provider.service_type = provider_data.serviceType
        if provider_data.coverageZone is not None:
            provider.coverage_zone = provider_data.coverageZone
        if provider_data.specialties is not None:
            provider.specialties = provider_data.specialties
        if provider_data.yearsExperience is not None:
            provider.years_experience = provider_data.yearsExperience
        if provider_data.bio is not None:
            provider.bio = provider_data.bio
        if provider_data.certifications is not None:
            provider.certifications = provider_data.certifications
        if provider_data.status is not None:
            status_mapping = {
                "active": ProviderStatus.ACTIVE,
                "inactive": ProviderStatus.INACTIVE,
                "new": ProviderStatus.NEW,
                "available": ProviderStatus.AVAILABLE,
                "busy": ProviderStatus.BUSY
            }
            if provider_data.status in status_mapping:
                provider.status = status_mapping[provider_data.status]
        
        provider.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(provider)
        
        # Format response
        response = {
            "id": provider.id,
            "name": provider.name,
            "phone": provider.phone_number,
            "serviceType": provider.service_type,
            "coverageZone": provider.coverage_zone,
            "status": provider.status.value if provider.status else "inactive",
            "rating": provider.rating or 0,
            "yearsExperience": provider.years_experience or 0,
            "bio": provider.bio or "",
            "specialties": provider.specialties or [],
            "certifications": provider.certifications or [],
            "verificationStatus": provider.verification_status or "unverified",
            "trustScore": provider.trust_score or 0,
            "joinedAt": provider.created_at.isoformat() + "Z" if provider.created_at else None,
            "updatedAt": provider.updated_at.isoformat() + "Z"
        }
        
        logger.info(f"Updated provider: {provider.name} (ID: {provider.id})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating provider {provider_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du prestataire")


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    DELETE /api/providers/{id} - Delete provider
    Remove a provider from the system
    """
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Prestataire non trouvé")
        
        # Check if provider has active requests
        active_requests = db.query(ServiceRequest).filter(
            ServiceRequest.provider_id == provider_id,
            ServiceRequest.status.in_([RequestStatus.PENDING, RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS])
        ).count()
        
        if active_requests > 0:
            raise HTTPException(
                status_code=400, 
                detail="Impossible de supprimer un prestataire avec des demandes actives"
            )
        
        # Soft delete by setting status to inactive
        provider.status = ProviderStatus.INACTIVE
        provider.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Deleted provider: {provider.name} (ID: {provider.id})")
        return {"message": "Prestataire supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting provider {provider_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du prestataire")


@router.post("/{provider_id}/contact")
async def contact_provider(
    provider_id: int,
    contact_data: ContactProviderRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/providers/{id}/contact - Contact provider
    Send a message to a provider
    """
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Prestataire non trouvé")
        
        # Here you would typically send the message via WhatsApp/SMS
        # For now, we'll just log it and return success
        
        logger.info(f"Contact request for provider {provider.name}: {contact_data.message}")
        
        response = {
            "message": "Message envoyé avec succès",
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "phone": provider.phone_number
            },
            "sentAt": datetime.utcnow().isoformat() + "Z"
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error contacting provider {provider_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'envoi du message")


@router.put("/{provider_id}/status")
async def update_provider_status(
    provider_id: int,
    status_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/providers/{id}/status - Update provider status
    Update the status of a provider
    """
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Prestataire non trouvé")
        
        new_status = status_data.get("status")
        if not new_status:
            raise HTTPException(status_code=400, detail="Statut manquant")
        
        # Map string status to boolean fields
        if new_status == "active":
            provider.is_active = True
        elif new_status == "inactive":
            provider.is_active = False
            provider.is_available = False  # Inactive providers are not available
        elif new_status == "available":
            provider.is_available = True
        elif new_status == "busy":
            provider.is_available = False
        else:
            raise HTTPException(status_code=400, detail="Statut invalide")
        provider.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(provider)
        
        response = {
            "id": provider.id,
            "name": provider.name,
            "status": "active" if provider.is_active else "inactive",
            "availability": "available" if provider.is_available else "busy",
            "updatedAt": provider.updated_at.isoformat() + "Z"
        }
        
        logger.info(f"Updated status for provider {provider.name}: {new_status}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating provider status {provider_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du statut")


@router.get("/available")
async def get_available_providers(
    serviceType: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/providers/available - Get available providers
    Retrieve list of available providers for immediate assignment
    """
    try:
        query = db.query(Provider).filter(
            Provider.status.in_([ProviderStatus.ACTIVE, ProviderStatus.AVAILABLE])
        )
        
        if serviceType:
            query = query.filter(Provider.service_type.ilike(f"%{serviceType}%"))
        
        if zone:
            query = query.filter(Provider.coverage_zone.ilike(f"%{zone}%"))
        
        providers = query.order_by(desc(Provider.rating)).all()
        
        available_providers = []
        for provider in providers:
            available_providers.append({
                "id": provider.id,
                "name": provider.name,
                "phone": provider.phone_number,
                "serviceType": provider.service_type,
                "coverageZone": provider.coverage_zone,
                "rating": provider.rating or 0,
                "trustScore": provider.trust_score or 0,
                "status": provider.status.value,
                "yearsExperience": provider.years_experience or 0
            })
        
        response = {
            "availableProviders": available_providers,
            "count": len(available_providers),
            "filters": {
                "serviceType": serviceType,
                "zone": zone
            }
        }
        
        logger.info(f"Retrieved {len(available_providers)} available providers")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving available providers: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des prestataires disponibles")


@router.get("/stats")
async def get_provider_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/providers/stats - Get provider statistics
    Retrieve overall provider statistics
    """
    try:
        # Basic counts
        total_providers = db.query(Provider).count()
        active_providers = db.query(Provider).filter(
            Provider.status == ProviderStatus.ACTIVE
        ).count()
        available_providers = db.query(Provider).filter(
            Provider.status == ProviderStatus.AVAILABLE
        ).count()
        new_providers = db.query(Provider).filter(
            Provider.status == ProviderStatus.NEW
        ).count()
        
        # Distribution by service type
        service_distribution = []
        services = db.query(
            Provider.service_type,
            func.count(Provider.id).label('count')
        ).group_by(Provider.service_type).all()
        
        for service_type, count in services:
            service_distribution.append({
                "serviceType": service_type,
                "count": count,
                "percentage": round((count / total_providers * 100) if total_providers > 0 else 0, 2)
            })
        
        # Distribution by zone
        zone_distribution = []
        zones = db.query(
            Provider.coverage_zone,
            func.count(Provider.id).label('count')
        ).group_by(Provider.coverage_zone).all()
        
        for zone, count in zones:
            zone_distribution.append({
                "zone": zone,
                "count": count,
                "percentage": round((count / total_providers * 100) if total_providers > 0 else 0, 2)
            })
        
        # Average ratings
        avg_rating = db.query(func.avg(Provider.rating)).scalar() or 0
        avg_trust_score = db.query(func.avg(Provider.trust_score)).scalar() or 0
        
        response = {
            "overview": {
                "totalProviders": total_providers,
                "activeProviders": active_providers,
                "availableProviders": available_providers,
                "newProviders": new_providers,
                "utilizationRate": round((active_providers / total_providers * 100) if total_providers > 0 else 0, 2)
            },
            "quality": {
                "avgRating": round(avg_rating, 2),
                "avgTrustScore": round(avg_trust_score, 2)
            },
            "distribution": {
                "byService": service_distribution,
                "byZone": zone_distribution
            }
        }
        
        logger.info("Provider statistics retrieved successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving provider stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques des prestataires")