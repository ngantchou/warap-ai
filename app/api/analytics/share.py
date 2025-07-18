"""
Share Analytics Report API for Djobea AI
Handles sharing analytics reports with specified recipients
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, EmailStr
import uuid
import json

from app.database import get_db
from app.models.database_models import ServiceRequest, Provider, User
from app.services.auth_service import AuthService
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()

# Authentication setup
security = HTTPBearer()
auth_service = AuthService()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

# Request Models
class ShareRecipient(BaseModel):
    email: EmailStr = Field(..., description="Recipient email address")
    name: str = Field(..., description="Recipient name")
    permissions: List[str] = Field(default=["view"], description="Permissions for recipient (view, download, edit)")

class ShareRequest(BaseModel):
    reportId: str = Field(..., description="ID of the report to share")
    recipients: List[ShareRecipient] = Field(..., description="List of recipients")
    message: Optional[str] = Field(default=None, description="Custom message to include with the share")
    expiresAt: Optional[str] = Field(default=None, description="Expiration date for the shared report")
    includeRawData: bool = Field(default=False, description="Whether to include raw data access")

# Response Models
class ShareResponse(BaseModel):
    shareId: str
    shareUrl: str
    recipients: int
    expiresAt: str
    emailsSent: bool

class ShareAPIResponse(BaseModel):
    success: bool
    data: ShareResponse
    message: str

# Helper Functions
async def _validate_report_exists(db: Session, report_id: str) -> bool:
    """Validate that the report exists and is accessible"""
    # Mock implementation - in production would check database
    # for report existence and user permissions
    return True

async def _generate_share_url(share_id: str, permissions: List[str]) -> str:
    """Generate a secure share URL"""
    base_url = "https://api.djobea.ai"
    permission_string = ",".join(permissions)
    return f"{base_url}/shared/analytics/{share_id}?permissions={permission_string}"

async def _send_share_email(
    recipient: ShareRecipient,
    share_url: str,
    message: Optional[str],
    expires_at: datetime,
    sender_name: str
):
    """Send share notification email to recipient"""
    # Mock implementation - in production would integrate with email service
    print(f"Sending share email to {recipient.email}")
    print(f"Recipient: {recipient.name}")
    print(f"Share URL: {share_url}")
    print(f"Permissions: {', '.join(recipient.permissions)}")
    print(f"Message: {message or 'Aucun message personnalisé'}")
    print(f"Expires at: {expires_at}")
    print(f"Shared by: {sender_name}")

async def _create_share_record(
    db: Session,
    share_id: str,
    report_id: str,
    recipients: List[ShareRecipient],
    expires_at: datetime,
    created_by: str
) -> Dict[str, Any]:
    """Create share record in database"""
    # Mock implementation - in production would create database record
    share_record = {
        "share_id": share_id,
        "report_id": report_id,
        "recipients": [
            {
                "email": r.email,
                "name": r.name,
                "permissions": r.permissions
            } for r in recipients
        ],
        "expires_at": expires_at.isoformat(),
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
        "access_count": 0,
        "status": "active"
    }
    
    # In production, would save to database
    # db.add(ShareRecord(**share_record))
    # db.commit()
    
    return share_record

@router.post("/share", response_model=ShareAPIResponse)
async def share_analytics_report(
    request: ShareRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Share analytics report with specified recipients"""
    
    try:
        # Validate report exists
        if not await _validate_report_exists(db, request.reportId):
            raise HTTPException(
                status_code=404,
                detail="Report not found or access denied"
            )
        
        # Validate recipients
        if not request.recipients:
            raise HTTPException(
                status_code=400,
                detail="At least one recipient is required"
            )
        
        # Validate permissions
        valid_permissions = ["view", "download", "edit", "share"]
        for recipient in request.recipients:
            invalid_perms = [p for p in recipient.permissions if p not in valid_permissions]
            if invalid_perms:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid permissions: {', '.join(invalid_perms)}"
                )
        
        # Generate share ID
        share_id = f"share_{uuid.uuid4().hex[:8]}"
        
        # Set expiration date
        if request.expiresAt:
            try:
                expires_at = datetime.fromisoformat(request.expiresAt.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid expiration date format"
                )
        else:
            # Default to 7 days from now
            expires_at = datetime.now() + timedelta(days=7)
        
        # Validate expiration is in the future
        if expires_at <= datetime.now():
            raise HTTPException(
                status_code=400,
                detail="Expiration date must be in the future"
            )
        
        # Create share record
        share_record = await _create_share_record(
            db, share_id, request.reportId, request.recipients, expires_at, current_user["user_id"]
        )
        
        # Generate share URL
        all_permissions = list(set(
            perm for recipient in request.recipients for perm in recipient.permissions
        ))
        share_url = await _generate_share_url(share_id, all_permissions)
        
        # Send emails to recipients
        emails_sent = True
        sender_name = current_user.get("username", "Djobea AI")
        
        for recipient in request.recipients:
            try:
                await _send_share_email(
                    recipient, share_url, request.message, expires_at, sender_name
                )
            except Exception as e:
                print(f"Failed to send email to {recipient.email}: {str(e)}")
                emails_sent = False
        
        return ShareAPIResponse(
            success=True,
            data=ShareResponse(
                shareId=share_id,
                shareUrl=share_url,
                recipients=len(request.recipients),
                expiresAt=expires_at.isoformat() + "Z",
                emailsSent=emails_sent
            ),
            message="Report shared successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sharing report: {str(e)}"
        )

@router.get("/share/{share_id}")
async def get_shared_report(
    share_id: str,
    permissions: Optional[str] = None
):
    """Access a shared analytics report"""
    
    try:
        # Mock implementation - in production would:
        # 1. Validate share_id exists and is not expired
        # 2. Check user permissions
        # 3. Return appropriate report data
        
        # For demo, return mock shared report data
        return {
            "success": True,
            "data": {
                "shareId": share_id,
                "reportId": "report_123456",
                "title": "Rapport d'Analyse Mensuel",
                "description": "Analyse des performances du mois dernier",
                "permissions": permissions.split(",") if permissions else ["view"],
                "expiresAt": (datetime.now() + timedelta(days=7)).isoformat() + "Z",
                "accessCount": 1,
                "lastAccessed": datetime.now().isoformat() + "Z",
                "reportData": {
                    "summary": "Données d'analyse partagées",
                    "charts": ["KPIs", "Performance", "Services"],
                    "dataPoints": 150
                }
            },
            "message": "Shared report accessed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error accessing shared report: {str(e)}"
        )

@router.get("/share/{share_id}/info")
async def get_share_info(
    share_id: str,
    current_user = Depends(get_current_user)
):
    """Get information about a shared report"""
    
    try:
        # Mock implementation - in production would query database
        return {
            "success": True,
            "data": {
                "shareId": share_id,
                "reportId": "report_123456",
                "createdBy": current_user["username"],
                "createdAt": datetime.now().isoformat() + "Z",
                "expiresAt": (datetime.now() + timedelta(days=7)).isoformat() + "Z",
                "recipients": [
                    {
                        "email": "manager@example.com",
                        "name": "Manager",
                        "permissions": ["view", "download"],
                        "lastAccessed": datetime.now().isoformat() + "Z"
                    }
                ],
                "accessCount": 5,
                "status": "active"
            },
            "message": "Share information retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving share info: {str(e)}"
        )

@router.delete("/share/{share_id}")
async def revoke_share(
    share_id: str,
    current_user = Depends(get_current_user)
):
    """Revoke access to a shared report"""
    
    try:
        # Mock implementation - in production would:
        # 1. Validate user owns the share or has admin permissions
        # 2. Mark share as revoked in database
        # 3. Send notification emails to recipients
        
        return {
            "success": True,
            "data": {
                "shareId": share_id,
                "status": "revoked",
                "revokedAt": datetime.now().isoformat() + "Z",
                "revokedBy": current_user["username"]
            },
            "message": "Share access revoked successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error revoking share: {str(e)}"
        )

@router.get("/shares")
async def list_user_shares(
    current_user = Depends(get_current_user)
):
    """List all shares created by the current user"""
    
    try:
        # Mock implementation - in production would query database
        return {
            "success": True,
            "data": [
                {
                    "shareId": "share_abc123",
                    "reportId": "report_123456",
                    "title": "Rapport Mensuel",
                    "recipients": 2,
                    "createdAt": datetime.now().isoformat() + "Z",
                    "expiresAt": (datetime.now() + timedelta(days=7)).isoformat() + "Z",
                    "accessCount": 10,
                    "status": "active"
                }
            ],
            "metadata": {
                "totalShares": 1,
                "activeShares": 1,
                "expiredShares": 0
            },
            "message": "User shares retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user shares: {str(e)}"
        )