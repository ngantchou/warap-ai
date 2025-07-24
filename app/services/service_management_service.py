"""
Service Management Service - Dynamic service management with intelligent search
Handles service creation, search, matching, and validation
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, String
import logging
from difflib import SequenceMatcher
import re
from unidecode import unidecode
import json
from datetime import datetime, timedelta

from app.models.dynamic_services import Service, ServiceCategory, ServiceZone, ServiceSearchLog, ServiceStatus
from app.services.zone_service import ZoneService

logger = logging.getLogger(__name__)

class ServiceManagementService:
    """Service for managing services with intelligent search and matching"""
    
    def __init__(self):
        self.service_cache: Dict[str, Service] = {}
        self.category_cache: Dict[str, ServiceCategory] = {}
        self.zone_service = ZoneService()
        
        # Synonyms and variations for Cameroon context
        self.service_synonyms = {
            "plomberie": ["plombier", "eau", "tuyau", "canalisation", "robinet", "fuite", "wc", "toilette"],
            "électricité": ["électricien", "courant", "lumière", "prise", "câble", "court-circuit", "disjoncteur"],
            "électroménager": ["frigo", "frigidaire", "télé", "télévision", "machine", "lave-linge", "réparation"],
            "ménage": ["nettoyage", "femme de ménage", "propre", "balayer", "nettoyer"],
            "jardinage": ["jardin", "plantes", "arroser", "tondre", "jardinier"],
            "sécurité": ["gardien", "surveillant", "protection", "alarme", "caméra"],
            "transport": ["taxi", "moto", "déplacement", "livraison", "courses"]
        }
    
    async def create_service(
        self, 
        db: Session, 
        code: str, 
        name: str, 
        category_id: int,
        **kwargs
    ) -> Service:
        """Create a new service"""
        try:
            service = Service(
                code=code,
                name=name,
                category_id=category_id,
                **kwargs
            )
            
            # Generate search keywords
            service.search_keywords = self._generate_search_keywords(service)
            
            db.add(service)
            db.commit()
            db.refresh(service)
            
            # Update cache
            self.service_cache[code] = service
            
            logger.info(f"Created service: {code} ({name})")
            return service
            
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            db.rollback()
            raise
    
    async def search_services(
        self, 
        db: Session, 
        query: str, 
        zone_code: Optional[str] = None,
        category_id: Optional[int] = None,
        language: str = "fr",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search services with fuzzy matching and intelligent suggestions"""
        try:
            # Log search
            await self._log_search(db, query, zone_code, language)
            
            # Normalize query
            normalized_query = self._normalize_text(query)
            
            # Build search filters
            filters = [Service.status == ServiceStatus.AVAILABLE]
            
            if category_id:
                filters.append(Service.category_id == category_id)
            
            # Zone-based filtering
            if zone_code:
                zone = await self.zone_service.find_zone_by_code(db, zone_code)
                if zone:
                    # Find services available in this zone
                    zone_service_ids = db.query(ServiceZone.service_id).filter(
                        ServiceZone.zone_id == zone.id,
                        ServiceZone.is_available == True
                    ).subquery()
                    
                    filters.append(Service.id.in_(zone_service_ids))
            
            # Search in multiple fields
            search_conditions = []
            
            # Direct name match
            search_conditions.append(
                func.lower(Service.name).ilike(f"%{normalized_query}%")
            )
            
            # Localized name match
            if language == "fr":
                search_conditions.append(
                    func.lower(Service.name_fr).ilike(f"%{normalized_query}%")
                )
            elif language == "en":
                search_conditions.append(
                    func.lower(Service.name_en).ilike(f"%{normalized_query}%")
                )
            
            # Description match
            search_conditions.append(
                func.lower(Service.description).ilike(f"%{normalized_query}%")
            )
            
            # Code match
            search_conditions.append(
                func.lower(Service.code).ilike(f"%{normalized_query}%")
            )
            
            # Search keywords match - convert JSON to text and search
            search_conditions.append(
                func.lower(func.cast(Service.search_keywords, String)).ilike(f"%{normalized_query}%")
            )
            
            # Execute search
            services = db.query(Service).filter(
                and_(*filters),
                or_(*search_conditions)
            ).order_by(desc(Service.avg_rating), desc(Service.total_bookings)).limit(limit).all()
            
            # Calculate relevance scores
            results = []
            for service in services:
                score = self._calculate_service_relevance_score(service, normalized_query, query)
                results.append({
                    "service": service,
                    "relevance_score": score,
                    "match_type": self._get_service_match_type(service, normalized_query),
                    "confidence": min(score / 10.0, 1.0)
                })
            
            # Sort by relevance score
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Add synonyms-based suggestions if no direct matches
            if not results:
                synonym_results = await self._search_by_synonyms(db, query, zone_code, language)
                results.extend(synonym_results)
            
            logger.info(f"Found {len(results)} services for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching services: {e}")
            return []
    
    async def get_service_suggestions(
        self, 
        db: Session, 
        failed_query: str, 
        zone_code: Optional[str] = None,
        language: str = "fr"
    ) -> List[Dict[str, Any]]:
        """Get service suggestions for failed queries"""
        try:
            suggestions = []
            
            # Try fuzzy matching
            all_services = db.query(Service).filter(
                Service.status == ServiceStatus.AVAILABLE
            ).all()
            
            for service in all_services:
                # Calculate similarity with service name
                similarity = SequenceMatcher(
                    None, 
                    self._normalize_text(failed_query), 
                    self._normalize_text(service.name)
                ).ratio()
                
                if similarity > 0.4:  # Threshold for suggestions
                    suggestions.append({
                        "service": service,
                        "similarity": similarity,
                        "reason": "name_similarity"
                    })
            
            # Try synonym matching
            synonym_suggestions = await self._get_synonym_suggestions(db, failed_query, zone_code)
            suggestions.extend(synonym_suggestions)
            
            # Sort by similarity
            suggestions.sort(key=lambda x: x["similarity"], reverse=True)
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(f"Error getting service suggestions: {e}")
            return []
    
    async def validate_service_availability(
        self, 
        db: Session, 
        service_code: str, 
        zone_code: str
    ) -> Dict[str, Any]:
        """Validate if a service is available in a zone"""
        try:
            service = await self.find_service_by_code(db, service_code)
            if not service:
                suggestions = await self.get_service_suggestions(db, service_code)
                return {
                    "available": False,
                    "error": "Service not found",
                    "suggestions": suggestions
                }
            
            if service.status != ServiceStatus.AVAILABLE:
                return {
                    "available": False,
                    "error": f"Service is {service.status}",
                    "service": service
                }
            
            # Check zone availability
            zone = await self.zone_service.find_zone_by_code(db, zone_code)
            if not zone:
                return {
                    "available": False,
                    "error": "Zone not found"
                }
            
            service_zone = db.query(ServiceZone).filter(
                ServiceZone.service_id == service.id,
                ServiceZone.zone_id == zone.id,
                ServiceZone.is_available == True
            ).first()
            
            if not service_zone:
                # Check parent zones
                parent_zones = await self.zone_service.get_zone_hierarchy(db, zone.id)
                for parent_zone in parent_zones:
                    parent_service_zone = db.query(ServiceZone).filter(
                        ServiceZone.service_id == service.id,
                        ServiceZone.zone_id == parent_zone.id,
                        ServiceZone.is_available == True
                    ).first()
                    
                    if parent_service_zone:
                        service_zone = parent_service_zone
                        break
            
            if not service_zone:
                return {
                    "available": False,
                    "error": "Service not available in this zone",
                    "service": service,
                    "zone": zone
                }
            
            return {
                "available": True,
                "service": service,
                "zone": zone,
                "service_zone": service_zone,
                "estimated_price": self._calculate_zone_price(service, service_zone),
                "estimated_duration": service.estimated_duration_minutes + (service_zone.estimated_travel_time_minutes or 0)
            }
            
        except Exception as e:
            logger.error(f"Error validating service availability: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    async def find_service_by_code(self, db: Session, code: str) -> Optional[Service]:
        """Find service by code with caching"""
        if code in self.service_cache:
            return self.service_cache[code]
        
        service = db.query(Service).filter(Service.code == code).first()
        if service:
            self.service_cache[code] = service
        
        return service
    
    async def get_services_by_category(
        self, 
        db: Session, 
        category_id: int,
        zone_code: Optional[str] = None
    ) -> List[Service]:
        """Get all services in a category"""
        try:
            filters = [
                Service.category_id == category_id,
                Service.status == ServiceStatus.AVAILABLE
            ]
            
            if zone_code:
                zone = await self.zone_service.find_zone_by_code(db, zone_code)
                if zone:
                    zone_service_ids = db.query(ServiceZone.service_id).filter(
                        ServiceZone.zone_id == zone.id,
                        ServiceZone.is_available == True
                    ).subquery()
                    
                    filters.append(Service.id.in_(zone_service_ids))
            
            services = db.query(Service).filter(and_(*filters)).order_by(
                desc(Service.avg_rating), desc(Service.total_bookings)
            ).all()
            
            return services
            
        except Exception as e:
            logger.error(f"Error getting services by category: {e}")
            return []
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for searching"""
        if not text:
            return ""
        
        # Remove accents and convert to lowercase
        normalized = unidecode(text.lower())
        
        # Remove special characters except spaces and dashes
        normalized = re.sub(r'[^a-z0-9\s\-]', '', normalized)
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _generate_search_keywords(self, service: Service) -> List[str]:
        """Generate search keywords for a service"""
        keywords = []
        
        # Add service name variations
        if service.name:
            keywords.append(service.name.lower())
            keywords.extend(service.name.lower().split())
        
        # Add synonyms based on service type
        for service_type, synonyms in self.service_synonyms.items():
            if service_type in service.name.lower():
                keywords.extend(synonyms)
        
        # Add category-based keywords
        if service.category:
            keywords.append(service.category.name.lower())
            if service.category.search_keywords:
                keywords.extend(service.category.search_keywords)
        
        # Remove duplicates and normalize
        unique_keywords = list(set(self._normalize_text(keyword) for keyword in keywords))
        
        return [kw for kw in unique_keywords if kw]
    
    def _calculate_service_relevance_score(self, service: Service, normalized_query: str, original_query: str) -> float:
        """Calculate relevance score for service search result"""
        score = 0.0
        
        # Direct name match (highest priority)
        if normalized_query in self._normalize_text(service.name):
            score += 10.0
        
        # Code match
        if normalized_query in service.code.lower():
            score += 9.0
        
        # Description match
        if service.description and normalized_query in self._normalize_text(service.description):
            score += 7.0
        
        # Keywords match
        if service.search_keywords:
            keywords = service.search_keywords if isinstance(service.search_keywords, list) else []
            for keyword in keywords:
                if normalized_query in self._normalize_text(keyword):
                    score += 6.0
        
        # Synonyms match
        if service.synonyms:
            synonyms = service.synonyms if isinstance(service.synonyms, list) else []
            for synonym in synonyms:
                if normalized_query in self._normalize_text(synonym):
                    score += 5.0
        
        # Tags match
        if service.tags:
            tags = service.tags if isinstance(service.tags, list) else []
            for tag in tags:
                if normalized_query in self._normalize_text(tag):
                    score += 4.0
        
        # Partial word matches
        service_words = self._normalize_text(service.name).split()
        query_words = normalized_query.split()
        
        for query_word in query_words:
            for service_word in service_words:
                if query_word in service_word or service_word in query_word:
                    score += 3.0
        
        # Boost score based on service quality
        score += service.avg_rating * 0.5
        score += min(service.total_bookings / 100, 2.0)  # Up to 2 points for popularity
        
        return score
    
    def _get_service_match_type(self, service: Service, query: str) -> str:
        """Determine the type of match"""
        if query in service.code.lower():
            return "code"
        elif query in self._normalize_text(service.name):
            return "name"
        elif service.description and query in self._normalize_text(service.description):
            return "description"
        else:
            return "keyword"
    
    def _calculate_zone_price(self, service: Service, service_zone: ServiceZone) -> Dict[str, float]:
        """Calculate price for service in specific zone"""
        base_price = service.base_price_xaf or 0
        adjustment = service_zone.price_adjustment_percent or 0
        additional_cost = service_zone.additional_cost_xaf or 0
        
        adjusted_price = base_price * (1 + adjustment / 100) + additional_cost
        
        return {
            "base_price": base_price,
            "adjusted_price": adjusted_price,
            "additional_cost": additional_cost,
            "min_price": service.min_price_xaf or adjusted_price,
            "max_price": service.max_price_xaf or adjusted_price * 2
        }
    
    async def _search_by_synonyms(
        self, 
        db: Session, 
        query: str, 
        zone_code: Optional[str] = None,
        language: str = "fr"
    ) -> List[Dict[str, Any]]:
        """Search services using synonyms"""
        results = []
        
        for service_type, synonyms in self.service_synonyms.items():
            for synonym in synonyms:
                if synonym in query.lower():
                    # Search for services of this type
                    type_results = await self.search_services(
                        db, service_type, zone_code, None, language, 3
                    )
                    
                    for result in type_results:
                        result["match_type"] = "synonym"
                        result["synonym_used"] = synonym
                        results.append(result)
        
        return results
    
    async def _get_synonym_suggestions(
        self, 
        db: Session, 
        query: str, 
        zone_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get suggestions based on synonyms"""
        suggestions = []
        
        for service_type, synonyms in self.service_synonyms.items():
            for synonym in synonyms:
                similarity = SequenceMatcher(None, query.lower(), synonym).ratio()
                if similarity > 0.6:
                    type_services = await self.search_services(db, service_type, zone_code, None, "fr", 2)
                    
                    for result in type_services:
                        suggestions.append({
                            "service": result["service"],
                            "similarity": similarity,
                            "reason": f"synonym_match_{synonym}"
                        })
        
        return suggestions
    
    async def _log_search(
        self, 
        db: Session, 
        query: str, 
        zone_code: Optional[str] = None,
        language: str = "fr"
    ):
        """Log search query for analytics"""
        try:
            zone_id = None
            if zone_code:
                zone = await self.zone_service.find_zone_by_code(db, zone_code)
                if zone:
                    zone_id = zone.id
            
            search_log = ServiceSearchLog(
                query=query,
                zone_id=zone_id,
                language=language,
                was_successful=False  # Will be updated if match found
            )
            
            db.add(search_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging search: {e}")
            db.rollback()