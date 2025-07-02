"""
Authentication service for Djobea AI admin interface
Provides JWT-based authentication with bcrypt password hashing
"""

import os
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from loguru import logger

from app.models.database_models import AdminUser, SecurityLog, AdminRole
from app.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


class AuthService:
    """Authentication service for admin users"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError:
            return None
    
    def get_user_by_username(self, username: str) -> Optional[AdminUser]:
        """Get user by username"""
        return self.db.query(AdminUser).filter(AdminUser.username == username).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[AdminUser]:
        """Get user by ID"""
        return self.db.query(AdminUser).filter(AdminUser.id == user_id).first()
    
    def is_user_locked(self, user: AdminUser) -> bool:
        """Check if user account is locked"""
        if not user.locked_until:
            return False
        return datetime.now(timezone.utc) < user.locked_until.replace(tzinfo=timezone.utc)
    
    def lock_user_account(self, user: AdminUser) -> None:
        """Lock user account after failed attempts"""
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        self.db.commit()
        logger.warning(f"User {user.username} account locked due to failed login attempts")
    
    def reset_failed_attempts(self, user: AdminUser) -> None:
        """Reset failed login attempts"""
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.commit()
    
    def increment_failed_attempts(self, user: AdminUser) -> None:
        """Increment failed login attempts"""
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            self.lock_user_account(user)
        else:
            self.db.commit()
    
    def log_security_event(self, event_type: str, user_id: Optional[int] = None, 
                          ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None) -> None:
        """Log security events"""
        security_log = SecurityLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        self.db.add(security_log)
        self.db.commit()
    
    def authenticate_user(self, username: str, password: str, ip_address: str, 
                         user_agent: str) -> Optional[AdminUser]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(username)
        
        if not user:
            self.log_security_event("failed_login_invalid_user", 
                                   ip_address=ip_address, user_agent=user_agent,
                                   details={"username": username})
            return None
        
        if not user.is_active:
            self.log_security_event("failed_login_inactive_user", user_id=user.id,
                                   ip_address=ip_address, user_agent=user_agent)
            return None
        
        if self.is_user_locked(user):
            self.log_security_event("failed_login_locked_user", user_id=user.id,
                                   ip_address=ip_address, user_agent=user_agent)
            return None
        
        if not self.verify_password(password, user.hashed_password):
            self.increment_failed_attempts(user)
            self.log_security_event("failed_login_wrong_password", user_id=user.id,
                                   ip_address=ip_address, user_agent=user_agent)
            return None
        
        # Successful authentication
        self.reset_failed_attempts(user)
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        
        self.log_security_event("successful_login", user_id=user.id,
                               ip_address=ip_address, user_agent=user_agent)
        
        return user
    
    def create_admin_user(self, username: str, email: str, password: str, 
                         role: AdminRole = AdminRole.ADMIN) -> AdminUser:
        """Create new admin user"""
        hashed_password = self.get_password_hash(password)
        
        admin_user = AdminUser(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role
        )
        
        self.db.add(admin_user)
        self.db.commit()
        self.db.refresh(admin_user)
        
        self.log_security_event("user_created", user_id=admin_user.id,
                               details={"username": username, "role": role})
        
        return admin_user
    
    def change_password(self, user: AdminUser, new_password: str) -> bool:
        """Change user password"""
        try:
            user.hashed_password = self.get_password_hash(new_password)
            user.password_changed_at = datetime.now(timezone.utc)
            self.db.commit()
            
            self.log_security_event("password_changed", user_id=user.id)
            return True
        except Exception as e:
            logger.error(f"Failed to change password for user {user.username}: {e}")
            return False
    
    def validate_twilio_signature(self, signature: str, url: str, params: Dict[str, str]) -> bool:
        """Validate Twilio webhook signature"""
        auth_token = settings.twilio_auth_token
        if not auth_token:
            logger.warning("Twilio auth token not configured")
            return False
        
        # Sort parameters and create query string
        sorted_params = sorted(params.items())
        data = url + ''.join(f'{k}{v}' for k, v in sorted_params)
        
        # Create signature
        expected_signature = hmac.new(
            auth_token.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Compare signatures
        import base64
        expected_signature_b64 = base64.b64encode(expected_signature).decode()
        
        return hmac.compare_digest(signature, expected_signature_b64)
    
    def sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent XSS and injection attacks"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript:', 'onclick', 'onload']
        sanitized = text
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        return sanitized[:max_length].strip()
    
    def validate_phone_number(self, phone: str) -> str:
        """Validate and normalize phone number"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone))
        
        # Cameroon phone number validation
        if len(digits_only) == 9 and digits_only.startswith('6'):
            return f"+237{digits_only}"
        elif len(digits_only) == 12 and digits_only.startswith('237'):
            return f"+{digits_only}"
        elif len(digits_only) == 13 and digits_only.startswith('237'):
            return f"+{digits_only}"
        
        raise ValueError(f"Invalid Cameroon phone number: {phone}")


def get_current_user(db: Session, token: str) -> AdminUser:
    """Get current authenticated user from JWT token"""
    auth_service = AuthService(db)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = auth_service.verify_token(token)
    if not payload:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    user = auth_service.get_user_by_id(int(user_id))
    if not user or not user.is_active:
        raise credentials_exception
    
    return user


def require_role(required_role: AdminRole):
    """Decorator to require specific admin role"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Implementation will be added in the router
            return func(*args, **kwargs)
        return wrapper
    return decorator