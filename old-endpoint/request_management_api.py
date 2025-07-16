"""
Request Management API - API REST pour la gestion des demandes utilisateur
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.database_models import Base
from app.services.request_management_service import RequestManagementService
from app.services.conversational_request_service import ConversationalRequestService
from app.models.request_management_models import RequestStatus, RequestPriority

router = APIRouter(prefix="/api/v1/requests", tags=["Request Management"])

# Initialize services
request_service = RequestManagementService()
conversational_service = ConversationalRequestService()

# Pydantic models
class RequestCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    service_type: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    priority: Optional[str] = Field(RequestPriority.NORMAL.value)
    estimated_price: Optional[float] = None
    estimated_duration: Optional[int] = None
    materials_needed: Optional[List[str]] = None
    special_requirements: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    deadline: Optional[datetime] = None

class RequestModifyRequest(BaseModel):
    modifications: Dict[str, Any] = Field(...)
    reason: Optional[str] = None

class ConversationRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None

class RequestResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# API Endpoints

@router.post("/create", response_model=RequestResponse)
async def create_request(
    request_data: RequestCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle demande"""
    
    try:
        # Convertir en dictionnaire
        request_dict = request_data.dict()
        
        # Créer la demande
        request = await request_service.create_request(
            db, user_id, request_dict
        )
        
        return RequestResponse(
            success=True,
            message="Demande créée avec succès",
            data={
                "request_id": request.request_id,
                "status": request.status,
                "created_at": request.created_at.isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de la demande: {str(e)}"
        )

@router.get("/list", response_model=RequestResponse)
async def list_requests(
    user_id: str = Query(..., description="User ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100, description="Number of requests to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """Récupérer les demandes d'un utilisateur"""
    
    try:
        requests = await request_service.get_user_requests(
            db, user_id, status_filter, limit, offset
        )
        
        requests_data = [
            {
                "request_id": req.request_id,
                "title": req.title,
                "description": req.description,
                "service_type": req.service_type,
                "location": req.location,
                "status": req.status,
                "priority": req.priority,
                "created_at": req.created_at.isoformat(),
                "updated_at": req.updated_at.isoformat()
            }
            for req in requests
        ]
        
        return RequestResponse(
            success=True,
            data={
                "requests": requests_data,
                "count": len(requests_data),
                "filters": {"status": status_filter}
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des demandes: {str(e)}"
        )

@router.get("/{request_id}", response_model=RequestResponse)
async def get_request_details(
    request_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Récupérer les détails d'une demande"""
    
    try:
        request = await request_service.get_request_details(db, request_id, user_id)
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demande non trouvée ou accès refusé"
            )
        
        return RequestResponse(
            success=True,
            data={
                "request_id": request.request_id,
                "title": request.title,
                "description": request.description,
                "service_type": request.service_type,
                "location": request.location,
                "status": request.status,
                "priority": request.priority,
                "estimated_price": request.estimated_price,
                "estimated_duration": request.estimated_duration,
                "materials_needed": request.materials_needed,
                "special_requirements": request.special_requirements,
                "created_at": request.created_at.isoformat(),
                "updated_at": request.updated_at.isoformat(),
                "scheduled_for": request.scheduled_for.isoformat() if request.scheduled_for else None,
                "deadline": request.deadline.isoformat() if request.deadline else None,
                "assigned_provider_id": request.assigned_provider_id,
                "modification_count": request.modification_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des détails: {str(e)}"
        )

@router.put("/{request_id}/modify", response_model=RequestResponse)
async def modify_request(
    request_id: str,
    modify_data: RequestModifyRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Modifier une demande"""
    
    try:
        conversation_context = {"reason": modify_data.reason} if modify_data.reason else None
        
        result = await request_service.modify_request(
            db, request_id, user_id, modify_data.modifications, conversation_context
        )
        
        if result["success"]:
            return RequestResponse(
                success=True,
                message="Demande modifiée avec succès",
                data={
                    "request_id": request_id,
                    "modifications_applied": result["modifications_applied"],
                    "modification_count": len(result["modifications_applied"])
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la modification: {str(e)}"
        )

@router.put("/{request_id}/status", response_model=RequestResponse)
async def change_request_status(
    request_id: str,
    new_status: str = Query(..., description="New status"),
    user_id: str = Query(..., description="User ID"),
    reason: Optional[str] = Query(None, description="Reason for status change"),
    db: Session = Depends(get_db)
):
    """Changer le statut d'une demande"""
    
    try:
        result = await request_service.change_request_status(
            db, request_id, new_status, user_id, reason
        )
        
        if result["success"]:
            return RequestResponse(
                success=True,
                message=f"Statut changé vers {new_status}",
                data={
                    "request_id": request_id,
                    "new_status": result["new_status"]
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du changement de statut: {str(e)}"
        )

@router.delete("/{request_id}/cancel", response_model=RequestResponse)
async def cancel_request(
    request_id: str,
    user_id: str = Query(..., description="User ID"),
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    db: Session = Depends(get_db)
):
    """Annuler une demande"""
    
    try:
        result = await request_service.cancel_request(db, request_id, user_id, reason)
        
        if result["success"]:
            return RequestResponse(
                success=True,
                message="Demande annulée avec succès",
                data={
                    "request_id": request_id,
                    "new_status": result["new_status"]
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'annulation: {str(e)}"
        )

@router.delete("/{request_id}", response_model=RequestResponse)
async def delete_request(
    request_id: str,
    user_id: str = Query(..., description="User ID"),
    reason: Optional[str] = Query(None, description="Reason for deletion"),
    db: Session = Depends(get_db)
):
    """Supprimer une demande"""
    
    try:
        result = await request_service.delete_request(db, request_id, user_id, reason)
        
        if result["success"]:
            return RequestResponse(
                success=True,
                message="Demande supprimée avec succès",
                data={"request_id": request_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )

@router.get("/{request_id}/history", response_model=RequestResponse)
async def get_request_history(
    request_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Récupérer l'historique d'une demande"""
    
    try:
        history = await request_service.get_request_history(db, request_id, user_id)
        
        if history["success"]:
            return RequestResponse(
                success=True,
                data=history
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=history["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'historique: {str(e)}"
        )

@router.post("/conversation", response_model=RequestResponse)
async def process_conversation(
    conversation: ConversationRequest,
    db: Session = Depends(get_db)
):
    """Traiter un message conversationnel"""
    
    try:
        result = await conversational_service.process_conversation_message(
            db, conversation.user_id, conversation.message, conversation.context
        )
        
        return RequestResponse(
            success=result["success"],
            message=result.get("response"),
            data=result.get("data", {})
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement de la conversation: {str(e)}"
        )

@router.get("/analytics/summary", response_model=RequestResponse)
async def get_analytics_summary(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Récupérer un résumé analytique des demandes"""
    
    try:
        requests = await request_service.get_user_requests(db, user_id, limit=1000)
        
        # Calculer les statistiques
        total_requests = len(requests)
        status_distribution = {}
        priority_distribution = {}
        
        for req in requests:
            # Distribution par statut
            status_distribution[req.status] = status_distribution.get(req.status, 0) + 1
            
            # Distribution par priorité
            priority_distribution[req.priority] = priority_distribution.get(req.priority, 0) + 1
        
        return RequestResponse(
            success=True,
            data={
                "total_requests": total_requests,
                "status_distribution": status_distribution,
                "priority_distribution": priority_distribution,
                "recent_requests": [
                    {
                        "request_id": req.request_id,
                        "title": req.title,
                        "status": req.status,
                        "created_at": req.created_at.isoformat()
                    }
                    for req in requests[:5]
                ]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des analytics: {str(e)}"
        )

@router.get("/test/conversational", response_model=RequestResponse)
async def test_conversational_interface(
    test_message: str = Query("voir mes demandes", description="Test message"),
    user_id: str = Query("test_user_123", description="Test user ID"),
    db: Session = Depends(get_db)
):
    """Tester l'interface conversationnelle"""
    
    try:
        result = await conversational_service.process_conversation_message(
            db, user_id, test_message
        )
        
        return RequestResponse(
            success=result["success"],
            message=result.get("response"),
            data={
                "test_message": test_message,
                "user_id": user_id,
                "result": result
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du test conversationnel: {str(e)}"
        )