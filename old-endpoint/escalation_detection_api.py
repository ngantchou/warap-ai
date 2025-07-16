"""
API Endpoints for Escalation Detection System
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.escalation_detection_service import EscalationDetectionService
from app.services.complexity_scoring_service import ComplexityScoringService

router = APIRouter()

# Request Models
class EscalationDetectionRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    context: Optional[Dict[str, Any]] = {}

class DetectorCreationRequest(BaseModel):
    detector_name: str
    detector_type: str  # failure_counter, sentiment_analysis, duration_based, complexity_scoring
    is_active: bool = True
    priority_level: int = 1
    escalation_threshold: float = 0.7
    failure_count_threshold: int = 3
    sentiment_threshold: float = -0.5
    duration_threshold_minutes: int = 15
    complexity_threshold: float = 0.8
    configuration_data: Optional[Dict[str, Any]] = {}

class RuleCreationRequest(BaseModel):
    rule_name: str
    description: Optional[str] = None
    condition_type: str = "combined_score"
    primary_detector: Optional[str] = None
    escalation_threshold: float = 0.7
    minimum_confidence: float = 0.6
    escalation_action: str = "human_handoff"
    escalation_target: Optional[str] = None
    notification_channels: List[str] = ["whatsapp"]
    service_type_filter: Optional[str] = None
    zone_filter: Optional[str] = None
    is_active: bool = True

class ComplexityAnalysisRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, Any]] = []
    context: Dict[str, Any] = {}

# Escalation Detection Endpoints
@router.post("/api/v1/escalation/detect")
async def detect_escalation(
    request: EscalationDetectionRequest,
    db: Session = Depends(get_db)
):
    """Detect escalation for a message"""
    try:
        escalation_service = EscalationDetectionService(db)
        
        result = escalation_service.detect_escalation(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message,
            context=request.context
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/escalation/detectors")
async def create_detector(
    request: DetectorCreationRequest,
    db: Session = Depends(get_db)
):
    """Create a new escalation detector"""
    try:
        escalation_service = EscalationDetectionService(db)
        
        result = escalation_service.create_detector(request.dict())
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/detectors")
async def get_detectors(
    active_only: bool = Query(True, description="Get only active detectors"),
    db: Session = Depends(get_db)
):
    """Get all escalation detectors"""
    try:
        from app.models.escalation_detection_models import EscalationDetector
        
        query = db.query(EscalationDetector)
        if active_only:
            query = query.filter(EscalationDetector.is_active == True)
        
        detectors = query.all()
        
        return {
            'success': True,
            'detectors': [
                {
                    'detector_id': d.detector_id,
                    'detector_name': d.detector_name,
                    'detector_type': d.detector_type,
                    'is_active': d.is_active,
                    'priority_level': d.priority_level,
                    'escalation_threshold': d.escalation_threshold,
                    'configuration': d.configuration_data
                }
                for d in detectors
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/v1/escalation/detectors/{detector_id}")
async def update_detector(
    detector_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update an escalation detector"""
    try:
        from app.models.escalation_detection_models import EscalationDetector
        
        detector = db.query(EscalationDetector).filter(
            EscalationDetector.detector_id == detector_id
        ).first()
        
        if not detector:
            raise HTTPException(status_code=404, detail="Detector not found")
        
        # Update allowed fields
        allowed_fields = [
            'detector_name', 'is_active', 'priority_level', 'escalation_threshold',
            'failure_count_threshold', 'sentiment_threshold', 'duration_threshold_minutes',
            'complexity_threshold', 'configuration_data'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(detector, field):
                setattr(detector, field, value)
        
        detector.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            'success': True,
            'message': f"Detector {detector_id} updated successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/v1/escalation/detectors/{detector_id}")
async def delete_detector(
    detector_id: str,
    db: Session = Depends(get_db)
):
    """Delete an escalation detector"""
    try:
        from app.models.escalation_detection_models import EscalationDetector
        
        detector = db.query(EscalationDetector).filter(
            EscalationDetector.detector_id == detector_id
        ).first()
        
        if not detector:
            raise HTTPException(status_code=404, detail="Detector not found")
        
        # Soft delete by deactivating
        detector.is_active = False
        detector.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            'success': True,
            'message': f"Detector {detector_id} deactivated successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Escalation Rules Endpoints
@router.post("/api/v1/escalation/rules")
async def create_escalation_rule(
    request: RuleCreationRequest,
    db: Session = Depends(get_db)
):
    """Create a new escalation rule"""
    try:
        from app.models.escalation_detection_models import EscalationBusinessRule
        import uuid
        
        rule = EscalationBusinessRule(
            rule_id=f"rule_{uuid.uuid4().hex[:12]}",
            rule_name=request.rule_name,
            description=request.description,
            condition_type=request.condition_type,
            primary_detector=request.primary_detector,
            escalation_threshold=request.escalation_threshold,
            minimum_confidence=request.minimum_confidence,
            escalation_action=request.escalation_action,
            escalation_target=request.escalation_target,
            notification_channels=request.notification_channels,
            service_type_filter=request.service_type_filter,
            zone_filter=request.zone_filter,
            is_active=request.is_active
        )
        
        db.add(rule)
        db.commit()
        
        return {
            'success': True,
            'rule_id': rule.rule_id,
            'message': f"Rule '{rule.rule_name}' created successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/rules")
async def get_escalation_rules(
    active_only: bool = Query(True, description="Get only active rules"),
    db: Session = Depends(get_db)
):
    """Get all escalation rules"""
    try:
        from app.models.escalation_detection_models import EscalationBusinessRule
        
        query = db.query(EscalationBusinessRule)
        if active_only:
            query = query.filter(EscalationBusinessRule.is_active == True)
        
        rules = query.order_by(EscalationBusinessRule.priority_order).all()
        
        return {
            'success': True,
            'rules': [
                {
                    'rule_id': r.rule_id,
                    'rule_name': r.rule_name,
                    'description': r.description,
                    'condition_type': r.condition_type,
                    'primary_detector': r.primary_detector,
                    'escalation_threshold': r.escalation_threshold,
                    'escalation_action': r.escalation_action,
                    'escalation_target': r.escalation_target,
                    'notification_channels': r.notification_channels,
                    'service_type_filter': r.service_type_filter,
                    'zone_filter': r.zone_filter,
                    'is_active': r.is_active,
                    'priority_order': r.priority_order
                }
                for r in rules
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Detection Logs Endpoints
@router.get("/api/v1/escalation/logs")
async def get_detection_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    escalation_triggered: Optional[bool] = Query(None, description="Filter by escalation status"),
    limit: int = Query(50, description="Number of logs to return"),
    offset: int = Query(0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """Get escalation detection logs"""
    try:
        from app.models.escalation_detection_models import EscalationDetectionLog
        from sqlalchemy import and_, func
        
        query = db.query(EscalationDetectionLog)
        
        # Apply filters
        filters = []
        if user_id:
            filters.append(EscalationDetectionLog.user_id == user_id)
        if session_id:
            filters.append(EscalationDetectionLog.session_id == session_id)
        if escalation_triggered is not None:
            filters.append(EscalationDetectionLog.escalation_triggered == escalation_triggered)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        logs = query.order_by(
            EscalationDetectionLog.timestamp.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            'success': True,
            'total_count': total_count,
            'logs': [
                {
                    'log_id': log.log_id,
                    'user_id': log.user_id,
                    'session_id': log.session_id,
                    'escalation_triggered': log.escalation_triggered,
                    'escalation_score': log.escalation_score,
                    'escalation_reason': log.escalation_reason,
                    'escalation_type': log.escalation_type,
                    'message_content': log.message_content,
                    'service_type': log.service_type,
                    'zone': log.zone,
                    'timestamp': log.timestamp.isoformat()
                }
                for log in logs
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Complexity Scoring Endpoints
@router.post("/api/v1/escalation/complexity/analyze")
async def analyze_complexity(
    request: ComplexityAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Analyze message complexity"""
    try:
        complexity_service = ComplexityScoringService(db)
        
        result = complexity_service.calculate_complexity_score(
            message=request.message,
            conversation_history=request.conversation_history,
            context=request.context
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/complexity/analytics")
async def get_complexity_analytics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get complexity scoring analytics"""
    try:
        complexity_service = ComplexityScoringService(db)
        
        result = complexity_service.get_complexity_analytics(days)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Endpoints
@router.get("/api/v1/escalation/analytics")
async def get_escalation_analytics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get escalation detection analytics"""
    try:
        escalation_service = EscalationDetectionService(db)
        
        result = escalation_service.get_escalation_analytics(days)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/analytics/dashboard")
async def get_escalation_dashboard(
    db: Session = Depends(get_db)
):
    """Get escalation detection dashboard"""
    try:
        from app.models.escalation_detection_models import EscalationDetectionLog, EscalationExecution
        from datetime import timedelta
        from sqlalchemy import func
        
        # Get today's statistics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total detections today
        detections_today = db.query(EscalationDetectionLog).filter(
            EscalationDetectionLog.timestamp >= today
        ).count()
        
        # Escalations triggered today
        escalations_today = db.query(EscalationDetectionLog).filter(
            EscalationDetectionLog.timestamp >= today,
            EscalationDetectionLog.escalation_triggered == True
        ).count()
        
        # Active escalations
        active_escalations = db.query(EscalationExecution).filter(
            EscalationExecution.execution_status.in_(['pending', 'executed'])
        ).count()
        
        # Average escalation score today
        avg_score = db.query(
            func.avg(EscalationDetectionLog.escalation_score)
        ).filter(
            EscalationDetectionLog.timestamp >= today
        ).scalar() or 0.0
        
        # Escalation rate
        escalation_rate = escalations_today / max(detections_today, 1)
        
        return {
            'success': True,
            'dashboard': {
                'detections_today': detections_today,
                'escalations_today': escalations_today,
                'active_escalations': active_escalations,
                'escalation_rate': round(escalation_rate, 3),
                'average_escalation_score': round(avg_score, 3),
                'last_updated': datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health Check
@router.get("/api/v1/escalation/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check for escalation detection system"""
    try:
        from sqlalchemy import text
        
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Count active detectors
        from app.models.escalation_detection_models import EscalationDetector
        active_detectors = db.query(EscalationDetector).filter(
            EscalationDetector.is_active == True
        ).count()
        
        return {
            'success': True,
            'status': 'healthy',
            'services': {
                'escalation_detection': 'operational',
                'complexity_scoring': 'operational',
                'database': 'connected'
            },
            'active_detectors': active_detectors,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }