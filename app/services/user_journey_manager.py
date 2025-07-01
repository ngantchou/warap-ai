"""
Sprint 4 - User Journey Manager
Complete user lifecycle management with status tracking, cancellation, and feedback
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime

from app.models.database_models import ServiceRequest, User, Provider, RequestStatus, Conversation
from app.services.request_service import RequestService
from app.services.whatsapp_service import WhatsAppService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserJourneyManager:
    """Manages complete user journey from request to completion"""
    
    def __init__(self, db: Session):
        self.db = db
        self.request_service = RequestService(db)
        self.whatsapp_service = WhatsAppService()
    
    def handle_status_request(self, user_id: int, whatsapp_id: str) -> str:
        """Handle user status inquiry: 'Quel est le statut de ma demande ?'"""
        try:
            # Get user's most recent request
            recent_request = (
                self.db.query(ServiceRequest)
                .filter(ServiceRequest.user_id == user_id)
                .order_by(desc(ServiceRequest.created_at))
                .first()
            )
            
            if not recent_request:
                response = (
                    "🔍 Aucune demande trouvée dans votre historique.\n"
                    "Vous pouvez faire une nouvelle demande en décrivant votre problème."
                )
                logger.info("status_request_no_history", extra={
                    "user_id": user_id,
                    "whatsapp_id": whatsapp_id
                })
                return response
            
            # Generate status response based on current status
            response = self._generate_status_response(recent_request)
            
            # Send response via WhatsApp
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.phone_number:
                self.whatsapp_service.send_message(user.phone_number, response)
            
            logger.info("status_request_handled", extra={
                "user_id": user_id,
                "request_id": recent_request.id,
                "status": recent_request.status,
                "whatsapp_id": whatsapp_id
            })
            
            return response
            
        except Exception as e:
            logger.error("status_request_error", extra={
                "user_id": user_id,
                "error": str(e),
                "whatsapp_id": whatsapp_id
            })
            return (
                "❌ Erreur lors de la vérification du statut.\n"
                "Veuillez réessayer dans quelques instants."
            )
    
    def handle_cancellation(self, user_id: int, request_id: Optional[int] = None, whatsapp_id: str = "") -> str:
        """Handle request cancellation before provider acceptance"""
        try:
            # Find request to cancel
            if request_id:
                request = (
                    self.db.query(ServiceRequest)
                    .filter(and_(
                        ServiceRequest.id == request_id,
                        ServiceRequest.user_id == user_id
                    ))
                    .first()
                )
            else:
                # Find most recent non-completed request
                request = (
                    self.db.query(ServiceRequest)
                    .filter(and_(
                        ServiceRequest.user_id == user_id,
                        ServiceRequest.status.in_([
                            RequestStatus.PENDING,
                            RequestStatus.PROVIDER_NOTIFIED
                        ])
                    ))
                    .order_by(desc(ServiceRequest.created_at))
                    .first()
                )
            
            if not request:
                response = (
                    "❌ Aucune demande en cours trouvée à annuler.\n"
                    "Seules les demandes en attente peuvent être annulées."
                )
                logger.warning("cancellation_no_request", extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "whatsapp_id": whatsapp_id
                })
                return response
            
            # Check if cancellation is allowed
            if request.status in [RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED]:
                response = (
                    f"❌ Impossible d'annuler cette demande.\n"
                    f"Statut actuel: {self._get_status_french(request.status)}\n"
                    "Contactez le prestataire directement si nécessaire."
                )
                logger.warning("cancellation_not_allowed", extra={
                    "user_id": user_id,
                    "request_id": request.id,
                    "status": request.status,
                    "whatsapp_id": whatsapp_id
                })
                return response
            
            # Cancel the request
            success = self.request_service.cancel_request(request.id, user_id)
            
            if success:
                response = (
                    f"✅ Demande #{request.id} annulée avec succès.\n"
                    f"Service: {request.service_type}\n"
                    f"Lieu: {request.location}\n\n"
                    "Vous pouvez faire une nouvelle demande quand vous voulez."
                )
                
                # Log cancellation for metrics
                logger.info("request_cancelled", extra={
                    "user_id": user_id,
                    "request_id": request.id,
                    "service_type": request.service_type,
                    "location": request.location,
                    "whatsapp_id": whatsapp_id
                })
                
                # Send notification to user
                user = self.db.query(User).filter(User.id == user_id).first()
                if user and user.phone_number:
                    self.whatsapp_service.send_message(user.phone_number, response)
                
            else:
                response = (
                    "❌ Erreur lors de l'annulation.\n"
                    "Veuillez réessayer ou contacter l'assistance."
                )
                logger.error("cancellation_failed", extra={
                    "user_id": user_id,
                    "request_id": request.id,
                    "whatsapp_id": whatsapp_id
                })
            
            return response
            
        except Exception as e:
            logger.error("cancellation_error", extra={
                "user_id": user_id,
                "request_id": request_id,
                "error": str(e),
                "whatsapp_id": whatsapp_id
            })
            return (
                "❌ Erreur lors de l'annulation.\n"
                "Veuillez réessayer dans quelques instants."
            )
    
    def handle_feedback(self, user_id: int, request_id: int, rating: int, comment: str = "", whatsapp_id: str = "") -> str:
        """Handle user feedback and rating system"""
        try:
            # Validate rating
            if not (1 <= rating <= 5):
                return (
                    "❌ Note invalide. Veuillez donner une note entre 1 et 5.\n"
                    "1 = Très mauvais, 5 = Excellent"
                )
            
            # Find completed request
            request = (
                self.db.query(ServiceRequest)
                .filter(and_(
                    ServiceRequest.id == request_id,
                    ServiceRequest.user_id == user_id,
                    ServiceRequest.status == RequestStatus.COMPLETED
                ))
                .first()
            )
            
            if not request:
                return (
                    "❌ Demande non trouvée ou non terminée.\n"
                    "Seules les demandes terminées peuvent être évaluées."
                )
            
            if not request.provider_id:
                return "❌ Aucun prestataire assigné à cette demande."
            
            # Update provider rating
            provider = self.db.query(Provider).filter(Provider.id == request.provider_id).first()
            if provider:
                # Calculate new average rating
                current_total = provider.rating * provider.total_jobs
                new_total = current_total + rating
                new_job_count = provider.total_jobs + 1
                new_rating = new_total / new_job_count
                
                # Update provider (this will be handled by database layer)
                # For now, log the feedback
                logger.info("feedback_received", extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "provider_id": request.provider_id,
                    "rating": rating,
                    "comment": comment,
                    "whatsapp_id": whatsapp_id
                })
                
                response = (
                    f"⭐ Merci pour votre évaluation!\n"
                    f"Note donnée: {rating}/5\n"
                    f"Prestataire: {provider.name}\n"
                )
                
                if comment:
                    response += f"Commentaire: {comment}\n"
                
                response += "\nVotre avis nous aide à améliorer nos services."
                
                # Send response to user
                user = self.db.query(User).filter(User.id == user_id).first()
                if user and user.phone_number:
                    self.whatsapp_service.send_message(user.phone_number, response)
                
                return response
            
            return "❌ Prestataire non trouvé."
            
        except Exception as e:
            logger.error("feedback_error", extra={
                "user_id": user_id,
                "request_id": request_id,
                "rating": rating,
                "error": str(e),
                "whatsapp_id": whatsapp_id
            })
            return (
                "❌ Erreur lors de l'enregistrement de votre évaluation.\n"
                "Veuillez réessayer dans quelques instants."
            )
    
    def _generate_status_response(self, request: ServiceRequest) -> str:
        """Generate user-friendly status response"""
        status_messages = {
            RequestStatus.PENDING: (
                f"⏳ Demande #{request.id} en attente\n"
                f"Service: {request.service_type}\n"
                f"Lieu: {request.location}\n"
                f"Créée le: {request.created_at.strftime('%d/%m/%Y à %H:%M')}\n\n"
                "🔍 Nous recherchons un prestataire disponible..."
            ),
            RequestStatus.PROVIDER_NOTIFIED: (
                f"📱 Demande #{request.id} - Prestataire contacté\n"
                f"Service: {request.service_type}\n"
                f"Lieu: {request.location}\n\n"
                "⏰ En attente de confirmation du prestataire..."
            ),
            RequestStatus.ASSIGNED: (
                f"✅ Demande #{request.id} assignée!\n"
                f"Service: {request.service_type}\n"
                f"Lieu: {request.location}\n"
                f"Acceptée le: {request.accepted_at.strftime('%d/%m/%Y à %H:%M') if request.accepted_at else 'N/A'}\n\n"
                "👨‍🔧 Un prestataire a accepté votre demande. Il vous contactera bientôt."
            ),
            RequestStatus.IN_PROGRESS: (
                f"🔧 Demande #{request.id} en cours\n"
                f"Service: {request.service_type}\n"
                f"Lieu: {request.location}\n\n"
                "⚡ Le prestataire travaille sur votre problème..."
            ),
            RequestStatus.COMPLETED: (
                f"🎉 Demande #{request.id} terminée!\n"
                f"Service: {request.service_type}\n"
                f"Lieu: {request.location}\n"
                f"Terminée le: {request.completed_at.strftime('%d/%m/%Y à %H:%M') if request.completed_at else 'N/A'}\n\n"
                "📝 N'hésitez pas à évaluer le service reçu."
            ),
            RequestStatus.CANCELLED: (
                f"❌ Demande #{request.id} annulée\n"
                f"Service: {request.service_type}\n"
                f"Lieu: {request.location}\n\n"
                "Vous pouvez faire une nouvelle demande quand vous voulez."
            )
        }
        
        return status_messages.get(request.status, f"❓ Statut inconnu pour la demande #{request.id}")
    
    def _get_status_french(self, status: RequestStatus) -> str:
        """Get French translation of status"""
        translations = {
            RequestStatus.PENDING: "En attente",
            RequestStatus.PROVIDER_NOTIFIED: "Prestataire notifié", 
            RequestStatus.ASSIGNED: "Assignée",
            RequestStatus.IN_PROGRESS: "En cours",
            RequestStatus.COMPLETED: "Terminée",
            RequestStatus.CANCELLED: "Annulée"
        }
        return translations.get(status, "Statut inconnu")
    
    def get_user_journey_stats(self, user_id: int) -> Dict:
        """Get user journey statistics"""
        try:
            requests = self.db.query(ServiceRequest).filter(ServiceRequest.user_id == user_id).all()
            
            stats = {
                "total_requests": len(requests),
                "completed_requests": len([r for r in requests if r.status == RequestStatus.COMPLETED]),
                "cancelled_requests": len([r for r in requests if r.status == RequestStatus.CANCELLED]),
                "pending_requests": len([r for r in requests if r.status in [
                    RequestStatus.PENDING, RequestStatus.PROVIDER_NOTIFIED, RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS
                ]]),
                "average_completion_time": None,
                "favorite_service": None
            }
            
            # Calculate completion rate
            if stats["total_requests"] > 0:
                stats["completion_rate"] = stats["completed_requests"] / stats["total_requests"]
            else:
                stats["completion_rate"] = 0.0
            
            # Find most requested service
            if requests:
                service_counts = {}
                for request in requests:
                    service = request.service_type
                    service_counts[service] = service_counts.get(service, 0) + 1
                stats["favorite_service"] = max(service_counts.items(), key=lambda x: x[1])[0]
            
            return stats
            
        except Exception as e:
            logger.error("user_stats_error", extra={
                "user_id": user_id,
                "error": str(e)
            })
            return {
                "total_requests": 0,
                "completed_requests": 0,
                "cancelled_requests": 0,
                "pending_requests": 0,
                "completion_rate": 0.0,
                "favorite_service": None
            }