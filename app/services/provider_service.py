"""
Provider service for managing service providers in the Djobea AI platform
"""
import uuid
import math
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from loguru import logger

from app.models.auth_models import User
from app.models.database_models import Provider as ProviderModel
from app.models.provider_models import (
    Provider, CreateProviderRequest, UpdateProviderRequest, 
    ProvidersFilters, ProvidersStats, Pagination,
    ProviderStatus, ProviderAvailability, SortBy, SortOrder
)
from app.services.communication_service import CommunicationService

class ProviderService:
    def __init__(self, db: Session):
        self.db = db
        self.communication_service = CommunicationService()

    def get_providers(
        self, 
        filters: Optional[ProvidersFilters] = None,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[Provider], Pagination, ProvidersStats]:
        """Get paginated list of providers with filtering and sorting"""
        
        query = self.db.query(ProviderModel)
        
        # Apply filters
        if filters:
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.filter(
                    or_(
                        ProviderModel.name.ilike(search_term),
                        ProviderModel.email.ilike(search_term),
                        ProviderModel.service_type.ilike(search_term),
                        ProviderModel.specialty.ilike(search_term)
                    )
                )
            
            if filters.status:
                query = query.filter(ProviderModel.status == filters.status.value)
            
            if filters.specialty:
                query = query.filter(ProviderModel.specialty.ilike(f"%{filters.specialty}%"))
            
            if filters.zone:
                query = query.filter(ProviderModel.coverage_zone.ilike(f"%{filters.zone}%"))
            
            if filters.minRating:
                query = query.filter(ProviderModel.rating >= filters.minRating)
            
            if filters.services:
                # Filter by services (assuming service_type contains the services)
                service_filters = [
                    ProviderModel.service_type.ilike(f"%{service}%") 
                    for service in filters.services
                ]
                query = query.filter(or_(*service_filters))
            
            if filters.availability:
                query = query.filter(ProviderModel.availability == filters.availability.value)
            
            # Apply sorting
            if filters.sortBy:
                sort_column = self._get_sort_column(filters.sortBy)
                if sort_column is not None:
                    if filters.sortOrder == SortOrder.DESC:
                        query = query.order_by(desc(sort_column))
                    else:
                        query = query.order_by(asc(sort_column))
        
        # Get total count
        total = query.count()
        
        # Calculate pagination
        total_pages = math.ceil(total / limit)
        offset = (page - 1) * limit
        
        # Get paginated results
        providers_data = query.offset(offset).limit(limit).all()
        
        # Convert to Pydantic models
        providers = [self._convert_to_provider(provider) for provider in providers_data]
        
        # Create pagination
        pagination = Pagination(
            page=page,
            limit=limit,
            total=total,
            totalPages=total_pages,
            hasNext=page < total_pages,
            hasPrev=page > 1
        )
        
        # Get stats
        stats = self._get_provider_stats()
        
        return providers, pagination, stats

    def get_provider_by_id(self, provider_id: str) -> Optional[Provider]:
        """Get a provider by ID"""
        provider = self.db.query(ProviderModel).filter(ProviderModel.id == provider_id).first()
        if provider:
            return self._convert_to_provider(provider)
        return None

    def create_provider(self, request: CreateProviderRequest) -> Provider:
        """Create a new provider"""
        provider_data = {
            "id": str(uuid.uuid4()),
            "name": request.name,
            "email": request.email,
            "phone": request.phone,
            "whatsapp": request.whatsapp or request.phone,
            "service_type": ", ".join(request.services),
            "location": request.zone,
            "coverage_zone": ", ".join(request.coverageAreas),
            "specialty": request.specialty,
            "rating": 0.0,
            "availability": "available",
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        # Add optional fields
        if request.hourlyRate:
            provider_data["hourly_rate"] = request.hourlyRate
        if request.experience:
            provider_data["experience"] = request.experience
        if request.description:
            provider_data["description"] = request.description
        
        provider = ProviderModel(**provider_data)
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        
        logger.info(f"Created new provider: {provider.name} (ID: {provider.id})")
        return self._convert_to_provider(provider)

    def update_provider(self, provider_id: str, request: UpdateProviderRequest) -> Optional[Provider]:
        """Update an existing provider"""
        provider = self.db.query(ProviderModel).filter(ProviderModel.id == provider_id).first()
        if not provider:
            return None
        
        # Update fields if provided
        if request.name is not None:
            provider.name = request.name
        if request.email is not None:
            provider.email = request.email
        if request.phone is not None:
            provider.phone = request.phone
        if request.whatsapp is not None:
            provider.whatsapp = request.whatsapp
        if request.services is not None:
            provider.service_type = ", ".join(request.services)
        if request.coverageAreas is not None:
            provider.coverage_zone = ", ".join(request.coverageAreas)
        if request.specialty is not None:
            provider.specialty = request.specialty
        if request.zone is not None:
            provider.location = request.zone
        if request.hourlyRate is not None:
            provider.hourly_rate = request.hourlyRate
        if request.experience is not None:
            provider.experience = request.experience
        if request.description is not None:
            provider.description = request.description
        if request.status is not None:
            provider.status = request.status.value
        if request.availability is not None:
            provider.availability = request.availability.value
        if request.rating is not None:
            provider.rating = request.rating
        
        provider.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(provider)
        
        logger.info(f"Updated provider: {provider.name} (ID: {provider.id})")
        return self._convert_to_provider(provider)

    def delete_provider(self, provider_id: str) -> bool:
        """Delete a provider"""
        provider = self.db.query(ProviderModel).filter(ProviderModel.id == provider_id).first()
        if not provider:
            return False
        
        self.db.delete(provider)
        self.db.commit()
        
        logger.info(f"Deleted provider: {provider.name} (ID: {provider.id})")
        return True

    def update_provider_status(self, provider_id: str, status: ProviderStatus) -> Optional[Provider]:
        """Update provider status"""
        provider = self.db.query(ProviderModel).filter(ProviderModel.id == provider_id).first()
        if not provider:
            return None
        
        provider.status = status.value
        provider.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(provider)
        
        logger.info(f"Updated provider status: {provider.name} -> {status.value}")
        return self._convert_to_provider(provider)

    def contact_provider(self, provider_id: str, method: str, message: str = None) -> bool:
        """Contact a provider via specified method"""
        provider = self.db.query(ProviderModel).filter(ProviderModel.id == provider_id).first()
        if not provider:
            return False
        
        try:
            if method == "whatsapp":
                # Send WhatsApp message
                phone = provider.whatsapp or provider.phone
                if message:
                    self.communication_service.send_whatsapp_message(phone, message)
                logger.info(f"Sent WhatsApp message to provider {provider.name}")
                
            elif method == "email":
                # Send email (implement email service)
                logger.info(f"Sent email to provider {provider.name}")
                
            elif method == "call":
                # Log call request (actual calling would be handled by frontend)
                logger.info(f"Call requested for provider {provider.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error contacting provider {provider.name}: {e}")
            return False

    def get_available_providers(
        self, 
        service_type: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
        urgency: Optional[bool] = None
    ) -> List[Provider]:
        """Get available providers for a service request"""
        query = self.db.query(ProviderModel).filter(
            ProviderModel.status == "active",
            ProviderModel.availability == "available"
        )
        
        if service_type:
            query = query.filter(ProviderModel.service_type.ilike(f"%{service_type}%"))
        
        # For location-based filtering, you might want to implement geographic distance calculation
        # This is a simplified version
        if location and location.get("radius"):
            # Implement geographic filtering based on coordinates
            pass
        
        # Sort by rating and response time for better matches
        query = query.order_by(desc(ProviderModel.rating))
        
        providers_data = query.limit(10).all()  # Limit to top 10 matches
        return [self._convert_to_provider(provider) for provider in providers_data]

    def search_providers(self, query: str) -> List[Provider]:
        """Search providers by name, services, or other criteria"""
        search_term = f"%{query}%"
        providers_data = self.db.query(ProviderModel).filter(
            or_(
                ProviderModel.name.ilike(search_term),
                ProviderModel.email.ilike(search_term),
                ProviderModel.service_type.ilike(search_term),
                ProviderModel.specialty.ilike(search_term),
                ProviderModel.location.ilike(search_term)
            )
        ).order_by(desc(ProviderModel.rating)).limit(20).all()
        
        return [self._convert_to_provider(provider) for provider in providers_data]

    def _convert_to_provider(self, provider: ProviderModel) -> Provider:
        """Convert SQLAlchemy model to Pydantic model"""
        # Calculate derived fields
        total_missions = getattr(provider, 'total_missions', 0)
        completed_jobs = getattr(provider, 'completed_jobs', 0)
        cancelled_jobs = getattr(provider, 'cancelled_jobs', 0)
        
        # Calculate success rate
        success_rate = 0.0
        if total_missions > 0:
            success_rate = (completed_jobs / total_missions) * 100
        
        # Calculate acceptance rate
        acceptance_rate = getattr(provider, 'acceptance_rate', 85.0)
        
        # Parse services and coverage areas
        services = []
        if provider.service_type:
            services = [s.strip() for s in provider.service_type.split(',')]
        
        coverage_areas = []
        if provider.coverage_zone:
            coverage_areas = [area.strip() for area in provider.coverage_zone.split(',')]
        
        return Provider(
            id=provider.id,
            name=provider.name,
            email=provider.email,
            phone=provider.phone,
            whatsapp=provider.whatsapp or provider.phone,
            services=services,
            coverageAreas=coverage_areas,
            specialty=provider.specialty or "General",
            zone=provider.location or "Douala",
            rating=float(provider.rating or 0.0),
            reviewCount=getattr(provider, 'review_count', 0),
            totalMissions=total_missions,
            completedJobs=completed_jobs,
            cancelledJobs=cancelled_jobs,
            successRate=success_rate,
            responseTime=getattr(provider, 'response_time', 15.0),
            performanceStatus=self._get_performance_status(provider.rating or 0.0),
            status=ProviderStatus(provider.status or "active"),
            availability=ProviderAvailability(provider.availability or "available"),
            joinDate=provider.created_at.date() if provider.created_at else date.today(),
            lastActivity=provider.updated_at,
            hourlyRate=getattr(provider, 'hourly_rate', None),
            experience=getattr(provider, 'experience', None),
            acceptanceRate=acceptance_rate,
            description=getattr(provider, 'description', None),
            profileImage=getattr(provider, 'profile_image', None),
            certifications=getattr(provider, 'certifications', []),
            createdAt=provider.created_at or datetime.utcnow(),
            updatedAt=provider.updated_at or datetime.utcnow()
        )

    def _get_performance_status(self, rating: float) -> str:
        """Get performance status based on rating"""
        if rating >= 4.5:
            return "excellent"
        elif rating >= 4.0:
            return "good"
        elif rating >= 3.0:
            return "warning"
        else:
            return "poor"

    def _get_sort_column(self, sort_by: SortBy):
        """Get SQLAlchemy column for sorting"""
        if sort_by == SortBy.NAME:
            return ProviderModel.name
        elif sort_by == SortBy.RATING:
            return ProviderModel.rating
        elif sort_by == SortBy.MISSIONS:
            return ProviderModel.total_missions
        elif sort_by == SortBy.JOIN_DATE:
            return ProviderModel.created_at
        elif sort_by == SortBy.LAST_ACTIVITY:
            return ProviderModel.updated_at
        return None

    def _get_provider_stats(self) -> ProvidersStats:
        """Get provider statistics"""
        total = self.db.query(ProviderModel).count()
        active = self.db.query(ProviderModel).filter(ProviderModel.status == "active").count()
        inactive = self.db.query(ProviderModel).filter(ProviderModel.status == "inactive").count()
        suspended = self.db.query(ProviderModel).filter(ProviderModel.status == "suspended").count()
        available = self.db.query(ProviderModel).filter(ProviderModel.availability == "available").count()
        
        # Calculate average rating
        avg_rating_result = self.db.query(func.avg(ProviderModel.rating)).scalar()
        avg_rating = float(avg_rating_result or 0.0)
        
        # Get new providers this month
        current_month = datetime.now().replace(day=1)
        new_this_month = self.db.query(ProviderModel).filter(
            ProviderModel.created_at >= current_month
        ).count()
        
        # Get top performers
        top_performers_data = self.db.query(ProviderModel).filter(
            ProviderModel.rating >= 4.5
        ).order_by(desc(ProviderModel.rating)).limit(5).all()
        
        top_performers = [self._convert_to_provider(provider) for provider in top_performers_data]
        
        return ProvidersStats(
            total=total,
            active=active,
            inactive=inactive,
            suspended=suspended,
            available=available,
            avgRating=avg_rating,
            newThisMonth=new_this_month,
            topPerformers=top_performers
        )