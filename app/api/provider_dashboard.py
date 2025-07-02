"""
Provider Dashboard API Endpoints for Djobea AI
Complete REST API for provider authentication and dashboard functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.services.provider_dashboard_service import provider_auth_service, provider_dashboard_service
from app.models.database_models import Provider
from app.models.provider_models import ProviderSession
from loguru import logger

# Security
security = HTTPBearer()
router = APIRouter(prefix="/provider/dashboard", tags=["Provider Dashboard"])

# Request/Response Models
class OTPRequest(BaseModel):
    phone_number: str = Field(..., description="Provider's phone number")

class OTPVerification(BaseModel):
    session_token: str = Field(..., description="Temporary session token")
    otp_code: str = Field(..., description="6-digit OTP code")
    otp_hash: str = Field(..., description="OTP verification hash")

class DashboardResponse(BaseModel):
    success: bool
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class RequestsListResponse(BaseModel):
    success: bool
    requests: Optional[List[Dict[str, Any]]] = None
    pagination: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ChartDataResponse(BaseModel):
    success: bool
    revenue_chart: Optional[List[Dict[str, Any]]] = None
    service_breakdown: Optional[Dict[str, str]] = None
    activity_heatmap: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class RequestActionRequest(BaseModel):
    action: str = Field(..., description="Action to perform: accept, decline, call")
    reason: Optional[str] = Field(None, description="Reason for decline (optional)")
    notes: Optional[str] = Field(None, description="Additional notes")

# Helper function to get authenticated provider
async def get_current_provider(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Provider:
    """
    Verify provider authentication and return provider object
    
    Args:
        credentials: HTTP Bearer token
        db: Database session
        
    Returns:
        Authenticated Provider object
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    provider = provider_auth_service.verify_session(db, token)
    
    if not provider:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token"
        )
    
    return provider

# Authentication Endpoints
@router.post("/auth/send-otp")
async def send_otp(
    request: OTPRequest,
    db: Session = Depends(get_db)
):
    """
    Send OTP to provider's WhatsApp for authentication
    
    Args:
        request: OTP request with phone number
        db: Database session
        
    Returns:
        Response with session token for OTP verification
    """
    try:
        result = await provider_auth_service.send_otp(db, request.phone_number)
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "OTP sent successfully",
            "session_token": result["session_token"],
            "otp_hash": result["otp_hash"],
            "expires_in": result["expires_in"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_otp endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP"
        )

@router.post("/auth/verify-otp")
async def verify_otp(
    request: OTPVerification,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and create authenticated session
    
    Args:
        request: OTP verification data
        db: Database session
        
    Returns:
        Authentication token and provider info
    """
    try:
        result = await provider_auth_service.verify_otp(
            db, 
            request.session_token, 
            request.otp_code, 
            request.otp_hash
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "Authentication successful",
            "auth_token": result["auth_token"],
            "provider": {
                "id": result["provider_id"],
                "name": result["provider_name"]
            },
            "expires_in": result["expires_in"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_otp endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="OTP verification failed"
        )

@router.post("/auth/refresh-token")
async def refresh_token(
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Refresh authentication token
    
    Args:
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        New authentication token
    """
    try:
        # In practice, you'd generate a new token here
        # For now, we'll return success with current provider info
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "provider": {
                "id": current_provider.id,
                "name": current_provider.name,
                "rating": current_provider.rating,
                "trust_score": current_provider.trust_score
            }
        }
        
    except Exception as e:
        logger.error(f"Error in refresh_token endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Token refresh failed"
        )

@router.delete("/auth/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout provider and invalidate session
    
    Args:
        credentials: HTTP Bearer token
        db: Database session
        
    Returns:
        Logout confirmation
    """
    try:
        token = credentials.credentials
        success = provider_auth_service.logout(db, token)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Logout failed"
            )
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in logout endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Logout failed"
        )

# Dashboard Endpoints
@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats(
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard statistics for provider
    
    Args:
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        Dashboard statistics and key metrics
    """
    try:
        result = provider_dashboard_service.get_dashboard_stats(db, current_provider)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_dashboard_stats endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load dashboard stats"
        )

@router.get("/chart-data/{period}", response_model=ChartDataResponse)
async def get_chart_data(
    period: str,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Get chart data for dashboard visualizations
    
    Args:
        period: Data period (week, month, year)
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        Chart data for revenue, service breakdown, and activity
    """
    try:
        if period not in ["week", "month", "year"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid period. Must be: week, month, or year"
            )
        
        result = provider_dashboard_service.get_chart_data(db, current_provider, period)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_chart_data endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load chart data"
        )

@router.get("/notifications")
async def get_notifications(
    limit: int = Query(10, description="Number of notifications to retrieve"),
    offset: int = Query(0, description="Offset for pagination"),
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Get provider notifications
    
    Args:
        limit: Number of notifications per page
        offset: Pagination offset
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        List of provider notifications
    """
    try:
        from app.models.provider_models import ProviderNotification
        
        # Get notifications for provider
        notifications = (
            db.query(ProviderNotification)
            .filter(ProviderNotification.provider_id == current_provider.id)
            .order_by(ProviderNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        # Format notifications
        formatted_notifications = []
        for notification in notifications:
            formatted_notifications.append({
                "id": str(notification.id),
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "is_read": notification.is_read,
                "is_urgent": notification.is_urgent,
                "created_at": notification.created_at.isoformat(),
                "service_request_id": notification.service_request_id
            })
        
        return {
            "success": True,
            "notifications": formatted_notifications,
            "unread_count": len([n for n in notifications if not n.is_read])
        }
        
    except Exception as e:
        logger.error(f"Error in get_notifications endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load notifications"
        )

# Requests Management Endpoints
@router.get("/requests", response_model=RequestsListResponse)
async def get_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, description="Number of requests per page"),
    offset: int = Query(0, description="Offset for pagination"),
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of requests for provider
    
    Args:
        status: Filter by request status (optional)
        limit: Number of requests per page
        offset: Pagination offset
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        Paginated list of service requests
    """
    try:
        result = provider_dashboard_service.get_requests_list(
            db, current_provider, status, limit, offset
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_requests endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load requests"
        )

@router.get("/requests/{request_id}")
async def get_request_details(
    request_id: int,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific request
    
    Args:
        request_id: Service request ID
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        Detailed request information
    """
    try:
        from app.models.database_models import ServiceRequest, User
        
        # Get request
        request = db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id,
            ServiceRequest.provider_id == current_provider.id
        ).first()
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail="Request not found"
            )
        
        # Get user info
        user = db.query(User).filter(User.id == request.user_id).first()
        
        # Format response
        return {
            "success": True,
            "request": {
                "id": request.id,
                "service_type": request.service_type,
                "location": request.location,
                "description": request.description,
                "urgency": request.urgency,
                "status": request.status,
                "created_at": request.created_at.isoformat(),
                "final_price": float(request.final_price) if request.final_price else None,
                "user": {
                    "name": user.name if user else "Unknown",
                    "phone": user.phone_number if user else "",
                    "rating": getattr(user, 'rating', 0)
                },
                "timeline": [
                    {
                        "status": "PENDING",
                        "timestamp": request.created_at.isoformat(),
                        "description": "Demande créée"
                    }
                    # Add more timeline events as needed
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_request_details endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load request details"
        )

@router.put("/requests/{request_id}/accept")
async def accept_request(
    request_id: int,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Accept a service request
    
    Args:
        request_id: Service request ID
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        Acceptance confirmation
    """
    try:
        from app.models.database_models import ServiceRequest
        
        # Get request
        request = db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id,
            ServiceRequest.provider_id == current_provider.id,
            ServiceRequest.status.in_(['PENDING', 'PROVIDER_NOTIFIED'])
        ).first()
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail="Request not found or cannot be accepted"
            )
        
        # Update status
        request.status = 'ASSIGNED'
        db.commit()
        
        # In a real implementation, you'd notify the client here
        logger.info(f"Provider {current_provider.id} accepted request {request_id}")
        
        return {
            "success": True,
            "message": "Request accepted successfully",
            "request_id": request_id,
            "new_status": "ASSIGNED"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in accept_request endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to accept request"
        )

@router.put("/requests/{request_id}/decline")
async def decline_request(
    request_id: int,
    action_request: RequestActionRequest,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Decline a service request
    
    Args:
        request_id: Service request ID
        action_request: Decline reason and notes
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        Decline confirmation
    """
    try:
        from app.models.database_models import ServiceRequest
        
        # Get request
        request = db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id,
            ServiceRequest.provider_id == current_provider.id,
            ServiceRequest.status.in_(['PENDING', 'PROVIDER_NOTIFIED'])
        ).first()
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail="Request not found or cannot be declined"
            )
        
        # Update status (this would trigger finding another provider)
        request.status = 'CANCELLED'
        request.cancellation_reason = action_request.reason or "Declined by provider"
        db.commit()
        
        logger.info(f"Provider {current_provider.id} declined request {request_id}: {action_request.reason}")
        
        return {
            "success": True,
            "message": "Request declined successfully",
            "request_id": request_id,
            "new_status": "CANCELLED"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in decline_request endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to decline request"
        )

@router.put("/requests/{request_id}/update-status")
async def update_request_status(
    request_id: int,
    status_data: Dict[str, Any] = Body(...),
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Update request status during service delivery
    
    Args:
        request_id: Service request ID
        status_data: New status and optional details
        current_provider: Authenticated provider
        db: Database session
        
    Returns:
        Status update confirmation
    """
    try:
        from app.models.database_models import ServiceRequest
        
        new_status = status_data.get("status")
        notes = status_data.get("notes")
        final_price = status_data.get("final_price")
        
        # Validate status
        valid_statuses = ['ASSIGNED', 'IN_PROGRESS', 'COMPLETED']
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        # Get request
        request = db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id,
            ServiceRequest.provider_id == current_provider.id
        ).first()
        
        if not request:
            raise HTTPException(
                status_code=404,
                detail="Request not found"
            )
        
        # Update request
        request.status = new_status
        if notes:
            request.provider_notes = notes
        if final_price:
            request.final_price = float(final_price)
        
        db.commit()
        
        logger.info(f"Provider {current_provider.id} updated request {request_id} to {new_status}")
        
        return {
            "success": True,
            "message": f"Status updated to {new_status}",
            "request_id": request_id,
            "new_status": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_request_status endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update request status"
        )

# Provider Profile Endpoints
@router.get("/profile")
async def get_provider_profile(
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """Get complete provider profile information"""
    try:
        result = provider_dashboard_service.get_provider_profile(db, current_provider.id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Provider profile not found")
            )
        
        return result["profile"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_provider_profile endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load provider profile"
        )

@router.put("/profile")
async def update_provider_profile(
    profile_data: dict,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """Update provider profile information"""
    try:
        result = provider_dashboard_service.update_provider_profile(
            db, current_provider.id, profile_data
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to update profile")
            )
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "profile": result["profile"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_provider_profile endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update provider profile"
        )