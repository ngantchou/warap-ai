"""
Request Management API - Standalone version for user requests
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import json
import uuid

from app.database import get_db

router = APIRouter(prefix="/api/v1/user-requests", tags=["User Request Management"])

# Pydantic models
class RequestCreateModel(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    service_type: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    priority: str = Field(default="normale")
    estimated_price: Optional[float] = None
    estimated_duration: Optional[int] = None
    materials_needed: Optional[List[str]] = None
    special_requirements: Optional[str] = None

class RequestUpdateModel(BaseModel):
    modifications: Dict[str, Any] = Field(...)

class ConversationModel(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)

class ResponseModel(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Helper functions
def format_request_data(row) -> Dict[str, Any]:
    """Format database row to request dictionary"""
    return {
        "request_id": row[0],
        "title": row[1],
        "description": row[2],
        "service_type": row[3],
        "location": row[4],
        "priority": row[5],
        "status": row[6],
        "estimated_price": row[7],
        "estimated_duration": row[8],
        "materials_needed": json.loads(row[9]) if row[9] else [],
        "special_requirements": row[10],
        "created_at": row[11].isoformat() if row[11] else None,
        "updated_at": row[12].isoformat() if row[12] else None,
        "scheduled_for": row[13].isoformat() if row[13] else None,
        "deadline": row[14].isoformat() if row[14] else None,
        "assigned_provider_id": row[15],
        "modification_count": row[16] or 0
    }

def process_conversation_message(message: str, user_id: str, db: Session) -> Dict[str, Any]:
    """Process conversational message for request management"""
    
    message_lower = message.lower()
    
    # View requests
    if any(word in message_lower for word in ["voir", "afficher", "liste", "demandes"]):
        query = text("""
            SELECT request_id, title, description, service_type, location, 
                   priority, status, estimated_price, estimated_duration,
                   materials_needed, special_requirements, created_at, updated_at,
                   scheduled_for, deadline, assigned_provider_id, modification_count
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        result = db.execute(query, {"user_id": user_id})
        requests = [format_request_data(row) for row in result]
        
        if not requests:
            return {
                "success": True,
                "response": "📭 Vous n'avez aucune demande active pour le moment.\n\n💡 Tapez 'nouvelle demande' pour créer votre première demande.",
                "data": {"requests": []}
            }
        
        response = "📋 **Vos demandes actives :**\n\n"
        for req in requests:
            status_emoji = "📝" if req["status"] == "brouillon" else "⏳" if req["status"] == "en_attente" else "✅"
            response += f"{status_emoji} **{req['request_id']}** - {req['title']}\n"
            response += f"   📍 {req['location']} | 🏷️ {req['status']}\n"
            if req['estimated_price']:
                response += f"   💰 {req['estimated_price']} XAF\n"
            response += "\n"
        
        response += "💡 *Tapez 'voir demande [ID]' pour plus de détails*"
        
        return {
            "success": True,
            "response": response,
            "data": {"requests": requests}
        }
    
    # Help
    elif any(word in message_lower for word in ["aide", "help", "comment"]):
        return {
            "success": True,
            "response": """🤖 **Aide - Gestion des demandes**

**Commandes disponibles :**
• `voir mes demandes` - Afficher toutes vos demandes
• `nouvelle demande` - Créer une nouvelle demande
• `voir demande [ID]` - Détails d'une demande
• `modifier demande [ID]` - Modifier une demande
• `annuler demande [ID]` - Annuler une demande

**Exemples :**
• "Voir mes demandes"
• "Nouvelle demande plomberie"
• "Voir demande req_abc123"
• "Modifier demande req_abc123"

*Vous pouvez utiliser un langage naturel !*""",
            "data": {"help_displayed": True}
        }
    
    # New request
    elif any(word in message_lower for word in ["nouvelle", "créer", "new"]) and "demande" in message_lower:
        return {
            "success": True,
            "response": """🆕 **Création d'une nouvelle demande**

Pour créer une demande, j'ai besoin de :
1. **Type de service** (plomberie, électricité, électroménager)
2. **Description** du problème
3. **Adresse** d'intervention
4. **Priorité** (normale, haute, urgente)

**Exemple :**
*"Nouvelle demande plomberie : fuite d'eau cuisine, 123 rue Liberté Bonamoussadi, urgente"*

Ou utilisez l'API POST /api/v1/user-requests/create""",
            "data": {"awaiting_new_request": True}
        }
    
    # Default response
    else:
        return {
            "success": True,
            "response": """🤖 **Assistant Demandes de Service**

Je peux vous aider à gérer vos demandes de service.

**Commandes rapides :**
• `voir mes demandes` - Voir toutes vos demandes
• `nouvelle demande` - Créer une demande
• `aide` - Afficher l'aide complète

*Que souhaitez-vous faire ?*""",
            "data": {"default_response": True}
        }

# API Endpoints

@router.post("/create", response_model=ResponseModel)
async def create_request(
    request_data: RequestCreateModel,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Create a new user request"""
    
    try:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        
        query = text("""
            INSERT INTO user_requests (
                request_id, user_id, title, description, service_type, 
                location, priority, status, estimated_price, estimated_duration,
                materials_needed, special_requirements, created_at, updated_at
            ) VALUES (
                :request_id, :user_id, :title, :description, :service_type,
                :location, :priority, :status, :estimated_price, :estimated_duration,
                :materials_needed, :special_requirements, :created_at, :updated_at
            )
        """)
        
        params = {
            "request_id": request_id,
            "user_id": user_id,
            "title": request_data.title,
            "description": request_data.description,
            "service_type": request_data.service_type,
            "location": request_data.location,
            "priority": request_data.priority,
            "status": "brouillon",
            "estimated_price": request_data.estimated_price,
            "estimated_duration": request_data.estimated_duration,
            "materials_needed": json.dumps(request_data.materials_needed or []),
            "special_requirements": request_data.special_requirements,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(query, params)
        db.commit()
        
        return ResponseModel(
            success=True,
            message="Demande créée avec succès",
            data={
                "request_id": request_id,
                "status": "brouillon",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création: {str(e)}")

@router.get("/list", response_model=ResponseModel)
async def list_requests(
    user_id: str = Query(..., description="User ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100, description="Limit results"),
    db: Session = Depends(get_db)
):
    """List user requests"""
    
    try:
        base_query = """
            SELECT request_id, title, description, service_type, location, 
                   priority, status, estimated_price, estimated_duration,
                   materials_needed, special_requirements, created_at, updated_at,
                   scheduled_for, deadline, assigned_provider_id, modification_count
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
        """
        
        params = {"user_id": user_id}
        
        if status_filter:
            base_query += " AND status = :status"
            params["status"] = status_filter
        
        base_query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit
        
        result = db.execute(text(base_query), params)
        requests = [format_request_data(row) for row in result]
        
        return ResponseModel(
            success=True,
            data={
                "requests": requests,
                "count": len(requests),
                "filter": status_filter
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.get("/{request_id}", response_model=ResponseModel)
async def get_request_details(
    request_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get request details"""
    
    try:
        query = text("""
            SELECT request_id, title, description, service_type, location, 
                   priority, status, estimated_price, estimated_duration,
                   materials_needed, special_requirements, created_at, updated_at,
                   scheduled_for, deadline, assigned_provider_id, modification_count
            FROM user_requests 
            WHERE request_id = :request_id AND user_id = :user_id AND is_active = true
        """)
        
        result = db.execute(query, {"request_id": request_id, "user_id": user_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        return ResponseModel(
            success=True,
            data=format_request_data(row)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.put("/{request_id}/modify", response_model=ResponseModel)
async def modify_request(
    request_id: str,
    update_data: RequestUpdateModel,
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Modify a request"""
    
    try:
        # Check if request exists
        check_query = text("""
            SELECT request_id, status FROM user_requests 
            WHERE request_id = :request_id AND user_id = :user_id AND is_active = true
        """)
        
        result = db.execute(check_query, {"request_id": request_id, "user_id": user_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        # Build update query
        update_fields = []
        params = {"request_id": request_id, "user_id": user_id, "updated_at": datetime.utcnow()}
        
        allowed_fields = ["title", "description", "location", "priority", "estimated_price", "estimated_duration", "special_requirements"]
        modifications_applied = []
        
        for field, new_value in update_data.modifications.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = :{field}")
                params[field] = new_value
                modifications_applied.append({
                    "field": field,
                    "new_value": new_value
                })
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="Aucune modification valide")
        
        # Update request
        update_query = text(f"""
            UPDATE user_requests 
            SET {', '.join(update_fields)}, updated_at = :updated_at, modification_count = modification_count + 1
            WHERE request_id = :request_id AND user_id = :user_id
        """)
        
        db.execute(update_query, params)
        db.commit()
        
        return ResponseModel(
            success=True,
            message="Demande modifiée avec succès",
            data={
                "request_id": request_id,
                "modifications_applied": modifications_applied
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la modification: {str(e)}")

@router.put("/{request_id}/status", response_model=ResponseModel)
async def change_status(
    request_id: str,
    new_status: str = Query(..., description="New status"),
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Change request status"""
    
    try:
        # Update status
        query = text("""
            UPDATE user_requests 
            SET status = :new_status, updated_at = :updated_at
            WHERE request_id = :request_id AND user_id = :user_id AND is_active = true
        """)
        
        result = db.execute(query, {
            "new_status": new_status,
            "updated_at": datetime.utcnow(),
            "request_id": request_id,
            "user_id": user_id
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        db.commit()
        
        return ResponseModel(
            success=True,
            message=f"Statut changé vers {new_status}",
            data={"request_id": request_id, "new_status": new_status}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du changement: {str(e)}")

@router.delete("/{request_id}/cancel", response_model=ResponseModel)
async def cancel_request(
    request_id: str,
    user_id: str = Query(..., description="User ID"),
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    db: Session = Depends(get_db)
):
    """Cancel a request"""
    
    try:
        query = text("""
            UPDATE user_requests 
            SET status = 'annulée', updated_at = :updated_at
            WHERE request_id = :request_id AND user_id = :user_id AND is_active = true
        """)
        
        result = db.execute(query, {
            "updated_at": datetime.utcnow(),
            "request_id": request_id,
            "user_id": user_id
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        
        db.commit()
        
        return ResponseModel(
            success=True,
            message="Demande annulée avec succès",
            data={"request_id": request_id, "new_status": "annulée"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'annulation: {str(e)}")

@router.get("/analytics/summary", response_model=ResponseModel)
async def get_analytics(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """Get analytics summary"""
    
    try:
        # Status distribution
        status_query = text("""
            SELECT status, COUNT(*) as count
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
            GROUP BY status
        """)
        
        status_result = db.execute(status_query, {"user_id": user_id})
        status_distribution = {row[0]: row[1] for row in status_result}
        
        # Priority distribution
        priority_query = text("""
            SELECT priority, COUNT(*) as count
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
            GROUP BY priority
        """)
        
        priority_result = db.execute(priority_query, {"user_id": user_id})
        priority_distribution = {row[0]: row[1] for row in priority_result}
        
        # Total requests
        total_query = text("""
            SELECT COUNT(*) as total FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
        """)
        
        total_result = db.execute(total_query, {"user_id": user_id})
        total_requests = total_result.fetchone()[0]
        
        # Recent requests
        recent_query = text("""
            SELECT request_id, title, status, created_at
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
            ORDER BY created_at DESC LIMIT 5
        """)
        
        recent_result = db.execute(recent_query, {"user_id": user_id})
        recent_requests = [
            {
                "request_id": row[0],
                "title": row[1],
                "status": row[2],
                "created_at": row[3].isoformat() if row[3] else None
            }
            for row in recent_result
        ]
        
        return ResponseModel(
            success=True,
            data={
                "total_requests": total_requests,
                "status_distribution": status_distribution,
                "priority_distribution": priority_distribution,
                "recent_requests": recent_requests
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors des analytics: {str(e)}")

@router.post("/conversation", response_model=ResponseModel)
async def process_conversation(
    conversation: ConversationModel,
    db: Session = Depends(get_db)
):
    """Process conversational message"""
    
    try:
        result = process_conversation_message(conversation.message, conversation.user_id, db)
        
        return ResponseModel(
            success=result["success"],
            message=result.get("response"),
            data=result.get("data", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur conversationnelle: {str(e)}")

@router.get("/test/conversation", response_model=ResponseModel)
async def test_conversation(
    message: str = Query("voir mes demandes", description="Test message"),
    user_id: str = Query("237691924172", description="Test user ID"),
    db: Session = Depends(get_db)
):
    """Test conversational interface"""
    
    try:
        result = process_conversation_message(message, user_id, db)
        
        return ResponseModel(
            success=True,
            message=result.get("response"),
            data={
                "test_message": message,
                "user_id": user_id,
                "result": result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du test: {str(e)}")