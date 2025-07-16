"""
Authentication API Endpoints for Djobea AI
Comprehensive JWT-based authentication with user management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.services.auth_service import auth_service
from app.models.auth_models import User

router = APIRouter()
security = HTTPBearer()

# Pydantic Models
class UserRegisterRequest(BaseModel):
    """User registration request model"""
    name: str
    email: EmailStr
    password: str
    role: str = "user"
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['user', 'provider', 'admin']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v

class UserResponse(BaseModel):
    """User response model"""
    id: str
    name: str
    email: str
    role: str
    avatar: Optional[str] = None
    permissions: List[str] = []
    isActive: bool = True
    lastLogin: Optional[datetime] = None

class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool = True
    message: str
    data: dict

class TokenResponse(BaseModel):
    """Token response model"""
    user: UserResponse
    token: str
    refreshToken: str
    expiresIn: int

# Helper functions
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user

def get_user_permissions(user: User, db: Session) -> List[str]:
    """Get user permissions"""
    return auth_service.get_user_permissions(user.id, db)

def format_user_response(user: User, permissions: List[str]) -> UserResponse:
    """Format user for response"""
    return UserResponse(
        id=user.id,
        name=user.full_name,
        email=user.email,
        role=user.role,
        avatar=user.avatar,
        permissions=permissions,
        isActive=user.is_active,
        lastLogin=user.last_login
    )

# API Endpoints

@router.post("/register", response_model=AuthResponse)
async def register_user(
    user_data: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    Creates a new user account with the provided information.
    Returns user data and authentication tokens.
    """
    try:
        # Extract username from name (first name as username)
        username = user_data.name.split()[0].lower()
        
        # Check if username already exists, if so append number
        base_username = username
        counter = 1
        while True:
            existing_user = db.query(User).filter(User.username == username).first()
            if not existing_user:
                break
            username = f"{base_username}{counter}"
            counter += 1
        
        # Register user
        user = auth_service.register_user(
            username=username,
            email=user_data.email,
            password=user_data.password,
            role=user_data.role,
            db=db
        )
        
        # Set full name
        names = user_data.name.strip().split()
        if len(names) >= 2:
            user.first_name = names[0]
            user.last_name = " ".join(names[1:])
        else:
            user.first_name = names[0]
        
        db.commit()
        db.refresh(user)
        
        # Login user to get tokens
        login_result = auth_service.login_user(username, user_data.password, db)
        
        # Get user permissions
        permissions = get_user_permissions(user, db)
        
        # Format response
        user_response = format_user_response(user, permissions)
        
        response_data = {
            "user": user_response.dict(),
            "token": login_result["access_token"],
            "refreshToken": login_result["refresh_token"],
            "expiresIn": login_result["expires_in"]
        }
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            data=response_data
        )
        
    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )

@router.get("/me", response_model=AuthResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    permissions = get_user_permissions(current_user, db)
    user_response = format_user_response(current_user, permissions)
    
    return AuthResponse(
        success=True,
        message="User information retrieved successfully",
        data={"user": user_response.dict()}
    )

@router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }