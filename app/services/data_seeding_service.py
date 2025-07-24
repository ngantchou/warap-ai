"""
Data Seeding Service for Dynamic Services System
Seeds initial data for zones, service categories, and services
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Any
import logging
from datetime import datetime

from app.models.dynamic_services import (
    Zone, ServiceCategory, Service, ServiceZone,
    ZoneType, ServiceStatus
)
from app.services.zone_service import ZoneService
from app.services.service_management_service import ServiceManagementService

logger = logging.getLogger(__name__)

class DataSeedingService:
    """Service for seeding initial data into the dynamic services system"""
    
    def __init__(self):
        self.zone_service = ZoneService()
        self.service_management = ServiceManagementService()
    
    async def seed_all_data(self, db: Session) -> Dict[str, Any]:
        """Seed all initial data"""
        try:
            results = {}
            
            # Seed zones
            results["zones"] = await self.seed_zones(db)
            
            # Seed service categories
            results["categories"] = await self.seed_service_categories(db)
            
            # Seed services
            results["services"] = await self.seed_services(db)
            
            # Seed service zones
            results["service_zones"] = await self.seed_service_zones(db)
            
            logger.info("All data seeding completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error seeding data: {e}")
            raise
    
    async def seed_zones(self, db: Session) -> Dict[str, Any]:
        """Seed geographic zones for Cameroon/Douala"""
        try:
            zones_data = [
                # Country level
                {
                    "code": "cm",
                    "name": "Cameroun",
                    "name_fr": "Cameroun",
                    "name_en": "Cameroon",
                    "zone_type": ZoneType.COUNTRY,
                    "latitude": 7.3697,
                    "longitude": 12.3547,
                    "radius_km": 500,
                    "search_keywords": ["cameroun", "cameroon", "cm"],
                    "population": 27914536,
                    "area_km2": 475440
                },
                # Region level
                {
                    "code": "littoral",
                    "name": "Littoral",
                    "name_fr": "Littoral",
                    "name_en": "Littoral",
                    "zone_type": ZoneType.REGION,
                    "parent_code": "cm",
                    "latitude": 4.0511,
                    "longitude": 9.7679,
                    "radius_km": 100,
                    "search_keywords": ["littoral", "region littorale"],
                    "population": 3173800,
                    "area_km2": 20248
                },
                # City level
                {
                    "code": "douala",
                    "name": "Douala",
                    "name_fr": "Douala",
                    "name_en": "Douala",
                    "zone_type": ZoneType.CITY,
                    "parent_code": "littoral",
                    "latitude": 4.0511,
                    "longitude": 9.7679,
                    "radius_km": 50,
                    "search_keywords": ["douala", "dla", "ville de douala"],
                    "population": 3663000,
                    "area_km2": 923
                },
                # Districts
                {
                    "code": "bonamoussadi",
                    "name": "Bonamoussadi",
                    "name_fr": "Bonamoussadi",
                    "name_en": "Bonamoussadi",
                    "zone_type": ZoneType.DISTRICT,
                    "parent_code": "douala",
                    "latitude": 4.0764,
                    "longitude": 9.7323,
                    "radius_km": 5,
                    "search_keywords": ["bonamoussadi", "bona", "bonamussadi"],
                    "population": 85000,
                    "area_km2": 15
                },
                {
                    "code": "akwa",
                    "name": "Akwa",
                    "name_fr": "Akwa",
                    "name_en": "Akwa",
                    "zone_type": ZoneType.DISTRICT,
                    "parent_code": "douala",
                    "latitude": 4.0511,
                    "longitude": 9.7679,
                    "radius_km": 3,
                    "search_keywords": ["akwa", "centre ville"],
                    "population": 120000,
                    "area_km2": 10
                },
                {
                    "code": "bonaberi",
                    "name": "Bonabéri",
                    "name_fr": "Bonabéri",
                    "name_en": "Bonaberi",
                    "zone_type": ZoneType.DISTRICT,
                    "parent_code": "douala",
                    "latitude": 4.0292,
                    "longitude": 9.7014,
                    "radius_km": 4,
                    "search_keywords": ["bonaberi", "bonabéri", "bona"],
                    "population": 95000,
                    "area_km2": 12
                },
                {
                    "code": "deido",
                    "name": "Deido",
                    "name_fr": "Deido",
                    "name_en": "Deido",
                    "zone_type": ZoneType.DISTRICT,
                    "parent_code": "douala",
                    "latitude": 4.0669,
                    "longitude": 9.7447,
                    "radius_km": 3,
                    "search_keywords": ["deido", "deïdo"],
                    "population": 78000,
                    "area_km2": 8
                }
            ]
            
            created_zones = []
            zone_id_map = {}
            
            for zone_data in zones_data:
                # Get parent_id if parent_code exists
                parent_id = None
                if "parent_code" in zone_data:
                    parent_id = zone_id_map.get(zone_data["parent_code"])
                    del zone_data["parent_code"]
                
                # Check if zone already exists
                existing_zone = await self.zone_service.find_zone_by_code(db, zone_data["code"])
                if existing_zone:
                    zone_id_map[zone_data["code"]] = existing_zone.id
                    continue
                
                zone = await self.zone_service.create_zone(
                    db=db,
                    parent_id=parent_id,
                    **zone_data
                )
                
                created_zones.append(zone)
                zone_id_map[zone.code] = zone.id
            
            logger.info(f"Created {len(created_zones)} zones")
            return {
                "created_count": len(created_zones),
                "zone_codes": [zone.code for zone in created_zones]
            }
            
        except Exception as e:
            logger.error(f"Error seeding zones: {e}")
            raise
    
    async def seed_service_categories(self, db: Session) -> Dict[str, Any]:
        """Seed service categories"""
        try:
            categories_data = [
                # Top-level categories
                {
                    "code": "maintenance",
                    "name": "Maintenance et Réparation",
                    "name_fr": "Maintenance et Réparation",
                    "name_en": "Maintenance and Repair",
                    "description": "Services de maintenance et réparation pour la maison",
                    "icon": "🔧",
                    "color": "#3B82F6",
                    "search_keywords": ["maintenance", "réparation", "repair", "fix"]
                },
                {
                    "code": "cleaning",
                    "name": "Nettoyage et Entretien",
                    "name_fr": "Nettoyage et Entretien",
                    "name_en": "Cleaning and Maintenance",
                    "description": "Services de nettoyage et d'entretien domestique",
                    "icon": "🧽",
                    "color": "#10B981",
                    "search_keywords": ["nettoyage", "ménage", "cleaning", "entretien"]
                },
                {
                    "code": "security",
                    "name": "Sécurité et Surveillance",
                    "name_fr": "Sécurité et Surveillance",
                    "name_en": "Security and Surveillance",
                    "description": "Services de sécurité et surveillance",
                    "icon": "🛡️",
                    "color": "#EF4444",
                    "search_keywords": ["sécurité", "surveillance", "security", "gardien"]
                },
                {
                    "code": "transport",
                    "name": "Transport et Livraison",
                    "name_fr": "Transport et Livraison",
                    "name_en": "Transport and Delivery",
                    "description": "Services de transport et livraison",
                    "icon": "🚗",
                    "color": "#F59E0B",
                    "search_keywords": ["transport", "livraison", "delivery", "taxi"]
                },
                # Sub-categories for maintenance
                {
                    "code": "plumbing",
                    "name": "Plomberie",
                    "name_fr": "Plomberie",
                    "name_en": "Plumbing",
                    "parent_code": "maintenance",
                    "description": "Services de plomberie et installation sanitaire",
                    "icon": "🚰",
                    "color": "#0EA5E9",
                    "base_price_xaf": 5000,
                    "avg_duration_minutes": 120,
                    "search_keywords": ["plomberie", "plombier", "eau", "tuyau", "robinet"]
                },
                {
                    "code": "electrical",
                    "name": "Électricité",
                    "name_fr": "Électricité",
                    "name_en": "Electrical",
                    "parent_code": "maintenance",
                    "description": "Services d'électricité et installation électrique",
                    "icon": "⚡",
                    "color": "#F59E0B",
                    "base_price_xaf": 3000,
                    "avg_duration_minutes": 90,
                    "search_keywords": ["électricité", "électricien", "courant", "prise", "câble"]
                },
                {
                    "code": "appliance",
                    "name": "Électroménager",
                    "name_fr": "Électroménager",
                    "name_en": "Appliance Repair",
                    "parent_code": "maintenance",
                    "description": "Réparation d'appareils électroménagers",
                    "icon": "🔌",
                    "color": "#8B5CF6",
                    "base_price_xaf": 2000,
                    "avg_duration_minutes": 60,
                    "search_keywords": ["électroménager", "frigo", "télé", "machine", "réparation"]
                }
            ]
            
            created_categories = []
            category_id_map = {}
            
            for category_data in categories_data:
                # Get parent_id if parent_code exists
                parent_id = None
                if "parent_code" in category_data:
                    parent_id = category_id_map.get(category_data["parent_code"])
                    del category_data["parent_code"]
                
                # Check if category already exists
                existing_category = db.query(ServiceCategory).filter(
                    ServiceCategory.code == category_data["code"]
                ).first()
                if existing_category:
                    category_id_map[category_data["code"]] = existing_category.id
                    continue
                
                # Calculate level and full path
                level = 0
                full_path = f"/{category_data['code']}"
                
                if parent_id:
                    parent = db.query(ServiceCategory).filter(
                        ServiceCategory.id == parent_id
                    ).first()
                    if parent:
                        level = parent.level + 1
                        full_path = f"{parent.full_path}/{category_data['code']}"
                
                category = ServiceCategory(
                    **category_data,
                    parent_id=parent_id,
                    level=level,
                    full_path=full_path
                )
                
                db.add(category)
                db.commit()
                
                created_categories.append(category)
                category_id_map[category.code] = category.id
            
            logger.info(f"Created {len(created_categories)} service categories")
            return {
                "created_count": len(created_categories),
                "category_codes": [cat.code for cat in created_categories]
            }
            
        except Exception as e:
            logger.error(f"Error seeding service categories: {e}")
            raise
    
    async def seed_services(self, db: Session) -> Dict[str, Any]:
        """Seed individual services"""
        try:
            # Get categories
            plumbing_cat = db.query(ServiceCategory).filter(ServiceCategory.code == "plumbing").first()
            electrical_cat = db.query(ServiceCategory).filter(ServiceCategory.code == "electrical").first()
            appliance_cat = db.query(ServiceCategory).filter(ServiceCategory.code == "appliance").first()
            
            if not all([plumbing_cat, electrical_cat, appliance_cat]):
                raise Exception("Service categories not found. Please seed categories first.")
            
            services_data = [
                # Plumbing services
                {
                    "code": "plumbing_leak_repair",
                    "name": "Réparation de fuite d'eau",
                    "name_fr": "Réparation de fuite d'eau",
                    "name_en": "Water Leak Repair",
                    "category_id": plumbing_cat.id,
                    "description": "Réparation de fuites d'eau dans les tuyaux, robinets et joints",
                    "base_price_xaf": 8000,
                    "min_price_xaf": 5000,
                    "max_price_xaf": 15000,
                    "estimated_duration_minutes": 90,
                    "requires_materials": True,
                    "is_emergency_service": True,
                    "search_keywords": ["fuite", "eau", "tuyau", "robinet", "joint"],
                    "synonyms": ["fuite d'eau", "coule-coule", "eau qui coule"],
                    "tags": ["urgent", "eau", "maison"]
                },
                {
                    "code": "plumbing_drain_cleaning",
                    "name": "Débouchage de canalisation",
                    "name_fr": "Débouchage de canalisation",
                    "name_en": "Drain Cleaning",
                    "category_id": plumbing_cat.id,
                    "description": "Débouchage de canalisations et évacuations bouchées",
                    "base_price_xaf": 6000,
                    "min_price_xaf": 4000,
                    "max_price_xaf": 12000,
                    "estimated_duration_minutes": 60,
                    "requires_materials": True,
                    "search_keywords": ["débouchage", "canalisation", "évier", "wc", "toilette"],
                    "synonyms": ["déboucher", "canalisation bouchée", "évacuation"],
                    "tags": ["sanitaire", "urgent"]
                },
                {
                    "code": "plumbing_installation",
                    "name": "Installation sanitaire",
                    "name_fr": "Installation sanitaire",
                    "name_en": "Plumbing Installation",
                    "category_id": plumbing_cat.id,
                    "description": "Installation de nouveaux équipements sanitaires",
                    "base_price_xaf": 12000,
                    "min_price_xaf": 8000,
                    "max_price_xaf": 25000,
                    "estimated_duration_minutes": 180,
                    "requires_materials": True,
                    "requires_quote": True,
                    "search_keywords": ["installation", "sanitaire", "lavabo", "douche", "wc"],
                    "synonyms": ["installer", "nouveau", "équipement"],
                    "tags": ["installation", "neuf"]
                },
                # Electrical services
                {
                    "code": "electrical_wiring",
                    "name": "Installation électrique",
                    "name_fr": "Installation électrique",
                    "name_en": "Electrical Wiring",
                    "category_id": electrical_cat.id,
                    "description": "Installation et réparation de câblage électrique",
                    "base_price_xaf": 5000,
                    "min_price_xaf": 3000,
                    "max_price_xaf": 15000,
                    "estimated_duration_minutes": 120,
                    "requires_materials": True,
                    "requires_quote": True,
                    "search_keywords": ["câblage", "fil", "prise", "interrupteur", "installation"],
                    "synonyms": ["câble", "électricité", "courant", "prise électrique"],
                    "tags": ["électricité", "installation"]
                },
                {
                    "code": "electrical_power_outage",
                    "name": "Panne de courant",
                    "name_fr": "Panne de courant",
                    "name_en": "Power Outage Repair",
                    "category_id": electrical_cat.id,
                    "description": "Diagnostic et réparation de pannes électriques",
                    "base_price_xaf": 4000,
                    "min_price_xaf": 2000,
                    "max_price_xaf": 10000,
                    "estimated_duration_minutes": 90,
                    "requires_materials": True,
                    "is_emergency_service": True,
                    "search_keywords": ["panne", "courant", "électricité", "disjoncteur", "court-circuit"],
                    "synonyms": ["plus de courant", "light don go", "courant a jump"],
                    "tags": ["urgent", "électricité"]
                },
                # Appliance services
                {
                    "code": "appliance_fridge_repair",
                    "name": "Réparation de réfrigérateur",
                    "name_fr": "Réparation de réfrigérateur",
                    "name_en": "Refrigerator Repair",
                    "category_id": appliance_cat.id,
                    "description": "Réparation de réfrigérateurs et congélateurs",
                    "base_price_xaf": 3000,
                    "min_price_xaf": 2000,
                    "max_price_xaf": 8000,
                    "estimated_duration_minutes": 60,
                    "requires_materials": True,
                    "search_keywords": ["frigo", "réfrigérateur", "congélateur", "froid"],
                    "synonyms": ["frigidaire", "frigo cassé", "réfrigérateur en panne"],
                    "tags": ["électroménager", "froid"]
                },
                {
                    "code": "appliance_tv_repair",
                    "name": "Réparation de télévision",
                    "name_fr": "Réparation de télévision",
                    "name_en": "Television Repair",
                    "category_id": appliance_cat.id,
                    "description": "Réparation de téléviseurs et écrans",
                    "base_price_xaf": 2500,
                    "min_price_xaf": 1500,
                    "max_price_xaf": 6000,
                    "estimated_duration_minutes": 45,
                    "requires_materials": True,
                    "search_keywords": ["télé", "télévision", "écran", "tv"],
                    "synonyms": ["télé cassée", "écran noir", "tv en panne"],
                    "tags": ["électroménager", "écran"]
                }
            ]
            
            created_services = []
            
            for service_data in services_data:
                # Check if service already exists
                existing_service = await self.service_management.find_service_by_code(
                    db, service_data["code"]
                )
                if existing_service:
                    continue
                
                service = await self.service_management.create_service(db, **service_data)
                created_services.append(service)
            
            logger.info(f"Created {len(created_services)} services")
            return {
                "created_count": len(created_services),
                "service_codes": [service.code for service in created_services]
            }
            
        except Exception as e:
            logger.error(f"Error seeding services: {e}")
            raise
    
    async def seed_service_zones(self, db: Session) -> Dict[str, Any]:
        """Seed service zone relationships"""
        try:
            # Get zones
            douala_zone = await self.zone_service.find_zone_by_code(db, "douala")
            bonamoussadi_zone = await self.zone_service.find_zone_by_code(db, "bonamoussadi")
            
            if not all([douala_zone, bonamoussadi_zone]):
                raise Exception("Required zones not found. Please seed zones first.")
            
            # Get all services
            services = db.query(Service).all()
            
            service_zones_data = []
            
            for service in services:
                # All services available in Douala
                service_zones_data.append({
                    "service_id": service.id,
                    "zone_id": douala_zone.id,
                    "is_available": True,
                    "price_adjustment_percent": 0.0,
                    "estimated_travel_time_minutes": 30,
                    "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
                    "available_hours": {"start": "07:00", "end": "19:00"}
                })
                
                # All services available in Bonamoussadi with special focus
                service_zones_data.append({
                    "service_id": service.id,
                    "zone_id": bonamoussadi_zone.id,
                    "is_available": True,
                    "price_adjustment_percent": -5.0,  # 5% discount for Bonamoussadi
                    "estimated_travel_time_minutes": 15,
                    "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                    "available_hours": {"start": "06:00", "end": "20:00"}
                })
            
            created_service_zones = []
            
            for sz_data in service_zones_data:
                # Check if service zone already exists
                existing_sz = db.query(ServiceZone).filter(
                    ServiceZone.service_id == sz_data["service_id"],
                    ServiceZone.zone_id == sz_data["zone_id"]
                ).first()
                
                if existing_sz:
                    continue
                
                service_zone = ServiceZone(**sz_data)
                db.add(service_zone)
                created_service_zones.append(service_zone)
            
            db.commit()
            
            logger.info(f"Created {len(created_service_zones)} service zone relationships")
            return {
                "created_count": len(created_service_zones),
                "total_services": len(services),
                "zones_covered": ["douala", "bonamoussadi"]
            }
            
        except Exception as e:
            logger.error(f"Error seeding service zones: {e}")
            raise