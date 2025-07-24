"""
Authentication utilities for API access
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import AdminUser
from app.services.auth_service import AuthService
from loguru import logger

# Security scheme for Bearer token
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AdminUser:
    """Get current authenticated user from JWT token"""
    auth_service = AuthService(db)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = auth_service.verify_token(credentials.credentials)
        if not payload:
            raise credentials_exception
        
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        
        user = auth_service.get_user_by_id(int(user_id))
        if not user or not user.is_active:
            raise credentials_exception
        
        return user
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception