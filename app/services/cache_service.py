"""
Redis Cache Service for Book Recommendations and AI Summaries

This service provides caching functionality similar to AWS ElastiCache.
It caches:
- Book recommendations (TTL: 60 seconds)
- Popular books list (TTL: 120 seconds)
- AI-generated summaries (TTL: 300 seconds)
"""
import json
import hashlib
from typing import Optional, Any, List
from datetime import timedelta
import redis.asyncio as redis
from loguru import logger

from app.config.settings import settings


class CacheService:
    """
    Redis-based caching service for improved API performance.
    Compatible with AWS ElastiCache (Redis mode).
    """
    
    # Cache TTL (Time To Live) settings
    TTL_RECOMMENDATIONS = 60      # 1 minute
    TTL_POPULAR_BOOKS = 120       # 2 minutes
    TTL_AI_SUMMARY = 300          # 5 minutes
    TTL_SIMILAR_BOOKS = 180       # 3 minutes
    
    # Cache key prefixes
    PREFIX_RECOMMENDATIONS = "rec:"
    PREFIX_POPULAR = "popular:"
    PREFIX_SUMMARY = "summary:"
    PREFIX_SIMILAR = "similar:"
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Initialize Redis connection"""
        try:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self._redis = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"Redis cache connected: {redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Redis cache not available: {e}. Running without cache.")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Redis cache disconnected")
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments"""
        key_data = ":".join(str(arg) for arg in args if arg is not None)
        if len(key_data) > 100:
            # Hash long keys
            key_data = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}{key_data}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            return None
        try:
            data = await self._redis.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(data)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set value in cache with TTL"""
        if not self._connected:
            return False
        try:
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._connected:
            return False
        try:
            await self._redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self._connected:
            return 0
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache CLEAR: {pattern} ({deleted} keys)")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    # =========================================================================
    # High-level caching methods for specific use cases
    # =========================================================================
    
    async def get_recommendations(self, user_id: int, genre: Optional[str] = None) -> Optional[dict]:
        """Get cached recommendations for user"""
        key = self._generate_key(self.PREFIX_RECOMMENDATIONS, user_id, genre)
        return await self.get(key)
    
    async def set_recommendations(self, user_id: int, data: dict, genre: Optional[str] = None) -> bool:
        """Cache recommendations for user"""
        key = self._generate_key(self.PREFIX_RECOMMENDATIONS, user_id, genre)
        return await self.set(key, data, self.TTL_RECOMMENDATIONS)
    
    async def get_popular_books(self, genre: Optional[str] = None, limit: int = 10) -> Optional[List]:
        """Get cached popular books"""
        key = self._generate_key(self.PREFIX_POPULAR, genre, limit)
        return await self.get(key)
    
    async def set_popular_books(self, data: List, genre: Optional[str] = None, limit: int = 10) -> bool:
        """Cache popular books list"""
        key = self._generate_key(self.PREFIX_POPULAR, genre, limit)
        return await self.set(key, data, self.TTL_POPULAR_BOOKS)
    
    async def get_ai_summary(self, content_hash: str) -> Optional[str]:
        """Get cached AI summary"""
        key = self._generate_key(self.PREFIX_SUMMARY, content_hash)
        return await self.get(key)
    
    async def set_ai_summary(self, content_hash: str, summary: str) -> bool:
        """Cache AI-generated summary"""
        key = self._generate_key(self.PREFIX_SUMMARY, content_hash)
        return await self.set(key, summary, self.TTL_AI_SUMMARY)
    
    async def get_similar_books(self, book_id: int, limit: int = 5) -> Optional[List]:
        """Get cached similar books"""
        key = self._generate_key(self.PREFIX_SIMILAR, book_id, limit)
        return await self.get(key)
    
    async def set_similar_books(self, book_id: int, data: List, limit: int = 5) -> bool:
        """Cache similar books list"""
        key = self._generate_key(self.PREFIX_SIMILAR, book_id, limit)
        return await self.set(key, data, self.TTL_SIMILAR_BOOKS)
    
    async def invalidate_book_caches(self, book_id: Optional[int] = None):
        """Invalidate book-related caches when data changes"""
        await self.clear_pattern(f"{self.PREFIX_POPULAR}*")
        if book_id:
            await self.clear_pattern(f"{self.PREFIX_SIMILAR}{book_id}*")
        await self.clear_pattern(f"{self.PREFIX_RECOMMENDATIONS}*")
    
    async def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        if not self._connected:
            return {"status": "disconnected"}
        try:
            info = await self._redis.info("stats")
            return {
                "status": "connected",
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "keys": await self._redis.dbsize()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global cache instance
cache_service = CacheService()

