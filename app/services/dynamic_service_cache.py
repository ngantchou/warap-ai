"""
Dynamic Service Cache - Intelligent caching for frequently used data
Redis-based cache with fallback to in-memory storage
"""
from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime, timedelta
import redis
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class DynamicServiceCache:
    """Intelligent cache for dynamic services system"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "redis_errors": 0
        }
        
        # Initialize Redis if available
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis not available, using memory cache: {e}")
                self.redis_client = None
    
    async def get_zones(self, zone_type: Optional[str] = None) -> Optional[List[Dict]]:
        """Get cached zones"""
        cache_key = f"zones:{zone_type or 'all'}"
        return await self._get_cached_data(cache_key)
    
    async def set_zones(self, zones: List[Dict], zone_type: Optional[str] = None, ttl: int = 3600):
        """Cache zones"""
        cache_key = f"zones:{zone_type or 'all'}"
        await self._set_cached_data(cache_key, zones, ttl)
    
    async def get_services(self, category_id: Optional[int] = None, zone_code: Optional[str] = None) -> Optional[List[Dict]]:
        """Get cached services"""
        cache_key = f"services:{category_id or 'all'}:{zone_code or 'all'}"
        return await self._get_cached_data(cache_key)
    
    async def set_services(self, services: List[Dict], category_id: Optional[int] = None, zone_code: Optional[str] = None, ttl: int = 1800):
        """Cache services"""
        cache_key = f"services:{category_id or 'all'}:{zone_code or 'all'}"
        await self._set_cached_data(cache_key, services, ttl)
    
    async def get_service_categories(self) -> Optional[List[Dict]]:
        """Get cached service categories"""
        return await self._get_cached_data("service_categories")
    
    async def set_service_categories(self, categories: List[Dict], ttl: int = 7200):
        """Cache service categories"""
        await self._set_cached_data("service_categories", categories, ttl)
    
    async def get_zone_hierarchy(self, zone_id: int) -> Optional[List[Dict]]:
        """Get cached zone hierarchy"""
        cache_key = f"zone_hierarchy:{zone_id}"
        return await self._get_cached_data(cache_key)
    
    async def set_zone_hierarchy(self, zone_id: int, hierarchy: List[Dict], ttl: int = 3600):
        """Cache zone hierarchy"""
        cache_key = f"zone_hierarchy:{zone_id}"
        await self._set_cached_data(cache_key, hierarchy, ttl)
    
    async def get_service_search_results(self, query: str, zone_code: Optional[str] = None) -> Optional[List[Dict]]:
        """Get cached search results"""
        cache_key = f"search:{self._normalize_query(query)}:{zone_code or 'all'}"
        return await self._get_cached_data(cache_key)
    
    async def set_service_search_results(self, query: str, results: List[Dict], zone_code: Optional[str] = None, ttl: int = 900):
        """Cache search results"""
        cache_key = f"search:{self._normalize_query(query)}:{zone_code or 'all'}"
        await self._set_cached_data(cache_key, results, ttl)
    
    async def get_popular_services(self, zone_code: Optional[str] = None) -> Optional[List[Dict]]:
        """Get cached popular services"""
        cache_key = f"popular_services:{zone_code or 'all'}"
        return await self._get_cached_data(cache_key)
    
    async def set_popular_services(self, services: List[Dict], zone_code: Optional[str] = None, ttl: int = 3600):
        """Cache popular services"""
        cache_key = f"popular_services:{zone_code or 'all'}"
        await self._set_cached_data(cache_key, services, ttl)
    
    async def invalidate_zone_cache(self, zone_code: Optional[str] = None):
        """Invalidate zone-related cache"""
        patterns = [
            f"zones:*",
            f"services:*:{zone_code or '*'}",
            f"popular_services:{zone_code or '*'}"
        ]
        
        for pattern in patterns:
            await self._invalidate_pattern(pattern)
    
    async def invalidate_service_cache(self, service_code: Optional[str] = None):
        """Invalidate service-related cache"""
        patterns = [
            "services:*",
            "popular_services:*",
            "search:*"
        ]
        
        for pattern in patterns:
            await self._invalidate_pattern(pattern)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = 0
        if self.cache_stats["hits"] + self.cache_stats["misses"] > 0:
            hit_rate = self.cache_stats["hits"] / (self.cache_stats["hits"] + self.cache_stats["misses"])
        
        stats = {
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "hit_rate": hit_rate,
            "redis_errors": self.cache_stats["redis_errors"],
            "redis_available": self.redis_client is not None,
            "memory_cache_size": len(self.memory_cache)
        }
        
        # Add Redis info if available
        if self.redis_client:
            try:
                redis_info = self.redis_client.info()
                stats["redis_memory_used"] = redis_info.get("used_memory_human", "N/A")
                stats["redis_connected_clients"] = redis_info.get("connected_clients", 0)
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return stats
    
    async def clear_all_cache(self):
        """Clear all cache"""
        # Clear Redis cache
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                logger.info("Redis cache cleared")
            except Exception as e:
                logger.error(f"Error clearing Redis cache: {e}")
        
        # Clear memory cache
        self.memory_cache.clear()
        logger.info("Memory cache cleared")
    
    async def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache"""
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    cached_data = self.redis_client.get(cache_key)
                    if cached_data:
                        self.cache_stats["hits"] += 1
                        return json.loads(cached_data)
                except Exception as e:
                    logger.error(f"Redis get error: {e}")
                    self.cache_stats["redis_errors"] += 1
            
            # Fall back to memory cache
            if cache_key in self.memory_cache:
                cache_entry = self.memory_cache[cache_key]
                if datetime.now() < cache_entry["expires_at"]:
                    self.cache_stats["hits"] += 1
                    return cache_entry["data"]
                else:
                    # Remove expired entry
                    del self.memory_cache[cache_key]
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            self.cache_stats["misses"] += 1
            return None
    
    async def _set_cached_data(self, cache_key: str, data: Any, ttl: int):
        """Set data in cache"""
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, ttl, json.dumps(data, default=str))
                    return
                except Exception as e:
                    logger.error(f"Redis set error: {e}")
                    self.cache_stats["redis_errors"] += 1
            
            # Fall back to memory cache
            self.memory_cache[cache_key] = {
                "data": data,
                "expires_at": datetime.now() + timedelta(seconds=ttl)
            }
            
            # Clean up expired entries periodically
            if len(self.memory_cache) > 1000:  # Arbitrary limit
                await self._cleanup_memory_cache()
            
        except Exception as e:
            logger.error(f"Error setting cached data: {e}")
    
    async def _invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        try:
            # Redis pattern invalidation
            if self.redis_client:
                try:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.error(f"Redis invalidation error: {e}")
                    self.cache_stats["redis_errors"] += 1
            
            # Memory cache pattern invalidation
            keys_to_delete = []
            for key in self.memory_cache.keys():
                if self._matches_pattern(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.memory_cache[key]
            
        except Exception as e:
            logger.error(f"Error invalidating cache pattern: {e}")
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple wildcard support)"""
        if "*" not in pattern:
            return key == pattern
        
        # Convert pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        import re
        return re.match(f"^{regex_pattern}$", key) is not None
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for caching"""
        return query.lower().strip().replace(" ", "_")
    
    async def _cleanup_memory_cache(self):
        """Clean up expired entries from memory cache"""
        try:
            now = datetime.now()
            expired_keys = []
            
            for key, cache_entry in self.memory_cache.items():
                if now >= cache_entry["expires_at"]:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        except Exception as e:
            logger.error(f"Error cleaning up memory cache: {e}")