"""
API simple pour la gestion des demandes - Version intégrée
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.simple_request_management import SimpleRequestManager

router = APIRouter(prefix="/api/v1/requests", tags=["Simple Request Management"])

# Service
request_manager = SimpleRequestManager()

# Modèles Pydantic
class RequestCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    service_type: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    priority: Optional[str] = Field("normale")
    estimated_price: Optional[float] = None
    estimated_duration: Optional[int] = None
    materials_needed: Optional[List[str]] = None
    special_requirements: Optional[str] = None

class RequestModifyRequest(BaseModel):
    modifications: Dict[str, Any] = Field(...)

class ConversationRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)

class RequestResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Endpoints
@router.post("/create", response_model=RequestResponse)
async def create_request(
    request_data: RequestCreateRequest,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle demande"""
    
    try:
        result = await request_manager.create_request(
            db, user_id, request_data.dict()
        )
        
        return RequestResponse(
            success=True,
            message="Demande créée avec succès",
            data=result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création: {str(e)}"
        )

@router.get("/list", response_model=RequestResponse)
async def list_requests(
    user_id: str = Query(..., description="User ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer les demandes d'un utilisateur"""
    
    try:
        requests = await request_manager.get_user_requests(
            db, user_id, status_filter, limit
        )
        
        return RequestResponse(
            success=True,
            data={
                "requests": requests,
                "count": len(requests)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.get("/{request_id}", response_model=RequestResponse)
async def get_request_details(
    request_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Récupérer les détails d'une demande"""
    
    try:
        request = await request_manager.get_request_details(db, request_id, user_id)
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demande non trouvée"
            )
        
        return RequestResponse(
            success=True,
            data=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}"
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
        result = await request_manager.modify_request(
            db, request_id, user_id, modify_data.modifications
        )
        
        if result["success"]:
            return RequestResponse(
                success=True,
                message="Demande modifiée avec succès",
                data=result
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
async def change_status(
    request_id: str,
    new_status: str = Query(..., description="New status"),
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Changer le statut d'une demande"""
    
    try:
        result = await request_manager.change_status(
            db, request_id, new_status, user_id
        )
        
        if result["success"]:
            return RequestResponse(
                success=True,
                message=f"Statut changé vers {new_status}",
                data=result
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
            detail=f"Erreur lors du changement: {str(e)}"
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
        result = await request_manager.cancel_request(db, request_id, user_id, reason)
        
        if result["success"]:
            return RequestResponse(
                success=True,
                message="Demande annulée avec succès",
                data=result
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

@router.get("/analytics/summary", response_model=RequestResponse)
async def get_analytics(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Récupérer les analytics des demandes"""
    
    try:
        result = await request_manager.get_analytics(db, user_id)
        
        return RequestResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des analytics: {str(e)}"
        )

@router.post("/conversation", response_model=RequestResponse)
async def process_conversation(
    conversation: ConversationRequest,
    db: Session = Depends(get_db)
):
    """Traiter un message conversationnel"""
    
    try:
        result = await request_manager.process_conversation(
            db, conversation.user_id, conversation.message
        )
        
        return RequestResponse(
            success=result["success"],
            message=result.get("response"),
            data=result.get("data", {})
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement: {str(e)}"
        )

@router.get("/test/conversational", response_model=RequestResponse)
async def test_conversational(
    test_message: str = Query("voir mes demandes", description="Test message"),
    user_id: str = Query("237691924172", description="Test user ID"),
    db: Session = Depends(get_db)
):
    """Tester l'interface conversationnelle"""
    
    try:
        result = await request_manager.process_conversation(db, user_id, test_message)
        
        return RequestResponse(
            success=True,
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
            detail=f"Erreur lors du test: {str(e)}"
        )