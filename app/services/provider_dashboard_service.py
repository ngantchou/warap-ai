"""
Provider Dashboard Service for Djobea AI
Comprehensive service for provider authentication, dashboard data, and performance analytics
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from loguru import logger

from app.models.database_models import Provider, ServiceRequest, User, ProviderReview, ProviderPhoto, ProviderCertification, ProviderSpecialization
from app.models.provider_models import (
    ProviderSession, ProviderSettings, ProviderStatsCache, 
    ProviderNotification, ProviderAvailability, ProviderDashboardWidget
)
from app.services.whatsapp_service import WhatsAppService
from app.config import get_settings

settings = get_settings()

class ProviderAuthService:
    """Handle provider authentication and session management"""
    
    def __init__(self):
        self.whatsapp_service = WhatsAppService()
    
    async def send_otp(self, db: Session, phone_number: str) -> Dict[str, Any]:
        """
        Send OTP to provider's WhatsApp for authentication
        
        Args:
            db: Database session
            phone_number: Provider's phone number
            
        Returns:
            Response with success status and session info
        """
        try:
            # Verify provider exists
            provider = db.query(Provider).filter(
                Provider.phone_number == phone_number
            ).first()
            
            if not provider:
                return {
                    "success": False,
                    "error": "Provider not found",
                    "code": "PROVIDER_NOT_FOUND"
                }
            
            # Generate 6-digit OTP
            otp_code = secrets.randbelow(900000) + 100000
            
            # Store OTP in session (temporary)
            session_token = secrets.token_urlsafe(32)
            
            # For now, store session info in a class variable to avoid database issues
            # In production, use Redis or fix the database relationship issues
            logger.info(f"Creating temporary session for provider {provider.id}")
            
            # Store temporary session data
            if not hasattr(self, '_temp_sessions'):
                self._temp_sessions = {}
            
            self._temp_sessions[session_token] = {
                'provider_id': provider.id,
                'otp_code': str(otp_code),
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(minutes=5)
            }
            
            # For demo: Log OTP instead of sending via WhatsApp
            message = f"""🔐 *Code de connexion Djobea Pro*

Votre code de vérification : *{otp_code}*

⏱️ Ce code expire dans 5 minutes
🔒 Ne partagez jamais ce code

Équipe Djobea AI"""
            
            logger.info(f"DEMO OTP for phone {phone_number}: {otp_code}")
            # Comment out WhatsApp sending for demo
            # await self.whatsapp_service.send_message(phone_number, message)
            
            # Store OTP hash for verification (in real implementation, use Redis)
            otp_hash = hashlib.sha256(f"{otp_code}_{session_token}".encode()).hexdigest()
            
            logger.info(f"OTP sent to provider {provider.id}, phone {phone_number}, code {otp_code}")
            
            return {
                "success": True,
                "session_token": session_token,
                "otp_hash": otp_hash,  # For verification
                "expires_in": 300  # 5 minutes
            }
            
        except Exception as e:
            logger.error(f"Error sending OTP to provider {phone_number}: {e}")
            return {
                "success": False,
                "error": "Failed to send OTP",
                "code": "OTP_SEND_FAILED"
            }
    
    async def verify_otp(self, db: Session, session_token: str, otp_code: str, otp_hash: str) -> Dict[str, Any]:
        """
        Verify OTP and create authenticated session
        
        Args:
            db: Database session
            session_token: Temporary session token
            otp_code: User-provided OTP
            otp_hash: Expected OTP hash for verification
            
        Returns:
            Response with authentication token or error
        """
        try:
            # Check temporary session from memory
            if not hasattr(self, '_temp_sessions') or session_token not in self._temp_sessions:
                return {
                    "success": False,
                    "error": "Invalid or expired session",
                    "code": "SESSION_INVALID"
                }
            
            session_data = self._temp_sessions[session_token]
            
            # Check if session has expired
            if datetime.utcnow() > session_data['expires_at']:
                del self._temp_sessions[session_token]
                return {
                    "success": False,
                    "error": "Session expired",
                    "code": "SESSION_EXPIRED"
                }
            
            # Verify OTP
            if otp_code != session_data['otp_code']:
                return {
                    "success": False,
                    "error": "Invalid OTP code",
                    "code": "OTP_INVALID"
                }
            
            # Create authenticated session
            auth_token = secrets.token_urlsafe(64)
            provider_id = session_data['provider_id']
            
            # Get provider info
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return {
                    "success": False,
                    "error": "Provider not found",
                    "code": "PROVIDER_NOT_FOUND"
                }
            
            # Create provider session record in database using raw SQL to avoid metadata issues
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)  # 30 days from now
            now = datetime.now(timezone.utc)
            try:
                # Use raw SQL insert to bypass any SQLAlchemy metadata issues
                from sqlalchemy import text
                sql = text("""
                    INSERT INTO provider_sessions (provider_id, session_token, expires_at, created_at, last_activity)
                    VALUES (:provider_id, :session_token, :expires_at, :created_at, :last_activity)
                """)
                db.execute(sql, {
                    'provider_id': provider.id,
                    'session_token': auth_token,
                    'expires_at': expires_at,
                    'created_at': now,
                    'last_activity': now
                })
                db.commit()
                logger.info(f"Successfully created provider session for provider {provider.id}")
            except Exception as session_error:
                logger.error(f"Failed to create provider session: {session_error}")
                db.rollback()
                return {
                    "success": False,
                    "error": "Failed to create authentication session",
                    "code": "SESSION_CREATION_FAILED"
                }
            
            # Clean up temporary session
            del self._temp_sessions[session_token]
            
            logger.info(f"Provider {provider.id} successfully authenticated")
            
            return {
                "success": True,
                "auth_token": auth_token,
                "provider_id": provider.id,
                "provider_name": provider.name,
                "expires_in": 30 * 24 * 60 * 60  # 30 days in seconds
            }
            
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return {
                "success": False,
                "error": "OTP verification failed",
                "code": "OTP_VERIFICATION_FAILED"
            }
    
    def verify_session(self, db: Session, auth_token: str) -> Optional[Provider]:
        """
        Verify provider session and return provider if valid
        
        Args:
            db: Database session
            auth_token: Authentication token
            
        Returns:
            Provider object if session is valid, None otherwise
        """
        try:
            session = db.query(ProviderSession).filter(
                ProviderSession.session_token == auth_token
            ).first()
            
            if not session or not session.is_valid:
                return None
            
            # Update last activity using raw SQL to avoid ORM issues
            from sqlalchemy import text
            sql = text("UPDATE provider_sessions SET last_activity = :now WHERE session_token = :token")
            db.execute(sql, {
                'now': datetime.now(timezone.utc),
                'token': auth_token
            })
            db.commit()
            
            # Get the provider using provider_id from session
            provider = db.query(Provider).filter(
                Provider.id == session.provider_id
            ).first()
            
            return provider
            
        except Exception as e:
            logger.error(f"Error verifying session: {e}")
            return None
    
    def logout(self, db: Session, auth_token: str) -> bool:
        """
        Logout provider and invalidate session
        
        Args:
            db: Database session
            auth_token: Authentication token to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = db.query(ProviderSession).filter(
                ProviderSession.session_token == auth_token
            ).first()
            
            if session:
                db.delete(session)
                db.commit()
                logger.info(f"Provider {session.provider_id} logged out")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False

class ProviderDashboardService:
    """Handle provider dashboard data and analytics"""
    
    def __init__(self):
        self.auth_service = ProviderAuthService()
    
    def get_dashboard_stats(self, db: Session, provider: Provider) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics for provider
        
        Args:
            db: Database session
            provider: Provider object
            
        Returns:
            Dashboard statistics and metrics
        """
        try:
            # Refresh provider object to ensure we have current data
            db.refresh(provider)
            
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            provider_id = provider.id
            
            # Today's requests
            today_requests = db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.provider_id == provider_id,
                    func.date(ServiceRequest.created_at) == today
                )
            ).all()
            
            # Week's requests
            week_requests = db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.provider_id == provider_id,
                    func.date(ServiceRequest.created_at) >= week_start
                )
            ).all()
            
            # Month's requests
            month_requests = db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.provider_id == provider_id,
                    func.date(ServiceRequest.created_at) >= month_start
                )
            ).all()
            
            # Calculate metrics
            today_stats = self._calculate_request_stats(today_requests)
            week_stats = self._calculate_request_stats(week_requests)
            month_stats = self._calculate_request_stats(month_requests)
            
            # Earnings calculation (15% commission)
            commission_rate = 0.15
            week_earnings = sum(float(r.final_price or 0) for r in week_requests if r.status == 'COMPLETED')
            week_net_earnings = week_earnings * (1 - commission_rate)
            
            # Notifications count
            unread_notifications = db.query(ProviderNotification).filter(
                and_(
                    ProviderNotification.provider_id == provider_id,
                    ProviderNotification.is_read == False
                )
            ).count()
            
            # Get provider attributes safely
            provider_rating = getattr(provider, 'rating', 0.0) or 0.0
            provider_total_jobs = getattr(provider, 'total_jobs', 0) or 0
            provider_trust_score = getattr(provider, 'trust_score', 0.0) or 0.0
            
            return {
                "success": True,
                "stats": {
                    "provider": {
                        "id": provider.id,
                        "name": getattr(provider, 'name', 'Prestataire'),
                        "service_type": getattr(provider, 'service_type', 'Service général'),
                        "location": getattr(provider, 'location', 'Douala'),
                        "verification_status": getattr(provider, 'verification_status', 'unverified'),
                        "phone": getattr(provider, 'phone', ''),
                        "rating": float(provider_rating),
                        "trust_score": float(provider_trust_score)
                    },
                    "today": {
                        "new_requests": today_stats["new"],
                        "in_progress": today_stats["in_progress"],
                        "completed": today_stats["completed"]
                    },
                    "week": {
                        "total_requests": len(week_requests),
                        "completed_requests": week_stats["completed"],
                        "acceptance_rate": week_stats["acceptance_rate"],
                        "gross_earnings": week_earnings,
                        "net_earnings": week_net_earnings,
                        "commission_paid": week_earnings * commission_rate
                    },
                    "performance": {
                        "average_rating": float(provider_rating),
                        "total_jobs": int(provider_total_jobs),
                        "response_time_avg": self._calculate_avg_response_time(db, provider),
                        "trust_score": float(provider_trust_score)
                    },
                    "notifications": {
                        "unread_count": unread_notifications,
                        "urgent_count": db.query(ProviderNotification).filter(
                            and_(
                                ProviderNotification.provider_id == provider_id,
                                ProviderNotification.is_read == False,
                                ProviderNotification.is_urgent == True
                            )
                        ).count()
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats for provider {provider.id}: {e}")
            return {
                "success": False,
                "error": "Failed to load dashboard stats"
            }
    
    def get_requests_list(
        self, 
        db: Session, 
        provider: Provider, 
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get paginated list of requests for provider
        
        Args:
            db: Database session
            provider: Provider object
            status: Filter by status (optional)
            limit: Number of results per page
            offset: Offset for pagination
            
        Returns:
            List of requests with pagination info
        """
        try:
            query = db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider.id
            )
            
            if status:
                query = query.filter(ServiceRequest.status == status.upper())
            
            # Get total count
            total_count = query.count()
            
            # Get paginated results
            requests = query.order_by(desc(ServiceRequest.created_at)).limit(limit).offset(offset).all()
            
            # Format requests with user info
            formatted_requests = []
            for request in requests:
                user = db.query(User).filter(User.id == request.user_id).first()
                
                formatted_requests.append({
                    "id": request.id,
                    "service_type": request.service_type,
                    "location": request.location,
                    "description": request.description,
                    "urgency": request.urgency,
                    "status": request.status,
                    "created_at": request.created_at.isoformat(),
                    "user": {
                        "name": user.name if user else "Unknown",
                        "phone": user.phone_number if user else "",
                        "rating": getattr(user, 'rating', 0)
                    },
                    "estimated_price": self._get_estimated_price(request.service_type),
                    "time_ago": self._format_time_ago(request.created_at)
                })
            
            return {
                "success": True,
                "requests": formatted_requests,
                "pagination": {
                    "total": total_count,
                    "page": (offset // limit) + 1,
                    "per_page": limit,
                    "pages": (total_count + limit - 1) // limit
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting requests list for provider {provider.id}: {e}")
            return {
                "success": False,
                "error": "Failed to load requests"
            }
    
    def get_chart_data(self, db: Session, provider: Provider, period: str = "week") -> Dict[str, Any]:
        """
        Get chart data for provider dashboard
        
        Args:
            db: Database session
            provider: Provider object
            period: Data period (week, month, year)
            
        Returns:
            Chart data for visualizations
        """
        try:
            today = date.today()
            
            if period == "week":
                start_date = today - timedelta(days=6)  # Last 7 days
                date_format = "%a"  # Mon, Tue, Wed
            elif period == "month":
                start_date = today - timedelta(days=29)  # Last 30 days
                date_format = "%d/%m"  # 01/01, 02/01
            else:  # year
                start_date = today - timedelta(days=364)  # Last 365 days
                date_format = "%b"  # Jan, Feb, Mar
            
            # Revenue chart data
            revenue_data = []
            current_date = start_date
            
            while current_date <= today:
                daily_requests = db.query(ServiceRequest).filter(
                    and_(
                        ServiceRequest.provider_id == provider.id,
                        func.date(ServiceRequest.created_at) == current_date,
                        ServiceRequest.status == 'COMPLETED'
                    )
                ).all()
                
                daily_revenue = sum(r.final_price or 0 for r in daily_requests)
                daily_net = daily_revenue * 0.85  # After 15% commission
                
                revenue_data.append({
                    "date": current_date.strftime(date_format),
                    "gross": float(daily_revenue),
                    "net": float(daily_net),
                    "requests": len(daily_requests)
                })
                
                current_date += timedelta(days=1)
            
            # Service type breakdown
            service_requests = db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.provider_id == provider.id,
                    func.date(ServiceRequest.created_at) >= start_date
                )
            ).all()
            
            service_breakdown = {}
            for request in service_requests:
                service = request.service_type
                if service not in service_breakdown:
                    service_breakdown[service] = 0
                service_breakdown[service] += 1
            
            # Activity heatmap (hours of day vs days of week)
            activity_data = []
            for hour in range(24):
                for day in range(7):
                    count = db.query(ServiceRequest).filter(
                        and_(
                            ServiceRequest.provider_id == provider.id,
                            func.extract('hour', ServiceRequest.created_at) == hour,
                            func.extract('dow', ServiceRequest.created_at) == day,
                            func.date(ServiceRequest.created_at) >= start_date
                        )
                    ).count()
                    
                    activity_data.append({
                        "hour": hour,
                        "day": day,
                        "count": count
                    })
            
            # Transform revenue data for API format (List of dictionaries)
            revenue_chart_data = []
            for item in revenue_data:
                revenue_chart_data.append({
                    "date": item["date"],
                    "net": item["net"],
                    "gross": item["gross"],
                    "requests": item["requests"]
                })
            
            # Transform service breakdown for API format (Dict[str, str])
            service_breakdown_data = {}
            if service_breakdown:
                for service, count in service_breakdown.items():
                    service_breakdown_data[service] = str(count)
            else:
                service_breakdown_data["Aucun service"] = "0"

            return {
                "success": True,
                "revenue_chart": revenue_chart_data,
                "service_breakdown": service_breakdown_data,
                "activity_heatmap": activity_data,
                "period": period,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": today.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting chart data for provider {provider.id}: {e}")
            return {
                "success": False,
                "error": "Failed to load chart data"
            }
    
    def _calculate_request_stats(self, requests: List[ServiceRequest]) -> Dict[str, Any]:
        """Calculate statistics for a list of requests"""
        total = len(requests)
        new = len([r for r in requests if r.status in ['PENDING', 'PROVIDER_NOTIFIED']])
        in_progress = len([r for r in requests if r.status in ['ASSIGNED', 'IN_PROGRESS']])
        completed = len([r for r in requests if r.status == 'COMPLETED'])
        declined = len([r for r in requests if r.status == 'CANCELLED'])
        
        acceptance_rate = ((total - declined) / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "new": new,
            "in_progress": in_progress,
            "completed": completed,
            "declined": declined,
            "acceptance_rate": round(acceptance_rate, 1)
        }
    
    def _calculate_avg_response_time(self, db: Session, provider: Provider) -> int:
        """Calculate average response time in minutes"""
        # This would need more detailed tracking in practice
        # For now, return a reasonable default based on provider performance
        if provider.acceptance_rate and provider.acceptance_rate > 80:
            return 12  # Fast responder
        elif provider.acceptance_rate and provider.acceptance_rate > 60:
            return 25  # Average responder
        else:
            return 45  # Slower responder
    
    def _get_estimated_price(self, service_type: str) -> Dict[str, int]:
        """Get estimated price range for service type"""
        pricing = settings.service_pricing
        if service_type in pricing:
            return {
                "min": pricing[service_type]["min"],
                "max": pricing[service_type]["max"]
            }
        return {"min": 5000, "max": 15000}
    
    def _format_time_ago(self, created_at: datetime) -> str:
        """Format time ago in French"""
        now = datetime.utcnow()
        diff = now - created_at.replace(tzinfo=None)
        
        if diff.days > 0:
            return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"il y a {hours} heure{'s' if hours > 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return "à l'instant"

    def get_provider_profile(self, db: Session, provider_id: int) -> Dict[str, Any]:
        """
        Get complete provider profile information
        
        Args:
            db: Database session
            provider_id: Provider ID
            
        Returns:
            Complete provider profile data
        """
        try:
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return {
                    "success": False,
                    "error": "Provider not found"
                }
            
            # Get provider specializations
            specializations = db.query(ProviderSpecialization).filter(
                ProviderSpecialization.provider_id == provider_id
            ).all()
            
            # Get provider certifications
            certifications = db.query(ProviderCertification).filter(
                ProviderCertification.provider_id == provider_id
            ).all()
            
            # Get provider photos
            photos = db.query(ProviderPhoto).filter(
                ProviderPhoto.provider_id == provider_id
            ).all()
            
            # Calculate trust score and stats
            total_reviews = db.query(ProviderReview).filter(
                ProviderReview.provider_id == provider_id
            ).count()
            
            avg_rating = db.query(func.avg(ProviderReview.rating)).filter(
                ProviderReview.provider_id == provider_id
            ).scalar() or 0
            
            completed_jobs = db.query(ServiceRequest).filter(
                and_(
                    ServiceRequest.provider_id == provider_id,
                    ServiceRequest.status == "COMPLETED"
                )
            ).count()
            
            # Calculate trust score
            trust_score = self._calculate_trust_score(
                avg_rating, total_reviews, completed_jobs, 
                provider.years_experience or 0, provider.verification_status or False
            )
            
            return {
                "success": True,
                "profile": {
                    "id": provider.id,
                    "name": provider.name,
                    "whatsapp_id": provider.whatsapp_id,
                    "service_type": provider.services[0] if provider.services else "",
                    "location": provider.coverage_areas[0] if provider.coverage_areas else "",
                    "coverage_area": ", ".join(provider.coverage_areas) if provider.coverage_areas else "",
                    "years_experience": provider.years_experience,
                    "bio": provider.bio,
                    "hourly_rate": float(provider.minimum_job_value) if provider.minimum_job_value else None,
                    "verification_status": provider.verification_status == "verified",
                    "profile_picture": provider.profile_photo_url,
                    "availability": provider.is_available,
                    "rating": float(avg_rating),
                    "total_reviews": total_reviews,
                    "completed_jobs": completed_jobs,
                    "trust_score": trust_score,
                    "created_at": provider.created_at.isoformat() if provider.created_at else None,
                    "specializations": [
                        {
                            "id": spec.id,
                            "name": spec.specialization_name,
                            "description": spec.description,
                            "years_experience": spec.years_experience
                        } for spec in specializations
                    ],
                    "certifications": [
                        {
                            "id": cert.id,
                            "name": cert.certification_name,
                            "issuer": cert.issuer,
                            "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
                            "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
                            "certificate_url": cert.certificate_url
                        } for cert in certifications
                    ],
                    "photos": [
                        {
                            "id": photo.id,
                            "photo_url": photo.photo_url,
                            "caption": photo.caption,
                            "photo_type": photo.photo_type
                        } for photo in photos
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting provider profile {provider_id}: {e}")
            return {
                "success": False,
                "error": "Failed to load provider profile"
            }

    def update_provider_profile(self, db: Session, provider_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update provider profile information
        
        Args:
            db: Database session
            provider_id: Provider ID
            update_data: Profile data to update
            
        Returns:
            Updated provider profile
        """
        try:
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if not provider:
                return {
                    "success": False,
                    "error": "Provider not found"
                }
            
            # Update basic profile fields with proper field mapping
            if 'name' in update_data:
                provider.name = update_data['name']
            if 'bio' in update_data:
                provider.bio = update_data['bio']
            if 'years_experience' in update_data:
                provider.years_experience = update_data['years_experience']
            if 'hourly_rate' in update_data:
                provider.minimum_job_value = float(update_data['hourly_rate']) if update_data['hourly_rate'] else 0.0
            if 'location' in update_data:
                # Update coverage_areas JSON field
                provider.coverage_areas = [update_data['location']] if update_data['location'] else []
            if 'coverage_area' in update_data:
                # Parse comma-separated coverage areas
                coverage_list = [area.strip() for area in update_data['coverage_area'].split(",") if area.strip()]
                provider.coverage_areas = coverage_list if coverage_list else []
            if 'profile_picture' in update_data:
                provider.profile_photo_url = update_data['profile_picture']
            if 'service_type' in update_data:
                # Update services JSON field
                provider.services = [update_data['service_type']] if update_data['service_type'] else []
            if 'availability' in update_data:
                provider.is_available = update_data['availability']
            
            # Handle specializations update
            if 'specializations' in update_data:
                # Delete existing specializations
                db.query(ProviderSpecialization).filter(
                    ProviderSpecialization.provider_id == provider_id
                ).delete()
                
                # Add new specializations
                for spec_data in update_data['specializations']:
                    specialization = ProviderSpecialization(
                        provider_id=provider_id,
                        specialization_name=spec_data.get('name'),
                        description=spec_data.get('description'),
                        years_experience=spec_data.get('years_experience', 0)
                    )
                    db.add(specialization)
            
            # Handle certifications update
            if 'certifications' in update_data:
                # Delete existing certifications
                db.query(ProviderCertification).filter(
                    ProviderCertification.provider_id == provider_id
                ).delete()
                
                # Add new certifications
                for cert_data in update_data['certifications']:
                    certification = ProviderCertification(
                        provider_id=provider_id,
                        certification_name=cert_data.get('name'),
                        issuer=cert_data.get('issuer'),
                        issue_date=datetime.fromisoformat(cert_data['issue_date']) if cert_data.get('issue_date') else None,
                        expiry_date=datetime.fromisoformat(cert_data['expiry_date']) if cert_data.get('expiry_date') else None,
                        certificate_url=cert_data.get('certificate_url')
                    )
                    db.add(certification)
            
            db.commit()
            
            # Return updated profile
            return self.get_provider_profile(db, provider_id)
            
        except Exception as e:
            logger.error(f"Error updating provider profile {provider_id}: {e}")
            db.rollback()
            return {
                "success": False,
                "error": "Failed to update provider profile"
            }

    def _calculate_trust_score(self, avg_rating: float, total_reviews: int, completed_jobs: int, 
                              years_experience: int, is_verified: bool) -> float:
        """Calculate provider trust score based on multiple factors"""
        score = 0.0
        
        # Rating contribution (40%)
        if avg_rating > 0:
            score += (avg_rating / 5.0) * 0.4
        
        # Experience contribution (20%)
        experience_score = min(years_experience / 10.0, 1.0)  # Max at 10 years
        score += experience_score * 0.2
        
        # Completed jobs contribution (15%)
        jobs_score = min(completed_jobs / 100.0, 1.0)  # Max at 100 jobs
        score += jobs_score * 0.15
        
        # Verification status (15%)
        if is_verified:
            score += 0.15
        
        # Review count contribution (10%)
        review_score = min(total_reviews / 50.0, 1.0)  # Max at 50 reviews
        score += review_score * 0.1
        
        return round(score * 100, 1)  # Return as percentage

# Service instances
provider_auth_service = ProviderAuthService()
provider_dashboard_service = ProviderDashboardService()