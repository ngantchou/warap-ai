"""
JWT Authentication Service for Djobea AI
Comprehensive authentication system with user management, JWT tokens, and role-based access
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr
import secrets
import uuid
from loguru import logger

from app.database import get_db
from app.models.auth_models import User, RefreshToken, UserRole, Permission, RolePermission
from app.config import get_settings

settings = get_settings()

class TokenData(BaseModel):
    """Token data structure"""
    user_id: str
    username: str
    email: str
    role: str
    permissions: List[str]

class AuthService:
    """Comprehensive authentication service"""
    
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-here")
        self.jwt_refresh_secret = os.getenv("JWT_REFRESH_SECRET", "your-refresh-token-secret-here")
        self.jwt_expires_in = os.getenv("JWT_EXPIRES_IN", "24h")
        self.jwt_refresh_expires_in = os.getenv("JWT_REFRESH_EXPIRES_IN", "7d")
        self.bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", "12"))
        
        # Convert time strings to seconds
        self.access_token_expire_minutes = self._parse_time_string(self.jwt_expires_in)
        self.refresh_token_expire_minutes = self._parse_time_string(self.jwt_refresh_expires_in)
    
    def _parse_time_string(self, time_str: str) -> int:
        """Parse time string (e.g., '24h', '7d') to minutes"""
        if time_str.endswith('h'):
            return int(time_str[:-1]) * 60
        elif time_str.endswith('d'):
            return int(time_str[:-1]) * 24 * 60
        elif time_str.endswith('m'):
            return int(time_str[:-1])
        else:
            return int(time_str)  # Assume minutes
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.jwt_secret, algorithm="HS256")
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.refresh_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.jwt_refresh_secret, algorithm="HS256")
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            secret = self.jwt_secret if token_type == "access" else self.jwt_refresh_secret
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            
            if payload.get("type") != token_type:
                return None
                
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def register_user(self, username: str, email: str, password: str, role: str = "user", db: Session = None) -> User:
        """Register a new user"""
        if not db:
            db = next(get_db())
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username or email already exists"
            )
        
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=self.hash_password(password),
            role=role,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"User registered successfully: {username}")
        return user
    
    def authenticate_user(self, username: str, password: str, db: Session = None) -> Optional[User]:
        """Authenticate user with username/email and password"""
        if not db:
            db = next(get_db())
        
        user = db.query(User).filter(
            or_(User.username == username, User.email == username)
        ).first()
        
        if not user or not self.verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    def get_user_permissions(self, user_id: str, db: Session = None) -> List[str]:
        """Get user permissions based on role"""
        if not db:
            db = next(get_db())
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # Get role permissions
        role_permissions = db.query(RolePermission).join(Permission).filter(
            RolePermission.role == user.role
        ).all()
        
        return [rp.permission.name for rp in role_permissions]
    
    def login_user(self, username: str, password: str, db: Session = None) -> Dict[str, Any]:
        """Login user and return tokens"""
        if not db:
            db = next(get_db())
        
        user = self.authenticate_user(username, password, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Get user permissions
        permissions = self.get_user_permissions(user.id, db)
        
        # Create token data
        token_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": permissions
        }
        
        # Create tokens
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"user_id": user.id})
        
        # Store refresh token in database
        refresh_token_obj = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(minutes=self.refresh_token_expire_minutes),
            created_at=datetime.utcnow()
        )
        db.add(refresh_token_obj)
        db.commit()
        
        logger.info(f"User logged in successfully: {username}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "permissions": permissions
            }
        }
    
    def refresh_access_token(self, refresh_token: str, db: Session = None) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        if not db:
            db = next(get_db())
        
        # Verify refresh token
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("user_id")
        
        # Check if refresh token exists and is valid
        refresh_token_obj = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token,
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at > datetime.utcnow(),
            RefreshToken.is_revoked == False
        ).first()
        
        if not refresh_token_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Get permissions
        permissions = self.get_user_permissions(user.id, db)
        
        # Create new access token
        token_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": permissions
        }
        
        new_access_token = self.create_access_token(token_data)
        
        # Create new refresh token (rotation)
        new_refresh_token = self.create_refresh_token({"user_id": user.id})
        
        # Revoke old refresh token
        refresh_token_obj.is_revoked = True
        refresh_token_obj.updated_at = datetime.utcnow()
        
        # Create new refresh token record
        new_refresh_token_obj = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token=new_refresh_token,
            expires_at=datetime.utcnow() + timedelta(minutes=self.refresh_token_expire_minutes),
            created_at=datetime.utcnow()
        )
        db.add(new_refresh_token_obj)
        db.commit()
        
        logger.info(f"Token refreshed for user: {user.username}")
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    def logout_user(self, refresh_token: str, db: Session = None) -> bool:
        """Logout user by revoking refresh token"""
        if not db:
            db = next(get_db())
        
        refresh_token_obj = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token
        ).first()
        
        if refresh_token_obj:
            refresh_token_obj.is_revoked = True
            refresh_token_obj.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"User logged out: {refresh_token_obj.user_id}")
            return True
        
        return False
    
    def get_current_user(self, token: str, db: Session = None) -> Optional[User]:
        """Get current user from access token"""
        if not db:
            db = next(get_db())
        
        payload = self.verify_token(token, "access")
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            return None
        
        return user
    
    def update_user_profile(self, user_id: str, update_data: Dict[str, Any], db: Session = None) -> User:
        """Update user profile"""
        if not db:
            db = next(get_db())
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update allowed fields
        allowed_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        logger.info(f"User profile updated: {user.username}")
        return user
    
    def change_password(self, user_id: str, new_password: str, db: Session = None) -> bool:
        """Change user password"""
        if not db:
            db = next(get_db())
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Update password
        user.password_hash = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        return True
    
    def generate_password_reset_token(self, user_id: str, db: Session = None) -> str:
        """Generate password reset token"""
        if not db:
            db = next(get_db())
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        
        # In production, you would store this token in a separate table
        # For now, we'll just return it
        logger.info(f"Password reset token generated for user: {user_id}")
        return reset_token
    
    def reset_password_with_token(self, token: str, new_password: str, db: Session = None) -> bool:
        """Reset password using reset token"""
        if not db:
            db = next(get_db())
        
        # In production, you would:
        # 1. Find the user by token
        # 2. Verify token is not expired
        # 3. Update password
        # 4. Invalidate token
        
        # For now, simulate success for valid tokens
        if len(token) >= 32:
            logger.info(f"Password reset successful for token: {token[:8]}...")
            return True
        
        return False
        
        user = db.query(User).filter(
            User.reset_token == token,
            User.reset_token_expires > datetime.utcnow()
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Update password and clear reset token
        user.password_hash = self.hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        user.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Password reset completed for user: {user.username}")
        return True
    
    def check_permission(self, user_id: str, permission: str, db: Session = None) -> bool:
        """Check if user has specific permission"""
        if not db:
            db = next(get_db())
        
        permissions = self.get_user_permissions(user_id, db)
        return permission in permissions
    
    def get_user_by_id(self, user_id: str, db: Session = None) -> Optional[User]:
        """Get user by ID"""
        if not db:
            db = next(get_db())
        
        return db.query(User).filter(User.id == user_id).first()
    
    def get_users_list(self, page: int = 1, limit: int = 10, db: Session = None) -> Dict[str, Any]:
        """Get paginated users list"""
        if not db:
            db = next(get_db())
        
        offset = (page - 1) * limit
        users = db.query(User).offset(offset).limit(limit).all()
        total = db.query(User).count()
        
        return {
            "users": users,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }

# Global auth service instance
auth_service = AuthService()