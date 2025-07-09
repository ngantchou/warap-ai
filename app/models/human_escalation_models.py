"""
Human Escalation Models for Djobea AI
Models pour le processus d'escalation vers support humain
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.database_models import Base


class HumanAgent(Base):
    """Agent humain du support client"""
    __tablename__ = "human_agents"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), unique=True, index=True)
    
    # Informations de base
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    department = Column(String(100))  # support, technical, supervisor
    
    # Statut et disponibilité
    status = Column(String(50), default='offline')  # online, offline, busy, away
    availability_status = Column(String(50), default='available')  # available, busy, unavailable
    max_concurrent_cases = Column(Integer, default=5)
    current_case_count = Column(Integer, default=0)
    
    # Spécialisations
    specializations = Column(JSON)  # Liste des spécialisations
    service_types = Column(JSON)  # Types de services gérés
    languages = Column(JSON)  # Langues parlées
    
    # Métriques de performance
    total_cases_handled = Column(Integer, default=0)
    average_resolution_time = Column(Float, default=0.0)  # en minutes
    customer_satisfaction_score = Column(Float, default=0.0)
    escalation_success_rate = Column(Float, default=0.0)
    
    # Paramètres de configuration
    notification_channels = Column(JSON)  # Canaux de notification
    working_hours = Column(JSON)  # Heures de travail
    timezone = Column(String(50), default='Africa/Douala')
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    escalation_cases = relationship("EscalationCase", back_populates="assigned_agent")
    handover_sessions = relationship("HandoverSession", back_populates="agent")


class EscalationCase(Base):
    """Cas d'escalation vers support humain"""
    __tablename__ = "escalation_cases"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(255), unique=True, index=True)
    
    # Informations du cas
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    original_request_id = Column(String(255), index=True)
    
    # Détails de l'escalation
    escalation_trigger = Column(String(100))  # sentiment, complexity, duration, failure
    escalation_score = Column(Float, default=0.0)
    escalation_reason = Column(Text)
    urgency_level = Column(String(20), default='medium')  # low, medium, high, critical
    
    # Assignation
    assigned_agent_id = Column(String(255), ForeignKey("human_agents.agent_id"))
    assigned_at = Column(DateTime)
    assignment_method = Column(String(50))  # auto, manual, escalated
    
    # Statut du cas
    status = Column(String(50), default='pending')  # pending, assigned, in_progress, resolved, closed
    priority = Column(String(20), default='medium')  # low, medium, high, critical
    
    # Contexte du problème
    service_type = Column(String(100))
    problem_category = Column(String(100))
    problem_description = Column(Text)
    customer_context = Column(JSON)  # Contexte client
    
    # Métriques temporelles
    created_at = Column(DateTime, default=datetime.utcnow)
    first_response_time = Column(DateTime)
    resolution_time = Column(DateTime)
    total_duration_minutes = Column(Integer)
    
    # Résolution
    resolution_method = Column(String(100))
    resolution_notes = Column(Text)
    customer_satisfaction = Column(Float)
    escalation_successful = Column(Boolean, default=False)
    
    # Métadonnées
    case_metadata = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    assigned_agent = relationship("HumanAgent", back_populates="escalation_cases")
    handover_session = relationship("HandoverSession", back_populates="escalation_case", uselist=False)
    case_actions = relationship("CaseAction", back_populates="escalation_case")


class HandoverSession(Base):
    """Session de handover AI vers agent humain"""
    __tablename__ = "handover_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True)
    
    # Références
    case_id = Column(String(255), ForeignKey("escalation_cases.case_id"))
    agent_id = Column(String(255), ForeignKey("human_agents.agent_id"))
    
    # Informations de handover
    handover_type = Column(String(50))  # immediate, scheduled, requested
    handover_trigger = Column(String(100))
    handover_reason = Column(Text)
    
    # Briefing automatique
    case_summary = Column(Text)
    conversation_summary = Column(Text)
    key_issues = Column(JSON)  # Points clés identifiés
    recommended_actions = Column(JSON)  # Actions recommandées
    blocking_points = Column(JSON)  # Points de blocage
    
    # Contexte technique
    technical_context = Column(JSON)
    service_history = Column(JSON)
    previous_interactions = Column(JSON)
    
    # Statut de handover
    status = Column(String(50), default='initiated')  # initiated, briefed, accepted, completed
    agent_briefed = Column(Boolean, default=False)
    agent_accepted = Column(Boolean, default=False)
    handover_quality_score = Column(Float)
    
    # Métriques
    handover_duration_seconds = Column(Integer)
    briefing_completeness = Column(Float)  # Score de complétude
    context_clarity = Column(Float)  # Clarté du contexte
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    handover_metadata = Column(JSON)
    
    # Relations
    escalation_case = relationship("EscalationCase", back_populates="handover_session")
    agent = relationship("HumanAgent", back_populates="handover_sessions")


class CaseAction(Base):
    """Actions prises sur un cas d'escalation"""
    __tablename__ = "case_actions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(String(255), unique=True, index=True)
    
    # Références
    case_id = Column(String(255), ForeignKey("escalation_cases.case_id"))
    agent_id = Column(String(255), ForeignKey("human_agents.agent_id"))
    
    # Type d'action
    action_type = Column(String(100))  # message, status_update, escalation, resolution
    action_category = Column(String(100))  # communication, technical, administrative
    
    # Contenu de l'action
    action_description = Column(Text)
    action_details = Column(JSON)
    internal_notes = Column(Text)  # Notes internes
    
    # Résultats
    action_result = Column(String(50))  # success, failure, pending
    customer_response = Column(Text)
    impact_on_case = Column(String(100))
    
    # Métriques
    action_duration_minutes = Column(Integer)
    effectiveness_score = Column(Float)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    action_metadata = Column(JSON)
    
    # Relations
    escalation_case = relationship("EscalationCase", back_populates="case_actions")


class EscalationFeedback(Base):
    """Feedback des agents humains vers le système"""
    __tablename__ = "escalation_feedback"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(String(255), unique=True, index=True)
    
    # Références
    case_id = Column(String(255), ForeignKey("escalation_cases.case_id"))
    agent_id = Column(String(255), ForeignKey("human_agents.agent_id"))
    
    # Type de feedback
    feedback_type = Column(String(100))  # escalation_quality, system_improvement, training_data
    feedback_category = Column(String(100))  # positive, negative, suggestion
    
    # Contenu du feedback
    feedback_title = Column(String(255))
    feedback_description = Column(Text)
    improvement_suggestions = Column(JSON)
    
    # Évaluation de l'escalation
    escalation_appropriateness = Column(Float)  # 1-5
    context_completeness = Column(Float)  # 1-5
    handover_quality = Column(Float)  # 1-5
    
    # Apprentissage pour l'IA
    ai_performance_rating = Column(Float)  # 1-5
    missed_opportunities = Column(JSON)
    successful_patterns = Column(JSON)
    
    # Statut du feedback
    status = Column(String(50), default='submitted')  # submitted, reviewed, implemented
    reviewed_by = Column(String(255))
    implementation_notes = Column(Text)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    feedback_metadata = Column(JSON)


class EscalationWorkflow(Base):
    """Configuration des workflows d'escalation"""
    __tablename__ = "escalation_workflows"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(255), unique=True, index=True)
    
    # Configuration du workflow
    workflow_name = Column(String(255), nullable=False)
    workflow_description = Column(Text)
    workflow_type = Column(String(100))  # standard, urgent, technical, supervisory
    
    # Conditions de déclenchement
    trigger_conditions = Column(JSON)
    escalation_thresholds = Column(JSON)
    service_type_filters = Column(JSON)
    
    # Étapes du workflow
    workflow_steps = Column(JSON)  # Étapes structurées
    required_actions = Column(JSON)  # Actions requises
    optional_actions = Column(JSON)  # Actions optionnelles
    
    # Assignation automatique
    auto_assignment_rules = Column(JSON)
    fallback_assignment = Column(JSON)
    notification_rules = Column(JSON)
    
    # Métriques et SLA
    target_response_time = Column(Integer)  # en minutes
    target_resolution_time = Column(Integer)  # en minutes
    escalation_sla = Column(JSON)
    
    # Statut
    is_active = Column(Boolean, default=True)
    priority_order = Column(Integer, default=1)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    workflow_metadata = Column(JSON)


class EscalationMetrics(Base):
    """Métriques d'escalation pour amélioration continue"""
    __tablename__ = "escalation_metrics"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(String(255), unique=True, index=True)
    
    # Période de mesure
    measurement_period = Column(String(50))  # hourly, daily, weekly, monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Métriques d'escalation
    total_escalations = Column(Integer, default=0)
    successful_escalations = Column(Integer, default=0)
    escalation_success_rate = Column(Float, default=0.0)
    
    # Métriques temporelles
    average_response_time = Column(Float, default=0.0)  # minutes
    average_resolution_time = Column(Float, default=0.0)  # minutes
    handover_efficiency = Column(Float, default=0.0)
    
    # Métriques de qualité
    customer_satisfaction = Column(Float, default=0.0)
    agent_satisfaction = Column(Float, default=0.0)
    case_quality_score = Column(Float, default=0.0)
    
    # Métriques d'apprentissage
    ai_improvement_rate = Column(Float, default=0.0)
    false_escalation_rate = Column(Float, default=0.0)
    missed_escalation_rate = Column(Float, default=0.0)
    
    # Analyse des tendances
    trend_analysis = Column(JSON)
    improvement_opportunities = Column(JSON)
    system_recommendations = Column(JSON)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    metrics_metadata = Column(JSON)