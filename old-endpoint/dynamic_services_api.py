"""
Dynamic Services API - REST endpoints for dynamic services system
Provides admin interface for managing zones, services, and categories
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from app.database import get_db
from app.models.dynamic_services import Zone, Service, ServiceCategory, ZoneType, ServiceStatus
from app.services.zone_service import ZoneService
from app.services.service_management_service import ServiceManagementService
from app.services.dynamic_service_cache import DynamicServiceCache
from app.services.data_seeding_service import DataSeedingService
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dynamic-services", tags=["Dynamic Services"])

# Initialize services
zone_service = ZoneService()
service_management = ServiceManagementService()
cache_service = DynamicServiceCache()
data_seeding_service = DataSeedingService()

# Pydantic models for requests
class ZoneCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    name_fr: Optional[str] = None
    name_en: Optional[str] = None
    zone_type: ZoneType
    parent_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    search_keywords: Optional[List[str]] = None
    population: Optional[int] = None
    area_km2: Optional[float] = None

class ServiceCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    name_fr: Optional[str] = None
    name_en: Optional[str] = None
    category_id: int
    description: Optional[str] = None
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    base_price_xaf: Optional[float] = None
    min_price_xaf: Optional[float] = None
    max_price_xaf: Optional[float] = None
    estimated_duration_minutes: Optional[int] = None
    requires_materials: bool = False
    requires_quote: bool = False
    is_emergency_service: bool = False
    search_keywords: Optional[List[str]] = None
    synonyms: Optional[List[str]] = None
    tags: Optional[List[str]] = None

class ServiceCategoryCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    name_fr: Optional[str] = None
    name_en: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    description_en: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    search_keywords: Optional[List[str]] = None

# Zone endpoints
@router.post("/zones", response_model=dict)
async def create_zone(
    zone_data: ZoneCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new geographic zone"""
    try:
        # Check if zone code already exists
        existing_zone = await zone_service.find_zone_by_code(db, zone_data.code)
        if existing_zone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Zone with code '{zone_data.code}' already exists"
            )
        
        # Create zone
        zone_dict = zone_data.dict(exclude_unset=True)
        zone = await zone_service.create_zone(db, **zone_dict)
        
        # Invalidate cache
        await cache_service.invalidate_zone_cache()
        
        return {
            "success": True,
            "zone": {
                "id": zone.id,
                "code": zone.code,
                "name": zone.name,
                "zone_type": zone.zone_type,
                "level": zone.level,
                "full_path": zone.full_path,
                "created_at": zone.created_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating zone: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/zones/search")
async def search_zones(
    query: str = Query(..., min_length=1),
    zone_type: Optional[ZoneType] = None,
    parent_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Search zones with fuzzy matching"""
    try:
        results = await zone_service.search_zones(
            db, query, zone_type, parent_id, limit
        )
        
        return {
            "success": True,
            "results": [
                {
                    "zone": {
                        "id": result["zone"].id,
                        "code": result["zone"].code,
                        "name": result["zone"].name,
                        "zone_type": result["zone"].zone_type,
                        "level": result["zone"].level,
                        "full_path": result["zone"].full_path,
                        "latitude": result["zone"].latitude,
                        "longitude": result["zone"].longitude
                    },
                    "relevance_score": result["relevance_score"],
                    "match_type": result["match_type"]
                }
                for result in results
            ]
        }
        
    except Exception as e:
        logger.error(f"Error searching zones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/zones/{zone_id}/hierarchy")
async def get_zone_hierarchy(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """Get zone hierarchy"""
    try:
        # Check cache first
        cached_hierarchy = await cache_service.get_zone_hierarchy(zone_id)
        if cached_hierarchy:
            return {
                "success": True,
                "hierarchy": cached_hierarchy,
                "cached": True
            }
        
        hierarchy = await zone_service.get_zone_hierarchy(db, zone_id)
        
        hierarchy_data = [
            {
                "id": zone.id,
                "code": zone.code,
                "name": zone.name,
                "zone_type": zone.zone_type,
                "level": zone.level
            }
            for zone in hierarchy
        ]
        
        # Cache the result
        await cache_service.set_zone_hierarchy(zone_id, hierarchy_data)
        
        return {
            "success": True,
            "hierarchy": hierarchy_data,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Error getting zone hierarchy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/zones/{zone_id}/children")
async def get_zone_children(
    zone_id: int,
    recursive: bool = False,
    db: Session = Depends(get_db)
):
    """Get child zones"""
    try:
        children = await zone_service.get_child_zones(db, zone_id, recursive)
        
        return {
            "success": True,
            "children": [
                {
                    "id": child.id,
                    "code": child.code,
                    "name": child.name,
                    "zone_type": child.zone_type,
                    "level": child.level,
                    "full_path": child.full_path
                }
                for child in children
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting zone children: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Service endpoints
@router.post("/services", response_model=dict)
async def create_service(
    service_data: ServiceCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new service"""
    try:
        # Check if service code already exists
        existing_service = await service_management.find_service_by_code(db, service_data.code)
        if existing_service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Service with code '{service_data.code}' already exists"
            )
        
        # Create service
        service_dict = service_data.dict(exclude_unset=True)
        service = await service_management.create_service(db, **service_dict)
        
        # Invalidate cache
        await cache_service.invalidate_service_cache()
        
        return {
            "success": True,
            "service": {
                "id": service.id,
                "code": service.code,
                "name": service.name,
                "category_id": service.category_id,
                "status": service.status,
                "base_price_xaf": service.base_price_xaf,
                "estimated_duration_minutes": service.estimated_duration_minutes,
                "created_at": service.created_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/services/search")
async def search_services(
    query: str = Query(..., min_length=1),
    zone_code: Optional[str] = None,
    category_id: Optional[int] = None,
    language: str = Query("fr", regex="^(fr|en)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Search services with intelligent matching"""
    try:
        # Check cache first
        cached_results = await cache_service.get_service_search_results(
            query, zone_code
        )
        if cached_results:
            return {
                "success": True,
                "results": cached_results,
                "cached": True
            }
        
        results = await service_management.search_services(
            db, query, zone_code, category_id, language, limit
        )
        
        search_results = [
            {
                "service": {
                    "id": result["service"].id,
                    "code": result["service"].code,
                    "name": result["service"].name,
                    "description": result["service"].description,
                    "category_id": result["service"].category_id,
                    "base_price_xaf": result["service"].base_price_xaf,
                    "min_price_xaf": result["service"].min_price_xaf,
                    "max_price_xaf": result["service"].max_price_xaf,
                    "estimated_duration_minutes": result["service"].estimated_duration_minutes,
                    "avg_rating": result["service"].avg_rating,
                    "total_bookings": result["service"].total_bookings,
                    "status": result["service"].status
                },
                "relevance_score": result["relevance_score"],
                "match_type": result["match_type"],
                "confidence": result["confidence"]
            }
            for result in results
        ]
        
        # Cache the results
        await cache_service.set_service_search_results(
            query, search_results, zone_code
        )
        
        return {
            "success": True,
            "results": search_results,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Error searching services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/services/{service_code}/availability")
async def check_service_availability(
    service_code: str,
    zone_code: str,
    db: Session = Depends(get_db)
):
    """Check service availability in zone"""
    try:
        availability = await service_management.validate_service_availability(
            db, service_code, zone_code
        )
        
        return {
            "success": True,
            "availability": availability
        }
        
    except Exception as e:
        logger.error(f"Error checking service availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/services/suggestions")
async def get_service_suggestions(
    query: str = Query(..., min_length=1),
    zone_code: Optional[str] = None,
    language: str = Query("fr", regex="^(fr|en)$"),
    db: Session = Depends(get_db)
):
    """Get service suggestions for failed queries"""
    try:
        suggestions = await service_management.get_service_suggestions(
            db, query, zone_code, language
        )
        
        return {
            "success": True,
            "suggestions": [
                {
                    "service": {
                        "id": suggestion["service"].id,
                        "code": suggestion["service"].code,
                        "name": suggestion["service"].name,
                        "description": suggestion["service"].description,
                        "category_id": suggestion["service"].category_id
                    },
                    "similarity": suggestion["similarity"],
                    "reason": suggestion["reason"]
                }
                for suggestion in suggestions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting service suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Service category endpoints
@router.post("/categories", response_model=dict)
async def create_service_category(
    category_data: ServiceCategoryCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new service category"""
    try:
        # Check if category code already exists
        existing_category = db.query(ServiceCategory).filter(
            ServiceCategory.code == category_data.code
        ).first()
        
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with code '{category_data.code}' already exists"
            )
        
        # Calculate level and full path
        level = 0
        full_path = f"/{category_data.code}"
        
        if category_data.parent_id:
            parent = db.query(ServiceCategory).filter(
                ServiceCategory.id == category_data.parent_id
            ).first()
            if parent:
                level = parent.level + 1
                full_path = f"{parent.full_path}/{category_data.code}"
        
        category = ServiceCategory(
            **category_data.dict(exclude_unset=True),
            level=level,
            full_path=full_path
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        # Invalidate cache
        await cache_service.invalidate_service_cache()
        
        return {
            "success": True,
            "category": {
                "id": category.id,
                "code": category.code,
                "name": category.name,
                "level": category.level,
                "full_path": category.full_path,
                "created_at": category.created_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating service category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/categories")
async def get_service_categories(
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get service categories"""
    try:
        # Check cache first
        cached_categories = await cache_service.get_service_categories()
        if cached_categories and parent_id is None:
            return {
                "success": True,
                "categories": cached_categories,
                "cached": True
            }
        
        filters = [ServiceCategory.is_active == True]
        if parent_id is not None:
            filters.append(ServiceCategory.parent_id == parent_id)
        
        categories = db.query(ServiceCategory).filter(*filters).all()
        
        category_data = [
            {
                "id": category.id,
                "code": category.code,
                "name": category.name,
                "name_fr": category.name_fr,
                "name_en": category.name_en,
                "description": category.description,
                "level": category.level,
                "full_path": category.full_path,
                "icon": category.icon,
                "color": category.color,
                "base_price_xaf": category.base_price_xaf,
                "avg_duration_minutes": category.avg_duration_minutes
            }
            for category in categories
        ]
        
        # Cache all categories
        if parent_id is None:
            await cache_service.set_service_categories(category_data)
        
        return {
            "success": True,
            "categories": category_data,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Error getting service categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Cache management endpoints
@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = await cache_service.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/cache/clear")
async def clear_cache():
    """Clear all cache"""
    try:
        await cache_service.clear_all_cache()
        return {
            "success": True,
            "message": "Cache cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Analytics endpoints
@router.get("/analytics/search-logs")
async def get_search_analytics(
    limit: int = Query(100, ge=1, le=1000),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get search analytics"""
    try:
        from datetime import datetime, timedelta
        from app.models.dynamic_services import ServiceSearchLog
        
        since_date = datetime.now() - timedelta(days=days)
        
        search_logs = db.query(ServiceSearchLog).filter(
            ServiceSearchLog.created_at >= since_date
        ).order_by(ServiceSearchLog.created_at.desc()).limit(limit).all()
        
        return {
            "success": True,
            "search_logs": [
                {
                    "id": log.id,
                    "query": log.query,
                    "was_successful": log.was_successful,
                    "confidence_score": log.confidence_score,
                    "language": log.language,
                    "created_at": log.created_at
                }
                for log in search_logs
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting search analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Data seeding endpoints
@router.post("/seed/all")
async def seed_all_data(db: Session = Depends(get_db)):
    """Seed all initial data for the dynamic services system"""
    try:
        # Direct seeding without service layer to avoid session issues
        results = await _seed_zones_direct(db)
        
        return {
            "success": True,
            "message": "All data seeded successfully",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def _seed_zones_direct(db: Session) -> Dict[str, Any]:
    """Direct zone seeding without service layer"""
    zones_data = [
        {
            "code": "cm",
            "name": "Cameroun",
            "zone_type": ZoneType.COUNTRY,
            "latitude": 7.3697,
            "longitude": 12.3547,
            "radius_km": 500,
            "search_keywords": ["cameroun", "cameroon", "cm"],
            "population": 27914536,
            "area_km2": 475440
        },
        {
            "code": "littoral",
            "name": "Littoral",
            "zone_type": ZoneType.REGION,
            "latitude": 4.0511,
            "longitude": 9.7679,
            "radius_km": 100,
            "search_keywords": ["littoral", "region littorale"],
            "population": 3173800,
            "area_km2": 20248
        },
        {
            "code": "douala",
            "name": "Douala",
            "zone_type": ZoneType.CITY,
            "latitude": 4.0511,
            "longitude": 9.7679,
            "radius_km": 50,
            "search_keywords": ["douala", "dla", "ville de douala"],
            "population": 3663000,
            "area_km2": 923
        },
        {
            "code": "bonamoussadi",
            "name": "Bonamoussadi",
            "zone_type": ZoneType.DISTRICT,
            "latitude": 4.0764,
            "longitude": 9.7323,
            "radius_km": 5,
            "search_keywords": ["bonamoussadi", "bona", "bonamussadi"],
            "population": 85000,
            "area_km2": 15
        }
    ]
    
    created_zones = []
    zone_id_map = {}
    
    for zone_data in zones_data:
        # Check if zone already exists
        existing_zone = db.query(Zone).filter(Zone.code == zone_data["code"]).first()
        if existing_zone:
            zone_id_map[zone_data["code"]] = existing_zone.id
            continue
        
        # Set parent_id based on hierarchy
        parent_id = None
        if zone_data["code"] == "littoral":
            parent_id = zone_id_map.get("cm")
        elif zone_data["code"] == "douala":
            parent_id = zone_id_map.get("littoral")
        elif zone_data["code"] == "bonamoussadi":
            parent_id = zone_id_map.get("douala")
        
        zone = Zone(
            code=zone_data["code"],
            name=zone_data["name"],
            name_fr=zone_data["name"],
            name_en=zone_data["name"],
            zone_type=zone_data["zone_type"],
            parent_id=parent_id,
            latitude=zone_data["latitude"],
            longitude=zone_data["longitude"],
            radius_km=zone_data["radius_km"],
            search_keywords=zone_data["search_keywords"],
            population=zone_data["population"],
            area_km2=zone_data["area_km2"],
            level=0 if not parent_id else 1,
            full_path=f"/{zone_data['code']}",
            is_active=True
        )
        
        db.add(zone)
        created_zones.append(zone)
        zone_id_map[zone_data["code"]] = zone.id
    
    db.commit()
    
    return {
        "created_count": len(created_zones),
        "zone_codes": [zone.code for zone in created_zones]
    }

@router.get("/test/system")
async def test_system(db: Session = Depends(get_db)):
    """Test the dynamic services system"""
    try:
        # Test basic database connectivity
        zones = db.query(Zone).limit(5).all()
        categories = db.query(ServiceCategory).limit(5).all()
        services = db.query(Service).limit(5).all()
        
        return {
            "success": True,
            "test_results": {
                "database_connectivity": True,
                "zone_count": len(zones),
                "category_count": len(categories),
                "service_count": len(services),
                "zones": [{"code": z.code, "name": z.name} for z in zones],
                "categories": [{"code": c.code, "name": c.name} for c in categories],
                "services": [{"code": s.code, "name": s.name} for s in services]
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/seed/zones-simple")
async def seed_zones_simple(db: Session = Depends(get_db)):
    """Simple zone seeding without service layer"""
    try:
        # Check existing zones
        existing_zones = db.query(Zone).count()
        
        if existing_zones > 0:
            return {
                "success": True,
                "message": f"Zones already exist ({existing_zones} zones found)",
                "existing_zones": existing_zones
            }
        
        # Create zones directly
        zones_to_create = [
            Zone(
                code="bonamoussadi",
                name="Bonamoussadi",
                name_fr="Bonamoussadi",
                name_en="Bonamoussadi",
                zone_type=ZoneType.DISTRICT,
                latitude=4.0764,
                longitude=9.7323,
                radius_km=5,
                search_keywords=["bonamoussadi", "bona", "bonamussadi"],
                population=85000,
                area_km2=15,
                level=0,
                full_path="/bonamoussadi",
                is_active=True
            ),
            Zone(
                code="douala",
                name="Douala",
                name_fr="Douala",
                name_en="Douala",
                zone_type=ZoneType.CITY,
                latitude=4.0511,
                longitude=9.7679,
                radius_km=50,
                search_keywords=["douala", "dla", "ville de douala"],
                population=3663000,
                area_km2=923,
                level=0,
                full_path="/douala",
                is_active=True
            )
        ]
        
        for zone in zones_to_create:
            db.add(zone)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Zones created successfully",
            "created_count": len(zones_to_create),
            "zones": [{"code": z.code, "name": z.name} for z in zones_to_create]
        }
        
    except Exception as e:
        logger.error(f"Error seeding zones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )