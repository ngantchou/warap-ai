from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.provider_service import ProviderService
from app.services.request_service import RequestService
from app.models.database_models import Provider, ServiceRequest, User, Conversation
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard with overview statistics"""
    
    try:
        request_service = RequestService(db)
        provider_service = ProviderService(db)
        
        # Get statistics
        request_stats = request_service.get_request_statistics()
        
        # Get recent requests
        recent_requests = db.query(ServiceRequest).order_by(
            ServiceRequest.created_at.desc()
        ).limit(10).all()
        
        # Get provider count
        total_providers = db.query(Provider).count()
        active_providers = db.query(Provider).filter(Provider.is_active == True).count()
        
        # Get pending requests
        pending_requests = request_service.get_pending_requests()
        
        context = {
            "request": request,
            "stats": {
                **request_stats,
                "total_providers": total_providers,
                "active_providers": active_providers,
                "pending_requests_count": len(pending_requests)
            },
            "recent_requests": recent_requests,
            "pending_requests": pending_requests
        }
        
        return templates.TemplateResponse("admin/dashboard.html", context)
        
    except Exception as e:
        logger.error(f"Error in admin dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/providers", response_class=HTMLResponse)
async def admin_providers(request: Request, db: Session = Depends(get_db)):
    """Admin providers management page"""
    
    try:
        provider_service = ProviderService(db)
        providers = provider_service.get_all_providers()
        
        # Get statistics for each provider
        provider_stats = {}
        for provider in providers:
            provider_stats[provider.id] = provider_service.get_provider_stats(provider.id)
        
        context = {
            "request": request,
            "providers": providers,
            "provider_stats": provider_stats
        }
        
        return templates.TemplateResponse("admin/providers.html", context)
        
    except Exception as e:
        logger.error(f"Error in admin providers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/providers/add")
async def add_provider(
    request: Request,
    name: str = Form(...),
    whatsapp_id: str = Form(...),
    phone_number: str = Form(...),
    services: str = Form(...),
    coverage_areas: str = Form(...),
    db: Session = Depends(get_db)
):
    """Add a new provider"""
    
    try:
        provider_service = ProviderService(db)
        
        # Parse services and coverage areas
        services_list = [s.strip() for s in services.split(",")]
        coverage_list = [c.strip() for c in coverage_areas.split(",")]
        
        provider_data = {
            "name": name,
            "whatsapp_id": whatsapp_id,
            "phone_number": phone_number,
            "services": services_list,
            "coverage_areas": coverage_list
        }
        
        provider = provider_service.add_provider(provider_data)
        
        if provider:
            logger.info(f"Added new provider via admin: {provider.name}")
            return RedirectResponse(url="/admin/providers", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Failed to add provider")
            
    except Exception as e:
        logger.error(f"Error adding provider: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/providers/{provider_id}/toggle-status")
async def toggle_provider_status(provider_id: int, db: Session = Depends(get_db)):
    """Toggle provider active/inactive status"""
    
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        provider.is_active = not provider.is_active
        if not provider.is_active:
            provider.is_available = False
        
        db.commit()
        
        logger.info(f"Toggled provider {provider_id} status to {'active' if provider.is_active else 'inactive'}")
        return RedirectResponse(url="/admin/providers", status_code=303)
        
    except Exception as e:
        logger.error(f"Error toggling provider status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/providers/{provider_id}/toggle-availability")
async def toggle_provider_availability(provider_id: int, db: Session = Depends(get_db)):
    """Toggle provider availability"""
    
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        if provider.is_active:
            provider.is_available = not provider.is_available
            db.commit()
            
            logger.info(f"Toggled provider {provider_id} availability to {'available' if provider.is_available else 'unavailable'}")
        
        return RedirectResponse(url="/admin/providers", status_code=303)
        
    except Exception as e:
        logger.error(f"Error toggling provider availability: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/requests", response_class=HTMLResponse)
async def admin_requests(request: Request, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Admin requests management page"""
    
    try:
        query = db.query(ServiceRequest)
        
        if status:
            query = query.filter(ServiceRequest.status == status)
        
        requests = query.order_by(ServiceRequest.created_at.desc()).limit(50).all()
        
        context = {
            "request": request,
            "requests": requests,
            "current_status": status
        }
        
        return templates.TemplateResponse("admin/requests.html", context)
        
    except Exception as e:
        logger.error(f"Error in admin requests: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/requests/{request_id}/cancel")
async def cancel_request(request_id: int, db: Session = Depends(get_db)):
    """Cancel a service request"""
    
    try:
        request_service = RequestService(db)
        
        if request_service.cancel_request(request_id):
            logger.info(f"Admin cancelled request {request_id}")
            return RedirectResponse(url="/admin/requests", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel request")
            
    except Exception as e:
        logger.error(f"Error cancelling request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/logs", response_class=HTMLResponse)
async def admin_logs(request: Request, db: Session = Depends(get_db)):
    """Admin logs page"""
    
    try:
        # Get recent conversations for debugging
        conversations = db.query(Conversation).order_by(
            Conversation.created_at.desc()
        ).limit(100).all()
        
        context = {
            "request": request,
            "conversations": conversations
        }
        
        return templates.TemplateResponse("admin/logs.html", context)
        
    except Exception as e:
        logger.error(f"Error in admin logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
