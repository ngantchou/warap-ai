"""
API Endpoints for Human Escalation System
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.human_escalation_service import HumanEscalationService

router = APIRouter()

# Request Models
class EscalationCaseRequest(BaseModel):
    user_id: str
    session_id: str
    original_request_id: Optional[str] = None
    escalation_trigger: str
    escalation_score: float
    escalation_reason: str
    service_type: str
    problem_category: str
    problem_description: str
    customer_context: Optional[Dict[str, Any]] = {}
    metadata: Optional[Dict[str, Any]] = {}

class CaseActionRequest(BaseModel):
    case_id: str
    action_type: str
    action_description: str
    action_details: Optional[Dict[str, Any]] = {}
    internal_notes: Optional[str] = None

class EscalationFeedbackRequest(BaseModel):
    case_id: str
    agent_id: str
    feedback_type: str = "escalation_quality"
    feedback_category: str = "positive"
    feedback_title: str
    feedback_description: str
    improvement_suggestions: List[Dict[str, Any]] = []
    escalation_appropriateness: Optional[float] = None
    context_completeness: Optional[float] = None
    handover_quality: Optional[float] = None
    ai_performance_rating: Optional[float] = None
    missed_opportunities: List[Dict[str, Any]] = []
    successful_patterns: List[Dict[str, Any]] = []

class AgentStatusUpdate(BaseModel):
    agent_id: str
    status: str  # online, offline, busy, away
    availability_status: str  # available, busy, unavailable

# Escalation Case Management
@router.post("/api/v1/escalation/cases")
async def create_escalation_case(
    request: EscalationCaseRequest,
    db: Session = Depends(get_db)
):
    """Create a new escalation case"""
    try:
        escalation_service = HumanEscalationService(db)
        
        result = escalation_service.create_escalation_case(
            escalation_data=request.dict()
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/cases")
async def get_escalation_cases(
    status: Optional[str] = Query(None, description="Filter by status"),
    urgency_level: Optional[str] = Query(None, description="Filter by urgency level"),
    assigned_agent_id: Optional[str] = Query(None, description="Filter by assigned agent"),
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    limit: int = Query(50, description="Number of cases to return"),
    offset: int = Query(0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """Get escalation cases with filtering"""
    try:
        from app.models.human_escalation_models import EscalationCase
        from sqlalchemy import and_
        
        query = db.query(EscalationCase)
        
        # Apply filters
        filters = []
        if status:
            filters.append(EscalationCase.status == status)
        if urgency_level:
            filters.append(EscalationCase.urgency_level == urgency_level)
        if assigned_agent_id:
            filters.append(EscalationCase.assigned_agent_id == assigned_agent_id)
        if service_type:
            filters.append(EscalationCase.service_type == service_type)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        cases = query.order_by(
            EscalationCase.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            'success': True,
            'total_count': total_count,
            'cases': [
                {
                    'case_id': case.case_id,
                    'user_id': case.user_id,
                    'session_id': case.session_id,
                    'escalation_trigger': case.escalation_trigger,
                    'escalation_score': case.escalation_score,
                    'escalation_reason': case.escalation_reason,
                    'urgency_level': case.urgency_level,
                    'assigned_agent_id': case.assigned_agent_id,
                    'status': case.status,
                    'service_type': case.service_type,
                    'problem_category': case.problem_category,
                    'problem_description': case.problem_description,
                    'created_at': case.created_at.isoformat(),
                    'assigned_at': case.assigned_at.isoformat() if case.assigned_at else None,
                    'resolution_time': case.resolution_time.isoformat() if case.resolution_time else None,
                    'customer_satisfaction': case.customer_satisfaction
                }
                for case in cases
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/cases/{case_id}")
async def get_escalation_case(
    case_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific escalation case"""
    try:
        from app.models.human_escalation_models import EscalationCase, HandoverSession
        
        case = db.query(EscalationCase).filter(
            EscalationCase.case_id == case_id
        ).first()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get handover session
        handover = db.query(HandoverSession).filter(
            HandoverSession.case_id == case_id
        ).first()
        
        return {
            'success': True,
            'case': {
                'case_id': case.case_id,
                'user_id': case.user_id,
                'session_id': case.session_id,
                'original_request_id': case.original_request_id,
                'escalation_trigger': case.escalation_trigger,
                'escalation_score': case.escalation_score,
                'escalation_reason': case.escalation_reason,
                'urgency_level': case.urgency_level,
                'assigned_agent_id': case.assigned_agent_id,
                'status': case.status,
                'priority': case.priority,
                'service_type': case.service_type,
                'problem_category': case.problem_category,
                'problem_description': case.problem_description,
                'customer_context': case.customer_context,
                'created_at': case.created_at.isoformat(),
                'assigned_at': case.assigned_at.isoformat() if case.assigned_at else None,
                'first_response_time': case.first_response_time.isoformat() if case.first_response_time else None,
                'resolution_time': case.resolution_time.isoformat() if case.resolution_time else None,
                'total_duration_minutes': case.total_duration_minutes,
                'resolution_method': case.resolution_method,
                'resolution_notes': case.resolution_notes,
                'customer_satisfaction': case.customer_satisfaction,
                'escalation_successful': case.escalation_successful,
                'case_metadata': case.case_metadata
            },
            'handover_session': {
                'session_id': handover.session_id,
                'handover_type': handover.handover_type,
                'handover_reason': handover.handover_reason,
                'case_summary': handover.case_summary,
                'conversation_summary': handover.conversation_summary,
                'key_issues': handover.key_issues,
                'recommended_actions': handover.recommended_actions,
                'blocking_points': handover.blocking_points,
                'technical_context': handover.technical_context,
                'service_history': handover.service_history,
                'status': handover.status,
                'agent_briefed': handover.agent_briefed,
                'agent_accepted': handover.agent_accepted,
                'handover_quality_score': handover.handover_quality_score,
                'briefing_completeness': handover.briefing_completeness,
                'context_clarity': handover.context_clarity,
                'created_at': handover.created_at.isoformat(),
                'completed_at': handover.completed_at.isoformat() if handover.completed_at else None
            } if handover else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/v1/escalation/cases/{case_id}/status")
async def update_case_status(
    case_id: str,
    status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update the status of an escalation case"""
    try:
        from app.models.human_escalation_models import EscalationCase
        
        case = db.query(EscalationCase).filter(
            EscalationCase.case_id == case_id
        ).first()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Update status
        old_status = case.status
        case.status = status
        case.updated_at = datetime.utcnow()
        
        # Update specific timestamps
        if status == 'in_progress' and not case.first_response_time:
            case.first_response_time = datetime.utcnow()
        elif status == 'resolved' and not case.resolution_time:
            case.resolution_time = datetime.utcnow()
            if case.assigned_at:
                case.total_duration_minutes = int(
                    (case.resolution_time - case.assigned_at).total_seconds() / 60
                )
        
        # Add notes if provided
        if notes:
            case.resolution_notes = notes
        
        db.commit()
        
        return {
            'success': True,
            'case_id': case_id,
            'old_status': old_status,
            'new_status': status,
            'updated_at': case.updated_at.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Agent Dashboard
@router.get("/api/v1/escalation/agents/{agent_id}/dashboard")
async def get_agent_dashboard(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Get agent dashboard with assigned cases and metrics"""
    try:
        escalation_service = HumanEscalationService(db)
        
        result = escalation_service.get_agent_dashboard(agent_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/agents")
async def get_agents(
    status: Optional[str] = Query(None, description="Filter by status"),
    availability_status: Optional[str] = Query(None, description="Filter by availability"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    db: Session = Depends(get_db)
):
    """Get list of human agents"""
    try:
        from app.models.human_escalation_models import HumanAgent
        from sqlalchemy import and_
        
        query = db.query(HumanAgent)
        
        # Apply filters
        filters = []
        if status:
            filters.append(HumanAgent.status == status)
        if availability_status:
            filters.append(HumanAgent.availability_status == availability_status)
        if specialization:
            filters.append(HumanAgent.specializations.contains([specialization]))
        
        if filters:
            query = query.filter(and_(*filters))
        
        agents = query.all()
        
        return {
            'success': True,
            'agents': [
                {
                    'agent_id': agent.agent_id,
                    'name': agent.name,
                    'email': agent.email,
                    'department': agent.department,
                    'status': agent.status,
                    'availability_status': agent.availability_status,
                    'current_case_count': agent.current_case_count,
                    'max_concurrent_cases': agent.max_concurrent_cases,
                    'specializations': agent.specializations,
                    'service_types': agent.service_types,
                    'languages': agent.languages,
                    'customer_satisfaction_score': agent.customer_satisfaction_score,
                    'escalation_success_rate': agent.escalation_success_rate,
                    'last_activity': agent.last_activity.isoformat() if agent.last_activity else None
                }
                for agent in agents
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/v1/escalation/agents/{agent_id}/status")
async def update_agent_status(
    agent_id: str,
    status_update: AgentStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update agent status and availability"""
    try:
        from app.models.human_escalation_models import HumanAgent
        
        agent = db.query(HumanAgent).filter(
            HumanAgent.agent_id == agent_id
        ).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update status
        agent.status = status_update.status
        agent.availability_status = status_update.availability_status
        agent.last_activity = datetime.utcnow()
        agent.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            'success': True,
            'agent_id': agent_id,
            'status': agent.status,
            'availability_status': agent.availability_status,
            'updated_at': agent.updated_at.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Case Actions
@router.post("/api/v1/escalation/cases/{case_id}/actions")
async def create_case_action(
    case_id: str,
    action_request: CaseActionRequest,
    db: Session = Depends(get_db)
):
    """Create a new action for a case"""
    try:
        from app.models.human_escalation_models import CaseAction
        import uuid
        
        # Verify case exists
        from app.models.human_escalation_models import EscalationCase
        case = db.query(EscalationCase).filter(
            EscalationCase.case_id == case_id
        ).first()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Create action
        action = CaseAction(
            action_id=f"action_{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            agent_id=case.assigned_agent_id,
            action_type=action_request.action_type,
            action_description=action_request.action_description,
            action_details=action_request.action_details,
            internal_notes=action_request.internal_notes,
            action_result='pending'
        )
        
        db.add(action)
        db.commit()
        
        return {
            'success': True,
            'action_id': action.action_id,
            'case_id': case_id,
            'action_type': action.action_type,
            'created_at': action.created_at.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/cases/{case_id}/actions")
async def get_case_actions(
    case_id: str,
    db: Session = Depends(get_db)
):
    """Get all actions for a case"""
    try:
        from app.models.human_escalation_models import CaseAction
        
        actions = db.query(CaseAction).filter(
            CaseAction.case_id == case_id
        ).order_by(CaseAction.created_at.desc()).all()
        
        return {
            'success': True,
            'case_id': case_id,
            'actions': [
                {
                    'action_id': action.action_id,
                    'action_type': action.action_type,
                    'action_description': action.action_description,
                    'action_details': action.action_details,
                    'internal_notes': action.internal_notes,
                    'action_result': action.action_result,
                    'action_duration_minutes': action.action_duration_minutes,
                    'created_at': action.created_at.isoformat()
                }
                for action in actions
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Feedback Management
@router.post("/api/v1/escalation/feedback")
async def submit_escalation_feedback(
    feedback_request: EscalationFeedbackRequest,
    db: Session = Depends(get_db)
):
    """Submit feedback about an escalation case"""
    try:
        escalation_service = HumanEscalationService(db)
        
        result = escalation_service.submit_case_feedback(
            feedback_data=feedback_request.dict()
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/feedback")
async def get_escalation_feedback(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type"),
    limit: int = Query(50, description="Number of feedback items to return"),
    offset: int = Query(0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """Get escalation feedback"""
    try:
        from app.models.human_escalation_models import EscalationFeedback
        from sqlalchemy import and_
        
        query = db.query(EscalationFeedback)
        
        # Apply filters
        filters = []
        if case_id:
            filters.append(EscalationFeedback.case_id == case_id)
        if agent_id:
            filters.append(EscalationFeedback.agent_id == agent_id)
        if feedback_type:
            filters.append(EscalationFeedback.feedback_type == feedback_type)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        feedback_items = query.order_by(
            EscalationFeedback.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            'success': True,
            'total_count': total_count,
            'feedback_items': [
                {
                    'feedback_id': feedback.feedback_id,
                    'case_id': feedback.case_id,
                    'agent_id': feedback.agent_id,
                    'feedback_type': feedback.feedback_type,
                    'feedback_category': feedback.feedback_category,
                    'feedback_title': feedback.feedback_title,
                    'feedback_description': feedback.feedback_description,
                    'improvement_suggestions': feedback.improvement_suggestions,
                    'escalation_appropriateness': feedback.escalation_appropriateness,
                    'context_completeness': feedback.context_completeness,
                    'handover_quality': feedback.handover_quality,
                    'ai_performance_rating': feedback.ai_performance_rating,
                    'status': feedback.status,
                    'created_at': feedback.created_at.isoformat()
                }
                for feedback in feedback_items
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analytics
@router.get("/api/v1/escalation/analytics/human")
async def get_human_escalation_analytics(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get human escalation analytics"""
    try:
        escalation_service = HumanEscalationService(db)
        
        result = escalation_service.get_escalation_analytics(days)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/escalation/analytics/dashboard")
async def get_escalation_dashboard(
    db: Session = Depends(get_db)
):
    """Get escalation dashboard with key metrics"""
    try:
        from app.models.human_escalation_models import EscalationCase, HumanAgent
        from datetime import timedelta
        from sqlalchemy import func
        
        # Get today's statistics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total cases today
        cases_today = db.query(EscalationCase).filter(
            EscalationCase.created_at >= today
        ).count()
        
        # Cases by status
        pending_cases = db.query(EscalationCase).filter(
            EscalationCase.status == 'pending'
        ).count()
        
        active_cases = db.query(EscalationCase).filter(
            EscalationCase.status.in_(['assigned', 'in_progress'])
        ).count()
        
        resolved_cases_today = db.query(EscalationCase).filter(
            EscalationCase.created_at >= today,
            EscalationCase.status == 'resolved'
        ).count()
        
        # Agents status
        online_agents = db.query(HumanAgent).filter(
            HumanAgent.status == 'online'
        ).count()
        
        available_agents = db.query(HumanAgent).filter(
            and_(
                HumanAgent.status == 'online',
                HumanAgent.availability_status == 'available'
            )
        ).count()
        
        # Average response time today
        response_times = db.query(
            func.avg(
                func.extract('epoch', EscalationCase.first_response_time - EscalationCase.assigned_at) / 60
            )
        ).filter(
            EscalationCase.created_at >= today,
            EscalationCase.first_response_time.isnot(None),
            EscalationCase.assigned_at.isnot(None)
        ).scalar() or 0
        
        # Customer satisfaction average
        satisfaction_avg = db.query(
            func.avg(EscalationCase.customer_satisfaction)
        ).filter(
            EscalationCase.created_at >= today,
            EscalationCase.customer_satisfaction.isnot(None)
        ).scalar() or 0
        
        return {
            'success': True,
            'dashboard': {
                'cases_today': cases_today,
                'pending_cases': pending_cases,
                'active_cases': active_cases,
                'resolved_cases_today': resolved_cases_today,
                'resolution_rate_today': resolved_cases_today / max(cases_today, 1),
                'online_agents': online_agents,
                'available_agents': available_agents,
                'avg_response_time_minutes': round(response_times, 2),
                'avg_customer_satisfaction': round(satisfaction_avg, 2),
                'last_updated': datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health Check
@router.get("/api/v1/escalation/human/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check for human escalation system"""
    try:
        from sqlalchemy import text
        
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Count active agents
        from app.models.human_escalation_models import HumanAgent
        active_agents = db.query(HumanAgent).filter(
            HumanAgent.status == 'online'
        ).count()
        
        # Count pending cases
        from app.models.human_escalation_models import EscalationCase
        pending_cases = db.query(EscalationCase).filter(
            EscalationCase.status == 'pending'
        ).count()
        
        return {
            'success': True,
            'status': 'healthy',
            'services': {
                'human_escalation': 'operational',
                'agent_management': 'operational',
                'case_management': 'operational',
                'database': 'connected'
            },
            'active_agents': active_agents,
            'pending_cases': pending_cases,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))