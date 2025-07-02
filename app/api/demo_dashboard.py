"""
Demo Dashboard API for testing Provider Dashboard
Provides mock data for dashboard functionality testing
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Any
from datetime import datetime, timedelta
import random
from app.api.demo_provider_auth import verify_demo_auth

router = APIRouter(prefix="/demo/dashboard", tags=["Demo Dashboard"])
security = HTTPBearer()

def get_demo_provider(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify demo authentication token"""
    provider = verify_demo_auth(credentials.credentials)
    if not provider:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return provider

@router.get("/stats")
async def get_demo_stats(provider: Dict = Depends(get_demo_provider)):
    """Get demo dashboard statistics"""
    
    return {
        "success": True,
        "stats": {
            "today": {
                "new_requests": random.randint(2, 8),
                "completed_jobs": random.randint(1, 5),
                "earnings": random.randint(15000, 45000)
            },
            "week": {
                "total_requests": random.randint(15, 35),
                "completed_jobs": random.randint(12, 28),
                "net_earnings": random.randint(120000, 280000),
                "acceptance_rate": random.randint(85, 98)
            },
            "performance": {
                "average_rating": round(random.uniform(4.2, 4.9), 1),
                "response_time_avg": random.randint(5, 15),
                "trust_score": random.randint(78, 95)
            },
            "notifications": {
                "unread_count": random.randint(1, 5),
                "total_count": random.randint(8, 20)
            }
        }
    }

@router.get("/requests")
async def get_demo_requests(
    status: str = "",
    limit: int = 20,
    provider: Dict = Depends(get_demo_provider)
):
    """Get demo service requests"""
    
    demo_requests = [
        {
            "id": 1,
            "service_type": "Plomberie",
            "location": "Bonamoussadi, Bloc M",
            "description": "Fuite d'eau sous l'évier de la cuisine",
            "urgency": "normal",
            "status": "PENDING",
            "estimated_price": {"min": 8000, "max": 15000},
            "user": {"name": "Marie Durand", "phone": "+237690123456"},
            "time_ago": "Il y a 15 minutes",
            "created_at": "2025-07-02T09:25:00Z"
        },
        {
            "id": 2,
            "service_type": "Électricité",
            "location": "Bonamoussadi, Rue des Palmiers",
            "description": "Panne électrique dans le salon",
            "urgency": "urgent",
            "status": "ASSIGNED",
            "estimated_price": {"min": 5000, "max": 12000},
            "user": {"name": "Paul Mbeki", "phone": "+237677987654"},
            "time_ago": "Il y a 1 heure",
            "created_at": "2025-07-02T08:40:00Z"
        },
        {
            "id": 3,
            "service_type": "Réparation électroménager",
            "location": "Bonamoussadi, Avenue de la Paix",
            "description": "Machine à laver ne démarre plus",
            "urgency": "normal",
            "status": "IN_PROGRESS",
            "estimated_price": {"min": 12000, "max": 25000},
            "user": {"name": "Claire Fokoua", "phone": "+237681567890"},
            "time_ago": "Il y a 3 heures",
            "created_at": "2025-07-02T06:40:00Z"
        },
        {
            "id": 4,
            "service_type": "Plomberie",
            "location": "Bonamoussadi, Carrefour Central",
            "description": "Réparation WC bloqué",
            "urgency": "normal", 
            "status": "COMPLETED",
            "estimated_price": {"min": 6000, "max": 10000},
            "user": {"name": "Jean Ondoua", "phone": "+237695432109"},
            "time_ago": "Il y a 1 jour",
            "created_at": "2025-07-01T14:20:00Z"
        }
    ]
    
    # Filter by status if provided
    if status:
        demo_requests = [req for req in demo_requests if req["status"] == status]
    
    return {
        "success": True,
        "requests": demo_requests[:limit],
        "pagination": {
            "current_page": 1,
            "total_pages": 1,
            "total_items": len(demo_requests)
        }
    }

@router.get("/notifications")
async def get_demo_notifications(
    limit: int = 20,
    provider: Dict = Depends(get_demo_provider)
):
    """Get demo notifications"""
    
    demo_notifications = [
        {
            "id": 1,
            "type": "new_request",
            "title": "Nouvelle demande reçue",
            "message": "Une nouvelle demande de plomberie à Bonamoussadi",
            "is_read": False,
            "is_urgent": True,
            "created_at": "2025-07-02T09:25:00Z"
        },
        {
            "id": 2,
            "type": "payment_received", 
            "title": "Paiement reçu",
            "message": "Paiement de 15,000 XAF reçu pour intervention électricité",
            "is_read": False,
            "is_urgent": False,
            "created_at": "2025-07-02T08:15:00Z"
        },
        {
            "id": 3,
            "type": "rating_received",
            "title": "Nouvelle évaluation",
            "message": "Vous avez reçu une note de 5/5 étoiles",
            "is_read": True,
            "is_urgent": False,
            "created_at": "2025-07-01T16:30:00Z"
        }
    ]
    
    return {
        "success": True,
        "notifications": demo_notifications[:limit]
    }

@router.get("/chart-data/{period}")
async def get_demo_chart_data(
    period: str,
    provider: Dict = Depends(get_demo_provider)
):
    """Get demo chart data for analytics"""
    
    if period == "week":
        revenue_data = [
            {"date": "Lun", "gross": 25000, "net": 21250},
            {"date": "Mar", "gross": 18000, "net": 15300},
            {"date": "Mer", "gross": 32000, "net": 27200},
            {"date": "Jeu", "gross": 15000, "net": 12750},
            {"date": "Ven", "gross": 28000, "net": 23800},
            {"date": "Sam", "gross": 35000, "net": 29750},
            {"date": "Dim", "gross": 22000, "net": 18700}
        ]
    elif period == "month":
        revenue_data = []
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            gross = random.randint(10000, 40000)
            revenue_data.append({
                "date": date.strftime("%d/%m"),
                "gross": gross,
                "net": int(gross * 0.85)  # 15% commission
            })
    else:
        revenue_data = []
        for i in range(12):
            month = datetime.now().replace(month=12-i) if 12-i > 0 else datetime.now().replace(year=datetime.now().year-1, month=12+12-i)
            gross = random.randint(150000, 400000)
            revenue_data.append({
                "date": month.strftime("%b"),
                "gross": gross,
                "net": int(gross * 0.85)
            })
    
    # Activity heatmap data (24 hours)
    activity_data = []
    for hour in range(24):
        activity_data.append({
            "hour": hour,
            "count": random.randint(0, 8) if 6 <= hour <= 22 else random.randint(0, 2)
        })
    
    return {
        "success": True,
        "revenue_chart": revenue_data,
        "service_breakdown": {
            "Plomberie": "45%",
            "Électricité": "35%", 
            "Électroménager": "20%"
        },
        "activity_heatmap": activity_data
    }

@router.put("/requests/{request_id}/accept")
async def accept_demo_request(
    request_id: int,
    provider: Dict = Depends(get_demo_provider)
):
    """Accept a demo request"""
    
    return {
        "success": True,
        "message": f"Demande {request_id} acceptée avec succès",
        "request_id": request_id,
        "status": "ASSIGNED"
    }

@router.put("/requests/{request_id}/decline")
async def decline_demo_request(
    request_id: int,
    provider: Dict = Depends(get_demo_provider)
):
    """Decline a demo request"""
    
    return {
        "success": True,
        "message": f"Demande {request_id} déclinée",
        "request_id": request_id,
        "status": "CANCELLED"
    }

@router.put("/requests/{request_id}/update-status")
async def update_demo_request_status(
    request_id: int,
    data: Dict[str, Any],
    provider: Dict = Depends(get_demo_provider)
):
    """Update demo request status"""
    
    status = data.get("status", "")
    notes = data.get("notes", "")
    final_price = data.get("final_price")
    
    return {
        "success": True,
        "message": f"Statut de la demande {request_id} mis à jour",
        "request_id": request_id,
        "status": status,
        "notes": notes,
        "final_price": final_price
    }