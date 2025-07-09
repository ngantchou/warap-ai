"""
Zone Service - Geographic zone management with hierarchical structure
Handles zone creation, search, and geographic matching
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import logging
from geopy.distance import geodesic
import re
from unidecode import unidecode
import json

from app.models.dynamic_services import Zone, ZoneType

logger = logging.getLogger(__name__)

class ZoneService:
    """Service for managing geographic zones with hierarchical structure"""
    
    def __init__(self):
        self.zone_cache: Dict[str, Zone] = {}
        self.hierarchy_cache: Dict[int, List[Zone]] = {}
        
    async def create_zone(
        self, 
        db: Session, 
        code: str, 
        name: str, 
        zone_type: ZoneType, 
        parent_id: Optional[int] = None,
        **kwargs
    ) -> Zone:
        """Create a new geographic zone"""
        try:
            # Calculate level and full path
            level = 0
            full_path = f"/{code}"
            
            if parent_id:
                parent = db.query(Zone).filter(Zone.id == parent_id).first()
                if parent:
                    level = parent.level + 1
                    full_path = f"{parent.full_path}/{code}"
            
            zone = Zone(
                code=code,
                name=name,
                zone_type=zone_type.value,
                parent_id=parent_id,
                level=level,
                full_path=full_path,
                **kwargs
            )
            
            db.add(zone)
            db.commit()
            
            # Update cache
            self.zone_cache[code] = zone
            self._update_hierarchy_cache(db)
            
            logger.info(f"Created zone: {code} ({name})")
            return zone
            
        except Exception as e:
            logger.error(f"Error creating zone: {e}")
            db.rollback()
            raise
    
    async def find_zone_by_code(self, db: Session, code: str) -> Optional[Zone]:
        """Find zone by code with caching"""
        if code in self.zone_cache:
            return self.zone_cache[code]
        
        zone = db.query(Zone).filter(Zone.code == code, Zone.is_active == True).first()
        if zone:
            self.zone_cache[code] = zone
        
        return zone
    
    async def search_zones(
        self, 
        db: Session, 
        query: str, 
        zone_type: Optional[ZoneType] = None,
        parent_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search zones with fuzzy matching"""
        try:
            # Normalize query
            normalized_query = self._normalize_text(query)
            
            # Build search filters
            filters = [Zone.is_active == True]
            
            if zone_type:
                filters.append(Zone.zone_type == zone_type.value)
            
            if parent_id:
                filters.append(Zone.parent_id == parent_id)
            
            # Search in multiple fields
            search_conditions = []
            
            # Direct name match
            search_conditions.append(
                func.lower(Zone.name).ilike(f"%{normalized_query}%")
            )
            
            # French name match
            search_conditions.append(
                func.lower(Zone.name_fr).ilike(f"%{normalized_query}%")
            )
            
            # English name match
            search_conditions.append(
                func.lower(Zone.name_en).ilike(f"%{normalized_query}%")
            )
            
            # Code match
            search_conditions.append(
                func.lower(Zone.code).ilike(f"%{normalized_query}%")
            )
            
            # Execute search
            zones = db.query(Zone).filter(
                and_(*filters),
                or_(*search_conditions)
            ).limit(limit).all()
            
            # Calculate relevance scores
            results = []
            for zone in zones:
                score = self._calculate_relevance_score(zone, normalized_query)
                results.append({
                    "zone": zone,
                    "relevance_score": score,
                    "match_type": self._get_match_type(zone, normalized_query)
                })
            
            # Sort by relevance score
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            logger.info(f"Found {len(results)} zones for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching zones: {e}")
            return []
    
    async def get_zone_hierarchy(self, db: Session, zone_id: int) -> List[Zone]:
        """Get complete hierarchy path for a zone"""
        try:
            hierarchy = []
            zone = db.query(Zone).filter(Zone.id == zone_id).first()
            
            while zone:
                hierarchy.insert(0, zone)
                if zone.parent_id:
                    zone = db.query(Zone).filter(Zone.id == zone.parent_id).first()
                else:
                    break
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error getting zone hierarchy: {e}")
            return []
    
    async def get_child_zones(
        self, 
        db: Session, 
        parent_id: int, 
        recursive: bool = False
    ) -> List[Zone]:
        """Get child zones with optional recursion"""
        try:
            children = db.query(Zone).filter(
                Zone.parent_id == parent_id,
                Zone.is_active == True
            ).all()
            
            if recursive:
                all_children = children.copy()
                for child in children:
                    grandchildren = await self.get_child_zones(db, child.id, recursive=True)
                    all_children.extend(grandchildren)
                return all_children
            
            return children
            
        except Exception as e:
            logger.error(f"Error getting child zones: {e}")
            return []
    
    async def find_nearest_zones(
        self, 
        db: Session, 
        latitude: float, 
        longitude: float, 
        radius_km: float = 10,
        zone_type: Optional[ZoneType] = None
    ) -> List[Dict[str, Any]]:
        """Find zones within specified radius"""
        try:
            filters = [
                Zone.is_active == True,
                Zone.latitude.isnot(None),
                Zone.longitude.isnot(None)
            ]
            
            if zone_type:
                filters.append(Zone.zone_type == zone_type.value)
            
            zones = db.query(Zone).filter(and_(*filters)).all()
            
            results = []
            for zone in zones:
                distance = geodesic(
                    (latitude, longitude),
                    (zone.latitude, zone.longitude)
                ).kilometers
                
                if distance <= radius_km:
                    results.append({
                        "zone": zone,
                        "distance_km": distance,
                        "within_radius": distance <= (zone.radius_km or 0)
                    })
            
            # Sort by distance
            results.sort(key=lambda x: x["distance_km"])
            
            logger.info(f"Found {len(results)} zones within {radius_km}km")
            return results
            
        except Exception as e:
            logger.error(f"Error finding nearest zones: {e}")
            return []
    
    async def validate_zone_coverage(
        self, 
        db: Session, 
        zone_code: str, 
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """Validate if a location is within zone coverage"""
        try:
            zone = await self.find_zone_by_code(db, zone_code)
            if not zone:
                return {
                    "valid": False,
                    "error": "Zone not found",
                    "suggestions": await self._get_zone_suggestions(db, zone_code)
                }
            
            if not zone.is_active:
                return {
                    "valid": False,
                    "error": "Zone is not active",
                    "zone": zone
                }
            
            # Check geographic coverage if coordinates provided
            if latitude and longitude and zone.latitude and zone.longitude:
                distance = geodesic(
                    (latitude, longitude),
                    (zone.latitude, zone.longitude)
                ).kilometers
                
                within_radius = distance <= (zone.radius_km or 10)
                
                return {
                    "valid": within_radius,
                    "distance_km": distance,
                    "zone": zone,
                    "within_radius": within_radius
                }
            
            return {
                "valid": True,
                "zone": zone
            }
            
        except Exception as e:
            logger.error(f"Error validating zone coverage: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
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
    
    def _calculate_relevance_score(self, zone: Zone, query: str) -> float:
        """Calculate relevance score for search result"""
        score = 0.0
        
        # Direct name match (highest priority)
        if query in self._normalize_text(zone.name):
            score += 10.0
        
        # Code match
        if query in zone.code.lower():
            score += 8.0
        
        # French name match
        if zone.name_fr and query in self._normalize_text(zone.name_fr):
            score += 7.0
        
        # English name match
        if zone.name_en and query in self._normalize_text(zone.name_en):
            score += 6.0
        
        # Keywords match
        if zone.search_keywords:
            keywords = zone.search_keywords if isinstance(zone.search_keywords, list) else []
            for keyword in keywords:
                if query in self._normalize_text(keyword):
                    score += 5.0
        
        # Partial matches
        zone_words = self._normalize_text(zone.name).split()
        query_words = query.split()
        
        for query_word in query_words:
            for zone_word in zone_words:
                if query_word in zone_word or zone_word in query_word:
                    score += 2.0
        
        return score
    
    def _get_match_type(self, zone: Zone, query: str) -> str:
        """Determine the type of match"""
        if query in zone.code.lower():
            return "code"
        elif query in self._normalize_text(zone.name):
            return "name"
        elif zone.name_fr and query in self._normalize_text(zone.name_fr):
            return "name_fr"
        elif zone.name_en and query in self._normalize_text(zone.name_en):
            return "name_en"
        else:
            return "keyword"
    
    async def _get_zone_suggestions(self, db: Session, query: str) -> List[Dict[str, Any]]:
        """Get zone suggestions for failed matches"""
        suggestions = await self.search_zones(db, query, limit=5)
        return [
            {
                "code": result["zone"].code,
                "name": result["zone"].name,
                "type": result["zone"].zone_type,
                "score": result["relevance_score"]
            }
            for result in suggestions
        ]
    
    def _update_hierarchy_cache(self, db: Session):
        """Update hierarchy cache"""
        try:
            # Clear existing cache
            self.hierarchy_cache.clear()
            
            # Rebuild cache
            zones = db.query(Zone).filter(Zone.is_active == True).all()
            for zone in zones:
                if zone.parent_id:
                    if zone.parent_id not in self.hierarchy_cache:
                        self.hierarchy_cache[zone.parent_id] = []
                    self.hierarchy_cache[zone.parent_id].append(zone)
            
        except Exception as e:
            logger.error(f"Error updating hierarchy cache: {e}")