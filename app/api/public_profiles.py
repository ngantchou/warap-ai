"""
Public Provider Profile API

Handles public-facing provider profile pages and shareable links.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database_models import Provider, ProviderReview, ProviderPhoto, ProviderCertification, ProviderSpecialization, ProviderProfileView
from app.database import get_db
from app.services.provider_profile_service import ProviderProfileService
from app.config import get_settings
from loguru import logger
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Get settings
settings = get_settings()

@router.get("/provider/{profile_slug}", response_class=HTMLResponse)
async def get_public_provider_profile(
    profile_slug: str,
    request: Request,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get public provider profile page by slug
    
    Args:
        profile_slug: Unique SEO-friendly provider identifier
        request: FastAPI request object
        source: Source of the profile view (whatsapp, direct, search)
        db: Database session
    
    Returns:
        HTML response with provider profile page
    """
    try:
        # Find provider by slug
        provider = db.query(Provider).filter(
            Provider.public_profile_slug == profile_slug,
            Provider.is_profile_public == True,
            Provider.is_active == True
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider profile not found")
        
        # Track profile view
        await _track_profile_view(provider.id, request, source, db)
        
        # Get additional profile data
        reviews = db.query(ProviderReview).filter(
            ProviderReview.provider_id == provider.id,
            ProviderReview.is_verified == True
        ).order_by(desc(ProviderReview.created_at)).limit(5).all()
        
        photos = db.query(ProviderPhoto).filter(
            ProviderPhoto.provider_id == provider.id,
            ProviderPhoto.is_active == True
        ).order_by(ProviderPhoto.display_order).all()
        
        certifications = db.query(ProviderCertification).filter(
            ProviderCertification.provider_id == provider.id,
            ProviderCertification.is_verified == True
        ).all()
        
        specializations = db.query(ProviderSpecialization).filter(
            ProviderSpecialization.provider_id == provider.id,
            ProviderSpecialization.is_available == True
        ).all()
        
        # Calculate trust score and get trust explanation
        trust_score = provider.trust_score
        profile_service = ProviderProfileService(db)
        # Get the provider's main service type
        main_service = provider.services[0] if provider.services else "services généraux"
        trust_explanation = profile_service.generate_trust_explanation(provider.id, main_service)
        
        # Generate profile analytics
        profile_data = {
            "provider": provider,
            "reviews": reviews,
            "photos": photos,
            "certifications": certifications,
            "specializations": specializations,
            "trust_score": trust_score,
            "trust_explanation": trust_explanation,
            "total_reviews": len(reviews),
            "avg_rating": provider.rating,
            "whatsapp_url": f"https://wa.me/{provider.whatsapp_id}?text=Bonjour {provider.name}, j'ai vu votre profil sur Djobea AI",
            "request_service_url": f"https://wa.me/{settings.twilio_phone_number}?text=Je veux faire une demande avec {provider.name}",
            "profile_url": f"{settings.base_url}/provider/{profile_slug}"
        }
        
        return templates.TemplateResponse(
            "public/provider_profile.html",
            {
                "request": request,
                **profile_data
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading provider profile {profile_slug}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading provider profile")

@router.get("/api/provider/{profile_slug}/public")
async def get_provider_public_data(
    profile_slug: str,
    db: Session = Depends(get_db)
):
    """
    Get provider public data as JSON
    
    Args:
        profile_slug: Unique provider identifier
        db: Database session
    
    Returns:
        JSON response with provider public data
    """
    try:
        provider = db.query(Provider).filter(
            Provider.public_profile_slug == profile_slug,
            Provider.is_profile_public == True,
            Provider.is_active == True
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Get public reviews
        reviews = db.query(ProviderReview).filter(
            ProviderReview.provider_id == provider.id,
            ProviderReview.is_verified == True
        ).order_by(desc(ProviderReview.created_at)).limit(10).all()
        
        # Get work photos
        photos = db.query(ProviderPhoto).filter(
            ProviderPhoto.provider_id == provider.id,
            ProviderPhoto.is_active == True
        ).order_by(ProviderPhoto.display_order).all()
        
        return {
            "id": provider.id,
            "name": provider.name,
            "slug": provider.public_profile_slug,
            "services": provider.services,
            "coverage_areas": provider.coverage_areas,
            "rating": provider.rating,
            "total_jobs": provider.total_jobs,
            "years_experience": provider.years_experience,
            "bio": provider.bio,
            "profile_photo_url": provider.profile_photo_url,
            "trust_score": provider.trust_score,
            "verification_status": provider.verification_status,
            "insurance_verified": provider.insurance_verified,
            "id_verified": provider.id_verified,
            "response_time_avg": provider.response_time_avg,
            "acceptance_rate": provider.acceptance_rate,
            "completion_rate": provider.completion_rate,
            "reviews": [
                {
                    "rating": review.rating,
                    "comment": review.comment,
                    "customer_name": review.customer_name,
                    "created_at": review.created_at.isoformat(),
                    "service_type": review.service_type
                }
                for review in reviews
            ],
            "photos": [
                {
                    "url": photo.photo_url,
                    "caption": photo.caption,
                    "photo_type": photo.photo_type
                }
                for photo in photos
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting provider public data {profile_slug}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading provider data")

@router.post("/api/provider/{profile_slug}/view")
async def track_profile_view(
    profile_slug: str,
    request: Request,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Track a profile view for analytics
    
    Args:
        profile_slug: Provider identifier
        request: FastAPI request object
        source: Source of the view
        db: Database session
    
    Returns:
        Success confirmation
    """
    try:
        provider = db.query(Provider).filter(
            Provider.public_profile_slug == profile_slug
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        await _track_profile_view(provider.id, request, source, db)
        
        return {"success": True, "message": "Profile view tracked"}
        
    except Exception as e:
        logger.error(f"Error tracking profile view {profile_slug}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error tracking view")

@router.get("/provider/{profile_slug}/qr")
async def generate_profile_qr(
    profile_slug: str,
    db: Session = Depends(get_db)
):
    """
    Generate QR code for provider profile
    
    Args:
        profile_slug: Provider identifier
        db: Database session
    
    Returns:
        QR code image or redirect URL
    """
    try:
        provider = db.query(Provider).filter(
            Provider.public_profile_slug == profile_slug,
            Provider.is_profile_public == True
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        profile_url = f"{settings.base_url}/provider/{profile_slug}"
        
        # For now, return QR code generation URL
        # In production, this would generate an actual QR code image
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={profile_url}"
        
        return {
            "qr_url": qr_url,
            "profile_url": profile_url,
            "provider_name": provider.name
        }
        
    except Exception as e:
        logger.error(f"Error generating QR code for {profile_slug}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating QR code")

async def _track_profile_view(
    provider_id: int,
    request: Request,
    source: Optional[str],
    db: Session
):
    """
    Track a profile view in the database
    
    Args:
        provider_id: Provider ID
        request: FastAPI request object
        source: View source
        db: Database session
    """
    try:
        # Extract request information
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else "unknown"
        referrer = request.headers.get("referer", "")
        
        # Generate session ID for tracking
        session_id = str(uuid.uuid4())
        
        # Create profile view record
        profile_view = ProviderProfileView(
            provider_id=provider_id,
            source=source or "direct",
            user_agent=user_agent,
            ip_address=client_ip,
            referrer=referrer,
            session_id=session_id
        )
        
        db.add(profile_view)
        
        # Update provider view count
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if provider:
            provider.profile_views += 1
        
        db.commit()
        
        logger.info(f"Tracked profile view for provider {provider_id} from {source or 'direct'}")
        
    except Exception as e:
        logger.error(f"Error tracking profile view: {str(e)}")
        db.rollback()