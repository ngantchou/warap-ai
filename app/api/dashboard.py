"""
Dashboard API endpoints for Djobea AI
Implements all dashboard routes with JWT authentication and PostgreSQL integration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

from app.database import get_db
from app.services.auth_service import get_current_user
from app.api.auth import get_current_admin_user
from app.models.database_models import (
    ServiceRequest, Provider, User, Conversation, RequestStatus, AdminUser
)
from app.config import get_settings
from loguru import logger

router = APIRouter(tags=["dashboard"])
settings = get_settings()

# Response models
class StatsResponse:
    """Dashboard statistics response"""
    def __init__(self, total_requests: int, success_rate: float, pending_requests: int, active_providers: int):
        self.totalRequests = total_requests
        self.successRate = success_rate
        self.pendingRequests = pending_requests
        self.activeProviders = active_providers

class ChartData:
    """Chart data structure"""
    def __init__(self, labels: List[str], values: List[int]):
        self.labels = labels
        self.values = values

class ActivityItem:
    """Activity item for recent activity"""
    def __init__(self, request_id: str, client_name: str, service_type: str, 
                 status: str, created_at: datetime, location: str = None):
        self.id = request_id
        self.clientName = client_name
        self.serviceType = service_type
        self.status = status
        self.createdAt = created_at.isoformat()
        self.location = location

class AlertItem:
    """Alert item for system alerts"""
    def __init__(self, alert_type: str, message: str, severity: str, created_at: datetime):
        self.type = alert_type
        self.message = message
        self.severity = severity
        self.createdAt = created_at.isoformat()

@router.get("/")
async def get_dashboard_data(
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/dashboard - Données principales du tableau de bord
    Récupère statistiques globales, données graphiques et activité récente
    """
    try:
        logger.info("Fetching comprehensive dashboard data")
        
        # Statistiques globales
        total_requests = db.query(ServiceRequest).count()
        completed_requests = db.query(ServiceRequest).filter(
            ServiceRequest.status == 'COMPLETED'
        ).count()
        success_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0.0
        
        # Demandes en attente
        pending_requests = db.query(ServiceRequest).filter(
            ServiceRequest.status.in_(['PENDING', 'PROVIDER_NOTIFIED', 'ASSIGNED'])
        ).count()
        
        # Prestataires actifs
        active_providers = db.query(Provider).filter(
            Provider.is_active == True
        ).count()
        
        # Données graphiques - Activité de la semaine
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
        
        # Activité par jour (derniers 7 jours)
        activity_data = []
        activity_labels = []
        
        for i in range(7):
            day_date = start_date + timedelta(days=i)
            day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_requests = db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.created_at >= day_start,
                    ServiceRequest.created_at < day_end
                )
            ).count()
            
            activity_data.append(day_requests)
            # Format français pour les jours
            day_names = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
            activity_labels.append(day_names[day_date.weekday()])
        
        # Distribution des services
        service_stats = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('count')
        ).group_by(ServiceRequest.service_type).all()
        
        service_labels = []
        service_values = []
        service_mapping = {
            'plomberie': 'Plomberie',
            'électricité': 'Électricité',
            'électroménager': 'Réparation'
        }
        
        for service_type, count in service_stats:
            if service_type:
                service_labels.append(service_mapping.get(service_type, service_type.capitalize()))
                service_values.append(count)
        
        # Activité récente (dernières demandes)
        recent_requests = db.query(ServiceRequest).join(
            User, ServiceRequest.user_id == User.id, isouter=True
        ).order_by(desc(ServiceRequest.created_at)).limit(10).all()
        
        requests_activity = []
        for request in recent_requests:
            # Générer un nom de client anonymisé
            client_name = f"Client #{request.id}"
            if request.user and hasattr(request.user, 'phone_number'):
                # Utiliser les 4 derniers chiffres du téléphone
                phone = request.user.phone_number or ""
                if len(phone) >= 4:
                    client_name = f"Client {phone[-4:]}"
            
            requests_activity.append({
                "id": f"req-{request.id}",
                "client": client_name,
                "service": service_mapping.get(request.service_type, request.service_type or "Service"),
                "location": request.location or "Douala",
                "time": request.created_at.isoformat() if request.created_at else datetime.now().isoformat(),
                "status": request.status or "pending",
                "avatar": f"/avatars/client{request.id % 10 + 1}.jpg"
            })
        
        # Alertes système
        alerts = []
        
        # Alerte pour demandes urgentes (basée sur le description ou urgency)
        urgent_requests = db.query(ServiceRequest).filter(
            and_(
                or_(
                    ServiceRequest.description.contains('urgent'),
                    ServiceRequest.urgency == 'urgent'
                ),
                ServiceRequest.status.in_(['PENDING', 'PROVIDER_NOTIFIED'])
            )
        ).count()
        
        if urgent_requests > 0:
            alerts.append({
                "id": f"alert-urgent-{datetime.now().strftime('%Y%m%d')}",
                "title": "Demandes urgentes en attente",
                "description": f"{urgent_requests} demande(s) urgente(s) nécessitent une attention immédiate",
                "time": datetime.now().isoformat(),
                "type": "warning",
                "status": "unread"
            })
        
        # Alerte pour prestataires inactifs
        if active_providers < 10:
            alerts.append({
                "id": f"alert-providers-{datetime.now().strftime('%Y%m%d')}",
                "title": "Nombre de prestataires faible",
                "description": f"Seulement {active_providers} prestataire(s) actif(s) disponible(s)",
                "time": datetime.now().isoformat(),
                "type": "info",
                "status": "unread"
            })
        
        # Alerte pour taux de succès faible
        if success_rate < 80 and total_requests > 0:
            alerts.append({
                "id": f"alert-success-{datetime.now().strftime('%Y%m%d')}",
                "title": "Taux de succès faible",
                "description": f"Taux de succès actuel: {success_rate:.1f}% - Optimisation nécessaire",
                "time": datetime.now().isoformat(),
                "type": "warning",
                "status": "unread"
            })
        
        # Construire la réponse selon les spécifications
        dashboard_data = {
            "stats": {
                "totalRequests": total_requests,
                "successRate": round(success_rate, 1),
                "pendingRequests": pending_requests,
                "activeProviders": active_providers
            },
            "charts": {
                "activity": {
                    "labels": activity_labels,
                    "values": activity_data
                },
                "services": {
                    "labels": service_labels,
                    "values": service_values
                }
            },
            "activity": {
                "requests": requests_activity,
                "alerts": alerts
            }
        }
        
        logger.info(f"Dashboard data retrieved successfully: {total_requests} requests, {success_rate:.1f}% success rate")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des données du tableau de bord")

@router.get("/stats")
async def get_dashboard_stats(
    period: str = Query("7d", regex="^(24h|7d|30d)$"),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/dashboard/stats - Statistiques en temps réel
    Supporter query params: period=24h|7d|30d
    """
    try:
        # Calculer la période
        if period == "24h":
            time_delta = timedelta(hours=24)
        elif period == "7d":
            time_delta = timedelta(days=7)
        elif period == "30d":
            time_delta = timedelta(days=30)
        else:
            time_delta = timedelta(days=7)
        
        start_date = datetime.utcnow() - time_delta
        previous_start = start_date - time_delta
        
        # Statistiques période courante
        current_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= start_date
        ).count()
        
        current_completed = db.query(ServiceRequest).filter(
            and_(
                ServiceRequest.created_at >= start_date,
                ServiceRequest.status == 'COMPLETED'
            )
        ).count()
        
        current_success_rate = (current_completed / current_requests * 100) if current_requests > 0 else 0
        
        # Temps de réponse moyen (simulé basé sur les données)
        avg_response_time = db.query(
            func.avg(
                func.extract('epoch', ServiceRequest.updated_at - ServiceRequest.created_at)
            ).label('avg_time')
        ).filter(
            and_(
                ServiceRequest.created_at >= start_date,
                ServiceRequest.status == 'COMPLETED'
            )
        ).scalar() or 0
        
        avg_response_time = avg_response_time / 60  # Convertir en minutes
        
        # Satisfaction (simulée basée sur le taux de succès)
        satisfaction = min(current_success_rate + 10, 100)
        
        # Statistiques période précédente pour les tendances
        previous_requests = db.query(ServiceRequest).filter(
            and_(
                ServiceRequest.created_at >= previous_start,
                ServiceRequest.created_at < start_date
            )
        ).count()
        
        previous_completed = db.query(ServiceRequest).filter(
            and_(
                ServiceRequest.created_at >= previous_start,
                ServiceRequest.created_at < start_date,
                ServiceRequest.status == 'COMPLETED'
            )
        ).count()
        
        previous_success_rate = (previous_completed / previous_requests * 100) if previous_requests > 0 else 0
        
        previous_avg_response_time = db.query(
            func.avg(
                func.extract('epoch', ServiceRequest.updated_at - ServiceRequest.created_at)
            ).label('avg_time')
        ).filter(
            and_(
                ServiceRequest.created_at >= previous_start,
                ServiceRequest.created_at < start_date,
                ServiceRequest.status == 'COMPLETED'
            )
        ).scalar() or 0
        
        previous_avg_response_time = previous_avg_response_time / 60
        
        # Calculer les tendances
        trends = {
            "requests": round(((current_requests - previous_requests) / previous_requests * 100) if previous_requests > 0 else 0, 1),
            "successRate": round(current_success_rate - previous_success_rate, 1),
            "responseTime": round(avg_response_time - previous_avg_response_time, 1)
        }
        
        response = {
            "totalRequests": current_requests,
            "successRate": round(current_success_rate, 1),
            "averageResponseTime": round(avg_response_time, 1),
            "satisfaction": round(satisfaction, 1),
            "trends": trends
        }
        
        logger.info(f"Dashboard stats retrieved for period {period}")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

@router.get("/activity")
async def get_dashboard_activity(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/dashboard/activity - Activité récente
    Supporter pagination (limit, offset)
    """
    try:
        # Récupérer les demandes récentes
        recent_requests = db.query(ServiceRequest).join(User).order_by(
            desc(ServiceRequest.created_at)
        ).offset(offset).limit(limit).all()
        
        requests_activity = []
        for req in recent_requests:
            client_name = "Client anonyme"
            if req.user:
                client_name = getattr(req.user, 'first_name', None) or getattr(req.user, 'whatsapp_id', 'Client anonyme')
            
            requests_activity.append({
                "id": str(req.id),
                "clientName": client_name,
                "serviceType": req.service_type,
                "status": req.status if isinstance(req.status, str) else req.status.value,
                "createdAt": req.created_at.isoformat(),
                "location": req.location,
                "description": req.description[:100] + "..." if len(req.description) > 100 else req.description,
                "urgency": req.urgency
            })
        
        # Alertes système récentes
        alerts = []
        
        # Vérifier les demandes urgentes non traitées
        urgent_requests = db.query(ServiceRequest).filter(
            and_(
                ServiceRequest.urgency.ilike('%urgent%'),
                ServiceRequest.status.in_(['PENDING', 'PROVIDER_NOTIFIED'])
            )
        ).count()
        
        if urgent_requests > 0:
            alerts.append({
                "type": "urgent_requests",
                "message": f"{urgent_requests} demandes urgentes nécessitent une attention immédiate",
                "severity": "error",
                "createdAt": datetime.utcnow().isoformat()
            })
        
        # Vérifier les demandes anciennes
        old_requests = db.query(ServiceRequest).filter(
            and_(
                ServiceRequest.created_at < datetime.utcnow() - timedelta(hours=24),
                ServiceRequest.status.in_(['PENDING', 'PROVIDER_NOTIFIED'])
            )
        ).count()
        
        if old_requests > 0:
            alerts.append({
                "type": "old_requests",
                "message": f"{old_requests} demandes de plus de 24h sans réponse",
                "severity": "warning",
                "createdAt": datetime.utcnow().isoformat()
            })
        
        # Notifications système
        notifications = []
        
        # Nouvelle demande dans les 30 dernières minutes
        recent_new_requests = db.query(ServiceRequest).filter(
            ServiceRequest.created_at >= datetime.utcnow() - timedelta(minutes=30)
        ).count()
        
        if recent_new_requests > 0:
            notifications.append({
                "type": "new_requests",
                "message": f"{recent_new_requests} nouvelle(s) demande(s) dans les 30 dernières minutes",
                "severity": "info",
                "createdAt": datetime.utcnow().isoformat()
            })
        
        # Prestataires récemment connectés
        active_providers = db.query(Provider).filter(
            Provider.availability_status == 'available'
        ).count()
        
        if active_providers > 0:
            notifications.append({
                "type": "active_providers",
                "message": f"{active_providers} prestataires actuellement disponibles",
                "severity": "info",
                "createdAt": datetime.utcnow().isoformat()
            })
        
        response = {
            "requests": requests_activity,
            "alerts": alerts,
            "notifications": notifications
        }
        
        logger.info(f"Dashboard activity retrieved: {len(requests_activity)} requests, {len(alerts)} alerts, {len(notifications)} notifications")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard activity: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'activité récente")

# Endpoint pour les métriques temps réel (optionnel)
@router.get("/metrics")
async def get_dashboard_metrics(
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/dashboard/metrics - Métriques temps réel
    Endpoint optionnel pour les métriques détaillées
    """
    try:
        # Métriques système
        total_users = db.query(User).count()
        total_providers = db.query(Provider).count()
        total_conversations = db.query(Conversation).count()
        
        # Métriques de performance
        today = datetime.utcnow().date()
        today_requests = db.query(ServiceRequest).filter(
            func.date(ServiceRequest.created_at) == today
        ).count()
        
        # Métriques par statut
        status_metrics = {}
        status_list = ['PENDING', 'PROVIDER_NOTIFIED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
        for status in status_list:
            count = db.query(ServiceRequest).filter(
                ServiceRequest.status == status
            ).count()
            status_metrics[status] = count
        
        # Métriques par service
        service_metrics = {}
        services_data = db.query(
            ServiceRequest.service_type,
            func.count(ServiceRequest.id).label('count')
        ).group_by(ServiceRequest.service_type).all()
        
        for row in services_data:
            service_metrics[row.service_type] = row.count
        
        response = {
            "system": {
                "totalUsers": total_users,
                "totalProviders": total_providers,
                "totalConversations": total_conversations,
                "todayRequests": today_requests
            },
            "byStatus": status_metrics,
            "byService": service_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("Dashboard metrics retrieved successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des métriques")

# Endpoint pour les graphiques détaillés (optionnel)
@router.get("/charts/{chart_type}")
async def get_dashboard_chart(
    chart_type: str,
    period: str = Query("7d", regex="^(24h|7d|30d)$"),
    current_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/dashboard/charts/{chart_type} - Données graphiques spécifiques
    Types: activity, services, providers, geographic
    """
    try:
        # Calculer la période
        if period == "24h":
            time_delta = timedelta(hours=24)
            date_format = '%H:00'
        elif period == "7d":
            time_delta = timedelta(days=7)
            date_format = '%d/%m'
        elif period == "30d":
            time_delta = timedelta(days=30)
            date_format = '%d/%m'
        else:
            time_delta = timedelta(days=7)
            date_format = '%d/%m'
        
        start_date = datetime.utcnow() - time_delta
        
        if chart_type == "activity":
            # Graphique d'activité
            data = db.query(
                func.date(ServiceRequest.created_at).label('date'),
                func.count(ServiceRequest.id).label('count')
            ).filter(
                ServiceRequest.created_at >= start_date
            ).group_by(
                func.date(ServiceRequest.created_at)
            ).order_by('date').all()
            
            labels = [row.date.strftime(date_format) for row in data]
            values = [row.count for row in data]
            
        elif chart_type == "services":
            # Graphique par services
            data = db.query(
                ServiceRequest.service_type,
                func.count(ServiceRequest.id).label('count')
            ).filter(
                ServiceRequest.created_at >= start_date
            ).group_by(
                ServiceRequest.service_type
            ).order_by(desc('count')).all()
            
            labels = [row.service_type for row in data]
            values = [row.count for row in data]
            
        elif chart_type == "providers":
            # Graphique par prestataires
            data = db.query(
                Provider.name,
                func.count(ServiceRequest.id).label('count')
            ).join(
                ServiceRequest, ServiceRequest.assigned_provider_id == Provider.id
            ).filter(
                ServiceRequest.created_at >= start_date
            ).group_by(
                Provider.name
            ).order_by(desc('count')).limit(10).all()
            
            labels = [row.name for row in data]
            values = [row.count for row in data]
            
        elif chart_type == "geographic":
            # Graphique par localisation
            data = db.query(
                ServiceRequest.location,
                func.count(ServiceRequest.id).label('count')
            ).filter(
                ServiceRequest.created_at >= start_date
            ).group_by(
                ServiceRequest.location
            ).order_by(desc('count')).limit(10).all()
            
            labels = [row.location for row in data]
            values = [row.count for row in data]
            
        else:
            raise HTTPException(status_code=400, detail="Type de graphique non supporté")
        
        response = {
            "type": chart_type,
            "period": period,
            "labels": labels,
            "values": values,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Chart data retrieved for type {chart_type}, period {period}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chart data: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des données graphiques")


@router.get("/requests")
async def get_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    service: str = Query(None),
    location: str = Query(None),
    dateFrom: str = Query(None),
    dateTo: str = Query(None),
    sortBy: str = Query("createdAt"),
    sortOrder: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    Get paginated list of service requests with filtering and sorting
    """
    try:
        logger.info(f"Fetching requests - Page {page}, Limit {limit}")
        
        # Build base query
        query = db.query(ServiceRequest).join(User)
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    ServiceRequest.description.ilike(f"%{search}%"),
                    ServiceRequest.location.ilike(f"%{search}%"),
                    ServiceRequest.service_type.ilike(f"%{search}%"),
                    User.phone_number.ilike(f"%{search}%")
                )
            )
        
        if status:
            status_upper = status.upper()
            if status_upper in ["PENDING", "PROVIDER_NOTIFIED", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"]:
                query = query.filter(ServiceRequest.status == status_upper)
        
        if priority:
            query = query.filter(ServiceRequest.urgency == priority.lower())
        
        if service:
            query = query.filter(ServiceRequest.service_type.ilike(f"%{service}%"))
        
        if location:
            query = query.filter(ServiceRequest.location.ilike(f"%{location}%"))
        
        if dateFrom:
            try:
                from_date = datetime.fromisoformat(dateFrom.replace('Z', '+00:00'))
                query = query.filter(ServiceRequest.created_at >= from_date)
            except ValueError:
                pass
        
        if dateTo:
            try:
                to_date = datetime.fromisoformat(dateTo.replace('Z', '+00:00'))
                query = query.filter(ServiceRequest.created_at <= to_date)
            except ValueError:
                pass
        
        # Apply sorting
        if sortBy == "createdAt":
            sort_column = ServiceRequest.created_at
        elif sortBy == "updatedAt":
            sort_column = ServiceRequest.updated_at
        elif sortBy == "status":
            sort_column = ServiceRequest.status
        elif sortBy == "service":
            sort_column = ServiceRequest.service_type
        elif sortBy == "location":
            sort_column = ServiceRequest.location
        else:
            sort_column = ServiceRequest.created_at
        
        if sortOrder == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        requests = query.offset(offset).limit(limit).all()
        
        # Calculate pagination metadata
        total_pages = (total + limit - 1) // limit
        has_next_page = page < total_pages
        has_prev_page = page > 1
        
        # Format requests data
        formatted_requests = []
        for req in requests:
            # Generate client data based on user info
            client_name = "Marie Kamga"
            if req.user:
                if req.user.name:
                    client_name = req.user.name
                elif req.user.whatsapp_id:
                    client_name = f"Client {req.user.whatsapp_id[-4:]}"
                else:
                    client_name = f"Client {req.user.id}"
            
            client_phone = req.user.phone_number if req.user and req.user.phone_number else "+237690123456"
            client_email = f"{client_name.lower().replace(' ', '.')}@email.com"
            
            # Map service types to French
            service_type_mapping = {
                "plomberie": "Plomberie",
                "electricite": "Électricité",
                "electrique": "Électricité",
                "reparation": "Réparation",
                "electromenager": "Réparation"
            }
            
            service_type_fr = service_type_mapping.get(req.service_type.lower(), req.service_type.title())
            
            # Determine service category
            if "plomb" in req.service_type.lower():
                category = "Réparation"
            elif "electr" in req.service_type.lower():
                category = "Électricité"
            else:
                category = "Réparation"
            
            # Map status to API format
            status_mapping = {
                "PENDING": "pending",
                "PROVIDER_NOTIFIED": "assigned",
                "ASSIGNED": "assigned",
                "IN_PROGRESS": "in_progress",
                "COMPLETED": "completed",
                "CANCELLED": "cancelled"
            }
            
            status_fr = status_mapping.get(req.status, "pending")
            
            # Determine priority based on urgency
            priority_mapping = {
                "urgent": "high",
                "normal": "medium",
                "flexible": "low"
            }
            
            priority = priority_mapping.get(req.urgency or "normal", "medium")
            
            # Generate estimated costs based on service type
            if service_type_fr == "Plomberie":
                estimated_cost = {"min": 15000, "max": 25000}
            elif service_type_fr == "Électricité":
                estimated_cost = {"min": 10000, "max": 20000}
            else:
                estimated_cost = {"min": 8000, "max": 18000}
            
            # Extract coordinates from location
            coordinates = {"lat": 4.0511, "lng": 9.7679}
            if "bonamoussadi" in req.location.lower():
                coordinates = {"lat": 4.0511, "lng": 9.7679}
            elif "douala" in req.location.lower():
                coordinates = {"lat": 4.0483, "lng": 9.7043}
            
            # Avatar selection
            avatar = f"/avatars/marie.jpg"
            
            formatted_request = {
                "id": f"req-{req.id}",
                "client": {
                    "name": client_name,
                    "phone": client_phone,
                    "email": client_email,
                    "avatar": avatar
                },
                "service": {
                    "type": service_type_fr,
                    "description": req.description,
                    "category": category
                },
                "location": {
                    "address": req.location,
                    "zone": "Bonamoussadi" if "bonamoussadi" in req.location.lower() else "Douala",
                    "coordinates": coordinates
                },
                "status": status_fr,
                "priority": priority,
                "createdAt": req.created_at.isoformat() + "Z",
                "updatedAt": (req.updated_at or req.created_at).isoformat() + "Z",
                "estimatedCost": {
                    "min": estimated_cost["min"],
                    "max": estimated_cost["max"],
                    "currency": "FCFA"
                }
            }
            
            formatted_requests.append(formatted_request)
        
        # Get status statistics
        status_stats = {
            "pending": db.query(ServiceRequest).filter(ServiceRequest.status == "PENDING").count(),
            "assigned": db.query(ServiceRequest).filter(ServiceRequest.status.in_(["PROVIDER_NOTIFIED", "ASSIGNED"])).count(),
            "completed": db.query(ServiceRequest).filter(ServiceRequest.status == "COMPLETED").count(),
            "cancelled": db.query(ServiceRequest).filter(ServiceRequest.status == "CANCELLED").count()
        }
        
        response = {
            "requests": formatted_requests,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasNextPage": has_next_page,
                "hasPrevPage": has_prev_page
            },
            "stats": status_stats
        }
        
        logger.info(f"Retrieved {len(formatted_requests)} requests (page {page}/{total_pages})")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des demandes")