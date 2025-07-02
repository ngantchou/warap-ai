"""
Security middleware for Djobea AI
Implements rate limiting, security headers, input validation, and protection
"""

import time
import json
import redis
from typing import Dict, Any, Optional, List
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from loguru import logger
import re
import os

from app.config import get_settings
from app.services.auth_service import AuthService

settings = get_settings()

# Redis connection for rate limiting
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Redis connection established for rate limiting")
except Exception as e:
    logger.warning(f"Redis not available, using in-memory rate limiting: {e}")
    redis_client = None


# Rate limiter configuration
def get_redis_client():
    """Get Redis client for rate limiting"""
    return redis_client


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}" if redis_client else "memory://",
    default_limits=["1000 per hour"]
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        }
        
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value
        
        # Remove server information
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize input data"""
    
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'<meta[^>]*>',
        r'<link[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'data:text/html',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
    ]
    
    SQL_INJECTION_PATTERNS = [
        r'(\bUNION\b.*\bSELECT\b)',
        r'(\bSELECT\b.*\bFROM\b)',
        r'(\bINSERT\b.*\bINTO\b)',
        r'(\bUPDATE\b.*\bSET\b)',
        r'(\bDELETE\b.*\bFROM\b)',
        r'(\bDROP\b.*\bTABLE\b)',
        r'(\bCREATE\b.*\bTABLE\b)',
        r'(\bALTER\b.*\bTABLE\b)',
        r'(--\s)',
        r'(\/\*.*\*\/)',
        r'(\bEXEC\b|\bEXECUTE\b)',
        r'(\bSP_\w+)',
        r'(\bXP_\w+)',
    ]
    
    def __init__(self, app, max_content_length: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_content_length = max_content_length
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request entity too large"}
            )
        
        # Skip validation for webhook and auth endpoints (they have their own validation)
        if request.url.path.startswith("/webhook/") or request.url.path.startswith("/auth/"):
            return await call_next(request)
        
        # Validate and sanitize form data and JSON
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                await self._validate_request_data(request)
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
        
        return await call_next(request)
    
    async def _validate_request_data(self, request: Request):
        """Validate request data for security threats"""
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    self._validate_json_data(data)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON format"
                )
        elif "application/x-www-form-urlencoded" in content_type:
            form_data = await request.form()
            for key, value in form_data.items():
                self._validate_string_input(str(value))
    
    def _validate_json_data(self, data: Any):
        """Recursively validate JSON data"""
        if isinstance(data, dict):
            for key, value in data.items():
                self._validate_json_data(value)
        elif isinstance(data, list):
            for item in data:
                self._validate_json_data(item)
        elif isinstance(data, str):
            self._validate_string_input(data)
    
    def _validate_string_input(self, text: str):
        """Validate string input for XSS and SQL injection"""
        if not text:
            return
        
        # Check for XSS patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"XSS attempt detected: {pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"SQL injection attempt detected: {pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting middleware"""
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client or get_redis_client()
        
        # Rate limit configurations
        self.rate_limits = {
            "admin_login": {"limit": 5, "window": 900},  # 5 attempts per 15 minutes
            "webhook": {"limit": 100, "window": 60},     # 100 requests per minute
            "api": {"limit": 60, "window": 60},          # 60 requests per minute
            "default": {"limit": 30, "window": 60},      # 30 requests per minute
        }
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_ip = get_remote_address(request)
        
        # Determine rate limit category
        category = self._get_rate_limit_category(request)
        
        # Check rate limit
        if not await self._check_rate_limit(client_ip, category, request.url.path):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": self.rate_limits[category]["window"]
                },
                headers={"Retry-After": str(self.rate_limits[category]["window"])}
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        limit_info = await self._get_limit_info(client_ip, category, request.url.path)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limits[category]["limit"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rate_limits[category]["limit"] - limit_info["count"]))
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset_time"])
        
        return response
    
    def _get_rate_limit_category(self, request: Request) -> str:
        """Determine rate limit category based on request"""
        path = request.url.path
        
        if path.startswith("/admin/login") or path.startswith("/auth/login"):
            return "admin_login"
        elif path.startswith("/webhook/"):
            return "webhook"
        elif path.startswith("/api/") or path.startswith("/admin/api/"):
            return "api"
        else:
            return "default"
    
    async def _check_rate_limit(self, client_ip: str, category: str, endpoint: str) -> bool:
        """Check if request is within rate limit"""
        if not self.redis_client:
            # Fallback to simple in-memory check (not recommended for production)
            return True
        
        key = f"rate_limit:{category}:{client_ip}:{endpoint}"
        window = self.rate_limits[category]["window"]
        limit = self.rate_limits[category]["limit"]
        
        current_time = int(time.time())
        window_start = current_time - (current_time % window)
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.multi()
            
            # Increment counter for current window
            pipe.hincrby(key, str(window_start), 1)
            pipe.expire(key, window * 2)  # Keep data for 2 windows
            
            # Get current count
            pipe.hget(key, str(window_start))
            
            results = pipe.execute()
            current_count = int(results[2] or 0)
            
            return current_count <= limit
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return True  # Fail open
    
    async def _get_limit_info(self, client_ip: str, category: str, endpoint: str) -> Dict[str, int]:
        """Get current rate limit information"""
        if not self.redis_client:
            return {"count": 0, "reset_time": int(time.time()) + self.rate_limits[category]["window"]}
        
        key = f"rate_limit:{category}:{client_ip}:{endpoint}"
        window = self.rate_limits[category]["window"]
        
        current_time = int(time.time())
        window_start = current_time - (current_time % window)
        
        try:
            count = int(self.redis_client.hget(key, str(window_start)) or 0)
            reset_time = window_start + window
            
            return {"count": count, "reset_time": reset_time}
        except Exception:
            return {"count": 0, "reset_time": current_time + window}


class WebhookSecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware specifically for webhook endpoints"""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_service = None
    
    async def dispatch(self, request: Request, call_next):
        # Only apply to webhook endpoints
        if not request.url.path.startswith("/webhook/"):
            return await call_next(request)
        
        # Initialize auth service
        if not self.auth_service:
            from app.database import get_db
            db = next(get_db())
            self.auth_service = AuthService(db)
        
        # Validate Twilio webhook signature
        if request.url.path.startswith("/webhook/whatsapp"):
            if not await self._validate_twilio_webhook(request):
                logger.warning(f"Invalid Twilio webhook signature from {get_remote_address(request)}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Invalid webhook signature"}
                )
        
        return await call_next(request)
    
    async def _validate_twilio_webhook(self, request: Request) -> bool:
        """Validate Twilio webhook signature"""
        signature = request.headers.get("X-Twilio-Signature")
        if not signature:
            return False
        
        # Get request URL and form parameters
        url = str(request.url)
        
        # Get form data
        try:
            form_data = await request.form()
            params = dict(form_data)
            
            return self.auth_service.validate_twilio_signature(signature, url, params)
        except Exception as e:
            logger.error(f"Error validating Twilio signature: {e}")
            return False


def setup_cors_middleware(app):
    """Configure CORS middleware"""
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5000",
        "https://*.replit.app",
        "https://*.replit.dev",
    ]
    
    # Add production domains if configured
    if settings.debug:
        allowed_origins.extend([
            "http://localhost:8000",
            "http://127.0.0.1:5000",
            "http://127.0.0.1:8000",
        ])
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    )


def setup_security_middleware(app):
    """Setup all security middleware"""
    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Custom security middleware (order matters)
    app.add_middleware(WebhookSecurityMiddleware)
    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    app.add_middleware(InputValidationMiddleware, max_content_length=10 * 1024 * 1024)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # CORS
    setup_cors_middleware(app)
    
    logger.info("Security middleware configured successfully")