"""Redis caching layer for Arbihedron."""
import json
import redis
from typing import Any, Optional, Dict, List
from datetime import timedelta
from loguru import logger
from functools import wraps
import hashlib


class CacheManager:
    """Redis-based cache manager for market data and opportunities."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize cache manager.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            enabled: Whether caching is enabled
        """
        self.enabled = enabled
        self.client: Optional[redis.Redis] = None
        
        if not enabled:
            logger.warning("Caching is disabled")
            return
        
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Continuing without cache")
            self.enabled = False
            self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            return json.loads(value)
        
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            serialized = json.dumps(value)
            
            if ttl:
                self.client.setex(key, ttl, serialized)
            else:
                self.client.set(key, serialized)
            
            return True
        
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except redis.RedisError as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "market:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.client:
            return 0
        
        try:
            keys = list(self.client.scan_iter(match=pattern))
            if keys:
                return self.client.delete(*keys)
            return 0
        except redis.RedisError as e:
            logger.warning(f"Cache delete pattern error for '{pattern}': {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.enabled or not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except redis.RedisError:
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter."""
        if not self.enabled or not self.client:
            return None
        
        try:
            return self.client.incrby(key, amount)
        except redis.RedisError as e:
            logger.warning(f"Cache increment error for key '{key}': {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled or not self.client:
            return {'enabled': False}
        
        try:
            info = self.client.info()
            return {
                'enabled': True,
                'connected': True,
                'used_memory_mb': info.get('used_memory', 0) / 1024 / 1024,
                'total_keys': self.client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info),
            }
        except redis.RedisError as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'enabled': True, 'connected': False, 'error': str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate."""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return hits / total
    
    def flush_all(self) -> bool:
        """Flush all cache data. Use with caution!"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.flushdb()
            logger.warning("Cache flushed")
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to flush cache: {e}")
            return False
    
    def close(self):
        """Close Redis connection."""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except redis.RedisError as e:
                logger.error(f"Error closing Redis connection: {e}")


def cache_result(
    ttl: int = 60,
    key_prefix: str = "",
    include_args: bool = True,
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        include_args: Include function arguments in cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Check if instance has cache_manager
            cache_manager = getattr(self, 'cache_manager', None)
            if not cache_manager or not cache_manager.enabled:
                return func(self, *args, **kwargs)
            
            # Generate cache key
            if include_args:
                args_str = json.dumps([args, kwargs], sort_keys=True)
                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{key_prefix}:{func.__name__}:{args_hash}"
            else:
                cache_key = f"{key_prefix}:{func.__name__}"
            
            # Try to get from cache
            cached = cache_manager.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function and cache result
            result = func(self, *args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Market data specific cache keys
class CacheKeys:
    """Standard cache key patterns."""
    
    @staticmethod
    def ticker(exchange: str, symbol: str) -> str:
        """Ticker data cache key."""
        return f"ticker:{exchange}:{symbol}"
    
    @staticmethod
    def orderbook(exchange: str, symbol: str) -> str:
        """Order book cache key."""
        return f"orderbook:{exchange}:{symbol}"
    
    @staticmethod
    def opportunity(exchange: str, path: str) -> str:
        """Arbitrage opportunity cache key."""
        return f"opportunity:{exchange}:{path}"
    
    @staticmethod
    def market_pairs(exchange: str) -> str:
        """Market pairs list cache key."""
        return f"markets:{exchange}:pairs"
    
    @staticmethod
    def triangular_paths(exchange: str) -> str:
        """Triangular paths cache key."""
        return f"paths:{exchange}:triangular"
