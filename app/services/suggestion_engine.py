"""
Suggestion Engine - Intelligent suggestions and recommendations
Provides alternative services, nearby zones, and smart recommendations
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict
import math

from app.models.dynamic_services import Service, Zone, ServiceZone, ServiceSearchLog, UserInteraction
from app.services.zone_service import ZoneService
from app.services.service_management_service import ServiceManagementService

logger = logging.getLogger(__name__)

class SuggestionType(Enum):
    """Types of suggestions"""
    ALTERNATIVE_SERVICE = "alternative_service"
    NEARBY_ZONE = "nearby_zone"
    SIMILAR_SERVICE = "similar_service"
    POPULAR_SERVICE = "popular_service"
    SEASONAL_SERVICE = "seasonal_service"
    HISTORICAL_PREFERENCE = "historical_preference"
    PRICE_BASED = "price_based"
    AVAILABILITY_BASED = "availability_based"

class SuggestionPriority(Enum):
    """Priority levels for suggestions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Suggestion:
    """Individual suggestion with metadata"""
    type: SuggestionType
    priority: SuggestionPriority
    service_code: Optional[str]
    zone_code: Optional[str]
    title: str
    description: str
    confidence: float
    metadata: Dict[str, Any]
    reasoning: str

@dataclass
class SuggestionResponse:
    """Response containing multiple suggestions"""
    suggestions: List[Suggestion]
    total_count: int
    categories: Dict[str, int]
    recommendation_confidence: float

class SuggestionEngine:
    """Engine for generating intelligent suggestions and recommendations"""
    
    def __init__(self):
        self.zone_service = ZoneService()
        self.service_management = ServiceManagementService()
        self.suggestion_cache: Dict[str, List[Suggestion]] = {}
        
        # Suggestion algorithms and weights
        self.suggestion_weights = {
            SuggestionType.ALTERNATIVE_SERVICE: 0.9,
            SuggestionType.NEARBY_ZONE: 0.8,
            SuggestionType.SIMILAR_SERVICE: 0.7,
            SuggestionType.POPULAR_SERVICE: 0.6,
            SuggestionType.HISTORICAL_PREFERENCE: 0.85,
            SuggestionType.PRICE_BASED: 0.5,
            SuggestionType.AVAILABILITY_BASED: 0.75
        }
        
        # Distance thresholds for zone suggestions
        self.zone_distance_thresholds = {
            'immediate': 5.0,   # Within 5km
            'nearby': 15.0,     # Within 15km
            'regional': 50.0,   # Within 50km
            'distant': 100.0    # Within 100km
        }
    
    async def generate_suggestions(
        self,
        db: Session,
        query: str,
        zone_code: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> SuggestionResponse:
        """
        Generate comprehensive suggestions based on query and context
        """
        try:
            suggestions = []
            
            # 1. Generate alternative service suggestions
            alternative_services = await self._generate_alternative_services(
                db, query, zone_code
            )
            suggestions.extend(alternative_services)
            
            # 2. Generate nearby zone suggestions
            if zone_code:
                nearby_zones = await self._generate_nearby_zone_suggestions(
                    db, query, zone_code
                )
                suggestions.extend(nearby_zones)
            
            # 3. Generate similar service suggestions
            similar_services = await self._generate_similar_services(
                db, query, zone_code
            )
            suggestions.extend(similar_services)
            
            # 4. Generate popular service suggestions
            popular_services = await self._generate_popular_services(
                db, zone_code
            )
            suggestions.extend(popular_services)
            
            # 5. Generate historical preference suggestions
            if user_id:
                historical_suggestions = await self._generate_historical_preferences(
                    db, user_id, zone_code
                )
                suggestions.extend(historical_suggestions)
            
            # 6. Generate price-based suggestions
            price_suggestions = await self._generate_price_based_suggestions(
                db, query, zone_code, context
            )
            suggestions.extend(price_suggestions)
            
            # 7. Generate availability-based suggestions
            availability_suggestions = await self._generate_availability_suggestions(
                db, query, zone_code
            )
            suggestions.extend(availability_suggestions)
            
            # 8. Rank and filter suggestions
            ranked_suggestions = self._rank_suggestions(suggestions)
            
            # 9. Generate response
            response = SuggestionResponse(
                suggestions=ranked_suggestions[:10],  # Top 10 suggestions
                total_count=len(ranked_suggestions),
                categories=self._categorize_suggestions(ranked_suggestions),
                recommendation_confidence=self._calculate_recommendation_confidence(ranked_suggestions)
            )
            
            # 10. Log suggestion generation
            await self._log_suggestion_generation(db, query, zone_code, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return SuggestionResponse(
                suggestions=[],
                total_count=0,
                categories={},
                recommendation_confidence=0.0
            )
    
    async def _generate_alternative_services(
        self,
        db: Session,
        query: str,
        zone_code: Optional[str] = None
    ) -> List[Suggestion]:
        """Generate alternative service suggestions"""
        suggestions = []
        
        try:
            # Search for services similar to the query
            search_results = await self.service_management.search_services(
                db, query, zone_code=zone_code, limit=5
            )
            
            for result in search_results:
                service = result['service']
                suggestions.append(Suggestion(
                    type=SuggestionType.ALTERNATIVE_SERVICE,
                    priority=SuggestionPriority.HIGH,
                    service_code=service.code,
                    zone_code=zone_code,
                    title=f"Service alternatif: {service.name}",
                    description=f"{service.description} - Prix: {service.base_price_xaf} XAF",
                    confidence=result['confidence'],
                    metadata={
                        'service_id': service.id,
                        'base_price': service.base_price_xaf,
                        'rating': service.avg_rating,
                        'relevance_score': result['relevance_score']
                    },
                    reasoning=f"Service similaire trouvé avec score de pertinence {result['relevance_score']}"
                ))
            
        except Exception as e:
            logger.error(f"Error generating alternative services: {e}")
        
        return suggestions
    
    async def _generate_nearby_zone_suggestions(
        self,
        db: Session,
        query: str,
        zone_code: str
    ) -> List[Suggestion]:
        """Generate nearby zone suggestions"""
        suggestions = []
        
        try:
            # Get current zone
            current_zone = await self.zone_service.find_zone_by_code(db, zone_code)
            if not current_zone:
                return suggestions
            
            # Find nearby zones
            nearby_zones = await self.zone_service.find_nearby_zones(
                db, current_zone.latitude, current_zone.longitude, radius_km=25
            )
            
            for zone in nearby_zones:
                if zone.code == zone_code:
                    continue
                
                # Check if query services are available in this zone
                search_results = await self.service_management.search_services(
                    db, query, zone_code=zone.code, limit=1
                )
                
                if search_results:
                    distance = self._calculate_distance(
                        current_zone.latitude, current_zone.longitude,
                        zone.latitude, zone.longitude
                    )
                    
                    priority = self._get_zone_priority_by_distance(distance)
                    
                    suggestions.append(Suggestion(
                        type=SuggestionType.NEARBY_ZONE,
                        priority=priority,
                        service_code=None,
                        zone_code=zone.code,
                        title=f"Zone proche: {zone.name}",
                        description=f"Services disponibles à {distance:.1f}km de votre position",
                        confidence=max(0.5, 1.0 - (distance / 50.0)),
                        metadata={
                            'zone_id': zone.id,
                            'distance_km': distance,
                            'service_count': len(search_results)
                        },
                        reasoning=f"Zone à {distance:.1f}km avec services disponibles"
                    ))
            
        except Exception as e:
            logger.error(f"Error generating nearby zone suggestions: {e}")
        
        return suggestions
    
    async def _generate_similar_services(
        self,
        db: Session,
        query: str,
        zone_code: Optional[str] = None
    ) -> List[Suggestion]:
        """Generate similar service suggestions"""
        suggestions = []
        
        try:
            # Get all services and find similar ones
            all_services = db.query(Service).filter(Service.status == 'available').all()
            
            for service in all_services:
                # Calculate similarity with query
                similarity = self._calculate_text_similarity(
                    query.lower(),
                    f"{service.name} {service.description}".lower()
                )
                
                if similarity > 0.3:  # Threshold for similarity
                    # Check availability in zone
                    if zone_code:
                        zone = await self.zone_service.find_zone_by_code(db, zone_code)
                        if zone:
                            service_zone = db.query(ServiceZone).filter(
                                ServiceZone.service_id == service.id,
                                ServiceZone.zone_id == zone.id,
                                ServiceZone.is_available == True
                            ).first()
                            
                            if not service_zone:
                                continue
                    
                    suggestions.append(Suggestion(
                        type=SuggestionType.SIMILAR_SERVICE,
                        priority=SuggestionPriority.MEDIUM,
                        service_code=service.code,
                        zone_code=zone_code,
                        title=f"Service similaire: {service.name}",
                        description=f"{service.description} - Similarité: {similarity:.2f}",
                        confidence=similarity,
                        metadata={
                            'service_id': service.id,
                            'similarity_score': similarity,
                            'base_price': service.base_price_xaf
                        },
                        reasoning=f"Service similaire avec score de similarité {similarity:.2f}"
                    ))
            
        except Exception as e:
            logger.error(f"Error generating similar services: {e}")
        
        return suggestions
    
    async def _generate_popular_services(
        self,
        db: Session,
        zone_code: Optional[str] = None
    ) -> List[Suggestion]:
        """Generate popular service suggestions"""
        suggestions = []
        
        try:
            # Get services ordered by popularity (bookings and ratings)
            query = db.query(Service).filter(Service.status == 'available')
            
            if zone_code:
                zone = await self.zone_service.find_zone_by_code(db, zone_code)
                if zone:
                    query = query.join(ServiceZone).filter(
                        ServiceZone.zone_id == zone.id,
                        ServiceZone.is_available == True
                    )
            
            popular_services = query.order_by(
                Service.total_bookings.desc(),
                Service.avg_rating.desc()
            ).limit(5).all()
            
            for service in popular_services:
                if service.total_bookings > 0:  # Only suggest services with bookings
                    suggestions.append(Suggestion(
                        type=SuggestionType.POPULAR_SERVICE,
                        priority=SuggestionPriority.MEDIUM,
                        service_code=service.code,
                        zone_code=zone_code,
                        title=f"Service populaire: {service.name}",
                        description=f"⭐ {service.avg_rating:.1f} ({service.total_bookings} réservations)",
                        confidence=min(1.0, service.total_bookings / 100.0),
                        metadata={
                            'service_id': service.id,
                            'total_bookings': service.total_bookings,
                            'avg_rating': service.avg_rating,
                            'base_price': service.base_price_xaf
                        },
                        reasoning=f"Service populaire avec {service.total_bookings} réservations"
                    ))
            
        except Exception as e:
            logger.error(f"Error generating popular services: {e}")
        
        return suggestions
    
    async def _generate_historical_preferences(
        self,
        db: Session,
        user_id: str,
        zone_code: Optional[str] = None
    ) -> List[Suggestion]:
        """Generate suggestions based on user's historical preferences"""
        suggestions = []
        
        try:
            # Get user's search history
            search_history = db.query(ServiceSearchLog).filter(
                ServiceSearchLog.user_id == user_id
            ).order_by(ServiceSearchLog.timestamp.desc()).limit(50).all()
            
            if not search_history:
                return suggestions
            
            # Analyze search patterns
            service_counts = defaultdict(int)
            for log in search_history:
                if log.selected_service_code:
                    service_counts[log.selected_service_code] += 1
            
            # Generate suggestions based on frequently searched services
            for service_code, count in service_counts.items():
                if count >= 2:  # At least 2 searches
                    service = db.query(Service).filter(Service.code == service_code).first()
                    if service:
                        suggestions.append(Suggestion(
                            type=SuggestionType.HISTORICAL_PREFERENCE,
                            priority=SuggestionPriority.HIGH,
                            service_code=service.code,
                            zone_code=zone_code,
                            title=f"Service habituel: {service.name}",
                            description=f"Vous avez recherché ce service {count} fois",
                            confidence=min(1.0, count / 10.0),
                            metadata={
                                'service_id': service.id,
                                'search_count': count,
                                'base_price': service.base_price_xaf
                            },
                            reasoning=f"Service recherché {count} fois par l'utilisateur"
                        ))
            
        except Exception as e:
            logger.error(f"Error generating historical preferences: {e}")
        
        return suggestions
    
    async def _generate_price_based_suggestions(
        self,
        db: Session,
        query: str,
        zone_code: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> List[Suggestion]:
        """Generate price-based suggestions"""
        suggestions = []
        
        try:
            # Get budget preference from context
            budget_preference = context.get('budget_preference', 'medium') if context else 'medium'
            
            # Define price ranges
            price_ranges = {
                'low': (0, 10000),
                'medium': (10000, 25000),
                'high': (25000, 100000)
            }
            
            min_price, max_price = price_ranges.get(budget_preference, (0, 25000))
            
            # Find services in price range
            query_obj = db.query(Service).filter(
                Service.status == 'available',
                Service.base_price_xaf >= min_price,
                Service.base_price_xaf <= max_price
            )
            
            if zone_code:
                zone = await self.zone_service.find_zone_by_code(db, zone_code)
                if zone:
                    query_obj = query_obj.join(ServiceZone).filter(
                        ServiceZone.zone_id == zone.id,
                        ServiceZone.is_available == True
                    )
            
            affordable_services = query_obj.limit(5).all()
            
            for service in affordable_services:
                suggestions.append(Suggestion(
                    type=SuggestionType.PRICE_BASED,
                    priority=SuggestionPriority.LOW,
                    service_code=service.code,
                    zone_code=zone_code,
                    title=f"Prix abordable: {service.name}",
                    description=f"Dans votre budget: {service.base_price_xaf} XAF",
                    confidence=0.6,
                    metadata={
                        'service_id': service.id,
                        'base_price': service.base_price_xaf,
                        'budget_category': budget_preference
                    },
                    reasoning=f"Service dans la gamme de prix {budget_preference}"
                ))
            
        except Exception as e:
            logger.error(f"Error generating price-based suggestions: {e}")
        
        return suggestions
    
    async def _generate_availability_suggestions(
        self,
        db: Session,
        query: str,
        zone_code: Optional[str] = None
    ) -> List[Suggestion]:
        """Generate availability-based suggestions"""
        suggestions = []
        
        try:
            # Find services with high availability
            query_obj = db.query(Service).filter(Service.status == 'available')
            
            if zone_code:
                zone = await self.zone_service.find_zone_by_code(db, zone_code)
                if zone:
                    query_obj = query_obj.join(ServiceZone).filter(
                        ServiceZone.zone_id == zone.id,
                        ServiceZone.is_available == True,
                        ServiceZone.avg_response_time_minutes < 60  # Quick response
                    )
            
            quick_services = query_obj.order_by(
                Service.avg_rating.desc()
            ).limit(3).all()
            
            for service in quick_services:
                suggestions.append(Suggestion(
                    type=SuggestionType.AVAILABILITY_BASED,
                    priority=SuggestionPriority.MEDIUM,
                    service_code=service.code,
                    zone_code=zone_code,
                    title=f"Disponible rapidement: {service.name}",
                    description=f"Temps de réponse moyen: < 1 heure",
                    confidence=0.7,
                    metadata={
                        'service_id': service.id,
                        'avg_response_time': 60,  # Default
                        'base_price': service.base_price_xaf
                    },
                    reasoning="Service avec temps de réponse rapide"
                ))
            
        except Exception as e:
            logger.error(f"Error generating availability suggestions: {e}")
        
        return suggestions
    
    def _rank_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Rank suggestions by priority and confidence"""
        def suggestion_score(suggestion: Suggestion) -> float:
            # Base score from confidence
            score = suggestion.confidence
            
            # Weight by type
            type_weight = self.suggestion_weights.get(suggestion.type, 0.5)
            score *= type_weight
            
            # Priority multiplier
            priority_multipliers = {
                SuggestionPriority.LOW: 1.0,
                SuggestionPriority.MEDIUM: 1.2,
                SuggestionPriority.HIGH: 1.5,
                SuggestionPriority.URGENT: 2.0
            }
            score *= priority_multipliers.get(suggestion.priority, 1.0)
            
            return score
        
        return sorted(suggestions, key=suggestion_score, reverse=True)
    
    def _categorize_suggestions(self, suggestions: List[Suggestion]) -> Dict[str, int]:
        """Categorize suggestions by type"""
        categories = defaultdict(int)
        for suggestion in suggestions:
            categories[suggestion.type.value] += 1
        return dict(categories)
    
    def _calculate_recommendation_confidence(self, suggestions: List[Suggestion]) -> float:
        """Calculate overall recommendation confidence"""
        if not suggestions:
            return 0.0
        
        # Average confidence of top suggestions
        top_suggestions = suggestions[:5]
        avg_confidence = sum(s.confidence for s in top_suggestions) / len(top_suggestions)
        
        # Adjust based on number of suggestions
        suggestion_count_factor = min(1.0, len(suggestions) / 10.0)
        
        return avg_confidence * suggestion_count_factor
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _get_zone_priority_by_distance(self, distance: float) -> SuggestionPriority:
        """Get priority based on distance"""
        if distance <= self.zone_distance_thresholds['immediate']:
            return SuggestionPriority.HIGH
        elif distance <= self.zone_distance_thresholds['nearby']:
            return SuggestionPriority.MEDIUM
        else:
            return SuggestionPriority.LOW
    
    async def _log_suggestion_generation(
        self,
        db: Session,
        query: str,
        zone_code: Optional[str],
        response: SuggestionResponse
    ) -> None:
        """Log suggestion generation for analytics"""
        try:
            # Create log entry (implement based on your logging model)
            logger.info(f"Generated {response.total_count} suggestions for query: {query}")
            
        except Exception as e:
            logger.error(f"Failed to log suggestion generation: {e}")