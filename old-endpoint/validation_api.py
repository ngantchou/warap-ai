"""
Validation API - RESTful endpoints for validation and improvement system
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from app.database import get_db
from app.services.validation_service import ValidationService
from app.services.suggestion_engine import SuggestionEngine
from app.services.error_management_service import ErrorManagementService
from app.services.continuous_improvement_service import ContinuousImprovementService
from app.models.validation_models import ValidationLog, ErrorLog, ImprovementSuggestion

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])

# Initialize services
validation_service = ValidationService()
suggestion_engine = SuggestionEngine()
error_management = ErrorManagementService()
improvement_service = ContinuousImprovementService()

@router.post("/validate")
async def validate_response(
    llm_response: Dict[str, Any],
    original_query: str,
    context: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Validate LLM response and return validation results
    """
    try:
        # Validate the response
        validation_result = await validation_service.validate_llm_response(
            db, llm_response, original_query, context or {}
        )
        
        return {
            "success": True,
            "validation_result": {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "corrections": validation_result.corrections,
                "confidence_score": validation_result.confidence_score,
                "suggestions": validation_result.suggestions,
                "corrected_data": validation_result.corrected_data
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.get("/suggestions")
async def get_suggestions(
    query: str,
    zone_code: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get intelligent suggestions for a query
    """
    try:
        # Generate suggestions
        suggestion_response = await suggestion_engine.generate_suggestions(
            db, query, zone_code, user_id
        )
        
        return {
            "success": True,
            "suggestions": [
                {
                    "type": s.type.value,
                    "priority": s.priority.value,
                    "service_code": s.service_code,
                    "zone_code": s.zone_code,
                    "title": s.title,
                    "description": s.description,
                    "confidence": s.confidence,
                    "metadata": s.metadata,
                    "reasoning": s.reasoning
                }
                for s in suggestion_response.suggestions[:limit]
            ],
            "total_count": suggestion_response.total_count,
            "categories": suggestion_response.categories,
            "recommendation_confidence": suggestion_response.recommendation_confidence
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")

@router.post("/handle-error")
async def handle_error(
    error_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Handle system error with intelligent retry and suggestions
    """
    try:
        # Create mock exception from error data
        error_message = error_data.get("message", "Unknown error")
        error_type = error_data.get("type")
        context = error_data.get("context", {})
        
        # Convert to exception-like object
        class MockError(Exception):
            def __init__(self, message):
                self.message = message
            
            def __str__(self):
                return self.message
        
        mock_error = MockError(error_message)
        
        # Handle the error
        resolution = await error_management.handle_error(
            db, mock_error, context, error_type
        )
        
        return {
            "success": True,
            "resolution": {
                "resolved": resolution.resolved,
                "resolution_method": resolution.resolution_method,
                "corrected_data": resolution.corrected_data,
                "retry_needed": resolution.retry_needed,
                "escalation_needed": resolution.escalation_needed,
                "suggestions": resolution.suggestions
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error handling failed: {str(e)}")

@router.get("/error-statistics")
async def get_error_statistics(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get error statistics for monitoring
    """
    try:
        # Get error statistics
        error_stats = await error_management.get_error_statistics(db)
        
        return {
            "success": True,
            "statistics": error_stats,
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error statistics: {str(e)}")

@router.get("/improvement-analysis")
async def get_improvement_analysis(
    db: Session = Depends(get_db)
):
    """
    Get system improvement analysis and recommendations
    """
    try:
        # Generate improvement report
        improvement_report = await improvement_service.analyze_system_performance(db)
        
        return {
            "success": True,
            "report": {
                "report_id": improvement_report.report_id,
                "generated_at": improvement_report.generated_at.isoformat(),
                "overall_score": improvement_report.overall_score,
                "error_patterns": [
                    {
                        "pattern_id": pattern.pattern_id,
                        "error_type": pattern.error_type,
                        "frequency": pattern.frequency,
                        "common_causes": pattern.common_causes,
                        "suggested_fixes": pattern.suggested_fixes,
                        "confidence": pattern.confidence
                    }
                    for pattern in improvement_report.error_patterns
                ],
                "performance_insights": [
                    {
                        "metric_name": insight.metric_name,
                        "current_value": insight.current_value,
                        "target_value": insight.target_value,
                        "improvement_potential": insight.improvement_potential,
                        "recommendations": insight.recommendations
                    }
                    for insight in improvement_report.performance_insights
                ],
                "keyword_suggestions": improvement_report.keyword_suggestions,
                "validation_improvements": improvement_report.validation_improvements,
                "priority_actions": improvement_report.priority_actions
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Improvement analysis failed: {str(e)}")

@router.post("/apply-improvements")
async def apply_improvements(
    improvements: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """
    Apply approved improvements to the system
    """
    try:
        # Apply improvements
        results = await improvement_service.apply_improvements(db, improvements)
        
        return {
            "success": True,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply improvements: {str(e)}")

@router.get("/improvement-metrics")
async def get_improvement_metrics(
    db: Session = Depends(get_db)
):
    """
    Get improvement metrics for monitoring
    """
    try:
        # Get improvement metrics
        metrics = await improvement_service.get_improvement_metrics(db)
        
        return {
            "success": True,
            "metrics": metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get improvement metrics: {str(e)}")

@router.get("/validation-logs")
async def get_validation_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get validation logs for analysis
    """
    try:
        # Get validation logs
        logs = db.query(ValidationLog).order_by(
            ValidationLog.timestamp.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "success": True,
            "logs": [
                {
                    "id": log.id,
                    "validation_id": log.validation_id,
                    "confidence_score": log.confidence_score,
                    "validation_success": log.validation_success,
                    "processing_time_ms": log.processing_time_ms,
                    "errors": json.loads(log.errors) if log.errors else [],
                    "corrections": json.loads(log.corrections) if log.corrections else [],
                    "timestamp": log.timestamp.isoformat()
                }
                for log in logs
            ],
            "total_count": db.query(ValidationLog).count()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get validation logs: {str(e)}")

@router.get("/error-logs")
async def get_error_logs(
    error_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get error logs with filtering
    """
    try:
        # Build query
        query = db.query(ErrorLog)
        
        if error_type:
            query = query.filter(ErrorLog.error_type == error_type)
        
        if severity:
            query = query.filter(ErrorLog.severity == severity)
        
        # Get logs
        logs = query.order_by(
            ErrorLog.timestamp.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "success": True,
            "logs": [
                {
                    "id": log.id,
                    "error_id": log.error_id,
                    "error_type": log.error_type,
                    "severity": log.severity,
                    "message": log.message,
                    "user_id": log.user_id,
                    "session_id": log.session_id,
                    "timestamp": log.timestamp.isoformat()
                }
                for log in logs
            ],
            "total_count": query.count()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get error logs: {str(e)}")

@router.get("/system-health")
async def get_system_health(
    db: Session = Depends(get_db)
):
    """
    Get current system health status
    """
    try:
        # Get validation metrics
        validation_metrics = await validation_service.get_validation_metrics(db)
        
        # Get error statistics
        error_stats = await error_management.get_error_statistics(db)
        
        # Get improvement metrics
        improvement_metrics = await improvement_service.get_improvement_metrics(db)
        
        # Calculate overall health score
        health_score = 10.0  # Start with perfect score
        
        # Adjust based on validation success rate
        if validation_metrics.success_rate < 0.9:
            health_score -= (0.9 - validation_metrics.success_rate) * 20
        
        # Adjust based on error rate
        if error_stats['recent_errors'] > 10:
            health_score -= min(3.0, error_stats['recent_errors'] / 10)
        
        # Adjust based on resolution rate
        if error_stats['resolution_rate'] < 0.8:
            health_score -= (0.8 - error_stats['resolution_rate']) * 10
        
        health_score = max(0.0, min(10.0, health_score))
        
        return {
            "success": True,
            "health": {
                "overall_score": health_score,
                "status": "healthy" if health_score > 7 else "degraded" if health_score > 4 else "critical",
                "validation_metrics": {
                    "total_validations": validation_metrics.total_validations,
                    "success_rate": validation_metrics.success_rate,
                    "auto_correction_rate": validation_metrics.auto_correction_rate
                },
                "error_statistics": error_stats,
                "improvement_metrics": improvement_metrics,
                "last_updated": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")

@router.post("/feedback")
async def submit_feedback(
    feedback_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Submit feedback on suggestions or system performance
    """
    try:
        # Process feedback (implementation depends on feedback model)
        feedback_type = feedback_data.get("type")
        rating = feedback_data.get("rating")
        comment = feedback_data.get("comment")
        
        # Log feedback for improvement
        # This would typically save to a feedback table
        
        return {
            "success": True,
            "message": "Feedback submitted successfully",
            "feedback_id": f"feedback_{datetime.utcnow().timestamp()}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")

@router.get("/performance-trends")
async def get_performance_trends(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get performance trends over time
    """
    try:
        # Get performance data over time
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get validation trends
        validation_logs = db.query(ValidationLog).filter(
            ValidationLog.timestamp >= cutoff_date
        ).order_by(ValidationLog.timestamp).all()
        
        # Calculate daily metrics
        daily_metrics = {}
        for log in validation_logs:
            day_key = log.timestamp.date().isoformat()
            if day_key not in daily_metrics:
                daily_metrics[day_key] = {
                    "validations": 0,
                    "successes": 0,
                    "avg_confidence": 0.0,
                    "processing_times": []
                }
            
            daily_metrics[day_key]["validations"] += 1
            if log.validation_success:
                daily_metrics[day_key]["successes"] += 1
            
            if log.confidence_score:
                daily_metrics[day_key]["avg_confidence"] += log.confidence_score
            
            if log.processing_time_ms:
                daily_metrics[day_key]["processing_times"].append(log.processing_time_ms)
        
        # Process daily metrics
        trends = []
        for day, metrics in daily_metrics.items():
            if metrics["validations"] > 0:
                success_rate = metrics["successes"] / metrics["validations"]
                avg_confidence = metrics["avg_confidence"] / metrics["validations"]
                avg_processing_time = (
                    sum(metrics["processing_times"]) / len(metrics["processing_times"])
                    if metrics["processing_times"] else 0
                )
                
                trends.append({
                    "date": day,
                    "validations": metrics["validations"],
                    "success_rate": success_rate,
                    "avg_confidence": avg_confidence,
                    "avg_processing_time_ms": avg_processing_time
                })
        
        return {
            "success": True,
            "trends": trends,
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance trends: {str(e)}")

@router.get("/test/validation-system")
async def test_validation_system(
    db: Session = Depends(get_db)
):
    """
    Test endpoint to verify validation system functionality
    """
    try:
        # Test validation service
        test_response = {
            "service_code": "plumbing_leak_repair",
            "zone_code": "bonamoussadi",
            "confidence": 0.85,
            "price_estimate": 8000
        }
        
        validation_result = await validation_service.validate_llm_response(
            db, test_response, "plomberie fuite", {}
        )
        
        # Test suggestion engine
        suggestion_response = await suggestion_engine.generate_suggestions(
            db, "plomberie", "bonamoussadi"
        )
        
        # Test error management
        error_stats = await error_management.get_error_statistics(db)
        
        # Test improvement service
        improvement_metrics = await improvement_service.get_improvement_metrics(db)
        
        return {
            "success": True,
            "test_results": {
                "validation_service": {
                    "is_valid": validation_result.is_valid,
                    "confidence_score": validation_result.confidence_score,
                    "errors_count": len(validation_result.errors),
                    "corrections_count": len(validation_result.corrections)
                },
                "suggestion_engine": {
                    "suggestions_count": len(suggestion_response.suggestions),
                    "total_suggestions": suggestion_response.total_count,
                    "recommendation_confidence": suggestion_response.recommendation_confidence
                },
                "error_management": {
                    "total_errors": error_stats["total_errors"],
                    "recent_errors": error_stats["recent_errors"],
                    "resolution_rate": error_stats["resolution_rate"]
                },
                "improvement_service": {
                    "total_improvements": improvement_metrics["total_improvements_applied"],
                    "keyword_updates": improvement_metrics["keyword_updates_count"]
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation system test failed: {str(e)}")