"""
Configuration API endpoints for Djobea AI
Implements dynamic configuration management API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.auth import get_current_admin_user
from app.services.config_service import ConfigService, ConfigSource

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Configuration"])

# Pydantic models
class ConfigUpdateRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: Any
    description: Optional[str] = None

class BulkConfigUpdateRequest(BaseModel):
    configs: List[ConfigUpdateRequest]

class ConfigExportRequest(BaseModel):
    include_sensitive: bool = False
    categories: Optional[List[str]] = None

@router.get("/")
async def get_all_configs(
    include_sensitive: bool = Query(False, description="Include sensitive configurations"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config - Get all configuration values
    Retrieve all system configuration values
    """
    try:
        config_service = ConfigService(db)
        
        if category:
            configs = config_service.get_configs_by_category(category)
        else:
            configs = config_service.get_all_configs()
        
        # Filter sensitive configs if not requested
        if not include_sensitive:
            configs = {
                key: item for key, item in configs.items()
                if not item.is_sensitive
            }
        
        # Format response
        result = {}
        for key, item in configs.items():
            result[key] = {
                "value": item.value,
                "source": item.source.value,
                "description": item.description,
                "is_sensitive": item.is_sensitive
            }
        
        return {
            "success": True,
            "data": result,
            "total": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configurations")

@router.get("/categories")
async def get_config_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/categories - Get configuration categories
    Get all available configuration categories
    """
    try:
        config_service = ConfigService(db)
        configs = config_service.get_all_configs()
        
        categories = set()
        for key in configs.keys():
            if "." in key:
                category = key.split(".", 1)[0]
                categories.add(category)
        
        return {
            "success": True,
            "data": {
                "categories": sorted(list(categories)),
                "total": len(categories)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting config categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")

@router.get("/business")
async def get_business_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/business - Get business configuration
    Get business-specific configuration values
    """
    try:
        config_service = ConfigService(db)
        business_config = config_service.get_business_config()
        
        return {
            "success": True,
            "data": business_config
        }
        
    except Exception as e:
        logger.error(f"Error getting business config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve business configuration")

@router.get("/ai")
async def get_ai_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/ai - Get AI configuration
    Get AI-specific configuration values
    """
    try:
        config_service = ConfigService(db)
        ai_config = config_service.get_ai_config()
        
        return {
            "success": True,
            "data": ai_config
        }
        
    except Exception as e:
        logger.error(f"Error getting AI config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve AI configuration")

@router.get("/provider")
async def get_provider_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/provider - Get provider configuration
    Get provider-specific configuration values
    """
    try:
        config_service = ConfigService(db)
        provider_config = config_service.get_provider_config()
        
        return {
            "success": True,
            "data": provider_config
        }
        
    except Exception as e:
        logger.error(f"Error getting provider config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve provider configuration")

@router.get("/request")
async def get_request_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/request - Get request configuration
    Get request processing configuration values
    """
    try:
        config_service = ConfigService(db)
        request_config = config_service.get_request_config()
        
        return {
            "success": True,
            "data": request_config
        }
        
    except Exception as e:
        logger.error(f"Error getting request config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve request configuration")

@router.get("/communication")
async def get_communication_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/communication - Get communication configuration
    Get communication-specific configuration values
    """
    try:
        config_service = ConfigService(db)
        communication_config = config_service.get_communication_config()
        
        return {
            "success": True,
            "data": communication_config
        }
        
    except Exception as e:
        logger.error(f"Error getting communication config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve communication configuration")

@router.get("/security")
async def get_security_config(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/security - Get security configuration
    Get security-specific configuration values
    """
    try:
        config_service = ConfigService(db)
        security_config = config_service.get_security_config()
        
        return {
            "success": True,
            "data": security_config
        }
        
    except Exception as e:
        logger.error(f"Error getting security config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security configuration")

@router.get("/{key}")
async def get_config_value(
    key: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/{key} - Get specific configuration value
    Get a specific configuration value by key
    """
    try:
        config_service = ConfigService(db)
        value = config_service.get(key)
        
        if value is None:
            raise HTTPException(status_code=404, detail=f"Configuration key '{key}' not found")
        
        # Check if it's sensitive
        configs = config_service.get_all_configs()
        is_sensitive = configs.get(key, {}).is_sensitive if key in configs else False
        
        return {
            "success": True,
            "data": {
                "key": key,
                "value": value,
                "is_sensitive": is_sensitive
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config value for {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration value")

@router.put("/{key}")
async def update_config_value(
    key: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    PUT /api/config/{key} - Update configuration value
    Update a specific configuration value
    """
    try:
        config_service = ConfigService(db)
        
        value = request.get("value")
        if value is None:
            raise HTTPException(status_code=400, detail="Value is required")
        
        success = config_service.set(key, value, ConfigSource.DATABASE)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update configuration")
        
        return {
            "success": True,
            "message": f"Configuration '{key}' updated successfully",
            "data": {
                "key": key,
                "value": value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config value for {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration value")

@router.post("/bulk")
async def bulk_update_configs(
    request: BulkConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/config/bulk - Bulk update configurations
    Update multiple configuration values in one request
    """
    try:
        config_service = ConfigService(db)
        
        results = []
        for config in request.configs:
            try:
                success = config_service.set(
                    config.key, 
                    config.value, 
                    ConfigSource.DATABASE
                )
                results.append({
                    "key": config.key,
                    "success": success,
                    "message": "Updated successfully" if success else "Update failed"
                })
            except Exception as e:
                results.append({
                    "key": config.key,
                    "success": False,
                    "message": str(e)
                })
        
        successful_updates = sum(1 for r in results if r["success"])
        
        return {
            "success": True,
            "message": f"Bulk update completed: {successful_updates}/{len(results)} successful",
            "data": {
                "results": results,
                "total": len(results),
                "successful": successful_updates,
                "failed": len(results) - successful_updates
            }
        }
        
    except Exception as e:
        logger.error(f"Error in bulk config update: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform bulk update")

@router.post("/reload")
async def reload_configs(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/config/reload - Reload configurations
    Reload all configurations from their sources
    """
    try:
        config_service = ConfigService(db)
        config_service.reload()
        
        return {
            "success": True,
            "message": "Configurations reloaded successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reloading configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload configurations")

@router.post("/export")
async def export_configs(
    request: ConfigExportRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    POST /api/config/export - Export configurations
    Export configurations as JSON
    """
    try:
        config_service = ConfigService(db)
        
        exported_configs = config_service.export_config(
            include_sensitive=request.include_sensitive
        )
        
        # Filter by categories if specified
        if request.categories:
            filtered_configs = {}
            for key, value in exported_configs.items():
                if any(key.startswith(f"{cat}.") for cat in request.categories):
                    filtered_configs[key] = value
            exported_configs = filtered_configs
        
        return {
            "success": True,
            "data": {
                "configurations": exported_configs,
                "export_info": {
                    "total_configs": len(exported_configs),
                    "include_sensitive": request.include_sensitive,
                    "categories": request.categories,
                    "exported_at": datetime.utcnow().isoformat()
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error exporting configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to export configurations")

@router.get("/validate/{key}")
async def validate_config(
    key: str,
    value: str = Query(..., description="Value to validate"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    GET /api/config/validate/{key} - Validate configuration value
    Validate a configuration value before setting it
    """
    try:
        # Basic validation logic
        validation_rules = {
            "business.tax_rate": lambda x: 0 <= float(x) <= 100,
            "business.commission_rate": lambda x: 0 <= float(x) <= 100,
            "business.minimum_order": lambda x: float(x) > 0,
            "ai.temperature": lambda x: 0 <= float(x) <= 2,
            "ai.max_tokens": lambda x: 1 <= int(x) <= 8192,
            "ai.confidence_threshold": lambda x: 0 <= float(x) <= 1,
            "provider.minimum_rating": lambda x: 1 <= float(x) <= 5,
            "request.max_distance": lambda x: float(x) > 0,
            "request.rating_weight": lambda x: 0 <= float(x) <= 1,
            "request.distance_weight": lambda x: 0 <= float(x) <= 1,
        }
        
        is_valid = True
        message = "Value is valid"
        
        if key in validation_rules:
            try:
                is_valid = validation_rules[key](value)
                if not is_valid:
                    message = f"Value '{value}' is not valid for {key}"
            except Exception as e:
                is_valid = False
                message = f"Validation error: {str(e)}"
        
        return {
            "success": True,
            "data": {
                "key": key,
                "value": value,
                "is_valid": is_valid,
                "message": message
            }
        }
        
    except Exception as e:
        logger.error(f"Error validating config {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate configuration")