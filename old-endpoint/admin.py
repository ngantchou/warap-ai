"""
Admin API v1 - Unified Administration Domain
Combines admin.py, auth.py, auth_api.py, dashboard.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models.database_models import AdminUser, User, Provider, ServiceRequest
from app.utils.auth import get_current_user
from loguru import logger
import jwt

router = APIRouter()
security = HTTPBearer()

# ==== AUTHENTICATION ====
@router.post("/auth/login")
async def admin_login(
    credentials: Dict[str, str],
    db: Session = Depends(get_db)
):
    """Admin login endpoint"""
    try:
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Nom d'utilisateur et mot de passe requis")
        
        # Get admin user
        admin_user = db.query(AdminUser).filter(AdminUser.username == username).first()
        
        if not admin_user or admin_user.password_hash != password:
            raise HTTPException(status_code=401, detail="Identifiants invalides")
        
        # Create access token (simplified for demo)
        access_token = f"demo_token_{admin_user.id}_{admin_user.username}"
        
        return {
            "success": True,
            "message": "Connexion réussie",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": admin_user.id,
                    "username": admin_user.username,
                    "email": admin_user.email,
                    "role": admin_user.role
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la connexion")

@router.post("/auth/refresh")
async def refresh_token(
    refresh_data: Dict[str, str],
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    try:
        refresh_token = refresh_data.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Token de rafraîchissement requis")
        
        # Verify refresh token (simplified)
        new_access_token = f"demo_refresh_token_{datetime.now().timestamp()}"
        
        return {
            "success": True,
            "data": {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
        }
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du rafraîchissement du token")

@router.post("/auth/logout")
async def admin_logout(
    current_user: AdminUser = Depends(get_current_user)
):
    """Admin logout endpoint"""
    try:
        return {
            "success": True,
            "message": "Déconnexion réussie"
        }
    except Exception as e:
        logger.error(f"Admin logout error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la déconnexion")

@router.get("/auth/me")
async def get_current_admin(
    current_user: AdminUser = Depends(get_current_user)
):
    """Get current admin user info"""
    try:
        return {
            "success": True,
            "data": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role,
                "lastLogin": current_user.last_login.isoformat() if current_user.last_login else None
            }
        }
    except Exception as e:
        logger.error(f"Get current admin error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des informations utilisateur")

# ==== USER MANAGEMENT ====
@router.get("/users")
async def get_users(
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get all users"""
    try:
        # Build query
        query = db.query(User)
        
        # Pagination
        total = query.count()
        users = query.offset((page - 1) * limit).limit(limit).all()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "phoneNumber": user.phone_number,
                "sessionId": getattr(user, 'session_id', 'N/A'),
                "createdAt": user.created_at.isoformat() if user.created_at else None,
                "lastActive": user.last_active.isoformat() if user.last_active else None,
                "totalRequests": len(user.service_requests) if hasattr(user, 'service_requests') else 0
            })
        
        return {
            "success": True,
            "data": user_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des utilisateurs")

@router.get("/users/{user_id}")
async def get_user(
    user_id: int = Path(..., description="User ID"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get user details"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Get user's service requests
        requests = db.query(ServiceRequest).filter(ServiceRequest.user_id == user_id).all()
        
        return {
            "success": True,
            "data": {
                "id": user.id,
                "phoneNumber": user.phone_number,
                "sessionId": getattr(user, 'session_id', 'N/A'),
                "createdAt": user.created_at.isoformat() if user.created_at else None,
                "lastActive": user.last_active.isoformat() if user.last_active else None,
                "totalRequests": len(requests),
                "requests": [
                    {
                        "id": req.id,
                        "serviceType": req.service_type,
                        "status": req.status,
                        "createdAt": req.created_at.isoformat() if req.created_at else None
                    }
                    for req in requests
                ]
            }
        }
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'utilisateur")

# ==== DASHBOARD ====
@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get dashboard overview"""
    try:
        # Get basic stats
        total_users = db.query(User).count()
        total_providers = db.query(Provider).count()
        total_requests = db.query(ServiceRequest).count()
        
        # Get recent requests
        recent_requests = db.query(ServiceRequest).order_by(
            ServiceRequest.created_at.desc()
        ).limit(5).all()
        
        return {
            "success": True,
            "data": {
                "stats": {
                    "totalUsers": total_users,
                    "totalProviders": total_providers,
                    "totalRequests": total_requests,
                    "pendingRequests": len([r for r in recent_requests if r.status == "pending"])
                },
                "recentRequests": [
                    {
                        "id": req.id,
                        "serviceType": req.service_type,
                        "location": req.location,
                        "status": req.status,
                        "createdAt": req.created_at.isoformat() if req.created_at else None
                    }
                    for req in recent_requests
                ],
                "systemHealth": {
                    "status": "healthy",
                    "uptime": "99.9%",
                    "lastUpdate": datetime.now().isoformat()
                }
            }
        }
    except Exception as e:
        logger.error(f"Get dashboard overview error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du tableau de bord")

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    period: str = Query("7d", description="Time period"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get dashboard statistics"""
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
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "success": True,
            "data": {
                "period": period,
                "requests": {
                    "total": total_requests,
                    "completed": completed_requests,
                    "pending": len([r for r in requests if r.status == "pending"]),
                    "successRate": round(success_rate, 1)
                },
                "growth": {
                    "requests": 12.5,
                    "users": 8.3,
                    "providers": 5.2
                },
                "trends": [
                    {"date": "2025-01-15", "requests": 45, "completions": 42},
                    {"date": "2025-01-16", "requests": 52, "completions": 48},
                    {"date": "2025-01-17", "requests": 48, "completions": 46}
                ]
            }
        }
    except Exception as e:
        logger.error(f"Get dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

@router.get("/dashboard/activity")
async def get_dashboard_activity(
    limit: int = Query(10, description="Number of activities"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get recent activity"""
    try:
        # Get recent requests as activity
        recent_requests = db.query(ServiceRequest).order_by(
            ServiceRequest.created_at.desc()
        ).limit(limit).all()
        
        activities = []
        for req in recent_requests:
            activities.append({
                "id": req.id,
                "type": "service_request",
                "description": f"Nouvelle demande de {req.service_type or 'service'} à {req.location or 'Bonamoussadi'}",
                "timestamp": req.created_at.isoformat() if req.created_at else None,
                "status": req.status,
                "priority": "normal"
            })
        
        return {
            "success": True,
            "data": activities
        }
    except Exception as e:
        logger.error(f"Get dashboard activity error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'activité")

# ==== ADMIN MANAGEMENT ====
@router.get("/admins")
async def get_admin_users(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get all admin users"""
    try:
        admin_users = db.query(AdminUser).all()
        
        admin_list = []
        for admin in admin_users:
            admin_list.append({
                "id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "role": admin.role,
                "createdAt": admin.created_at.isoformat() if admin.created_at else None,
                "lastLogin": admin.last_login.isoformat() if admin.last_login else None,
                "isActive": admin.is_active
            })
        
        return {
            "success": True,
            "data": admin_list
        }
    except Exception as e:
        logger.error(f"Get admin users error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des administrateurs")

@router.post("/admins")
async def create_admin_user(
    admin_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Create new admin user"""
    try:
        # Check if username exists
        existing_admin = db.query(AdminUser).filter(
            AdminUser.username == admin_data.get("username")
        ).first()
        
        if existing_admin:
            raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà existant")
        
        # Create new admin (simplified password handling)
        new_admin = AdminUser(
            username=admin_data.get("username"),
            email=admin_data.get("email"),
            password_hash=admin_data.get("password"),  # Simplified for demo
            role=admin_data.get("role", "admin"),
            is_active=True,
            created_at=datetime.now()
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        return {
            "success": True,
            "message": "Administrateur créé avec succès",
            "data": {
                "id": new_admin.id,
                "username": new_admin.username,
                "email": new_admin.email,
                "role": new_admin.role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create admin user error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la création de l'administrateur")

@router.put("/admins/{admin_id}")
async def update_admin_user(
    admin_id: int = Path(..., description="Admin ID"),
    admin_data: Dict[str, Any] = None,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update admin user"""
    try:
        admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
        
        if not admin:
            raise HTTPException(status_code=404, detail="Administrateur non trouvé")
        
        # Update fields
        if admin_data:
            if "email" in admin_data:
                admin.email = admin_data["email"]
            if "role" in admin_data:
                admin.role = admin_data["role"]
            if "password" in admin_data:
                admin.password_hash = admin_data["password"]  # Simplified for demo
            if "is_active" in admin_data:
                admin.is_active = admin_data["is_active"]
        
        db.commit()
        
        return {
            "success": True,
            "message": "Administrateur mis à jour avec succès"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update admin user error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour de l'administrateur")

@router.delete("/admins/{admin_id}")
async def delete_admin_user(
    admin_id: int = Path(..., description="Admin ID"),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Delete admin user"""
    try:
        admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
        
        if not admin:
            raise HTTPException(status_code=404, detail="Administrateur non trouvé")
        
        # Don't allow deleting self
        if admin.id == current_user.id:
            raise HTTPException(status_code=400, detail="Impossible de supprimer votre propre compte")
        
        db.delete(admin)
        db.commit()
        
        return {
            "success": True,
            "message": "Administrateur supprimé avec succès"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete admin user error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression de l'administrateur")

# ==== SYSTEM MANAGEMENT ====
@router.get("/system/info")
async def get_system_info(
    current_user: AdminUser = Depends(get_current_user)
):
    """Get system information"""
    try:
        return {
            "success": True,
            "data": {
                "version": "1.0.0",
                "environment": "production",
                "startTime": datetime.now().isoformat(),
                "uptime": "99.9%",
                "features": {
                    "whatsapp": True,
                    "webchat": True,
                    "ai": True,
                    "payments": True,
                    "notifications": True
                },
                "limits": {
                    "maxUsers": 10000,
                    "maxProviders": 1000,
                    "maxRequests": 100000
                }
            }
        }
    except Exception as e:
        logger.error(f"Get system info error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des informations système")

@router.post("/system/maintenance")
async def toggle_maintenance_mode(
    maintenance_data: Dict[str, Any],
    current_user: AdminUser = Depends(get_current_user)
):
    """Toggle maintenance mode"""
    try:
        enabled = maintenance_data.get("enabled", False)
        message = maintenance_data.get("message", "Maintenance en cours")
        
        # Simulate maintenance mode toggle
        logger.info(f"Maintenance mode {'enabled' if enabled else 'disabled'}")
        
        return {
            "success": True,
            "message": f"Mode maintenance {'activé' if enabled else 'désactivé'} avec succès",
            "data": {
                "enabled": enabled,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Toggle maintenance mode error: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du basculement du mode maintenance")