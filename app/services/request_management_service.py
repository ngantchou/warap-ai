"""
Request Management Service - Service principal pour la gestion des demandes
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.request_management_models import (
    UserRequest, RequestModification, RequestStatusHistory, 
    RequestConversationLog, RequestValidationRule, UserRequestPermission,
    RequestNotification, RequestConflict, RequestTemplate, RequestAnalytics,
    RequestStatus, RequestPriority, ModificationType, ConversationAction
)
from app.services.notification_service import NotificationService
# from app.services.validation_service import ValidationService

class RequestManagementService:
    """Service principal pour la gestion complète des demandes"""
    
    def __init__(self):
        self.notification_service = NotificationService()
        # self.validation_service = ValidationService()
        
    async def create_request(
        self, 
        db: Session,
        user_id: str,
        request_data: Dict[str, Any],
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> UserRequest:
        """Créer une nouvelle demande utilisateur"""
        
        # Générer ID unique
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        
        # Créer la demande
        request = UserRequest(
            request_id=request_id,
            user_id=user_id,
            title=request_data.get("title", ""),
            description=request_data.get("description", ""),
            service_type=request_data.get("service_type", ""),
            location=request_data.get("location", ""),
            priority=request_data.get("priority", RequestPriority.NORMAL.value),
            status=RequestStatus.DRAFT.value,
            estimated_price=request_data.get("estimated_price"),
            estimated_duration=request_data.get("estimated_duration"),
            materials_needed=json.dumps(request_data.get("materials_needed", [])),
            special_requirements=request_data.get("special_requirements", ""),
            scheduled_for=request_data.get("scheduled_for"),
            deadline=request_data.get("deadline"),
            conversation_context=json.dumps(conversation_context or {})
        )
        
        db.add(request)
        db.commit()
        db.refresh(request)
        
        # Créer historique initial
        await self._create_modification_record(
            db, request_id, user_id, ModificationType.CREATION,
            "request", None, "Demande créée", "Création initiale"
        )
        
        # Créer permission par défaut
        await self._create_default_permissions(db, user_id, request_id)
        
        return request
    
    async def get_user_requests(
        self,
        db: Session,
        user_id: str,
        status_filter: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[UserRequest]:
        """Récupérer les demandes d'un utilisateur"""
        
        query = db.query(UserRequest).filter(
            UserRequest.user_id == user_id,
            UserRequest.is_active == True
        )
        
        if status_filter:
            query = query.filter(UserRequest.status == status_filter)
        
        return query.order_by(desc(UserRequest.created_at)).offset(offset).limit(limit).all()
    
    async def get_request_details(
        self,
        db: Session,
        request_id: str,
        user_id: str
    ) -> Optional[UserRequest]:
        """Récupérer les détails d'une demande"""
        
        # Vérifier les permissions
        if not await self._check_permission(db, user_id, request_id, "view"):
            return None
            
        return db.query(UserRequest).filter(
            UserRequest.request_id == request_id,
            UserRequest.is_active == True
        ).first()
    
    async def modify_request(
        self,
        db: Session,
        request_id: str,
        user_id: str,
        modifications: Dict[str, Any],
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Modifier une demande existante"""
        
        # Vérifier les permissions
        if not await self._check_permission(db, user_id, request_id, "modify"):
            return {"success": False, "error": "Permission refusée"}
        
        # Récupérer la demande
        request = db.query(UserRequest).filter(
            UserRequest.request_id == request_id
        ).first()
        
        if not request:
            return {"success": False, "error": "Demande non trouvée"}
        
        # Valider les modifications
        validation_result = await self._validate_modifications(
            db, request, modifications, user_id
        )
        
        if not validation_result["valid"]:
            return {"success": False, "error": validation_result["errors"]}
        
        # Détecter les conflits
        conflict_check = await self._check_conflicts(db, request_id, modifications)
        if conflict_check["has_conflicts"]:
            return {"success": False, "error": "Conflit détecté", "conflicts": conflict_check["conflicts"]}
        
        # Appliquer les modifications
        applied_modifications = []
        for field, new_value in modifications.items():
            if hasattr(request, field):
                old_value = getattr(request, field)
                if old_value != new_value:
                    setattr(request, field, new_value)
                    
                    # Enregistrer la modification
                    await self._create_modification_record(
                        db, request_id, user_id, ModificationType.UPDATE,
                        field, str(old_value), str(new_value),
                        conversation_context.get("reason", "") if conversation_context else ""
                    )
                    
                    applied_modifications.append({
                        "field": field,
                        "old_value": old_value,
                        "new_value": new_value
                    })
        
        # Mettre à jour le compteur de modifications
        request.modification_count += len(applied_modifications)
        request.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Envoyer notifications
        await self._send_modification_notifications(
            db, request, applied_modifications, user_id
        )
        
        return {
            "success": True,
            "modifications_applied": applied_modifications,
            "request": request
        }
    
    async def change_request_status(
        self,
        db: Session,
        request_id: str,
        new_status: str,
        user_id: str,
        reason: Optional[str] = None,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Changer le statut d'une demande"""
        
        # Récupérer la demande
        request = db.query(UserRequest).filter(
            UserRequest.request_id == request_id
        ).first()
        
        if not request:
            return {"success": False, "error": "Demande non trouvée"}
        
        # Valider la transition de statut
        if not await self._validate_status_transition(
            db, request.status, new_status, user_id
        ):
            return {"success": False, "error": "Transition de statut non autorisée"}
        
        # Enregistrer l'historique
        status_history = RequestStatusHistory(
            request_id=request_id,
            status_change_id=f"status_{uuid.uuid4().hex[:12]}",
            previous_status=request.status,
            new_status=new_status,
            changed_by=user_id,
            change_reason=reason or "",
            conversation_context=json.dumps(conversation_context or {}),
            system_notes=f"Statut changé de {request.status} à {new_status}"
        )
        
        db.add(status_history)
        
        # Mettre à jour la demande
        request.status = new_status
        request.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Envoyer notifications
        await self._send_status_change_notifications(
            db, request, request.status, new_status, user_id
        )
        
        return {"success": True, "new_status": new_status}
    
    async def cancel_request(
        self,
        db: Session,
        request_id: str,
        user_id: str,
        reason: Optional[str] = None,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Annuler une demande"""
        
        # Vérifier les permissions
        if not await self._check_permission(db, user_id, request_id, "cancel"):
            return {"success": False, "error": "Permission refusée"}
        
        # Vérifier si l'annulation est possible
        request = db.query(UserRequest).filter(
            UserRequest.request_id == request_id
        ).first()
        
        if not request:
            return {"success": False, "error": "Demande non trouvée"}
        
        if request.status in [RequestStatus.COMPLETED.value, RequestStatus.CANCELLED.value]:
            return {"success": False, "error": "Impossible d'annuler une demande terminée ou déjà annulée"}
        
        # Changer le statut
        result = await self.change_request_status(
            db, request_id, RequestStatus.CANCELLED.value, user_id, reason, conversation_context
        )
        
        if result["success"]:
            # Enregistrer la modification d'annulation
            await self._create_modification_record(
                db, request_id, user_id, ModificationType.CANCELLATION,
                "status", request.status, RequestStatus.CANCELLED.value,
                reason or "Annulation demandée par l'utilisateur"
            )
        
        return result
    
    async def delete_request(
        self,
        db: Session,
        request_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Supprimer une demande (soft delete)"""
        
        # Vérifier les permissions
        if not await self._check_permission(db, user_id, request_id, "delete"):
            return {"success": False, "error": "Permission refusée"}
        
        # Récupérer la demande
        request = db.query(UserRequest).filter(
            UserRequest.request_id == request_id
        ).first()
        
        if not request:
            return {"success": False, "error": "Demande non trouvée"}
        
        # Soft delete
        request.is_active = False
        request.updated_at = datetime.utcnow()
        
        # Enregistrer la modification
        await self._create_modification_record(
            db, request_id, user_id, ModificationType.DELETION,
            "is_active", "True", "False",
            reason or "Suppression demandée par l'utilisateur"
        )
        
        db.commit()
        
        return {"success": True, "message": "Demande supprimée"}
    
    async def get_request_history(
        self,
        db: Session,
        request_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Récupérer l'historique complet d'une demande"""
        
        # Vérifier les permissions
        if not await self._check_permission(db, user_id, request_id, "view"):
            return {"success": False, "error": "Permission refusée"}
        
        # Récupérer l'historique des modifications
        modifications = db.query(RequestModification).filter(
            RequestModification.request_id == request_id
        ).order_by(RequestModification.created_at).all()
        
        # Récupérer l'historique des statuts
        status_history = db.query(RequestStatusHistory).filter(
            RequestStatusHistory.request_id == request_id
        ).order_by(RequestStatusHistory.changed_at).all()
        
        # Récupérer les logs de conversation
        conversation_logs = db.query(RequestConversationLog).filter(
            RequestConversationLog.request_id == request_id
        ).order_by(RequestConversationLog.created_at).all()
        
        return {
            "success": True,
            "request_id": request_id,
            "modifications": [
                {
                    "id": mod.modification_id,
                    "type": mod.modification_type,
                    "field": mod.field_name,
                    "old_value": mod.old_value,
                    "new_value": mod.new_value,
                    "reason": mod.reason,
                    "created_at": mod.created_at.isoformat(),
                    "user_id": mod.user_id
                }
                for mod in modifications
            ],
            "status_history": [
                {
                    "id": status.status_change_id,
                    "previous_status": status.previous_status,
                    "new_status": status.new_status,
                    "changed_by": status.changed_by,
                    "reason": status.change_reason,
                    "changed_at": status.changed_at.isoformat()
                }
                for status in status_history
            ],
            "conversation_logs": [
                {
                    "id": log.conversation_id,
                    "user_message": log.user_message,
                    "detected_action": log.detected_action,
                    "system_response": log.system_response,
                    "created_at": log.created_at.isoformat()
                }
                for log in conversation_logs
            ]
        }
    
    # Méthodes privées
    
    async def _create_modification_record(
        self,
        db: Session,
        request_id: str,
        user_id: str,
        modification_type: ModificationType,
        field_name: str,
        old_value: str,
        new_value: str,
        reason: str
    ):
        """Créer un enregistrement de modification"""
        
        modification = RequestModification(
            request_id=request_id,
            modification_id=f"mod_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            modification_type=modification_type.value,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            applied_at=datetime.utcnow()
        )
        
        db.add(modification)
        db.commit()
    
    async def _create_default_permissions(
        self,
        db: Session,
        user_id: str,
        request_id: str
    ):
        """Créer les permissions par défaut pour une demande"""
        
        permission = UserRequestPermission(
            user_id=user_id,
            request_id=request_id,
            can_view=True,
            can_modify=True,
            can_cancel=True,
            can_delete=False,
            granted_by="system",
            permission_reason="Propriétaire de la demande"
        )
        
        db.add(permission)
        db.commit()
    
    async def _check_permission(
        self,
        db: Session,
        user_id: str,
        request_id: str,
        action: str
    ) -> bool:
        """Vérifier les permissions d'un utilisateur"""
        
        permission = db.query(UserRequestPermission).filter(
            UserRequestPermission.user_id == user_id,
            UserRequestPermission.request_id == request_id,
            UserRequestPermission.is_active == True
        ).first()
        
        if not permission:
            return False
        
        permission_map = {
            "view": permission.can_view,
            "modify": permission.can_modify,
            "cancel": permission.can_cancel,
            "delete": permission.can_delete
        }
        
        return permission_map.get(action, False)
    
    async def _validate_modifications(
        self,
        db: Session,
        request: UserRequest,
        modifications: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Valider les modifications proposées"""
        
        errors = []
        
        # Vérifier les règles de validation
        for field, new_value in modifications.items():
            rules = db.query(RequestValidationRule).filter(
                RequestValidationRule.applicable_status == request.status,
                RequestValidationRule.field_name == field,
                RequestValidationRule.is_active == True
            ).all()
            
            for rule in rules:
                validation_logic = json.loads(rule.validation_logic)
                
                # Appliquer la logique de validation
                if not await self._apply_validation_rule(validation_logic, new_value, request):
                    if rule.is_blocking:
                        errors.append(rule.error_message)
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    async def _apply_validation_rule(
        self,
        validation_logic: Dict[str, Any],
        new_value: Any,
        request: UserRequest
    ) -> bool:
        """Appliquer une règle de validation"""
        
        # Logique de validation basique
        rule_type = validation_logic.get("type")
        
        if rule_type == "required":
            return new_value is not None and str(new_value).strip() != ""
        elif rule_type == "max_length":
            return len(str(new_value)) <= validation_logic.get("max_length", 255)
        elif rule_type == "status_dependent":
            allowed_statuses = validation_logic.get("allowed_statuses", [])
            return request.status in allowed_statuses
        
        return True
    
    async def _check_conflicts(
        self,
        db: Session,
        request_id: str,
        modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Vérifier les conflits potentiels"""
        
        # Vérifier les modifications concurrentes
        recent_modifications = db.query(RequestModification).filter(
            RequestModification.request_id == request_id,
            RequestModification.created_at >= datetime.utcnow() - timedelta(minutes=5)
        ).all()
        
        conflicts = []
        for modification in recent_modifications:
            if modification.field_name in modifications:
                conflicts.append({
                    "field": modification.field_name,
                    "conflicting_user": modification.user_id,
                    "timestamp": modification.created_at.isoformat()
                })
        
        return {"has_conflicts": len(conflicts) > 0, "conflicts": conflicts}
    
    async def _validate_status_transition(
        self,
        db: Session,
        current_status: str,
        new_status: str,
        user_id: str
    ) -> bool:
        """Valider une transition de statut"""
        
        # Règles de transition des statuts
        valid_transitions = {
            RequestStatus.DRAFT.value: [RequestStatus.PENDING.value, RequestStatus.CANCELLED.value],
            RequestStatus.PENDING.value: [RequestStatus.ASSIGNED.value, RequestStatus.CANCELLED.value],
            RequestStatus.ASSIGNED.value: [RequestStatus.IN_PROGRESS.value, RequestStatus.CANCELLED.value],
            RequestStatus.IN_PROGRESS.value: [RequestStatus.COMPLETED.value, RequestStatus.CANCELLED.value],
            RequestStatus.COMPLETED.value: [],
            RequestStatus.CANCELLED.value: []
        }
        
        allowed_transitions = valid_transitions.get(current_status, [])
        return new_status in allowed_transitions
    
    async def _send_modification_notifications(
        self,
        db: Session,
        request: UserRequest,
        modifications: List[Dict[str, Any]],
        user_id: str
    ):
        """Envoyer les notifications de modification"""
        
        # Notifier l'utilisateur
        notification_message = f"Votre demande '{request.title}' a été modifiée:\n"
        for mod in modifications:
            notification_message += f"- {mod['field']}: {mod['old_value']} → {mod['new_value']}\n"
        
        await self.notification_service.send_notification(
            db, user_id, "request_modified", "Demande modifiée",
            notification_message, request.request_id
        )
        
        # Notifier le prestataire si assigné
        if request.assigned_provider_id:
            await self.notification_service.send_notification(
                db, request.assigned_provider_id, "request_modified", 
                "Demande client modifiée", notification_message, request.request_id
            )
    
    async def _send_status_change_notifications(
        self,
        db: Session,
        request: UserRequest,
        old_status: str,
        new_status: str,
        user_id: str
    ):
        """Envoyer les notifications de changement de statut"""
        
        status_messages = {
            RequestStatus.PENDING.value: "Votre demande est en attente d'assignation",
            RequestStatus.ASSIGNED.value: "Votre demande a été assignée à un prestataire",
            RequestStatus.IN_PROGRESS.value: "Votre demande est en cours de traitement",
            RequestStatus.COMPLETED.value: "Votre demande a été complétée",
            RequestStatus.CANCELLED.value: "Votre demande a été annulée"
        }
        
        message = status_messages.get(new_status, f"Statut changé: {new_status}")
        
        await self.notification_service.send_notification(
            db, user_id, "status_change", "Changement de statut",
            message, request.request_id
        )