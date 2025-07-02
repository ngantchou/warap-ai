"""
Provider Profile Service for Djobea AI
Handles comprehensive provider profiles, trust-building features, and enhanced provider information management
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from loguru import logger

from app.models.database_models import (
    Provider, ProviderReview, ProviderPhoto, ProviderCertification, 
    ProviderSpecialization, ServiceRequest, RequestStatus
)
from app.config import get_settings

settings = get_settings()

class ProviderProfileService:
    """Enhanced provider profile management with trust-building features"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_provider_introduction(self, provider_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive provider introduction for customer notifications
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Dict containing formatted introduction message and provider details
        """
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                raise ValueError(f"Provider {provider_id} not found")
            
            # Get recent reviews
            recent_reviews = self.get_recent_reviews(provider_id, limit=3)
            
            # Calculate trust indicators
            trust_score = provider.trust_score
            verification_badges = self._get_verification_badges(provider)
            
            # Build introduction message
            intro_parts = []
            
            # Header with provider name and trust score
            intro_parts.append(f"👨‍🔧 *{provider.name}* vous a été assigné!")
            intro_parts.append(f"🏆 Score de confiance: {trust_score:.0f}/100")
            
            # Experience and specialties
            if provider.years_experience > 0:
                intro_parts.append(f"📅 {provider.years_experience} ans d'expérience")
            
            if provider.specialties:
                specialties_text = ", ".join(provider.specialties[:3])
                intro_parts.append(f"⚡ Spécialités: {specialties_text}")
            
            # Verification badges
            if verification_badges:
                badges_text = " ".join(verification_badges)
                intro_parts.append(f"✅ {badges_text}")
            
            # Rating and reviews
            if provider.rating > 0:
                rating_stars = "⭐" * int(provider.rating)
                intro_parts.append(f"{rating_stars} {provider.rating:.1f}/5 ({provider.total_jobs} services)")
            
            # Response time
            if provider.response_time_avg > 0:
                response_category = provider.response_time_category
                intro_parts.append(f"⚡ Réponse: {response_category}")
            
            # Recent testimonial
            if recent_reviews:
                top_review = recent_reviews[0]
                if top_review['comment'] and len(top_review['comment']) > 20:
                    comment_preview = top_review['comment'][:80] + "..." if len(top_review['comment']) > 80 else top_review['comment']
                    intro_parts.append(f"💬 \"{comment_preview}\" - Client récent")
            
            # Contact information
            intro_parts.append(f"📞 Contact: {provider.phone_number}")
            
            # Online status
            if provider.is_online:
                intro_parts.append("🟢 En ligne maintenant")
            
            message = "\n".join(intro_parts)
            
            return {
                "message": message,
                "provider_details": {
                    "id": provider.id,
                    "name": provider.name,
                    "rating": provider.rating,
                    "trust_score": trust_score,
                    "years_experience": provider.years_experience,
                    "specialties": provider.specialties,
                    "verification_badges": verification_badges,
                    "is_online": provider.is_online,
                    "response_time_category": provider.response_time_category,
                    "phone_number": provider.phone_number,
                    "recent_reviews": recent_reviews[:2]  # Top 2 reviews
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating provider introduction: {e}")
            # Fallback to basic introduction
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                return {
                    "message": f"👨‍🔧 *{provider.name}* vous a été assigné!\n📞 Contact: {provider.phone_number}",
                    "provider_details": {"id": provider.id, "name": provider.name}
                }
            return {
                "message": "👨‍🔧 Un prestataire qualifié vous a été assigné!",
                "provider_details": {}
            }
    
    def get_recent_reviews(self, provider_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent reviews for a provider"""
        try:
            reviews = (
                self.db.query(ProviderReview)
                .filter(ProviderReview.provider_id == provider_id)
                .filter(ProviderReview.is_verified == True)
                .order_by(desc(ProviderReview.created_at))
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "id": review.id,
                    "rating": review.rating,
                    "comment": review.comment,
                    "service_quality": review.service_quality,
                    "punctuality": review.punctuality,
                    "professionalism": review.professionalism,
                    "value_for_money": review.value_for_money,
                    "is_featured": review.is_featured,
                    "helpful_count": review.helpful_count,
                    "created_at": review.created_at.strftime("%d/%m/%Y") if review.created_at else None
                }
                for review in reviews
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent reviews: {e}")
            return []
    
    def get_provider_portfolio(self, provider_id: int) -> Dict[str, Any]:
        """Get provider's work portfolio and photos"""
        try:
            photos = (
                self.db.query(ProviderPhoto)
                .filter(ProviderPhoto.provider_id == provider_id)
                .filter(ProviderPhoto.is_active == True)
                .order_by(desc(ProviderPhoto.is_featured), ProviderPhoto.display_order)
                .all()
            )
            
            portfolio = {
                "profile_photos": [],
                "work_photos": [],
                "before_after": [],
                "certificates": []
            }
            
            for photo in photos:
                photo_data = {
                    "id": photo.id,
                    "url": photo.photo_url,
                    "title": photo.title,
                    "description": photo.description,
                    "service_type": photo.service_type,
                    "is_featured": photo.is_featured
                }
                
                if photo.photo_type == "profile":
                    portfolio["profile_photos"].append(photo_data)
                elif photo.photo_type in ["before", "after"]:
                    portfolio["before_after"].append(photo_data)
                elif photo.photo_type == "certificate":
                    portfolio["certificates"].append(photo_data)
                else:
                    portfolio["work_photos"].append(photo_data)
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error getting provider portfolio: {e}")
            return {"profile_photos": [], "work_photos": [], "before_after": [], "certificates": []}
    
    def get_provider_certifications(self, provider_id: int) -> List[Dict[str, Any]]:
        """Get provider's certifications and qualifications"""
        try:
            certifications = (
                self.db.query(ProviderCertification)
                .filter(ProviderCertification.provider_id == provider_id)
                .filter(ProviderCertification.is_active == True)
                .order_by(desc(ProviderCertification.is_verified), ProviderCertification.display_order)
                .all()
            )
            
            return [
                {
                    "id": cert.id,
                    "name": cert.name,
                    "issuing_authority": cert.issuing_authority,
                    "certificate_number": cert.certificate_number,
                    "issue_date": cert.issue_date.strftime("%d/%m/%Y") if cert.issue_date else None,
                    "expiry_date": cert.expiry_date.strftime("%d/%m/%Y") if cert.expiry_date else None,
                    "is_verified": cert.is_verified,
                    "verification_date": cert.verification_date.strftime("%d/%m/%Y") if cert.verification_date else None,
                    "certificate_url": cert.certificate_url
                }
                for cert in certifications
            ]
            
        except Exception as e:
            logger.error(f"Error getting provider certifications: {e}")
            return []
    
    def get_provider_specializations(self, provider_id: int) -> List[Dict[str, Any]]:
        """Get detailed provider specializations"""
        try:
            specializations = (
                self.db.query(ProviderSpecialization)
                .filter(ProviderSpecialization.provider_id == provider_id)
                .filter(ProviderSpecialization.is_available == True)
                .order_by(ProviderSpecialization.service_type, desc(ProviderSpecialization.years_experience))
                .all()
            )
            
            return [
                {
                    "id": spec.id,
                    "service_type": spec.service_type,
                    "specialization": spec.specialization,
                    "skill_level": spec.skill_level,
                    "years_experience": spec.years_experience,
                    "min_rate": spec.min_rate,
                    "max_rate": spec.max_rate,
                    "rate_type": spec.rate_type
                }
                for spec in specializations
            ]
            
        except Exception as e:
            logger.error(f"Error getting provider specializations: {e}")
            return []
    
    def calculate_provider_metrics(self, provider_id: int) -> Dict[str, Any]:
        """Calculate comprehensive provider performance metrics"""
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return {}
            
            # Get completed requests in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_requests = (
                self.db.query(ServiceRequest)
                .filter(ServiceRequest.provider_id == provider_id)
                .filter(ServiceRequest.created_at >= thirty_days_ago)
                .all()
            )
            
            # Calculate metrics
            total_recent = len(recent_requests)
            completed_recent = len([r for r in recent_requests if r.status == RequestStatus.COMPLETED])
            
            # Response time calculation (mock for now - would need actual response tracking)
            avg_response_time = provider.response_time_avg or 0
            
            # Calculate acceptance rate (mock for now)
            acceptance_rate = provider.acceptance_rate or 0
            
            # Completion rate
            completion_rate = (completed_recent / total_recent * 100) if total_recent > 0 else 0
            
            # Customer satisfaction from reviews
            reviews = self.get_recent_reviews(provider_id, limit=20)
            avg_satisfaction = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0
            
            return {
                "trust_score": provider.trust_score,
                "total_jobs": provider.total_jobs,
                "recent_jobs_30_days": total_recent,
                "completion_rate": completion_rate,
                "acceptance_rate": acceptance_rate,
                "avg_response_time_minutes": avg_response_time,
                "response_time_category": provider.response_time_category,
                "customer_satisfaction": avg_satisfaction,
                "verification_status": provider.verification_status,
                "years_experience": provider.years_experience,
                "is_online": provider.is_online,
                "last_active": provider.last_active.strftime("%d/%m/%Y %H:%M") if provider.last_active else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating provider metrics: {e}")
            return {}
    
    def generate_trust_explanation(self, provider_id: int, service_type: str) -> str:
        """Generate explanation of why this provider was chosen"""
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return "Ce prestataire a été sélectionné selon nos critères de qualité."
            
            reasons = []
            
            # Experience-based reasons
            if provider.years_experience >= 5:
                reasons.append(f"Expert avec {provider.years_experience} ans d'expérience")
            elif provider.years_experience >= 2:
                reasons.append(f"Expérimenté ({provider.years_experience} ans)")
            
            # Rating-based reasons
            if provider.rating >= 4.5:
                reasons.append("Excellentes évaluations clients")
            elif provider.rating >= 4.0:
                reasons.append("Très bien noté par les clients")
            
            # Verification reasons
            if provider.verification_status == "verified":
                reasons.append("Identité vérifiée")
            if provider.insurance_verified:
                reasons.append("Assurance validée")
            
            # Service-specific reasons
            specializations = self.get_provider_specializations(provider_id)
            service_specs = [s for s in specializations if s['service_type'] == service_type]
            if service_specs:
                expert_specs = [s for s in service_specs if s['skill_level'] == 'expert']
                if expert_specs:
                    reasons.append(f"Spécialiste expert en {service_type}")
                else:
                    reasons.append(f"Spécialisé en {service_type}")
            
            # Response time reasons
            if provider.response_time_avg <= 10:
                reasons.append("Réponse très rapide")
            
            # Proximity reason (would need actual location matching)
            reasons.append("Proche de votre localisation")
            
            if reasons:
                reason_text = ", ".join(reasons[:3])  # Top 3 reasons
                return f"✅ *Pourquoi {provider.name}?*\n{reason_text}"
            else:
                return f"✅ {provider.name} répond à nos critères de sélection qualité"
                
        except Exception as e:
            logger.error(f"Error generating trust explanation: {e}")
            return "Ce prestataire a été sélectionné selon nos critères de qualité."
    
    def _get_verification_badges(self, provider: Provider) -> List[str]:
        """Get verification badges for provider"""
        badges = []
        
        if provider.verification_status == "verified":
            badges.append("✅ Vérifié")
        if provider.id_verified:
            badges.append("🆔 ID Confirmé")
        if provider.insurance_verified:
            badges.append("🛡️ Assuré")
        
        return badges
    
    def update_provider_activity(self, provider_id: int) -> None:
        """Update provider's last activity timestamp"""
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                provider.last_active = datetime.utcnow()
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error updating provider activity: {e}")
            self.db.rollback()
    
    def get_provider_showcase_data(self, provider_id: int) -> Dict[str, Any]:
        """Get complete provider showcase data for admin interface"""
        try:
            provider = self.db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return {}
            
            return {
                "basic_info": {
                    "id": provider.id,
                    "name": provider.name,
                    "phone_number": provider.phone_number,
                    "profile_photo_url": provider.profile_photo_url,
                    "bio": provider.bio,
                    "years_experience": provider.years_experience,
                    "services": provider.services,
                    "coverage_areas": provider.coverage_areas
                },
                "metrics": self.calculate_provider_metrics(provider_id),
                "reviews": self.get_recent_reviews(provider_id, limit=10),
                "portfolio": self.get_provider_portfolio(provider_id),
                "certifications": self.get_provider_certifications(provider_id),
                "specializations": self.get_provider_specializations(provider_id),
                "trust_indicators": {
                    "trust_score": provider.trust_score,
                    "verification_status": provider.verification_status,
                    "verification_badges": self._get_verification_badges(provider),
                    "response_time_category": provider.response_time_category,
                    "is_online": provider.is_online
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting provider showcase data: {e}")
            return {}

# Global instance
provider_profile_service = None

def get_provider_profile_service(db: Session) -> ProviderProfileService:
    """Get or create provider profile service instance"""
    return ProviderProfileService(db)