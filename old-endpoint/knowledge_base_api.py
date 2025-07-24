"""
Knowledge Base API - Contextual Information System
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from app.database import get_db
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.contextual_support_service import ContextualSupportService
from app.services.knowledge_maintenance_service import KnowledgeMaintenanceService
from loguru import logger

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge_base"])

# Request/Response Models
class KnowledgeSearchRequest(BaseModel):
    query: str
    service_type: Optional[str] = None
    zone: Optional[str] = None
    user_type: Optional[str] = None

class SupportRequest(BaseModel):
    message: str
    user_id: str
    context: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    content_id: str
    content_type: str  # 'faq' or 'article'
    helpful: bool
    comment: Optional[str] = None
    rating: Optional[int] = None

class PricingUpdateRequest(BaseModel):
    service_data: List[Dict[str, Any]]

@router.get("/search")
async def search_knowledge(
    query: str = Query(..., description="Search query"),
    service_type: Optional[str] = Query(None, description="Service type filter"),
    zone: Optional[str] = Query(None, description="Zone filter"),
    user_type: Optional[str] = Query(None, description="User type filter"),
    db: Session = Depends(get_db)
):
    """Search knowledge base with contextual filtering"""
    try:
        service = KnowledgeBaseService(db)
        results = service.search_knowledge(query, service_type, zone, user_type)
        return results
    except Exception as e:
        logger.error(f"Error searching knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/faq/category/{category_id}")
async def get_faq_by_category(
    category_id: str,
    service_type: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get FAQs by category with contextual filtering"""
    try:
        service = KnowledgeBaseService(db)
        faqs = service.get_faq_by_category(category_id, service_type, zone)
        return {
            "success": True,
            "data": faqs,
            "category_id": category_id
        }
    except Exception as e:
        logger.error(f"Error getting FAQs by category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pricing/{service_type}/{zone}")
async def get_pricing_info(
    service_type: str,
    zone: str,
    db: Session = Depends(get_db)
):
    """Get contextual pricing information"""
    try:
        service = KnowledgeBaseService(db)
        pricing = service.get_pricing_info(service_type, zone)
        
        if pricing:
            return {
                "success": True,
                "data": pricing
            }
        else:
            return {
                "success": False,
                "error": "Pricing information not found",
                "data": None
            }
    except Exception as e:
        logger.error(f"Error getting pricing info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processes/{service_type}")
async def get_service_processes(
    service_type: str,
    zone: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get service processes with contextual information"""
    try:
        service = KnowledgeBaseService(db)
        processes = service.get_service_processes(service_type, zone)
        return {
            "success": True,
            "data": processes,
            "service_type": service_type
        }
    except Exception as e:
        logger.error(f"Error getting service processes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/support/detect")
async def detect_support_need(
    request: SupportRequest,
    db: Session = Depends(get_db)
):
    """Detect support need and provide contextual response"""
    try:
        service = ContextualSupportService(db)
        result = service.detect_support_need(
            request.message, 
            request.user_id, 
            request.context
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error detecting support need: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/support/session")
async def start_support_session(
    user_id: str = Body(..., embed=True),
    session_type: str = Body("bot", embed=True),
    db: Session = Depends(get_db)
):
    """Start a new support session"""
    try:
        service = ContextualSupportService(db)
        session_id = service.start_support_session(user_id, session_type)
        
        if session_id:
            return {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "status": "active",
                    "type": session_type
                }
            }
        else:
            return {
                "success": False,
                "error": "Failed to start support session"
            }
    except Exception as e:
        logger.error(f"Error starting support session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/support/escalate")
async def escalate_support(
    session_id: str = Body(...),
    user_id: str = Body(...),
    reason: str = Body(...),
    priority: str = Body("medium"),
    db: Session = Depends(get_db)
):
    """Escalate support to human agent"""
    try:
        service = ContextualSupportService(db)
        result = service.escalate_support(session_id, user_id, reason, priority)
        return result
    except Exception as e:
        logger.error(f"Error escalating support: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/support/guided-resolution/{issue_type}")
async def get_guided_resolution(
    issue_type: str,
    service_type: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get guided resolution for common issues"""
    try:
        service = ContextualSupportService(db)
        result = service.provide_guided_resolution(issue_type, service_type, zone)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting guided resolution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    user_id: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Submit feedback on knowledge content"""
    try:
        service = KnowledgeBaseService(db)
        
        if request.content_type == 'faq':
            success = service.mark_faq_helpful(request.content_id, request.helpful)
        else:
            # For articles, would implement article feedback
            success = True
        
        return {
            "success": success,
            "message": "Feedback submitted successfully" if success else "Failed to submit feedback"
        }
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/question")
async def record_question(
    user_id: str = Body(...),
    question: str = Body(...),
    context: Optional[Dict[str, Any]] = Body(None),
    service_type: Optional[str] = Body(None),
    zone: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Record user question for analysis"""
    try:
        service = KnowledgeBaseService(db)
        question_id = service.record_user_question(
            user_id, question, context, service_type, zone
        )
        
        return {
            "success": True,
            "data": {
                "question_id": question_id,
                "status": "recorded"
            }
        }
    except Exception as e:
        logger.error(f"Error recording question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/support")
async def get_support_analytics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get support analytics for improvement"""
    try:
        service = ContextualSupportService(db)
        analytics = service.get_support_analytics(days)
        return {
            "success": True,
            "data": analytics
        }
    except Exception as e:
        logger.error(f"Error getting support analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/popular-questions")
async def get_popular_questions(
    service_type: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    limit: int = Query(10),
    db: Session = Depends(get_db)
):
    """Get popular questions for content improvement"""
    try:
        service = KnowledgeBaseService(db)
        questions = service.get_popular_questions(service_type, zone, limit)
        return {
            "success": True,
            "data": questions
        }
    except Exception as e:
        logger.error(f"Error getting popular questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Maintenance endpoints
@router.post("/maintenance/update-pricing")
async def update_pricing_information(
    request: PricingUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update pricing information automatically"""
    try:
        service = KnowledgeMaintenanceService(db)
        result = service.update_pricing_information(request.service_data)
        return result
    except Exception as e:
        logger.error(f"Error updating pricing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/analyze-questions")
async def analyze_user_questions(
    days: int = Body(30, embed=True),
    db: Session = Depends(get_db)
):
    """Analyze user questions to identify content gaps"""
    try:
        service = KnowledgeMaintenanceService(db)
        result = service.analyze_user_questions(days)
        return result
    except Exception as e:
        logger.error(f"Error analyzing questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/update-versions")
async def update_content_versions(db: Session = Depends(get_db)):
    """Update content versions and track changes"""
    try:
        service = KnowledgeMaintenanceService(db)
        result = service.update_content_versions()
        return result
    except Exception as e:
        logger.error(f"Error updating versions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/optimize-content")
async def optimize_content_performance(db: Session = Depends(get_db)):
    """Optimize content based on performance metrics"""
    try:
        service = KnowledgeMaintenanceService(db)
        result = service.optimize_content_performance()
        return result
    except Exception as e:
        logger.error(f"Error optimizing content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/generate-faqs")
async def generate_faq_from_questions(
    threshold: int = Body(5, embed=True),
    db: Session = Depends(get_db)
):
    """Generate new FAQs from frequently asked questions"""
    try:
        service = KnowledgeMaintenanceService(db)
        result = service.generate_faq_from_questions(threshold)
        return result
    except Exception as e:
        logger.error(f"Error generating FAQs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/cleanup")
async def cleanup_outdated_content(
    days: int = Body(90, embed=True),
    db: Session = Depends(get_db)
):
    """Clean up outdated or low-performing content"""
    try:
        service = KnowledgeMaintenanceService(db)
        result = service.cleanup_outdated_content(days)
        return result
    except Exception as e:
        logger.error(f"Error cleaning up content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/maintenance/analytics")
async def get_maintenance_analytics(db: Session = Depends(get_db)):
    """Get maintenance analytics and system health"""
    try:
        service = KnowledgeMaintenanceService(db)
        result = service.get_maintenance_analytics()
        return result
    except Exception as e:
        logger.error(f"Error getting maintenance analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))