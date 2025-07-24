#!/usr/bin/env python3
"""
Script to create service-zone relationships in the database.
This will make services available in specific zones.
"""

import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.insert(0, '/home/runner/Djobea-AI-Agent-Assistant/app')

from models.dynamic_services import ServiceZone
from models.database_models import SessionLocal

def create_service_zone_relationships():
    """Create service-zone relationships for testing"""
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get all zones and services
        zones_query = text("SELECT id, code, name FROM zones ORDER BY id")
        services_query = text("SELECT id, code, name FROM services ORDER BY id")
        
        zones = db.execute(zones_query).fetchall()
        services = db.execute(services_query).fetchall()
        
        print(f"Found {len(zones)} zones and {len(services)} services")
        
        # Create relationships - make all services available in all zones
        relationships_created = 0
        
        for zone in zones:
            for service in services:
                # Check if relationship already exists
                existing = db.execute(text("""
                    SELECT id FROM service_zones 
                    WHERE service_id = :service_id AND zone_id = :zone_id
                """), {
                    'service_id': service.id,
                    'zone_id': zone.id
                }).fetchone()
                
                if not existing:
                    # Create new relationship
                    db.execute(text("""
                        INSERT INTO service_zones (service_id, zone_id, is_available, demand_level, avg_response_time_minutes)
                        VALUES (:service_id, :zone_id, :is_available, :demand_level, :avg_response_time)
                    """), {
                        'service_id': service.id,
                        'zone_id': zone.id,
                        'is_available': True,
                        'demand_level': 'medium',
                        'avg_response_time': 30
                    })
                    relationships_created += 1
                    print(f"Created relationship: {service.name} -> {zone.name}")
        
        # Commit the changes
        db.commit()
        print(f"Successfully created {relationships_created} service-zone relationships")
        
        # Verify the relationships
        count_query = text("SELECT COUNT(*) FROM service_zones WHERE is_available = true")
        total_relationships = db.execute(count_query).scalar()
        print(f"Total active service-zone relationships: {total_relationships}")
        
    except Exception as e:
        print(f"Error creating service-zone relationships: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_service_zone_relationships()