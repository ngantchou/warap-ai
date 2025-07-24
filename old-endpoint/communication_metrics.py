"""
Communication Metrics API for Enhanced Agent-LLM Communication
Provides endpoints to monitor and improve conversation quality
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.database import get_db
from app.services.natural_conversation_engine import NaturalConversationEngine
from app.api.auth import get_current_admin_user
from app.models.database_models import AdminUser

router = APIRouter()

@router.get("/metrics")
async def get_communication_metrics(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get current communication metrics"""
    
    try:
        # Initialize conversation engine
        conversation_engine = NaturalConversationEngine(db)
        
        # Get metrics from enhanced communication system
        metrics = conversation_engine.get_communication_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")

@router.get("/improvement-suggestions")
async def get_improvement_suggestions(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get suggestions for improving communication quality"""
    
    try:
        # Initialize conversation engine
        conversation_engine = NaturalConversationEngine(db)
        
        # Get improvement suggestions
        suggestions = conversation_engine.get_improvement_suggestions()
        
        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting suggestions: {str(e)}")

@router.post("/test-enhanced-communication")
async def test_enhanced_communication(
    test_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Test the enhanced communication system with sample data"""
    
    try:
        # Initialize conversation engine
        conversation_engine = NaturalConversationEngine(db)
        
        # Test message
        test_message = test_data.get("message", "J'ai un problème de plomberie à Douala")
        user_identifier = test_data.get("user_id", "test_user_237691924172")
        
        # Process with enhanced system
        result = await conversation_engine.process_natural_conversation(
            user_identifier=user_identifier,
            message=test_message
        )
        
        # Get metrics after processing
        metrics = conversation_engine.get_communication_metrics()
        
        return {
            "success": True,
            "test_result": {
                "input_message": test_message,
                "response": result.response_message,
                "confidence_score": result.confidence_score,
                "system_actions": result.system_actions,
                "requires_follow_up": result.requires_follow_up
            },
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing communication: {str(e)}")

@router.get("/conversation-analytics")
async def get_conversation_analytics(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get conversation analytics for the last 24 hours"""
    
    try:
        from app.models.database_models import Conversation
        
        # Get recent conversations
        recent_conversations = db.query(Conversation).filter(
            Conversation.created_at >= datetime.now() - timedelta(days=1)
        ).order_by(Conversation.created_at.desc()).limit(50).all()
        
        analytics = {
            "total_conversations": len(recent_conversations),
            "unique_users": len(set(conv.user_id for conv in recent_conversations)),
            "average_message_length": 0,
            "conversation_types": {},
            "hourly_distribution": {}
        }
        
        if recent_conversations:
            # Calculate average message length
            total_length = sum(len(conv.message_content or "") for conv in recent_conversations)
            analytics["average_message_length"] = total_length / len(recent_conversations)
            
            # Analyze conversation types
            for conv in recent_conversations:
                message = (conv.message_content or "").lower()
                if any(word in message for word in ["plomberie", "plumber", "eau", "tuyau"]):
                    analytics["conversation_types"]["plomberie"] = analytics["conversation_types"].get("plomberie", 0) + 1
                elif any(word in message for word in ["électricité", "electric", "lumière", "courant"]):
                    analytics["conversation_types"]["électricité"] = analytics["conversation_types"].get("électricité", 0) + 1
                elif any(word in message for word in ["électroménager", "appliance", "frigo", "machine"]):
                    analytics["conversation_types"]["électroménager"] = analytics["conversation_types"].get("électroménager", 0) + 1
                else:
                    analytics["conversation_types"]["général"] = analytics["conversation_types"].get("général", 0) + 1
            
            # Hourly distribution
            for conv in recent_conversations:
                hour = conv.created_at.hour
                analytics["hourly_distribution"][f"{hour}:00"] = analytics["hourly_distribution"].get(f"{hour}:00", 0) + 1
        
        return {
            "success": True,
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting analytics: {str(e)}")

@router.get("/system-health")
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin_user)
):
    """Get system health metrics related to communication"""
    
    try:
        from app.models.database_models import Provider, ServiceRequest
        
        # Get system health metrics
        active_providers = db.query(Provider).filter(Provider.is_active == True).count()
        total_providers = db.query(Provider).count()
        
        # Get recent request stats
        recent_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= datetime.now() - timedelta(hours=24)
        ).count()
        
        pending_requests = db.query(ServiceRequest).filter(
            ServiceRequest.status == "PENDING"
        ).count()
        
        health_metrics = {
            "provider_availability": {
                "active_providers": active_providers,
                "total_providers": total_providers,
                "availability_rate": (active_providers / max(total_providers, 1)) * 100
            },
            "request_processing": {
                "recent_requests_24h": recent_requests,
                "pending_requests": pending_requests,
                "processing_load": "normal" if pending_requests < 10 else "high"
            },
            "system_status": {
                "database_connection": "healthy",
                "ai_service": "operational",
                "communication_system": "enhanced"
            }
        }
        
        return {
            "success": True,
            "health_metrics": health_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting system health: {str(e)}")