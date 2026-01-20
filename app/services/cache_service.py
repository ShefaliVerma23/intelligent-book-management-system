"""
Redis Cache Service for Book Recommendations and AI Summaries

This service provides caching functionality similar to AWS ElastiCache.
It caches:
- Book recommendations (TTL: 60 seconds)
- Popular books list (TTL: 120 seconds)
- AI-generated summaries (TTL: 300 seconds)

Error Handling:
- All methods log errors and fail gracefully (return None/False)
- Connection issues are properly reported
- Cache is disabled automatically if Redis is unavailable
"""
import json
import hashlib
from typing import Optional, Any, List
import redis.asyncio as redis
from loguru import logger

from app.config.settings import settings


class CacheService:
    """
    Redis-based caching service for improved API performance.
    Compatible with AWS ElastiCache (Redis mode).
    
    Features:
    - Graceful degradation when Redis is unavailable
    - Detailed error logging with context
    - Automatic key hashing for long keys
    - TTL-based expiration for all cached data
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
        self._connection_attempted = False
    
    async def connect(self) -> bool:
        """
        Initialize Redis connection.
        
        Returns True if connection successful, False otherwise.
        Never raises exceptions - logs and returns False on failure.
        """
        self._connection_attempted = True
        
        # Check if caching is configured
        if not settings.CACHE_ENABLED:
            logger.info("Caching is disabled by configuration (CACHE_ENABLED=False)")
            return False
        
        if not settings.REDIS_URL:
            logger.warning(
                "REDIS_URL not configured - caching disabled. "
                "Set REDIS_URL environment variable to enable caching."
            )
            return False
        
        try:
            redis_url = settings.REDIS_URL
            
            logger.info(f"Attempting Redis connection to: {self._mask_url(redis_url)}")
            
            self._redis = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,  # 5 second timeout for connection
                socket_timeout=3,  # 3 second timeout for operations
            )
            
            # Test connection with timeout
            await self._redis.ping()
            self._connected = True
            
            logger.info(
                "Redis cache connected successfully",
                extra={"redis_url": self._mask_url(redis_url)}
            )
            return True
            
        except redis.ConnectionError as e:
            logger.error(
                f"Redis connection failed - connection refused or host not reachable",
                extra={"error": str(e), "redis_url": self._mask_url(settings.REDIS_URL)}
            )
            self._connected = False
            return False
            
        except redis.TimeoutError as e:
            logger.error(
                f"Redis connection timed out",
                extra={"error": str(e), "redis_url": self._mask_url(settings.REDIS_URL)}
            )
            self._connected = False
            return False
            
        except Exception as e:
            logger.error(
                f"Redis cache initialization failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "redis_url": self._mask_url(settings.REDIS_URL)
                },
                exc_info=True
            )
            self._connected = False
            return False
    
    def _mask_url(self, url: str) -> str:
        """Mask password in Redis URL for safe logging"""
        if not url:
            return "(none)"
        if "@" in url:
            # Format: redis://:password@host:port/db or redis://user:password@host:port/db
            parts = url.split("@")
            return f"redis://***@{parts[-1]}"
        return url
    
    async def disconnect(self):
        """Close Redis connection gracefully"""
        if self._redis:
            try:
                await self._redis.close()
                logger.info("Redis cache disconnected")
            except Exception as e:
                logger.warning(f"Error during Redis disconnect: {e}")
            finally:
                self._connected = False
                self._redis = None
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is currently connected"""
        return self._connected
    
    @property
    def is_configured(self) -> bool:
        """Check if caching is properly configured"""
        return settings.CACHE_ENABLED and bool(settings.REDIS_URL)
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments"""
        key_data = ":".join(str(arg) for arg in args if arg is not None)
        if len(key_data) > 100:
            # Hash long keys to prevent key length issues
            key_data = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}{key_data}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Returns None on cache miss or error.
        Never raises exceptions.
        """
        if not self._connected:
            return None
            
        try:
            data = await self._redis.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(data)
            logger.debug(f"Cache MISS: {key}")
            return None
            
        except json.JSONDecodeError as e:
            logger.warning(
                f"Cache data corrupted (invalid JSON)",
                extra={"key": key, "error": str(e)}
            )
            # Delete corrupted data
            try:
                await self._redis.delete(key)
            except Exception:
                pass
            return None
            
        except redis.ConnectionError as e:
            logger.error(
                f"Redis connection lost during GET operation",
                extra={"key": key, "error": str(e)}
            )
            self._connected = False
            return None
            
        except Exception as e:
            logger.error(
                f"Cache GET error",
                extra={"key": key, "error": str(e), "error_type": type(e).__name__}
            )
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """
        Set value in cache with TTL.
        
        Returns True if successful, False otherwise.
        Never raises exceptions.
        """
        if not self._connected:
            return False
            
        try:
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
            
        except redis.ConnectionError as e:
            logger.error(
                f"Redis connection lost during SET operation",
                extra={"key": key, "error": str(e)}
            )
            self._connected = False
            return False
            
        except TypeError as e:
            logger.error(
                f"Cache SET failed - value not JSON serializable",
                extra={"key": key, "error": str(e)}
            )
            return False
            
        except Exception as e:
            logger.error(
                f"Cache SET error",
                extra={"key": key, "error": str(e), "error_type": type(e).__name__}
            )
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Returns True if successful (even if key didn't exist).
        Never raises exceptions.
        """
        if not self._connected:
            return False
            
        try:
            await self._redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
            
        except redis.ConnectionError as e:
            logger.error(
                f"Redis connection lost during DELETE operation",
                extra={"key": key, "error": str(e)}
            )
            self._connected = False
            return False
            
        except Exception as e:
            logger.error(
                f"Cache DELETE error",
                extra={"key": key, "error": str(e), "error_type": type(e).__name__}
            )
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Returns number of keys deleted.
        Never raises exceptions.
        """
        if not self._connected:
            return 0
            
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache CLEAR: {pattern} ({deleted} keys)")
                return deleted
            return 0
            
        except redis.ConnectionError as e:
            logger.error(
                f"Redis connection lost during CLEAR operation",
                extra={"pattern": pattern, "error": str(e)}
            )
            self._connected = False
            return 0
            
        except Exception as e:
            logger.error(
                f"Cache CLEAR error",
                extra={"pattern": pattern, "error": str(e), "error_type": type(e).__name__}
            )
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
        """
        Get cache statistics.
        
        Returns dict with connection status and hit/miss counts if connected.
        """
        if not self._connected:
            return {
                "status": "disconnected",
                "configured": self.is_configured,
                "connection_attempted": self._connection_attempted
            }
            
        try:
            info = await self._redis.info("stats")
            db_size = await self._redis.dbsize()
            
            return {
                "status": "connected",
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "keys": db_size,
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) * 100, 
                    2
                )
            }
            
        except Exception as e:
            logger.error(
                f"Error getting cache stats",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }


# Global cache instance
cache_service = CacheService()
