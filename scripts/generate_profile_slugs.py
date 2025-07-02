"""
Generate public profile slugs for existing providers

This script creates SEO-friendly slugs for all providers and ensures they can be
accessed via public profile URLs.
"""

import os
import sys
import re
from pathlib import Path
from unidecode import unidecode

# Add parent directory to Python path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.database_models import Provider
from loguru import logger

def create_slug(name: str, service_type: str = "", location: str = "") -> str:
    """
    Create a SEO-friendly slug from provider name and details
    
    Args:
        name: Provider name
        service_type: Main service type
        location: Location/area
    
    Returns:
        SEO-friendly slug
    """
    # Combine name with service type and location for uniqueness
    slug_text = f"{name}"
    
    if service_type:
        # Extract main service (first word)
        main_service = service_type.split()[0].lower()
        if main_service in ["plomberie", "électricité", "électroménager"]:
            if main_service == "plomberie":
                slug_text += "-plombier"
            elif main_service == "électricité":
                slug_text += "-electricien" 
            elif main_service == "électroménager":
                slug_text += "-reparateur"
    
    if location and "bonamoussadi" in location.lower():
        slug_text += "-bonamoussadi"
    elif location and "douala" in location.lower():
        slug_text += "-douala"
    
    # Convert to ASCII and lowercase
    slug = unidecode.unidecode(slug_text).lower()
    
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug[:100]  # Limit length to database constraint

def ensure_unique_slug(db, base_slug: str, provider_id: int = None) -> str:
    """
    Ensure slug is unique by adding numbers if needed
    
    Args:
        db: Database session
        base_slug: Base slug to check
        provider_id: Current provider ID (to exclude from uniqueness check)
    
    Returns:
        Unique slug
    """
    slug = base_slug
    counter = 1
    
    while True:
        # Check if slug exists for a different provider
        query = db.query(Provider).filter(Provider.public_profile_slug == slug)
        if provider_id:
            query = query.filter(Provider.id != provider_id)
        
        existing = query.first()
        if not existing:
            return slug
        
        # Add counter and try again
        counter += 1
        slug = f"{base_slug}-{counter}"

def generate_profile_slugs():
    """Generate public profile slugs for all providers"""
    db = SessionLocal()
    
    try:
        # Get all providers without public profile slugs
        providers = db.query(Provider).filter(
            Provider.public_profile_slug.is_(None)
        ).all()
        
        logger.info(f"Found {len(providers)} providers without public profile slugs")
        
        updated_count = 0
        
        for provider in providers:
            try:
                # Get main service type
                main_service = ""
                if provider.services and len(provider.services) > 0:
                    main_service = provider.services[0]
                
                # Get location
                location = ""
                if provider.coverage_areas and len(provider.coverage_areas) > 0:
                    location = provider.coverage_areas[0]
                
                # Create base slug
                base_slug = create_slug(provider.name, main_service, location)
                
                # Ensure uniqueness
                unique_slug = ensure_unique_slug(db, base_slug, provider.id)
                
                # Update provider
                provider.public_profile_slug = unique_slug
                provider.is_profile_public = True
                
                logger.info(f"Generated slug '{unique_slug}' for provider {provider.name}")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error generating slug for provider {provider.name}: {str(e)}")
                continue
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully generated {updated_count} public profile slugs")
        
        # Show examples
        examples = db.query(Provider).filter(
            Provider.public_profile_slug.isnot(None)
        ).limit(5).all()
        
        logger.info("Example profile URLs:")
        for provider in examples:
            profile_url = f"https://djobea-ai.replit.app/provider/{provider.public_profile_slug}"
            logger.info(f"  {provider.name}: {profile_url}")
        
    except Exception as e:
        logger.error(f"Error generating profile slugs: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Install unidecode if not available
    try:
        import unidecode
    except ImportError:
        logger.info("Installing unidecode for slug generation...")
        os.system("pip install unidecode")
        import unidecode
    
    generate_profile_slugs()