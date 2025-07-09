"""
Sprint 3 - Provider Matching Algorithm
Advanced matching system for connecting clients with optimal service providers
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, String

from app.models.database_models import Provider, ServiceRequest, User
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ProviderScore:
    """Provider scoring for matching algorithm"""
    provider_id: int
    provider: Provider
    total_score: float
    proximity_score: float
    rating_score: float
    response_time_score: float
    specialization_score: float
    availability_score: float


class ProviderMatcher:
    """Advanced provider matching algorithm with scoring system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.min_rating_threshold = 0.0  # Allow new providers with 0 rating
        self.max_providers_to_notify = 3
        
        # Scoring weights
        self.weights = {
            'proximity': 0.3,
            'rating': 0.25,
            'response_time': 0.2,
            'specialization': 0.15,
            'availability': 0.1
        }
        
        # Geographic zones for Douala/Bonamoussadi
        self.geographic_zones = {
            'bonamoussadi': ['bonamoussadi', 'makepe', 'bonapriso', 'akwa'],
            'douala_center': ['akwa', 'bonapriso', 'bonanjo', 'deido'],
            'douala_suburbs': ['makepe', 'pk8', 'pk10', 'logbaba', 'cite_sic']
        }
    
    def find_available_providers(self, request: ServiceRequest) -> List[Provider]:
        """
        Find available providers based on matching criteria
        
        Matching criteria:
        1. Service type corresponds
        2. Geographic zone covered
        3. Current availability
        4. Rating above threshold
        5. Positive response history
        """
        try:
            # Base query for providers
            query = self.db.query(Provider).filter(
                Provider.is_active == True,
                Provider.is_available == True,
                Provider.rating >= self.min_rating_threshold
            )
            
            # Filter by service type
            service_type = request.service_type.lower()
            logger.info(f"Filtering providers by service type: {service_type}")
            
            # Check if services array contains the service type
            query = query.filter(
                func.json_array_length(Provider.services) > 0
            ).filter(
                func.cast(Provider.services.op('->')(0), String).ilike(f'%{service_type}%')
            )
            
            # Filter by geographic coverage
            location_keywords = self._extract_location_keywords(request.location)
            logger.info(f"Filtering providers by location keywords: {location_keywords}")
            if location_keywords:
                coverage_conditions = []
                for keyword in location_keywords:
                    coverage_conditions.append(
                        func.cast(Provider.coverage_areas.op('->')(0), String).ilike(f'%{keyword}%')
                    )
                query = query.filter(or_(*coverage_conditions))
            
            # Exclude providers currently handling too many requests
            busy_providers = self.db.query(ServiceRequest.provider_id).filter(
                ServiceRequest.status.in_(['assigned', 'in_progress']),
                ServiceRequest.provider_id.isnot(None)
            ).group_by(ServiceRequest.provider_id).having(
                func.count(ServiceRequest.id) >= 3  # Max 3 concurrent jobs
            ).subquery()
            
            query = query.filter(~Provider.id.in_(busy_providers))
            
            providers = query.all()
            
            logger.info(f"Found {len(providers)} available providers for service '{service_type}' in '{request.location}'")
            return providers
            
        except Exception as e:
            logger.error(f"Error finding available providers: {e}")
            return []
    
    def rank_providers(self, providers: List[Provider], request: ServiceRequest) -> List[ProviderScore]:
        """
        Rank providers using multi-criteria scoring algorithm
        
        Scoring based on:
        - Geographic proximity
        - Client rating
        - Historical response time
        - Service specialization
        - Current availability
        """
        try:
            scored_providers = []
            
            for provider in providers:
                proximity_score = self._calculate_proximity_score(provider, request.location)
                rating_score = self._calculate_rating_score(provider)
                response_time_score = self._calculate_response_time_score(provider)
                specialization_score = self._calculate_specialization_score(provider, request.service_type)
                availability_score = self._calculate_availability_score(provider)
                
                # Calculate weighted total score
                total_score = (
                    proximity_score * self.weights['proximity'] +
                    rating_score * self.weights['rating'] +
                    response_time_score * self.weights['response_time'] +
                    specialization_score * self.weights['specialization'] +
                    availability_score * self.weights['availability']
                )
                
                provider_score = ProviderScore(
                    provider_id=provider.id,
                    provider=provider,
                    total_score=total_score,
                    proximity_score=proximity_score,
                    rating_score=rating_score,
                    response_time_score=response_time_score,
                    specialization_score=specialization_score,
                    availability_score=availability_score
                )
                
                scored_providers.append(provider_score)
            
            # Sort by total score (descending)
            scored_providers.sort(key=lambda x: x.total_score, reverse=True)
            
            logger.info(f"Ranked {len(scored_providers)} providers by score")
            return scored_providers
            
        except Exception as e:
            logger.error(f"Error ranking providers: {e}")
            return []
    
    def get_best_providers(self, request: ServiceRequest, limit: int = None) -> List[ProviderScore]:
        """Get best matched providers for a service request"""
        if limit is None:
            limit = self.max_providers_to_notify
            
        available_providers = self.find_available_providers(request)
        if not available_providers:
            logger.warning(f"No available providers found for request {request.id}")
            return []
        
        ranked_providers = self.rank_providers(available_providers, request)
        return ranked_providers[:limit]
    
    def _extract_location_keywords(self, location: str) -> List[str]:
        """Extract location keywords for geographic matching"""
        if not location:
            return []
        
        location_lower = location.lower()
        keywords = []
        
        # Check for specific neighborhoods and landmarks
        location_mappings = {
            'bonamoussadi': 'bonamoussadi',
            'makepe': 'makepe',
            'bonapriso': 'bonapriso', 
            'akwa': 'akwa',
            'deido': 'deido',
            'bonanjo': 'bonanjo',
            'shell': 'station_shell',
            'total': 'station_total',
            'carrefour': 'carrefour',
            'marché': 'marché'
        }
        
        for term, keyword in location_mappings.items():
            if term in location_lower:
                keywords.append(keyword)
        
        # Default to bonamoussadi if no specific location found
        if not keywords:
            keywords.append('bonamoussadi')
        
        return keywords
    
    def _calculate_proximity_score(self, provider: Provider, request_location: str) -> float:
        """Calculate geographic proximity score (0-1)"""
        try:
            request_keywords = set(self._extract_location_keywords(request_location))
            provider_areas = set(provider.coverage_areas or [])
            
            # Calculate overlap between request location and provider coverage
            overlap = len(request_keywords.intersection(provider_areas))
            total_request_keywords = len(request_keywords)
            
            if total_request_keywords == 0:
                return 0.5  # Neutral score if no location info
            
            proximity_score = min(overlap / total_request_keywords, 1.0)
            
            # Bonus for exact neighborhood match
            if 'bonamoussadi' in request_keywords and 'bonamoussadi' in provider_areas:
                proximity_score = min(proximity_score + 0.2, 1.0)
            
            return proximity_score
            
        except Exception as e:
            logger.error(f"Error calculating proximity score: {e}")
            return 0.0
    
    def _calculate_rating_score(self, provider: Provider) -> float:
        """Calculate rating score (0-1)"""
        try:
            if provider.rating <= 0:
                return 0.0
            
            # Normalize rating from 0-5 scale to 0-1 scale
            rating_score = min(provider.rating / 5.0, 1.0)
            
            # Bonus for high ratings and many completed jobs
            if provider.rating >= 4.5 and provider.total_jobs >= 10:
                rating_score = min(rating_score + 0.1, 1.0)
            
            return rating_score
            
        except Exception as e:
            logger.error(f"Error calculating rating score: {e}")
            return 0.0
    
    def _calculate_response_time_score(self, provider: Provider) -> float:
        """Calculate historical response time score (0-1)"""
        try:
            # Query recent requests to calculate average response time
            recent_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider.id,
                ServiceRequest.accepted_at.isnot(None),
                ServiceRequest.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            if not recent_requests:
                return 0.5  # Neutral score for new providers
            
            response_times = []
            for req in recent_requests:
                if req.accepted_at and req.created_at:
                    response_time = (req.accepted_at - req.created_at).total_seconds() / 60  # in minutes
                    response_times.append(response_time)
            
            if not response_times:
                return 0.5
            
            avg_response_time = sum(response_times) / len(response_times)
            
            # Score based on response time (faster = better)
            # Perfect score for responses under 5 minutes
            if avg_response_time <= 5:
                return 1.0
            elif avg_response_time <= 10:
                return 0.8
            elif avg_response_time <= 20:
                return 0.6
            elif avg_response_time <= 30:
                return 0.4
            else:
                return 0.2
            
        except Exception as e:
            logger.error(f"Error calculating response time score: {e}")
            return 0.5
    
    def _calculate_specialization_score(self, provider: Provider, service_type: str) -> float:
        """Calculate service specialization score (0-1)"""
        try:
            provider_services = provider.services or []
            service_type_lower = service_type.lower()
            
            if service_type_lower in [s.lower() for s in provider_services]:
                # Bonus for specialists (providers with fewer service types)
                num_services = len(provider_services)
                if num_services == 1:
                    return 1.0  # Specialist
                elif num_services <= 2:
                    return 0.9  # Semi-specialist
                elif num_services <= 3:
                    return 0.8  # Multi-service
                else:
                    return 0.7  # Generalist
            
            return 0.0  # Service not offered
            
        except Exception as e:
            logger.error(f"Error calculating specialization score: {e}")
            return 0.0
    
    def _calculate_availability_score(self, provider: Provider) -> float:
        """Calculate current availability score (0-1)"""
        try:
            if not provider.is_available:
                return 0.0
            
            # Check current workload
            current_jobs = self.db.query(ServiceRequest).filter(
                ServiceRequest.provider_id == provider.id,
                ServiceRequest.status.in_(['assigned', 'in_progress'])
            ).count()
            
            # Score based on current workload
            if current_jobs == 0:
                return 1.0  # Fully available
            elif current_jobs == 1:
                return 0.8  # Slightly busy
            elif current_jobs == 2:
                return 0.6  # Moderately busy
            else:
                return 0.2  # Very busy
            
        except Exception as e:
            logger.error(f"Error calculating availability score: {e}")
            return 0.5