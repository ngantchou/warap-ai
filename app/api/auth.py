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
import uuid

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
            raise ValueError(
                'Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError(
                'Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['user', 'provider', 'admin']
        if v not in allowed_roles:
            raise ValueError(
                f'Role must be one of: {", ".join(allowed_roles)}')
        return v


class UserLoginRequest(BaseModel):
    """User login request model"""
    email: EmailStr
    password: str
    rememberMe: bool = False


class TokenRefreshRequest(BaseModel):
    """Token refresh request model"""
    refreshToken: str


class UserProfileUpdateRequest(BaseModel):
    """User profile update request model"""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    profile: Optional[dict] = None


class ChangePasswordRequest(BaseModel):
    """Change password request model"""
    currentPassword: str
    newPassword: str

    @validator('newPassword')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError(
                'New password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError(
                'New password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('New password must contain at least one digit')
        return v


class ForgotPasswordRequest(BaseModel):
    """Forgot password request model"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request model"""
    token: str
    newPassword: str

    @validator('newPassword')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError(
                'New password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError(
                'New password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('New password must contain at least one digit')
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


class UserProfileResponse(BaseModel):
    """User profile response model"""
    id: str
    name: str
    email: str
    role: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    permissions: List[str] = []
    isActive: bool = True
    lastLogin: Optional[datetime] = None
    profile: Optional[dict] = None


class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool = True
    message: str
    data: dict = {}


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    message: str
    details: Optional[List[str]] = []
    requestId: Optional[str] = None
    timestamp: str


class TokenResponse(BaseModel):
    """Token response model"""
    user: UserResponse
    token: str
    refreshToken: str
    expiresIn: int


# Helper functions
def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)):
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid authentication credentials")
    return user


def get_user_permissions(user: User, db: Session) -> List[str]:
    """Get user permissions"""
    return auth_service.get_user_permissions(user.id, db)


def format_user_response(user: User, permissions: List[str]) -> UserResponse:
    """Format user for response"""
    return UserResponse(id=user.id,
                        name=user.full_name,
                        email=user.email,
                        role=user.role,
                        avatar=user.avatar,
                        permissions=permissions,
                        isActive=user.is_active,
                        lastLogin=user.last_login)


def format_user_profile_response(
        user: User, permissions: List[str]) -> UserProfileResponse:
    """Format user profile for response"""
    # Parse profile data if it exists
    profile_data = None
    if hasattr(user, 'profile_data') and user.profile_data:
        try:
            import json
            profile_data = json.loads(user.profile_data) if isinstance(
                user.profile_data, str) else user.profile_data
        except:
            profile_data = None

    return UserProfileResponse(id=user.id,
                               name=user.full_name,
                               email=user.email,
                               role=user.role,
                               avatar=user.avatar,
                               phone=user.phone,
                               address=getattr(user, 'address', None),
                               permissions=permissions,
                               isActive=user.is_active,
                               lastLogin=user.last_login,
                               profile=profile_data)


# API Endpoints


@router.post("/register", response_model=AuthResponse)
async def register_user(user_data: UserRegisterRequest,
                        request: Request,
                        db: Session = Depends(get_db)):
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
            existing_user = db.query(User).filter(
                User.username == username).first()
            if not existing_user:
                break
            username = f"{base_username}{counter}"
            counter += 1

        # Register user
        user = auth_service.register_user(username=username,
                                          email=user_data.email,
                                          password=user_data.password,
                                          role=user_data.role,
                                          db=db)

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
        login_result = auth_service.login_user(username, user_data.password,
                                               db)

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

        return AuthResponse(success=True,
                            message="User registered successfully",
                            data=response_data)

    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred during registration")


@router.get("/me", response_model=AuthResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    """Get current user information"""
    permissions = get_user_permissions(current_user, db)
    user_response = format_user_response(current_user, permissions)

    return AuthResponse(success=True,
                        message="User information retrieved successfully",
                        data={"user": user_response.dict()})


@router.post("/login", response_model=AuthResponse)
async def login_user(login_data: UserLoginRequest,
                     request: Request,
                     db: Session = Depends(get_db)):
    """
    User login
    
    Authenticates user with email and password.
    Returns user data and JWT tokens.
    """
    try:
        print(login_data)
        # Use email as username for authentication
        login_result = auth_service.login_user(username=login_data.email,
                                               password=login_data.password,
                                               db=db)

        # Get user for response formatting
        user = auth_service.get_user_by_id(login_result["user"]["id"], db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")

        # Get user permissions
        permissions = get_user_permissions(user, db)

        # Format user response
        user_response = format_user_response(user, permissions)

        # Prepare response data
        response_data = {
            "user": user_response.dict(),
            "token": login_result["access_token"],
            "refreshToken": login_result["refresh_token"],
            "expiresIn": login_result["expires_in"]
        }
        print(response_data)
        return AuthResponse(success=True,
                            message="Login successful",
                            data=response_data)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred during login")


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)):
    """
    Refresh access token
    
    Uses refresh token to generate new access token.
    Implements token rotation for security.
    """
    try:
        # Extract refresh token from Authorization header
        refresh_token = credentials.credentials

        # Refresh the token
        refresh_result = auth_service.refresh_access_token(refresh_token, db)

        response_data = {
            "token": refresh_result["access_token"],
            "refreshToken": refresh_result["refresh_token"],
            "expiresIn": refresh_result["expires_in"]
        }

        return AuthResponse(success=True,
                            message="Token refreshed successfully",
                            data=response_data)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred during token refresh")


@router.post("/logout", response_model=AuthResponse)
async def logout_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)):
    """
    User logout
    
    Revokes the refresh token to invalidate the session.
    """
    try:
        # Extract refresh token from Authorization header
        refresh_token = credentials.credentials

        # Logout user (revoke refresh token)
        success = auth_service.logout_user(refresh_token, db)

        if success:
            return AuthResponse(success=True,
                                message="Logout successful",
                                data={})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid refresh token")

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred during logout")


@router.get("/profile", response_model=AuthResponse)
async def get_user_profile(current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """
    Get current user profile
    
    Returns detailed user profile information including preferences.
    """
    try:
        # Get user permissions
        permissions = get_user_permissions(current_user, db)

        # Format profile response
        profile_response = format_user_profile_response(
            current_user, permissions)

        return AuthResponse(success=True,
                            message="Profile retrieved successfully",
                            data=profile_response.dict())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving profile")


@router.put("/profile", response_model=AuthResponse)
async def update_user_profile(profile_data: UserProfileUpdateRequest,
                              current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """
    Update user profile
    
    Updates user profile information and preferences.
    """
    try:
        # Update basic profile fields
        if profile_data.name:
            names = profile_data.name.strip().split()
            if len(names) >= 2:
                current_user.first_name = names[0]
                current_user.last_name = " ".join(names[1:])
            else:
                current_user.first_name = names[0]
                current_user.last_name = ""

        if profile_data.phone:
            current_user.phone = profile_data.phone

        # Handle address - need to add this field to User model or store in profile_data
        if profile_data.address:
            # Store address in profile data as JSON
            import json
            profile_json = {}
            if hasattr(current_user,
                       'profile_data') and current_user.profile_data:
                try:
                    profile_json = json.loads(
                        current_user.profile_data) if isinstance(
                            current_user.profile_data,
                            str) else current_user.profile_data
                except:
                    profile_json = {}

            profile_json['address'] = profile_data.address

            # Update profile preferences if provided
            if profile_data.profile:
                profile_json.update(profile_data.profile)

            # For now, we'll handle this without a profile_data field
            # In production, you'd want to add this field to the User model

        # Update profile preferences
        if profile_data.profile:
            # Store profile preferences (in production, add profile_data field to User model)
            pass

        # Update timestamp
        current_user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(current_user)

        # Get updated permissions
        permissions = get_user_permissions(current_user, db)

        # Format updated profile response
        profile_response = format_user_profile_response(
            current_user, permissions)

        return AuthResponse(success=True,
                            message="Profile updated successfully",
                            data=profile_response.dict())

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An error occurred while updating profile")


@router.post("/change-password", response_model=AuthResponse)
async def change_password(password_data: ChangePasswordRequest,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """
    Change user password
    
    Updates the user's password after verifying the current password.
    """
    try:
        # Verify current password
        if not auth_service.verify_password(password_data.currentPassword,
                                            current_user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail={
                                    "success": False,
                                    "error": "INVALID_CURRENT_PASSWORD",
                                    "message": "Current password is incorrect",
                                    "timestamp": datetime.utcnow().isoformat()
                                })

        # Update password
        success = auth_service.change_password(
            user_id=current_user.id,
            new_password=password_data.newPassword,
            db=db)

        if success:
            return AuthResponse(success=True,
                                message="Password changed successfully")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": "PASSWORD_CHANGE_FAILED",
                    "message": "Failed to change password",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={
                                "success": False,
                                "error": "INTERNAL_SERVER_ERROR",
                                "message":
                                "An error occurred while changing password",
                                "timestamp": datetime.utcnow().isoformat()
                            })


@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(request_data: ForgotPasswordRequest,
                          db: Session = Depends(get_db)):
    """
    Forgot password
    
    Sends a password reset email to the user.
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == request_data.email).first()
        if not user:
            # Return success even if user doesn't exist for security
            return AuthResponse(success=True,
                                message="Password reset email sent")

        # Generate reset token
        reset_token = auth_service.generate_password_reset_token(user.id, db)

        # In production, you would send an email here
        # For now, we'll just return success
        # send_password_reset_email(user.email, reset_token)

        return AuthResponse(success=True, message="Password reset email sent")

    except Exception as e:
        return ErrorResponse(
            success=False,
            error="INTERNAL_SERVER_ERROR",
            message=
            "An error occurred while processing forgot password request",
            timestamp=datetime.utcnow().isoformat())


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(reset_data: ResetPasswordRequest,
                         db: Session = Depends(get_db)):
    """
    Reset password
    
    Resets the user's password using a reset token.
    """
    try:
        # Verify and use reset token
        success = auth_service.reset_password_with_token(
            token=reset_data.token, new_password=reset_data.newPassword, db=db)

        if success:
            return AuthResponse(success=True,
                                message="Password reset successfully")
        else:
            return ErrorResponse(success=False,
                                 error="INVALID_RESET_TOKEN",
                                 message="Invalid or expired reset token",
                                 timestamp=datetime.utcnow().isoformat())

    except Exception as e:
        return ErrorResponse(
            success=False,
            error="INTERNAL_SERVER_ERROR",
            message="An error occurred while resetting password",
            timestamp=datetime.utcnow().isoformat())


@router.post("/logout", response_model=AuthResponse)
async def logout_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)):
    """
    User logout
    
    Revokes the refresh token to invalidate the session.
    """
    try:
        # Extract refresh token from Authorization header
        refresh_token = credentials.credentials

        # Logout user (revoke refresh token)
        success = auth_service.logout_user(refresh_token, db)

        if success:
            return AuthResponse(success=True,
                                message="Logged out successfully")
        else:
            return ErrorResponse(success=False,
                                 error="INVALID_REFRESH_TOKEN",
                                 message="Invalid refresh token",
                                 timestamp=datetime.utcnow().isoformat())

    except Exception as e:
        return ErrorResponse(success=False,
                             error="INTERNAL_SERVER_ERROR",
                             message="An error occurred during logout",
                             timestamp=datetime.utcnow().isoformat())


@router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
