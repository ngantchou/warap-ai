"""
Provider Fallback Service for Djobea AI
When notifications fail, provides users with a list of matching providers to contact directly
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.database_models import Provider, ServiceRequest


class ProviderFallbackService:
    """Service for handling provider notification failures with fallback options"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_provider_fallback_list(
        self, 
        service_request: ServiceRequest,
        max_providers: int = 3
    ) -> Dict[str, Any]:
        """
        Get top providers that match the service request criteria
        when notification system fails
        """
        try:
            logger.info(f"Generating provider fallback list for request {service_request.id}")
            
            # Get matching providers directly from database
            matching_providers = self._find_matching_providers(
                service_type=service_request.service_type,
                location=service_request.location,
                urgency=service_request.urgency
            )
            
            # Format providers for user-friendly display
            formatted_providers = []
            for provider in matching_providers[:max_providers]:
                formatted_provider = await self._format_provider_for_user(provider)
                formatted_providers.append(formatted_provider)
            
            return {
                "success": True,
                "providers": formatted_providers,
                "fallback_message": self._generate_fallback_message(
                    service_request, len(formatted_providers)
                ),
                "contact_instructions": self._generate_contact_instructions()
            }
            
        except Exception as e:
            logger.error(f"Error generating provider fallback list: {e}")
            return {
                "success": False,
                "providers": [],
                "fallback_message": self._generate_emergency_fallback_message(service_request),
                "contact_instructions": self._generate_contact_instructions()
            }
    
    async def _format_provider_for_user(self, provider: Provider) -> Dict[str, Any]:
        """Format provider information for user display"""
        
        # Get provider specializations if available
        specializations = []
        if hasattr(provider, 'specializations') and provider.specializations:
            specializations = [spec.name for spec in provider.specializations]
        
        # Calculate approximate response time
        response_time = "15-30 minutes"
        if provider.response_time_avg:
            if provider.response_time_avg <= 15:
                response_time = "10-15 minutes"
            elif provider.response_time_avg <= 30:
                response_time = "15-30 minutes"
            else:
                response_time = "30-45 minutes"
        
        return {
            "name": provider.name,
            "phone": provider.phone_number,
            "whatsapp": provider.whatsapp_id or provider.phone_number,
            "rating": round(provider.rating, 1),
            "trust_score": round(provider.rating, 1) if provider.rating else 0,
            "specializations": specializations,
            "years_experience": provider.years_experience,
            "location": provider.coverage_areas[0] if provider.coverage_areas else "Douala",
            "response_time": response_time,
            "verification_status": provider.verification_status,
            "is_available": provider.is_available,
            "bio": provider.bio[:100] + "..." if provider.bio and len(provider.bio) > 100 else provider.bio
        }
    
    def _generate_fallback_message(self, service_request: ServiceRequest, provider_count: int) -> str:
        """Generate fallback message when notifications fail"""
        
        service_type_fr = {
            "plomberie": "plomberie",
            "electricite": "électricité", 
            "electromenager": "électroménager"
        }.get(service_request.service_type, service_request.service_type)
        
        if provider_count == 0:
            return f"""
🚨 **Notification non disponible**

Nous n'avons pas pu contacter automatiquement les prestataires pour votre demande de {service_type_fr}.

Malheureusement, aucun prestataire n'est disponible dans votre zone pour le moment.

**Que faire maintenant ?**
• Essayez plus tard dans la journée
• Contactez notre service client au 237 691 924 172
• Élargissez votre zone de recherche si possible

Nous nous excusons pour ce désagrément.
"""
        
        return f"""
🚨 **Notification automatique non disponible**

Nous n'avons pas pu contacter automatiquement les prestataires pour votre demande de {service_type_fr}.

**Pas de problème !** Voici les **{provider_count} meilleurs prestataires** qui correspondent à vos critères :

👇 **Contactez-les directement vous-même**

*Vous pouvez les appeler ou leur envoyer un message WhatsApp avec les détails de votre problème.*
"""
    
    def _generate_emergency_fallback_message(self, service_request: ServiceRequest) -> str:
        """Generate emergency fallback message when everything fails"""
        
        return f"""
🚨 **Service temporairement indisponible**

Nous rencontrons actuellement des difficultés techniques pour traiter votre demande.

**Pour une assistance immédiate :**
• Appelez notre service client : 237 691 924 172
• Envoyez un WhatsApp à : 237 691 924 172
• Email : support@djobea.com

Nous nous excusons pour ce désagrément et travaillons à résoudre le problème rapidement.

**Votre demande :** {service_request.description}
**Localisation :** {service_request.location}
**ID de référence :** REQ-{service_request.id}
"""
    
    def _generate_contact_instructions(self) -> str:
        """Generate instructions for contacting providers directly"""
        
        return """
**💬 Comment contacter les prestataires :**

1. **Par téléphone** : Appelez directement le numéro indiqué
2. **Par WhatsApp** : Envoyez un message avec :
   - Votre nom
   - Le type de problème
   - Votre localisation exacte
   - L'urgence de la situation

**📝 Message type à envoyer :**
"Bonjour, j'ai un problème de [type de service] à [votre localisation]. Pouvez-vous intervenir aujourd'hui ? Merci."

**⭐ Vérifiez les évaluations** et choisissez le prestataire qui vous convient le mieux.
"""
    
    async def handle_notification_failure(
        self, 
        service_request: ServiceRequest,
        failure_reason: str = "notification_failed"
    ) -> str:
        """
        Handle notification failure and return formatted message with provider list
        """
        try:
            logger.info(f"Handling notification failure for request {service_request.id}: {failure_reason}")
            
            # Get fallback provider list
            fallback_data = await self.get_provider_fallback_list(service_request)
            
            if not fallback_data["success"] or not fallback_data["providers"]:
                return fallback_data["fallback_message"]
            
            # Format complete message with providers
            message = fallback_data["fallback_message"]
            
            # Add provider list
            for i, provider in enumerate(fallback_data["providers"], 1):
                trust_badge = "✅" if provider["verification_status"] == "verified" else "⚪"
                rating_stars = "⭐" * int(provider["rating"])
                
                provider_info = f"""
**{i}. {provider['name']}** {trust_badge}
📞 **Téléphone :** {provider['phone']}
📱 **WhatsApp :** {provider['whatsapp']}
⭐ **Note :** {provider['rating']}/5 {rating_stars}
📍 **Zone :** {provider['location']}
⏱️ **Temps de réponse :** {provider['response_time']}
💼 **Expérience :** {provider['years_experience']} ans
"""
                
                if provider['bio']:
                    provider_info += f"📝 **À propos :** {provider['bio']}\n"
                
                message += provider_info
            
            # Add contact instructions
            message += "\n" + fallback_data["contact_instructions"]
            
            # Update service request status
            service_request.status = "NOTIFICATION_FAILED"
            service_request.notes = f"Notification failed: {failure_reason}. Fallback list provided."
            self.db.commit()
            
            return message
            
        except Exception as e:
            logger.error(f"Error handling notification failure: {e}")
            return self._generate_emergency_fallback_message(service_request)
    
    async def log_notification_failure(
        self, 
        service_request: ServiceRequest,
        failure_type: str,
        error_details: str
    ):
        """Log notification failure for analytics and improvement"""
        
        logger.warning(f"Notification failure logged - Request: {service_request.id}, Type: {failure_type}, Details: {error_details}")
        
        # Could be stored in a notification_failures table for analytics
        try:
            # Example: store in database for analytics
            pass
        except Exception as e:
            logger.error(f"Failed to log notification failure: {e}")
    
    def _find_matching_providers(self, service_type: str, location: str, urgency: str = "normal") -> List[Provider]:
        """Find matching providers for fallback system"""
        try:
            from sqlalchemy import and_, or_, func
            
            # Query providers who:
            # 1. Offer the requested service
            # 2. Cover the requested area
            # 3. Are currently available and active
            providers = self.db.query(Provider).filter(
                and_(
                    Provider.is_available == True,
                    Provider.is_active == True,
                    func.json_array_length(Provider.services) > 0,  # Has services
                    or_(
                        func.json_array_length(Provider.coverage_areas) > 0,  # Has coverage areas
                        Provider.coverage_areas.is_(None)  # Accept null coverage (city-wide)
                    )
                )
            ).order_by(Provider.rating.desc(), Provider.total_jobs.asc()).limit(5).all()
            
            # Filter in Python for JSON array matching (more reliable)
            matching_providers = []
            for provider in providers:
                try:
                    # Check if provider offers the service
                    if provider.services and isinstance(provider.services, list):
                        if service_type in provider.services:
                            matching_providers.append(provider)
                            continue
                    
                    # Check coverage areas
                    if provider.coverage_areas and isinstance(provider.coverage_areas, list):
                        if any(area in provider.coverage_areas for area in [location, "Bonamoussadi", "Douala"]):
                            matching_providers.append(provider)
                            continue
                    
                    # If no coverage areas specified, assume city-wide
                    if not provider.coverage_areas:
                        matching_providers.append(provider)
                        
                except Exception as provider_error:
                    logger.warning(f"Error checking provider {provider.id}: {provider_error}")
                    continue
            
            logger.info(f"Found {len(matching_providers)} matching providers for {service_type} in {location}")
            return matching_providers[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Error finding matching providers: {e}")
            # Fallback: return any available providers
            try:
                fallback_providers = self.db.query(Provider).filter(
                    Provider.is_available == True,
                    Provider.is_active == True
                ).limit(2).all()
                logger.info(f"Fallback: returning {len(fallback_providers)} available providers")
                return fallback_providers
            except Exception as fallback_error:
                logger.error(f"Even fallback query failed: {fallback_error}")
                return []