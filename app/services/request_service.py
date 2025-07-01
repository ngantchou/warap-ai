from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models.database_models import ServiceRequest, User, Provider, RequestStatus, Conversation
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class RequestService:
    """Service for managing service requests"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_request(self, user_id: int, request_data: Dict) -> Optional[ServiceRequest]:
        """Create a new service request"""
        try:
            request = ServiceRequest(
                user_id=user_id,
                service_type=request_data["service_type"],
                description=request_data["description"],
                location=request_data["location"],
                preferred_time=request_data.get("preferred_time"),
                urgency=request_data.get("urgency", "normal"),
                status=RequestStatus.PENDING
            )
            
            self.db.add(request)
            self.db.commit()
            self.db.refresh(request)
            
            logger.info(f"Created new service request: {request.id} for user {user_id}")
            return request
            
        except Exception as e:
            logger.error(f"Error creating service request: {e}")
            self.db.rollback()
            return None
    
    def get_request_by_id(self, request_id: int) -> Optional[ServiceRequest]:
        """Get service request by ID"""
        try:
            return self.db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        except Exception as e:
            logger.error(f"Error getting request by ID: {e}")
            return None
    
    def get_user_requests(self, user_id: int, limit: int = 10) -> List[ServiceRequest]:
        """Get user's service requests"""
        try:
            return self.db.query(ServiceRequest).filter(
                ServiceRequest.user_id == user_id
            ).order_by(ServiceRequest.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting user requests: {e}")
            return []
    
    def get_pending_requests(self) -> List[ServiceRequest]:
        """Get all pending requests"""
        try:
            return self.db.query(ServiceRequest).filter(
                ServiceRequest.status == RequestStatus.PENDING
            ).order_by(ServiceRequest.created_at.asc()).all()
        except Exception as e:
            logger.error(f"Error getting pending requests: {e}")
            return []
    
    def update_request_status(self, request_id: int, status: RequestStatus, provider_id: int = None) -> bool:
        """Update request status"""
        try:
            request = self.db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
            if not request:
                return False
            
            request.status = status
            
            if provider_id:
                request.provider_id = provider_id
            
            if status == RequestStatus.ASSIGNED:
                request.accepted_at = func.now()
            elif status == RequestStatus.COMPLETED:
                request.completed_at = func.now()
            
            self.db.commit()
            logger.info(f"Updated request {request_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating request status: {e}")
            self.db.rollback()
            return False
    
    def cancel_request(self, request_id: int, user_id: int = None) -> bool:
        """Cancel a service request"""
        try:
            query = self.db.query(ServiceRequest).filter(ServiceRequest.id == request_id)
            
            if user_id:
                query = query.filter(ServiceRequest.user_id == user_id)
            
            request = query.first()
            
            if not request:
                return False
            
            # Only allow cancellation if not yet completed
            if request.status in [RequestStatus.COMPLETED]:
                return False
            
            request.status = RequestStatus.CANCELLED
            self.db.commit()
            
            logger.info(f"Cancelled request {request_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling request: {e}")
            self.db.rollback()
            return False
    
    def get_active_requests(self) -> List[ServiceRequest]:
        """Get all active requests (assigned or in progress)"""
        try:
            return self.db.query(ServiceRequest).filter(
                ServiceRequest.status.in_([RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS])
            ).order_by(ServiceRequest.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting active requests: {e}")
            return []
    
    def get_completed_requests(self, days: int = 7) -> List[ServiceRequest]:
        """Get completed requests within specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.status == RequestStatus.COMPLETED,
                    ServiceRequest.completed_at >= cutoff_date
                )
            ).order_by(ServiceRequest.completed_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting completed requests: {e}")
            return []
    
    def get_request_statistics(self) -> Dict:
        """Get request statistics"""
        try:
            total_requests = self.db.query(ServiceRequest).count()
            pending_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == RequestStatus.PENDING
            ).count()
            assigned_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == RequestStatus.ASSIGNED
            ).count()
            in_progress_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == RequestStatus.IN_PROGRESS
            ).count()
            completed_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == RequestStatus.COMPLETED
            ).count()
            cancelled_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.status == RequestStatus.CANCELLED
            ).count()
            
            # Calculate completion rate
            total_non_pending = total_requests - pending_requests
            completion_rate = completed_requests / total_non_pending if total_non_pending > 0 else 0
            
            return {
                "total_requests": total_requests,
                "pending_requests": pending_requests,
                "assigned_requests": assigned_requests,
                "in_progress_requests": in_progress_requests,
                "completed_requests": completed_requests,
                "cancelled_requests": cancelled_requests,
                "completion_rate": completion_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting request statistics: {e}")
            return {}
    
    def log_conversation(self, user_id: int, message_content: str, ai_response: str, 
                        extracted_data: Dict = None, request_id: int = None):
        """Log conversation for debugging and improvement"""
        try:
            conversation = Conversation(
                user_id=user_id,
                request_id=request_id,
                message_type="incoming",
                message_content=message_content,
                ai_response=ai_response,
                extracted_data=extracted_data
            )
            
            self.db.add(conversation)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging conversation: {e}")
            self.db.rollback()
    
    def get_user_or_create(self, whatsapp_id: str, name: str = None) -> User:
        """Get existing user or create new one"""
        try:
            user = self.db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
            
            if not user:
                user = User(
                    whatsapp_id=whatsapp_id,
                    name=name,
                    phone_number=whatsapp_id  # WhatsApp ID is usually the phone number
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"Created new user: {user.id} with WhatsApp ID: {whatsapp_id}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error getting or creating user: {e}")
            self.db.rollback()
            raise
    
    def find_incomplete_request_for_user(self, user_id: int) -> Optional[ServiceRequest]:
        """Find an incomplete request for a user to continue the conversation"""
        try:
            return self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.user_id == user_id,
                    ServiceRequest.status == RequestStatus.PENDING,
                    ServiceRequest.description == "",  # Incomplete request
                    ServiceRequest.created_at >= datetime.utcnow() - timedelta(hours=2)  # Within 2 hours
                )
            ).order_by(ServiceRequest.created_at.desc()).first()
        except Exception as e:
            logger.error(f"Error finding incomplete request: {e}")
            return None
