"""
Authentication API endpoints for external applications
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models.database_models import AdminUser
from app.services.auth_service import AuthService
from app.utils.auth import get_current_user
from loguru import logger

router = APIRouter()

@router.get("/api/auth/profile")
async def get_profile(current_user: AdminUser = Depends(get_current_user)):
    """Get user profile information"""
    try:
        return {
            "success": True,
            "data": {
                "id": str(current_user.id),
                "name": current_user.username,
                "email": current_user.email,
                "role": current_user.role,
                "avatar": f"https://ui-avatars.com/api/?name={current_user.username}&background=007bff&color=fff",
                "permissions": ["read", "write", "admin"] if current_user.role == "admin" else ["read"],
                "lastLogin": current_user.last_login.isoformat() if current_user.last_login else None,
                "createdAt": current_user.created_at.isoformat() if current_user.created_at else None
            }
        }
    except Exception as e:
        logger.error(f"Profile error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du profil")

@router.post("/api/auth/logout")
async def logout(current_user: AdminUser = Depends(get_current_user)):
    """User logout"""
    try:
        # In a real implementation, you might want to blacklist the token
        # For now, we'll just return success
        return {
            "success": True,
            "message": "Déconnexion réussie"
        }
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la déconnexion")

@router.post("/api/auth/refresh")
async def refresh_token(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh JWT token"""
    try:
        # Generate new token
        auth_service = AuthService(db)
        new_token = auth_service.create_access_token(data={"sub": str(current_user.id)})
        
        return {
            "success": True,
            "data": {
                "token": new_token,
                "expiresAt": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
            }
        }
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du rafraîchissement du token")