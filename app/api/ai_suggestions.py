"""
AI Suggestions API Endpoints
Provides endpoints for testing and managing AI-powered suggestions
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.services.ai_suggestion_service import AISuggestionService
from app.models.database_models import AdminUser
from app.api.auth import get_current_admin_user

router = APIRouter(prefix="/api/ai-suggestions", tags=["ai-suggestions"])

class SuggestionRequest(BaseModel):
    """Request model for generating suggestions"""
    current_message: str
    ai_response: str
    user_id: str
    conversation_context: Dict[str, Any] = {}
    conversation_phase: str = "information_gathering"

class SuggestionResponse(BaseModel):
    """Response model for suggestions"""
    success: bool
    suggestions: List[str]
    total_count: int
    generation_time_ms: int
    fallback_used: bool = False
    timestamp: str

@router.post("/generate", response_model=SuggestionResponse)
async def generate_ai_suggestions(
    request: SuggestionRequest,
    db: Session = Depends(get_db)
):
    """Generate AI-powered suggestions for a conversation context"""
    try:
        start_time = datetime.now()
        
        # Initialize AI suggestion service
        ai_suggestion_service = AISuggestionService(db)
        
        # Generate suggestions
        suggestions = await ai_suggestion_service.generate_contextual_suggestions(
            conversation_context=request.conversation_context,
            current_message=request.current_message,
            ai_response=request.ai_response,
            user_id=request.user_id,
            conversation_phase=request.conversation_phase
        )
        
        # Calculate generation time
        generation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return SuggestionResponse(
            success=True,
            suggestions=suggestions,
            total_count=len(suggestions),
            generation_time_ms=int(generation_time),
            fallback_used=False,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating AI suggestions: {str(e)}"
        )

@router.get("/analytics", response_model=Dict[str, Any])
async def get_suggestion_analytics(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get analytics about AI suggestion usage"""
    try:
        ai_suggestion_service = AISuggestionService(db)
        analytics = ai_suggestion_service.get_suggestion_analytics()
        
        return {
            "success": True,
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting suggestion analytics: {str(e)}"
        )

@router.post("/test-scenarios")
async def test_suggestion_scenarios(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Test AI suggestions with predefined scenarios"""
    try:
        ai_suggestion_service = AISuggestionService(db)
        
        # Test scenarios
        scenarios = [
            {
                "name": "Plomberie - Information Gathering",
                "current_message": "J'ai un problème de plomberie",
                "ai_response": "Je vais vous aider avec votre problème de plomberie. Pouvez-vous me dire où vous vous trouvez?",
                "user_id": "test_user_1",
                "conversation_context": {
                    "extracted_info": {
                        "service_type": "plomberie"
                    }
                },
                "conversation_phase": "information_gathering"
            },
            {
                "name": "Électricité - Location Missing",
                "current_message": "Le courant a sauté",
                "ai_response": "Je comprends que vous avez une panne électrique. Dans quel quartier de Douala êtes-vous?",
                "user_id": "test_user_2",
                "conversation_context": {
                    "extracted_info": {
                        "service_type": "électricité",
                        "description": "courant qui a sauté"
                    }
                },
                "conversation_phase": "information_gathering"
            },
            {
                "name": "Urgence - Priorité Handling",
                "current_message": "C'est urgent!",
                "ai_response": "Je comprends que c'est urgent. Pouvez-vous me décrire le problème en détail?",
                "user_id": "test_user_3",
                "conversation_context": {
                    "extracted_info": {
                        "urgency": "élevée"
                    }
                },
                "conversation_phase": "information_gathering"
            }
        ]
        
        # Test each scenario
        results = []
        for scenario in scenarios:
            try:
                start_time = datetime.now()
                
                suggestions = await ai_suggestion_service.generate_contextual_suggestions(
                    conversation_context=scenario["conversation_context"],
                    current_message=scenario["current_message"],
                    ai_response=scenario["ai_response"],
                    user_id=scenario["user_id"],
                    conversation_phase=scenario["conversation_phase"]
                )
                
                generation_time = (datetime.now() - start_time).total_seconds() * 1000
                
                results.append({
                    "scenario": scenario["name"],
                    "success": True,
                    "suggestions": suggestions,
                    "suggestion_count": len(suggestions),
                    "generation_time_ms": int(generation_time),
                    "error": None
                })
                
            except Exception as e:
                results.append({
                    "scenario": scenario["name"],
                    "success": False,
                    "suggestions": [],
                    "suggestion_count": 0,
                    "generation_time_ms": 0,
                    "error": str(e)
                })
        
        # Calculate overall statistics
        successful_tests = sum(1 for r in results if r["success"])
        total_suggestions = sum(r["suggestion_count"] for r in results)
        avg_generation_time = sum(r["generation_time_ms"] for r in results) / len(results)
        
        return {
            "success": True,
            "test_results": results,
            "summary": {
                "total_scenarios": len(scenarios),
                "successful_tests": successful_tests,
                "success_rate": (successful_tests / len(scenarios)) * 100,
                "total_suggestions_generated": total_suggestions,
                "avg_generation_time_ms": int(avg_generation_time)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error testing suggestion scenarios: {str(e)}"
        )

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check for AI suggestion service"""
    try:
        ai_suggestion_service = AISuggestionService(db)
        
        # Test basic functionality
        test_suggestions = await ai_suggestion_service.generate_contextual_suggestions(
            conversation_context={},
            current_message="test",
            ai_response="test response",
            user_id="health_check",
            conversation_phase="information_gathering"
        )
        
        return {
            "success": True,
            "status": "healthy",
            "ai_service_available": True,
            "test_suggestions_generated": len(test_suggestions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }