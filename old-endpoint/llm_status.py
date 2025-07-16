"""
LLM Status API Endpoints
Provides endpoints for monitoring and managing multi-LLM provider status
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.services.multi_llm_service import MultiLLMService, LLMProvider
from app.models.database_models import AdminUser
from app.api.auth import get_current_admin_user

router = APIRouter(prefix="/api/llm", tags=["llm-management"])

class LLMStatusResponse(BaseModel):
    """Response model for LLM provider status"""
    providers: Dict[str, Any]
    recommended_provider: Optional[str]
    total_providers: int
    active_providers: int
    failed_providers: int
    timestamp: str

class ProviderSwitchRequest(BaseModel):
    """Request model for switching LLM provider"""
    provider: str
    reset_failures: bool = False

class TestLLMRequest(BaseModel):
    """Request model for testing LLM provider"""
    provider: Optional[str] = None
    test_message: str = "Bonjour, comment allez-vous?"

class TestLLMResponse(BaseModel):
    """Response model for LLM testing"""
    success: bool
    provider_used: str
    response: str
    response_time_ms: int
    error_message: Optional[str] = None

# Global multi-LLM instance
multi_llm_service = MultiLLMService()

@router.get("/status", response_model=LLMStatusResponse)
async def get_llm_status(
    db: Session = Depends(get_db)
):
    """Get status of all LLM providers"""
    try:
        provider_status = multi_llm_service.get_provider_status()
        recommended = multi_llm_service.get_recommended_provider()
        
        active_count = sum(1 for p in provider_status.values() if p["status"] == "operational")
        failed_count = sum(1 for p in provider_status.values() if p["status"] == "failed")
        
        return LLMStatusResponse(
            providers=provider_status,
            recommended_provider=recommended.value if recommended else None,
            total_providers=len(provider_status),
            active_providers=active_count,
            failed_providers=failed_count,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting LLM status: {str(e)}")

@router.post("/reset-failures")
async def reset_failed_providers(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Reset failed providers list (admin only)"""
    try:
        multi_llm_service.reset_failed_providers()
        return {"success": True, "message": "Failed providers list reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting failed providers: {str(e)}")

@router.post("/test", response_model=TestLLMResponse)
async def test_llm_provider(
    request: TestLLMRequest,
    db: Session = Depends(get_db)
):
    """Test LLM provider with a sample message"""
    try:
        import time
        start_time = time.time()
        
        # Prepare test message
        messages = [{"role": "user", "content": request.test_message}]
        system_prompt = "Tu es un assistant IA professionnel. Réponds brièvement et poliment."
        
        # Determine provider to test
        preferred_provider = None
        if request.provider:
            try:
                preferred_provider = LLMProvider(request.provider)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")
        
        # Generate response
        response = await multi_llm_service.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=100,
            temperature=0.7,
            preferred_provider=preferred_provider
        )
        
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        # Determine which provider was actually used
        provider_used = multi_llm_service.get_recommended_provider()
        
        return TestLLMResponse(
            success=True,
            provider_used=provider_used.value if provider_used else "unknown",
            response=response,
            response_time_ms=response_time_ms
        )
        
    except Exception as e:
        return TestLLMResponse(
            success=False,
            provider_used="none",
            response="",
            response_time_ms=0,
            error_message=str(e)
        )

@router.get("/health")
async def llm_health_check():
    """Health check for LLM management service"""
    try:
        status = multi_llm_service.get_provider_status()
        active_providers = [p for p, data in status.items() if data["status"] == "operational"]
        
        return {
            "success": True,
            "active_providers": active_providers,
            "total_providers": len(status),
            "service_operational": len(active_providers) > 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/analytics")
async def get_llm_analytics(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get LLM usage analytics (admin only)"""
    try:
        status = multi_llm_service.get_provider_status()
        
        # Calculate totals
        total_success = sum(p["success_count"] for p in status.values())
        total_failures = sum(p["failure_count"] for p in status.values())
        total_requests = total_success + total_failures
        
        # Provider breakdown
        provider_analytics = {}
        for provider, data in status.items():
            provider_requests = data["success_count"] + data["failure_count"]
            provider_analytics[provider] = {
                "success_count": data["success_count"],
                "failure_count": data["failure_count"],
                "success_rate": data["success_rate"],
                "usage_percentage": (provider_requests / total_requests * 100) if total_requests > 0 else 0,
                "status": data["status"]
            }
        
        return {
            "success": True,
            "total_requests": total_requests,
            "total_success": total_success,
            "total_failures": total_failures,
            "overall_success_rate": (total_success / total_requests * 100) if total_requests > 0 else 0,
            "provider_analytics": provider_analytics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting analytics: {str(e)}")

@router.get("/providers")
async def list_available_providers():
    """List all available LLM providers"""
    try:
        providers = []
        for provider in LLMProvider:
            providers.append({
                "id": provider.value,
                "name": provider.value.title(),
                "description": _get_provider_description(provider)
            })
        
        return {
            "success": True,
            "providers": providers,
            "total": len(providers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing providers: {str(e)}")

def _get_provider_description(provider: LLMProvider) -> str:
    """Get description for LLM provider"""
    descriptions = {
        LLMProvider.CLAUDE: "Anthropic Claude - Advanced reasoning and analysis",
        LLMProvider.GEMINI: "Google Gemini - Multimodal AI with vision capabilities",
        LLMProvider.OPENAI: "OpenAI GPT-4 - Versatile language model"
    }
    return descriptions.get(provider, "Unknown provider")