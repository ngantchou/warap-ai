from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.database_models import Provider, ServiceRequest, RequestStatus
from app.utils.logger import setup_logger
from app.services.communication_service import CommunicationService

logger = setup_logger(__name__)

class ProviderService:
    """Service for managing service providers"""
    
    def __init__(self, db: Session):
        self.db = db
        self.communication_service = CommunicationService()
    
    def find_available_providers(self, service_type: str, location: str) -> List[Provider]:
        """Find available providers for a specific service and location"""
        try:
            from sqlalchemy import and_, or_, func
            
            # Query providers who are available and active
            providers = self.db.query(Provider).filter(
                and_(
                    Provider.is_available == True,
                    Provider.is_active == True
                )
            ).order_by(Provider.rating.desc(), Provider.total_jobs.asc()).all()
            
            # Filter in Python for JSON array matching (more reliable)
            matching_providers = []
            for provider in providers:
                try:
                    # Check if provider offers the service
                    if provider.services and isinstance(provider.services, list):
                        if service_type in provider.services:
                            # Check coverage areas
                            if provider.coverage_areas and isinstance(provider.coverage_areas, list):
                                if any(area in provider.coverage_areas for area in [location, "Bonamoussadi", "Douala"]):
                                    matching_providers.append(provider)
                                    continue
                            
                            # If no coverage areas specified, assume city-wide
                            if not provider.coverage_areas:
                                matching_providers.append(provider)
                                continue
                        
                except Exception as provider_error:
                    logger.warning(f"Error checking provider {provider.id}: {provider_error}")
                    continue
            
            logger.info(f"Found {len(matching_providers)} available providers for {service_type} in {location}")
            return matching_providers
            
        except Exception as e:
            logger.error(f"Error finding available providers: {e}")
            return []
    
    async def find_matching_providers(self, service_type: str, location: str, urgency: str = "normal") -> List[Provider]:
        """Find matching providers for fallback system (alias for find_available_providers)"""
        return self.find_available_providers(service_type, location)
    
    def get_provider_by_whatsapp_id(self, whatsapp_id: str) -> Optional[Provider]:
        """Get provider by WhatsApp ID"""
        try:
            provider = self.db.query(Provider).filter(
                Provider.whatsapp_id == whatsapp_id
            ).first()
            
            return provider
            
        except Exception as e:
            logger.error(f"Error getting provider by WhatsApp ID: {e}")
            return None
    
    def update_provider_availability(self, provider_id: int, is_available: bool) -> bool:
        """Update provider availability status"""
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                provider.is_available = is_available
                self.db.commit()
                logger.info(f"Updated provider {provider_id} availability to {is_available}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating provider availability: {e}")
            self.db.rollback()
            return False
    
    def accept_request(self, provider_whatsapp_id: str, request_id: int) -> bool:
        """Mark a request as accepted by a provider"""
        try:
            # Get the provider
            provider = self.get_provider_by_whatsapp_id(provider_whatsapp_id)
            if not provider:
                logger.error(f"Provider not found with WhatsApp ID: {provider_whatsapp_id}")
                return False
            
            # Get the request
            request = self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.id == request_id,
                    ServiceRequest.status == RequestStatus.PENDING
                )
            ).first()
            
            if not request:
                logger.error(f"Request not found or already assigned: {request_id}")
                return False
            
            # Assign the request to the provider
            request.provider_id = provider.id
            request.status = RequestStatus.ASSIGNED
            request.accepted_at = func.now()
            
            # Update provider stats
            provider.total_jobs += 1
            
            self.db.commit()
            logger.info(f"Request {request_id} accepted by provider {provider.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error accepting request: {e}")
            self.db.rollback()
            return False
    
    def reject_request(self, provider_whatsapp_id: str, request_id: int) -> bool:
        """Handle request rejection by provider"""
        try:
            provider = self.get_provider_by_whatsapp_id(provider_whatsapp_id)
            if not provider:
                return False
            
            # Log the rejection (could be used for future matching improvements)
            logger.info(f"Provider {provider.id} rejected request {request_id}")
            
            # The request remains in PENDING status for other providers
            return True
            
        except Exception as e:
            logger.error(f"Error handling request rejection: {e}")
            return False
    
    def get_provider_stats(self, provider_id: int) -> Dict:
        """Get provider statistics"""
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return {}
            
            # Count requests by status
            total_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider_id
            ).count()
            
            completed_requests = self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.provider_id == provider_id,
                    ServiceRequest.status == RequestStatus.COMPLETED
                )
            ).count()
            
            pending_requests = self.db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.provider_id == provider_id,
                    ServiceRequest.status.in_([RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS])
                )
            ).count()
            
            return {
                "total_requests": total_requests,
                "completed_requests": completed_requests,
                "pending_requests": pending_requests,
                "rating": provider.rating,
                "completion_rate": completed_requests / total_requests if total_requests > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting provider stats: {e}")
            return {}
    
    def add_provider(self, provider_data: Dict) -> Optional[Provider]:
        """Add a new service provider"""
        try:
            provider = Provider(
                name=provider_data["name"],
                whatsapp_id=provider_data["whatsapp_id"],
                phone_number=provider_data["phone_number"],
                services=provider_data["services"],
                coverage_areas=provider_data.get("coverage_areas", ["Bonamoussadi"]),
                is_available=provider_data.get("is_available", True),
                is_active=provider_data.get("is_active", True)
            )
            
            self.db.add(provider)
            self.db.commit()
            self.db.refresh(provider)
            
            logger.info(f"Added new provider: {provider.name} (ID: {provider.id})")
            return provider
            
        except Exception as e:
            logger.error(f"Error adding provider: {e}")
            self.db.rollback()
            return None
    
    def get_all_providers(self) -> List[Provider]:
        """Get all providers"""
        try:
            return self.db.query(Provider).all()
        except Exception as e:
            logger.error(f"Error getting all providers: {e}")
            return []
    
    def deactivate_provider(self, provider_id: int) -> bool:
        """Deactivate a provider"""
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                provider.is_active = False
                provider.is_available = False
                self.db.commit()
                logger.info(f"Deactivated provider {provider_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deactivating provider: {e}")
            self.db.rollback()
            return False
    
    async def notify_providers_with_fallback(self, request: ServiceRequest, providers: List[Provider]) -> bool:
        """Notify providers and handle failures with fallback provider list"""
        try:
            from app.services.whatsapp_service import WhatsAppService
            
            whatsapp_service = WhatsAppService()
            failed_providers = []
            successful_notifications = 0
            
            for provider in providers:
                try:
                    # Create notification message
                    message = f"""
🔔 **Nouvelle demande de service**

📋 **Service :** {request.service_type}
📍 **Localisation :** {request.location}
💰 **Budget estimé :** {request.estimated_price or 'À négocier'}
⏰ **Urgence :** {request.urgency}

📝 **Description :**
{request.description}

✅ **Répondez "OUI" pour accepter cette demande**
❌ **Répondez "NON" pour refuser**

**Référence :** REQ-{request.id}
"""
                    
                    # Try to send notification
                    success = whatsapp_service.send_message(provider.whatsapp_id, message)
                    
                    if success:
                        successful_notifications += 1
                        logger.info(f"Notification sent to provider {provider.id} ({provider.name})")
                    else:
                        failed_providers.append(provider)
                        logger.warning(f"Failed to notify provider {provider.id} ({provider.name})")
                        
                except Exception as e:
                    failed_providers.append(provider)
                    logger.error(f"Error notifying provider {provider.id}: {e}")
            
            # If all notifications failed, trigger fallback
            if successful_notifications == 0:
                logger.warning(f"All provider notifications failed for request {request.id}")
                
                # Use communication service to send fallback message
                fallback_success = await self.communication_service.handle_provider_notification_failure(
                    request, failed_providers, self.db
                )
                
                if fallback_success:
                    logger.info(f"Provider fallback message sent for request {request.id}")
                    return True
                else:
                    # Complete system failure
                    logger.error(f"Complete notification failure for request {request.id}")
                    await self.communication_service.handle_complete_system_failure(request, self.db)
                    return False
            
            # If some notifications succeeded, log partial failures
            if failed_providers:
                logger.warning(f"Partial notification failure for request {request.id}: {len(failed_providers)} providers failed")
                
                # Log failed providers for analytics
                for provider in failed_providers:
                    logger.warning(f"Failed to notify provider {provider.id} ({provider.name})")
            
            return successful_notifications > 0
            
        except Exception as e:
            logger.error(f"Error in notify_providers_with_fallback: {e}")
            
            # Emergency fallback
            try:
                await self.communication_service.handle_complete_system_failure(request, self.db)
            except Exception as fallback_error:
                logger.critical(f"Emergency fallback also failed: {fallback_error}")
            
            return False
