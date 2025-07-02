"""
Simple demo provider authentication for testing the dashboard
Bypasses complex model relationships for immediate testing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import secrets
import hashlib
from loguru import logger

router = APIRouter(prefix="/demo/auth", tags=["Provider Demo Auth"])

# In-memory storage for demo (would use Redis in production)
demo_sessions = {}
demo_otps = {}

# Demo provider credentials
DEMO_PROVIDERS = {
    "+237690000003": {"id": 3, "name": "Paul Réparateur", "service": "réparation électroménager"},
    "+237677123456": {"id": 4, "name": "Jean-Claude Mbida", "service": "plomberie"},
    "+237681234567": {"id": 5, "name": "Marie Fotso", "service": "électricité"},
    "237690000003": {"id": 3, "name": "Paul Réparateur", "service": "réparation électroménager"},
    "237677123456": {"id": 4, "name": "Jean-Claude Mbida", "service": "plomberie"},
    "237681234567": {"id": 5, "name": "Marie Fotso", "service": "électricité"},
}

class OTPRequest(BaseModel):
    phone_number: str

class OTPVerification(BaseModel):
    session_token: str
    otp_code: str
    otp_hash: str

@router.post("/send-otp")
async def send_demo_otp(request: OTPRequest):
    """Send OTP for demo (displays OTP in logs)"""
    phone = request.phone_number.strip()
    
    # Normalize phone number
    if phone.startswith("+"):
        phone = phone[1:]
    
    if phone not in DEMO_PROVIDERS:
        raise HTTPException(status_code=400, detail="Provider not found")
    
    # Generate demo OTP
    otp_code = "123456"  # Fixed OTP for demo
    session_token = secrets.token_urlsafe(32)
    otp_hash = hashlib.sha256(f"{otp_code}_{session_token}".encode()).hexdigest()
    
    # Store in demo session
    demo_sessions[session_token] = {
        "phone": phone,
        "provider": DEMO_PROVIDERS[phone],
        "expires_at": "2025-07-02T15:00:00Z"  # Demo expiry
    }
    demo_otps[session_token] = otp_code
    
    logger.info(f"DEMO: OTP for {phone} is: {otp_code}")
    
    return {
        "success": True,
        "message": "OTP sent successfully (check logs for demo OTP)",
        "session_token": session_token,
        "otp_hash": otp_hash,
        "expires_in": 300,
        "demo_note": f"Demo OTP: {otp_code}"  # For demo only
    }

@router.post("/verify-otp")
async def verify_demo_otp(request: OTPVerification):
    """Verify OTP for demo"""
    session_token = request.session_token
    otp_code = request.otp_code
    
    if session_token not in demo_sessions:
        raise HTTPException(status_code=400, detail="Invalid session token")
    
    if session_token not in demo_otps:
        raise HTTPException(status_code=400, detail="OTP expired or invalid")
    
    stored_otp = demo_otps[session_token]
    if otp_code != stored_otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    
    # Generate auth token
    auth_token = secrets.token_urlsafe(32)
    session_data = demo_sessions[session_token]
    
    # Store auth session
    demo_sessions[auth_token] = {
        "type": "authenticated",
        "provider_id": session_data["provider"]["id"],
        "provider_name": session_data["provider"]["name"],
        "phone": session_data["phone"],
        "expires_at": "2025-07-02T20:00:00Z"  # Extended demo expiry
    }
    
    # Clean up OTP session
    del demo_otps[session_token]
    
    logger.info(f"DEMO: Provider {session_data['provider']['name']} authenticated successfully")
    
    return {
        "success": True,
        "message": "Authentication successful",
        "auth_token": auth_token,
        "provider": session_data["provider"]
    }

def verify_demo_auth(token: str) -> Dict[str, Any]:
    """Verify authentication token for demo"""
    if token not in demo_sessions:
        return None
    
    session = demo_sessions[token]
    if session.get("type") != "authenticated":
        return None
    
    return {
        "id": session["provider_id"],
        "name": session["provider_name"],
        "phone_number": session["phone"]
    }