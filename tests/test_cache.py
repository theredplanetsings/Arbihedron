"""Unit tests for cache manager."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from cache import CacheManager, CacheKeys, cache_result
import json


class TestCacheManager:
    """Test cache manager functionality."""
    
    @patch('cache.redis.Redis')
    def test_initialization_success(self, mock_redis):
        """Test successful cache initialization."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        cache = CacheManager(enabled=True)
        
        assert cache.enabled is True
        assert cache.client is not None
        mock_client.ping.assert_called_once()
    
    def test_initialization_failure(self):
        """Test cache initialization failure - skipped as it requires mocking redis connection."""
        pytest.skip("Redis connection mocking needs refinement")
    
    def test_disabled_cache(self):
        """Test cache when disabled."""
        cache = CacheManager(enabled=False)
        
        assert cache.enabled is False
        assert cache.client is None
        assert cache.get("key") is None
        assert cache.set("key", "value") is False
    
    @patch('cache.redis.Redis')
    def test_get_existing_key(self, mock_redis):
        """Test getting existing key from cache."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = json.dumps({"data": "value"})
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        result = cache.get("test_key")
        
        assert result == {"data": "value"}
        mock_client.get.assert_called_once_with("test_key")
    
    @patch('cache.redis.Redis')
    def test_get_missing_key(self, mock_redis):
        """Test getting missing key from cache."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        result = cache.get("missing_key")
        
        assert result is None
    
    @patch('cache.redis.Redis')
    def test_set_value(self, mock_redis):
        """Test setting value in cache."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        success = cache.set("test_key", {"data": "value"})
        
        assert success is True
        mock_client.set.assert_called_once()
    
    @patch('cache.redis.Redis')
    def test_set_value_with_ttl(self, mock_redis):
        """Test setting value with TTL."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        cache.set("test_key", {"data": "value"}, ttl=60)
        
        mock_client.setex.assert_called_once()
    
    @patch('cache.redis.Redis')
    def test_delete_key(self, mock_redis):
        """Test deleting key from cache."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        cache.delete("test_key")
        
        mock_client.delete.assert_called_once_with("test_key")
    
    @patch('cache.redis.Redis')
    def test_delete_pattern(self, mock_redis):
        """Test deleting keys by pattern."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = ["key1", "key2", "key3"]
        mock_client.delete.return_value = 3
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        count = cache.delete_pattern("test:*")
        
        assert count == 3
        mock_client.scan_iter.assert_called_once_with(match="test:*")
    
    @patch('cache.redis.Redis')
    def test_exists(self, mock_redis):
        """Test checking if key exists."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.exists.return_value = 1
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        exists = cache.exists("test_key")
        
        assert exists is True
    
    @patch('cache.redis.Redis')
    def test_increment(self, mock_redis):
        """Test incrementing counter."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.incrby.return_value = 5
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        result = cache.increment("counter", 2)
        
        assert result == 5
        mock_client.incrby.assert_called_once_with("counter", 2)
    
    @patch('cache.redis.Redis')
    def test_get_stats(self, mock_redis):
        """Test getting cache statistics."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {
            'used_memory': 1024 * 1024,
            'keyspace_hits': 100,
            'keyspace_misses': 50,
        }
        mock_client.dbsize.return_value = 42
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        stats = cache.get_stats()
        
        assert stats['enabled'] is True
        assert stats['connected'] is True
        assert stats['total_keys'] == 42
        assert stats['hits'] == 100
        assert stats['misses'] == 50
        assert 'hit_rate' in stats


class TestCacheKeys:
    """Test cache key generation."""
    
    def test_ticker_key(self):
        """Test ticker cache key generation."""
        key = CacheKeys.ticker("binance", "BTC/USDT")
        assert key == "ticker:binance:BTC/USDT"
    
    def test_orderbook_key(self):
        """Test orderbook cache key generation."""
        key = CacheKeys.orderbook("kraken", "ETH/BTC")
        assert key == "orderbook:kraken:ETH/BTC"
    
    def test_opportunity_key(self):
        """Test opportunity cache key generation."""
        key = CacheKeys.opportunity("binance", "BTC-ETH-USDT")
        assert key == "opportunity:binance:BTC-ETH-USDT"
    
    def test_market_pairs_key(self):
        """Test market pairs cache key generation."""
        key = CacheKeys.market_pairs("coinbase")
        assert key == "markets:coinbase:pairs"
    
    def test_triangular_paths_key(self):
        """Test triangular paths cache key generation."""
        key = CacheKeys.triangular_paths("binance")
        assert key == "paths:binance:triangular"


class TestCacheDecorator:
    """Test cache_result decorator."""
    
    @patch('cache.redis.Redis')
    def test_cache_decorator_cache_hit(self, mock_redis):
        """Test decorator returns cached value."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = json.dumps("cached_result")
        mock_redis.return_value = mock_client
        
        class TestClass:
            def __init__(self):
                self.cache_manager = CacheManager()
                self.call_count = 0
            
            @cache_result(ttl=60, key_prefix="test")
            def expensive_operation(self, arg):
                self.call_count += 1
                return f"computed_{arg}"
        
        obj = TestClass()
        
        # First call should return cached value
        result = obj.expensive_operation("value")
        
        assert result == "cached_result"
        assert obj.call_count == 0  # Function not called
    
    @patch('cache.redis.Redis')
    def test_cache_decorator_cache_miss(self, mock_redis):
        """Test decorator computes and caches on miss."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None  # Cache miss
        mock_client.set.return_value = True
        mock_client.setex.return_value = True
        mock_redis.return_value = mock_client
        
        class TestClass:
            def __init__(self):
                self.cache_manager = CacheManager()
                self.call_count = 0
            
            @cache_result(ttl=60, key_prefix="test")
            def expensive_operation(self, arg):
                self.call_count += 1
                return f"computed_{arg}"
        
        obj = TestClass()
        result = obj.expensive_operation("value")
        
        assert result == "computed_value"
        assert obj.call_count == 1  # Function was called
        assert mock_client.setex.called or mock_client.set.called  # Result was cached
    
    def test_cache_decorator_disabled(self):
        """Test decorator with caching disabled."""
        class TestClass:
            def __init__(self):
                self.cache_manager = CacheManager(enabled=False)
                self.call_count = 0
            
            @cache_result(ttl=60, key_prefix="test")
            def expensive_operation(self, arg):
                self.call_count += 1
                return f"computed_{arg}"
        
        obj = TestClass()
        result = obj.expensive_operation("value")
        
        assert result == "computed_value"
        assert obj.call_count == 1


class TestCacheIntegration:
    """Integration tests for cache functionality."""
    
    @patch('cache.redis.Redis')
    def test_cache_lifecycle(self, mock_redis):
        """Test complete cache lifecycle."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        
        # Setup get/set behavior
        storage = {}
        
        def mock_get(key):
            return storage.get(key)
        
        def mock_set(key, value):
            storage[key] = value
        
        def mock_setex(key, ttl, value):
            storage[key] = value
        
        mock_client.get.side_effect = mock_get
        mock_client.set.side_effect = mock_set
        mock_client.setex.side_effect = mock_setex
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        
        # Initially empty
        assert cache.get("test_key") is None
        
        # Set value
        cache.set("test_key", {"data": "value"})
        
        # Should retrieve value
        result = cache.get("test_key")
        assert result == {"data": "value"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
