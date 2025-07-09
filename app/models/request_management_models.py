"""
Request Management Models - Gestion complète des demandes utilisateur avec historique
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from app.models.database_models import Base

class RequestStatus(str, Enum):
    """Statuts des demandes de service"""
    DRAFT = "brouillon"
    PENDING = "en_attente"
    ASSIGNED = "assignee"
    IN_PROGRESS = "en_cours"
    COMPLETED = "terminee"
    CANCELLED = "annulee"
    EXPIRED = "expiree"

class RequestPriority(str, Enum):
    """Priorités des demandes"""
    LOW = "basse"
    NORMAL = "normale"
    HIGH = "haute"
    URGENT = "urgente"

class ModificationType(str, Enum):
    """Types de modification"""
    CREATION = "creation"
    UPDATE = "modification"
    STATUS_CHANGE = "changement_statut"
    CANCELLATION = "annulation"
    DELETION = "suppression"

class ConversationAction(str, Enum):
    """Actions conversationnelles"""
    VIEW_REQUESTS = "voir_demandes"
    VIEW_DETAILS = "voir_details"
    MODIFY_REQUEST = "modifier_demande"
    CANCEL_REQUEST = "annuler_demande"
    CREATE_REQUEST = "creer_demande"
    CONFIRM_ACTION = "confirmer_action"

class UserRequest(Base):
    """Demande utilisateur complète avec gestion d'état"""
    __tablename__ = "user_requests"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255), index=True)
    title = Column(String(255))
    description = Column(Text)
    service_type = Column(String(100))
    location = Column(String(255))
    priority = Column(String(20), default=RequestPriority.NORMAL.value)
    status = Column(String(20), default=RequestStatus.DRAFT.value)
    
    # Informations techniques
    estimated_price = Column(Float)
    estimated_duration = Column(Integer)  # en minutes
    materials_needed = Column(Text)  # JSON
    special_requirements = Column(Text)
    
    # Gestion temporelle
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_for = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    # Assignation
    assigned_provider_id = Column(String(255), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Métadonnées
    conversation_context = Column(Text)  # JSON
    modification_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Relations
    modifications = relationship("RequestModification", back_populates="request")
    conversation_logs = relationship("RequestConversationLog", back_populates="request")
    status_history = relationship("RequestStatusHistory", back_populates="request")

class RequestModification(Base):
    """Historique des modifications de demande"""
    __tablename__ = "request_modifications"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), ForeignKey("user_requests.request_id"))
    modification_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255))
    
    # Type de modification
    modification_type = Column(String(50))
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    
    # Contexte
    reason = Column(Text)
    conversation_message = Column(Text)
    
    # Validation
    is_authorized = Column(Boolean, default=True)
    authorized_by = Column(String(255))
    validation_rules_applied = Column(Text)  # JSON
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    applied_at = Column(DateTime, nullable=True)
    
    # Relation
    request = relationship("UserRequest", back_populates="modifications")

class RequestStatusHistory(Base):
    """Historique des changements de statut"""
    __tablename__ = "request_status_history"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), ForeignKey("user_requests.request_id"))
    status_change_id = Column(String(255), unique=True, index=True)
    
    # Changement de statut
    previous_status = Column(String(20))
    new_status = Column(String(20))
    changed_by = Column(String(255))
    change_reason = Column(Text)
    
    # Contexte
    triggered_by_action = Column(String(100))
    conversation_context = Column(Text)
    system_notes = Column(Text)
    
    # Timing
    changed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation
    request = relationship("UserRequest", back_populates="status_history")

class RequestConversationLog(Base):
    """Journal des interactions conversationnelles"""
    __tablename__ = "request_conversation_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), ForeignKey("user_requests.request_id"))
    conversation_id = Column(String(255), unique=True, index=True)
    
    # Interaction
    user_message = Column(Text)
    detected_action = Column(String(100))
    system_response = Column(Text)
    
    # Analyse
    intent_confidence = Column(Float)
    extracted_data = Column(Text)  # JSON
    validation_errors = Column(Text)  # JSON
    
    # Contexte
    conversation_state = Column(String(50))
    requires_confirmation = Column(Boolean, default=False)
    confirmation_received = Column(Boolean, default=False)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation
    request = relationship("UserRequest", back_populates="conversation_logs")

class RequestValidationRule(Base):
    """Règles de validation pour les modifications"""
    __tablename__ = "request_validation_rules"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(255), unique=True, index=True)
    rule_name = Column(String(255))
    
    # Conditions
    applicable_status = Column(String(50))
    field_name = Column(String(100))
    modification_type = Column(String(50))
    
    # Règle
    validation_logic = Column(Text)  # JSON
    error_message = Column(Text)
    is_blocking = Column(Boolean, default=True)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class UserRequestPermission(Base):
    """Permissions utilisateur pour les demandes"""
    __tablename__ = "user_request_permissions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True)
    request_id = Column(String(255), ForeignKey("user_requests.request_id"))
    
    # Permissions
    can_view = Column(Boolean, default=True)
    can_modify = Column(Boolean, default=True)
    can_cancel = Column(Boolean, default=True)
    can_delete = Column(Boolean, default=False)
    
    # Contexte
    granted_by = Column(String(255))
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Audit
    permission_reason = Column(Text)
    is_active = Column(Boolean, default=True)

class RequestNotification(Base):
    """Notifications liées aux demandes"""
    __tablename__ = "request_notifications"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(255), unique=True, index=True)
    request_id = Column(String(255), ForeignKey("user_requests.request_id"))
    
    # Notification
    recipient_id = Column(String(255))
    recipient_type = Column(String(50))  # user, provider, admin
    notification_type = Column(String(100))
    title = Column(String(255))
    message = Column(Text)
    
    # Delivery
    delivery_method = Column(String(50))  # whatsapp, email, sms
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), default="pending")
    retry_count = Column(Integer, default=0)
    last_error = Column(Text)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)

class RequestConflict(Base):
    """Gestion des conflits et concurrence"""
    __tablename__ = "request_conflicts"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    conflict_id = Column(String(255), unique=True, index=True)
    request_id = Column(String(255), ForeignKey("user_requests.request_id"))
    
    # Conflit
    conflict_type = Column(String(100))
    conflicting_user_id = Column(String(255))
    conflicting_modification_id = Column(String(255))
    
    # Détails
    conflict_description = Column(Text)
    field_conflicts = Column(Text)  # JSON
    resolution_required = Column(Boolean, default=True)
    
    # Résolution
    resolution_strategy = Column(String(100))
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text)
    
    # Timing
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # Status
    status = Column(String(20), default="open")

class RequestTemplate(Base):
    """Templates de demandes pour faciliter la création"""
    __tablename__ = "request_templates"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    description = Column(Text)
    
    # Template
    service_type = Column(String(100))
    template_data = Column(Text)  # JSON
    default_priority = Column(String(20))
    
    # Usage
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RequestAnalytics(Base):
    """Analytics des demandes pour amélioration"""
    __tablename__ = "request_analytics"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), ForeignKey("user_requests.request_id"))
    
    # Métriques
    creation_time_seconds = Column(Float)
    modification_count = Column(Integer)
    conversation_turns = Column(Integer)
    user_satisfaction = Column(Float)
    
    # Patterns
    common_modifications = Column(Text)  # JSON
    user_behavior_pattern = Column(Text)  # JSON
    completion_rate = Column(Float)
    
    # Timing
    analyzed_at = Column(DateTime, default=datetime.utcnow)