"""
Service de gestion simple des demandes - Version intégrée
"""
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

class SimpleRequestManager:
    """Gestionnaire simple des demandes utilisateur"""
    
    def __init__(self):
        pass
    
    async def create_request(self, db: Session, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Créer une nouvelle demande"""
        
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        
        # SQL pour insérer la demande
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
            "title": request_data.get("title", ""),
            "description": request_data.get("description", ""),
            "service_type": request_data.get("service_type", ""),
            "location": request_data.get("location", ""),
            "priority": request_data.get("priority", "normale"),
            "status": "brouillon",
            "estimated_price": request_data.get("estimated_price"),
            "estimated_duration": request_data.get("estimated_duration"),
            "materials_needed": json.dumps(request_data.get("materials_needed", [])),
            "special_requirements": request_data.get("special_requirements", ""),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(query, params)
        db.commit()
        
        return {
            "success": True,
            "request_id": request_id,
            "status": "brouillon",
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def get_user_requests(self, db: Session, user_id: str, status_filter: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupérer les demandes d'un utilisateur"""
        
        base_query = """
            SELECT request_id, title, description, service_type, location, 
                   priority, status, estimated_price, created_at, updated_at
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
        
        requests = []
        for row in result:
            requests.append({
                "request_id": row[0],
                "title": row[1],
                "description": row[2],
                "service_type": row[3],
                "location": row[4],
                "priority": row[5],
                "status": row[6],
                "estimated_price": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None
            })
        
        return requests
    
    async def get_request_details(self, db: Session, request_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer les détails d'une demande"""
        
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
            return None
        
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
    
    async def modify_request(self, db: Session, request_id: str, user_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Modifier une demande"""
        
        # Vérifier que la demande existe
        request = await self.get_request_details(db, request_id, user_id)
        if not request:
            return {"success": False, "error": "Demande non trouvée"}
        
        # Construire la requête de mise à jour
        update_fields = []
        params = {"request_id": request_id, "user_id": user_id, "updated_at": datetime.utcnow()}
        
        allowed_fields = ["title", "description", "location", "priority", "estimated_price", "estimated_duration", "special_requirements"]
        
        modifications_applied = []
        for field, new_value in modifications.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = :{field}")
                params[field] = new_value
                modifications_applied.append({
                    "field": field,
                    "old_value": request.get(field),
                    "new_value": new_value
                })
        
        if not update_fields:
            return {"success": False, "error": "Aucune modification valide"}
        
        # Mettre à jour la demande
        query = text(f"""
            UPDATE user_requests 
            SET {', '.join(update_fields)}, updated_at = :updated_at, modification_count = modification_count + 1
            WHERE request_id = :request_id AND user_id = :user_id
        """)
        
        db.execute(query, params)
        db.commit()
        
        return {
            "success": True,
            "modifications_applied": modifications_applied,
            "request": await self.get_request_details(db, request_id, user_id)
        }
    
    async def change_status(self, db: Session, request_id: str, new_status: str, user_id: str) -> Dict[str, Any]:
        """Changer le statut d'une demande"""
        
        # Vérifier que la demande existe
        request = await self.get_request_details(db, request_id, user_id)
        if not request:
            return {"success": False, "error": "Demande non trouvée"}
        
        # Mettre à jour le statut
        query = text("""
            UPDATE user_requests 
            SET status = :new_status, updated_at = :updated_at
            WHERE request_id = :request_id AND user_id = :user_id
        """)
        
        db.execute(query, {
            "new_status": new_status,
            "updated_at": datetime.utcnow(),
            "request_id": request_id,
            "user_id": user_id
        })
        db.commit()
        
        return {
            "success": True,
            "new_status": new_status
        }
    
    async def cancel_request(self, db: Session, request_id: str, user_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Annuler une demande"""
        
        return await self.change_status(db, request_id, "annulée", user_id)
    
    async def get_analytics(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Obtenir les analytics pour un utilisateur"""
        
        # Compter les demandes par statut
        status_query = text("""
            SELECT status, COUNT(*) as count
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
            GROUP BY status
        """)
        
        status_result = db.execute(status_query, {"user_id": user_id})
        status_distribution = {row[0]: row[1] for row in status_result}
        
        # Compter les demandes par priorité
        priority_query = text("""
            SELECT priority, COUNT(*) as count
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
            GROUP BY priority
        """)
        
        priority_result = db.execute(priority_query, {"user_id": user_id})
        priority_distribution = {row[0]: row[1] for row in priority_result}
        
        # Total des demandes
        total_query = text("""
            SELECT COUNT(*) as total
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
        """)
        
        total_result = db.execute(total_query, {"user_id": user_id})
        total_requests = total_result.fetchone()[0]
        
        # Demandes récentes
        recent_query = text("""
            SELECT request_id, title, status, created_at
            FROM user_requests 
            WHERE user_id = :user_id AND is_active = true
            ORDER BY created_at DESC
            LIMIT 5
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
        
        return {
            "success": True,
            "total_requests": total_requests,
            "status_distribution": status_distribution,
            "priority_distribution": priority_distribution,
            "recent_requests": recent_requests
        }
    
    async def process_conversation(self, db: Session, user_id: str, message: str) -> Dict[str, Any]:
        """Traiter un message conversationnel simple"""
        
        message_lower = message.lower()
        
        # Reconnaissance d'intention simple
        if "voir" in message_lower and "demande" in message_lower:
            # Afficher les demandes
            requests = await self.get_user_requests(db, user_id, limit=10)
            
            if not requests:
                return {
                    "success": True,
                    "response": "📭 Vous n'avez aucune demande active pour le moment.\n\n💡 Tapez 'nouvelle demande' pour créer votre première demande."
                }
            
            response = "📋 **Vos demandes actives :**\n\n"
            for req in requests:
                status_emoji = "📝" if req["status"] == "brouillon" else "⏳" if req["status"] == "en_attente" else "✅"
                response += f"{status_emoji} **{req['request_id']}** - {req['title']}\n"
                response += f"   📍 {req['location']} | 🏷️ {req['status']}\n\n"
            
            return {
                "success": True,
                "response": response
            }
        
        elif "aide" in message_lower or "help" in message_lower:
            # Aide
            return {
                "success": True,
                "response": """🤖 **Aide - Gestion des demandes**

**Commandes disponibles :**
• `voir mes demandes` - Afficher toutes vos demandes
• `nouvelle demande` - Créer une nouvelle demande
• `aide` - Afficher cette aide

**Exemples :**
• "Voir mes demandes"
• "Nouvelle demande plomberie"
• "Aide"

*Vous pouvez utiliser un langage naturel !*"""
            }
        
        else:
            # Réponse par défaut
            return {
                "success": True,
                "response": "🤖 Je peux vous aider avec vos demandes de service.\n\n💡 Tapez 'voir mes demandes' pour voir vos demandes ou 'aide' pour plus d'options."
            }