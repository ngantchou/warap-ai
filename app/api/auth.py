"""
Authentication API endpoints for Djobea AI admin interface
Handles login, logout, token refresh, and user management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from loguru import logger

from app.database import get_db
from app.models.database_models import AdminUser, AdminRole
from app.services.auth_service import AuthService, get_current_user
from app.config import get_settings
from fastapi.templating import Jinja2Templates

settings = get_settings()
templates = Jinja2Templates(directory="templates")
security = HTTPBearer(auto_error=False)

router = APIRouter()


# Pydantic models for request/response
class LoginRequest(BaseModel):
    email: str
    password: str
    rememberMe: bool = False


class LoginResponse(BaseModel):
    success: bool
    token: str
    refreshToken: str
    user: dict
    expiresAt: str


class TokenRefreshRequest(BaseModel):
    refreshToken: str


class TokenRefreshResponse(BaseModel):
    success: bool
    token: str
    expiresAt: str


class LogoutResponse(BaseModel):
    success: bool
    message: str


class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: AdminRole = AdminRole.ADMIN


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and user agent from request"""
    # Get real IP from various headers (for reverse proxy setups)
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
        request.headers.get("x-real-ip") or
        request.client.host if request.client else "unknown"
    )
    
    user_agent = request.headers.get("user-agent", "")
    return client_ip, user_agent


async def get_current_admin_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> AdminUser:
    """Get current authenticated admin user"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return get_current_user(db, credentials.credentials)


def require_admin_role(required_role: AdminRole = AdminRole.ADMIN):
    """Decorator to require specific admin role"""
    def dependency(current_user: AdminUser = Depends(get_current_admin_user)):
        user_role = AdminRole(current_user.role)
        
        # Super admin can access everything
        if user_role == AdminRole.SUPER_ADMIN:
            return current_user
        
        # Check if user has required role
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return dependency


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve admin login page"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login_for_access_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token (legacy form-based endpoint)"""
    # Get form data directly from request
    try:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
        
        logger.info(f"Form data received - username: '{username}', password: {'*' * len(password) if password else 'None'}")
        
        if not username or not password:
            logger.error(f"Missing credentials - username: '{username}', password provided: {bool(password)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username and password are required"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing form data: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid form data"
        )
    
    auth_service = AuthService(db)
    client_ip, user_agent = get_client_info(request)
    
    # Debug logging
    logger.info(f"Login attempt for username: {username} from {client_ip}")
    
    # Authenticate user
    user = auth_service.authenticate_user(username, password, client_ip, user_agent)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=60)  # Default 60 minutes
    
    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    
    access_token = auth_service.create_access_token(
        data=token_data, expires_delta=access_token_expires
    )
    
    refresh_token = auth_service.create_refresh_token(data=token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds())
    }


@router.post("/api/auth/login", response_model=LoginResponse)
async def api_login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user with email and password for external admin interface"""
    auth_service = AuthService(db)
    client_ip, user_agent = get_client_info(request)
    
    logger.info(f"API Login attempt for email: {login_data.email} from {client_ip}")
    
    # Authenticate user by email
    user = auth_service.authenticate_user_by_email(
        login_data.email, 
        login_data.password, 
        client_ip, 
        user_agent
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens with appropriate expiration
    access_token_expires = timedelta(hours=24 if login_data.rememberMe else 1)
    refresh_token_expires = timedelta(days=30 if login_data.rememberMe else 7)
    
    token_data = {
        "sub": str(user.id), 
        "username": user.username, 
        "email": user.email,
        "role": user.role
    }
    
    access_token = auth_service.create_access_token(
        data=token_data, 
        expires_delta=access_token_expires
    )
    
    refresh_token = auth_service.create_refresh_token(data=token_data)
    
    # Calculate expiration timestamp
    expires_at = datetime.now(timezone.utc) + access_token_expires
    
    # Store refresh token (in production, store in database)
    # For now, we'll include it in the response
    
    return LoginResponse(
        success=True,
        token=access_token,
        refreshToken=refresh_token,
        user={
            "id": str(user.id),
            "name": user.username,
            "email": user.email,
            "role": user.role,
            "avatar": "/avatars/default.jpg"  # Default avatar
        },
        expiresAt=expires_at.isoformat()
    )
    access_token = auth_service.create_access_token(
        data=token_data, expires_delta=access_token_expires
    )
    refresh_token = auth_service.create_refresh_token(data=token_data)
    
    # Create response
    response = RedirectResponse(url="/admin/", status_code=303)
    
    # Set secure HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=access_token_expires.total_seconds(),
        httponly=True,
        secure=not settings.debug,  # Use secure cookies in production
        samesite="lax"
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=timedelta(days=7).total_seconds(),
        httponly=True,
        secure=not settings.debug,
        samesite="lax"
    )
    
    logger.info(f"User {username} logged in successfully from {client_ip}")
    return response


@router.post("/api/login")
async def api_login(
    login_request: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """API endpoint for login (returns JSON)"""
    auth_service = AuthService(db)
    client_ip, user_agent = get_client_info(request)
    
    user = auth_service.authenticate_user(
        login_request.username, login_request.password, client_ip, user_agent
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=60)
    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    
    access_token = auth_service.create_access_token(
        data=token_data, expires_delta=access_token_expires
    )
    refresh_token = auth_service.create_refresh_token(data=token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_token_expires.total_seconds()),
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "last_login": user.last_login
        }
    )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Logout user and clear cookies"""
    auth_service = AuthService(db)
    auth_service.log_security_event("logout", user_id=current_user.id)
    
    # Clear cookies
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    
    logger.info(f"User {current_user.username} logged out")
    return response


@router.post("/api/logout")
async def api_logout(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """API logout endpoint"""
    auth_service = AuthService(db)
    auth_service.log_security_event("logout", user_id=current_user.id)
    
    return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_access_token(
    refresh_request: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token (legacy endpoint)"""
    auth_service = AuthService(db)
    
    # Verify refresh token
    payload = auth_service.verify_token(refresh_request.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = auth_service.get_user_by_id(int(user_id))
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=60)
    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    
    access_token = auth_service.create_access_token(
        data=token_data, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds())
    }


@router.post("/api/auth/refresh", response_model=TokenRefreshResponse)
async def api_refresh_token(
    refresh_request: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token for external admin interface"""
    auth_service = AuthService(db)
    
    # Verify refresh token
    payload = auth_service.verify_token(refresh_request.refreshToken, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = auth_service.get_user_by_id(int(user_id))
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token_expires = timedelta(hours=1)
    token_data = {
        "sub": str(user.id), 
        "username": user.username, 
        "email": user.email,
        "role": user.role
    }
    
    access_token = auth_service.create_access_token(
        data=token_data, 
        expires_delta=access_token_expires
    )
    
    # Calculate expiration timestamp
    expires_at = datetime.now(timezone.utc) + access_token_expires
    
    return TokenRefreshResponse(
        success=True,
        token=access_token,
        expiresAt=expires_at.isoformat()
    )


@router.post("/api/auth/logout", response_model=LogoutResponse)
async def api_logout(
    request: Request,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Logout user and revoke tokens for external admin interface"""
    auth_service = AuthService(db)
    client_ip, user_agent = get_client_info(request)
    
    # Log security event
    auth_service.log_security_event(
        "logout_success", 
        current_user.id, 
        client_ip, 
        user_agent
    )
    
    # In production, you would revoke the refresh token from database
    # For now, we'll just log the logout
    logger.info(f"User {current_user.email} logged out from {client_ip}")
    
    return LogoutResponse(
        success=True,
        message="Déconnexion réussie"
    )


# Missing endpoint from API documentation
@router.get("/auth/profile")
async def get_user_profile(
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user profile information"""
    return {
        "success": True,
        "data": {
            "id": str(current_user.id),
            "name": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "avatar": f"/avatars/{current_user.username}.jpg",
            "permissions": ["read", "write", "admin"] if current_user.role == "admin" else ["read"],
            "lastLogin": current_user.last_login.isoformat() if current_user.last_login else None,
            "createdAt": current_user.created_at.isoformat() if current_user.created_at else None
        }
    }


@router.get("/me")
async def get_current_user_info(
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    password_request: ChangePasswordRequest,
    request: Request,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    auth_service = AuthService(db)
    client_ip, user_agent = get_client_info(request)
    
    # Verify current password
    if not auth_service.verify_password(password_request.current_password, current_user.hashed_password):
        auth_service.log_security_event(
            "failed_password_change", 
            user_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Change password
    success = auth_service.change_password(current_user, password_request.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
    
    auth_service.log_security_event(
        "password_changed",
        user_id=current_user.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return {"message": "Password changed successfully"}


@router.post("/users", dependencies=[Depends(require_admin_role(AdminRole.SUPER_ADMIN))])
async def create_admin_user(
    user_request: CreateUserRequest,
    request: Request,
    current_user: AdminUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create new admin user (super admin only)"""
    auth_service = AuthService(db)
    client_ip, user_agent = get_client_info(request)
    
    # Check if user already exists
    existing_user = auth_service.get_user_by_username(user_request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create user
    try:
        new_user = auth_service.create_admin_user(
            username=user_request.username,
            email=user_request.email,
            password=user_request.password,
            role=user_request.role
        )
        
        auth_service.log_security_event(
            "admin_user_created",
            user_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={
                "created_user_id": new_user.id,
                "created_username": new_user.username,
                "created_role": new_user.role
            }
        )
        
        return UserResponse.from_orm(new_user)
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/users", dependencies=[Depends(require_admin_role(AdminRole.ADMIN))])
async def list_admin_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all admin users"""
    users = db.query(AdminUser).offset(skip).limit(limit).all()
    return [UserResponse.from_orm(user) for user in users]


@router.get("/security-logs", dependencies=[Depends(require_admin_role(AdminRole.ADMIN))])
async def get_security_logs(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get security logs"""
    from app.models.database_models import SecurityLog
    
    query = db.query(SecurityLog)
    
    if event_type:
        query = query.filter(SecurityLog.event_type == event_type)
    
    logs = query.order_by(SecurityLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "user_id": log.user_id,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": log.details,
            "created_at": log.created_at
        }
        for log in logs
    ]


@router.get("/health")
async def auth_health_check():
    """Health check for auth service"""
    return {"status": "healthy", "service": "auth"}