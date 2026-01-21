"""Integration tests for Arbihedron system."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

@pytest.mark.integration
class TestExchangeIntegration:
    """Integration tests for exchange client."""
    
    @pytest.mark.asyncio
    async def test_fetch_markets(self):
        """Test fetching markets from exchange."""
        # This would test actual API calls in a real integration test
        # For now, we'll mock it
        pass
    
    @pytest.mark.asyncio
    async def test_fetch_ticker(self):
        """Test fetching ticker data."""
        pass

@pytest.mark.integration
class TestArbitrageEngineIntegration:
    """Integration tests for arbitrage engine."""
    
    @pytest.mark.asyncio
    async def test_find_opportunities_workflow(self):
        """Test complete opportunity finding workflow."""
        from arbihedron.core.arbitrage_engine import ArbitrageEngine
        from arbihedron.core.exchange_client import ExchangeClient
        from arbihedron.config import arbihedron.config as config
        
        # Mock exchange client
        mock_exchange = Mock(spec=ExchangeClient)
        mock_exchange.get_triangular_pairs = Mock(return_value=[
            {
                'path': ['BTC/USDT', 'ETH/BTC', 'ETH/USDT'],
                'symbols': ['BTC/USDT', 'ETH/BTC', 'ETH/USDT']
            }
        ])
        
        mock_exchange.fetch_ticker = AsyncMock(return_value={
            'bid': 50000,
            'ask': 50010,
            'last': 50005
        })
        
        engine = ArbitrageEngine(mock_exchange, config.trading)
        
        # This would test the actual workflow
        # opportunities = await engine.find_opportunities()
        # assert isinstance(opportunities, list)
    
    def test_calculate_profit(self):
        """Test profit calculation logic."""
        from arbihedron.core.arbitrage_engine import ArbitrageEngine
        from arbihedron.config import arbihedron.config as config
        
        mock_exchange = Mock()
        engine = ArbitrageEngine(mock_exchange, config.trading)
        
        # Test with sample prices
        # profit = engine.calculate_profit(prices, amounts, fees)
        # assert profit >= 0

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    def test_session_lifecycle(self):
        """Test complete session lifecycle in database."""
        from arbihedron.infrastructure.database import ArbihedronDatabase
        
        from arbihedron.models import ArbitrageOpportunity, TriangularPath
        from datetime import datetime
        
        db = ArbihedronDatabase(":memory:")  # Use in-memory DB for testing
        
        # Create session
        session_id = db.create_session("test_exchange", "kraken", {})
        assert session_id is not None
        
        # Record opportunity
        from arbihedron.models import TradingPair, TradeDirection
        
        pair = TradingPair(
            symbol="BTC/USDT", 
            base="BTC",
            quote="USDT",
            bid=50000.0, 
            ask=50001.0, 
            bid_volume=1.0,
            ask_volume=1.0,
            timestamp=datetime.now()
        )
        path = TriangularPath(
            path=["BTC", "ETH", "USDT"],
            pairs=[pair],
            directions=[TradeDirection.BUY],
            profit_percentage=1.5,
            profit_amount=50.0,
            start_amount=1000.0,
            fees_total=5.0
        )
        opp = ArbitrageOpportunity(
            path=path,
            timestamp=datetime.now(),
            expected_profit=50.0,
            executable=True,
            reason="test",
            risk_score=0.5
        )
        opportunity_id = db.save_opportunity(session_id, opp)
        assert opportunity_id is not None
        
        # End session
        db.end_session(session_id)
        
        # Verify session stats
        stats = db.get_session_stats(session_id)
        assert stats is not None
        assert stats['total_opportunities'] == 1

@pytest.mark.integration  
class TestCachingIntegration:
    """Integration tests for caching layer."""
    
    @patch('cache.redis.Redis')
    def test_cache_with_engine(self, mock_redis):
        """Test cache integration with arbitrage engine."""
        from arbihedron.infrastructure.cache import CacheManager, CacheKeys
        
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client
        
        cache = CacheManager()
        
        # Test ticker caching
        key = CacheKeys.ticker("binance", "BTC/USDT")
        cache.set(key, {"bid": 50000, "ask": 50010}, ttl=5)
        
        # Verify it was cached
        mock_client.setex.assert_called_once()

@pytest.mark.integration
class TestPerformanceMonitoring:
    """Integration tests for performance monitoring."""
    
    def test_monitor_with_real_operations(self):
        """Test performance monitor with real operations."""
        from arbihedron.infrastructure.performance import PerformanceMonitor
        import time
        
        monitor = PerformanceMonitor()
        
        # Simulate multiple operations
        for i in range(10):
            with monitor.measure("test_operation"):
                pass  # removed sleep for faster tests
        
        metrics = monitor.get_metrics("test_operation")
        assert metrics['total_operations'] == 10
        assert metrics['success_rate'] == 1.0
        assert metrics['average_duration'] > 0
        
        summary = monitor.get_summary()
        assert summary['total_operations'] == 10
        assert summary['system']['memory_mb'] > 0

@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling."""
    
    def test_circuit_breaker_with_api_calls(self):
        """Test circuit breaker with simulated API calls."""
        from arbihedron.infrastructure.error_handling import CircuitBreaker
        
        call_count = 0
        
        def unstable_api():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ConnectionError("API unavailable")
            return "success"
        
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        # open circuit after 3 failures
        for i in range(3):
            with pytest.raises(ConnectionError):
                cb.call(unstable_api)
        
        # Circuit should be open
        from arbihedron.infrastructure.error_handling import CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            cb.call(unstable_api)
    
    @pytest.mark.asyncio
    async def test_retry_with_async_operations(self):
        """Test retry logic with async operations."""
        from arbihedron.infrastructure.error_handling import async_retry_with_backoff
        
        call_count = 0
        
        @async_retry_with_backoff(max_retries=3, initial_delay=0.001)
        async def flaky_async_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            await asyncio.sleep(0.001)
            return "success"
        
        result = await flaky_async_operation()
        assert result == "success"
        assert call_count == 3

@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_arbitrage_cycle(self):
        """Test complete arbitrage detection and execution cycle."""
        # This would test the entire flow from:
        # 1. Fetching market data
        # 2. Finding opportunities
        # 3. Validating opportunities
        # 4. Executing trades (paper trading)
        # 5. Recording results
        pass
    
    def test_bot_lifecycle(self):
        """Test complete bot initialisation and shutdown."""
        # This would test:
        # 1. Bot initialisation
        # 2. Component setup
        # 3. Starting monitoring
        # 4. Graceful shutdown
        pass

@pytest.mark.integration
@pytest.mark.slow
class TestStressTests:
    """Stress and load tests."""
    
    def test_high_frequency_opportunity_detection(self):
        """Test system under high-frequency operation."""
        from arbihedron.infrastructure.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Simulate high-frequency operations
        for i in range(1000):
            with monitor.measure("detection"):
                # Simulate opportunity detection
                pass
        
        metrics = monitor.get_metrics("detection")
        assert metrics['total_operations'] == 1000
        
        # Check system resources didn't explode
        sys_metrics = monitor.get_system_metrics()
        assert sys_metrics['memory_mb'] < 1000  # Less than 1GB
    
    def test_cache_under_load(self):
        """Test cache performance under load."""
        from arbihedron.infrastructure.cache import CacheManager
        
        cache = CacheManager(enabled=False)  # Use disabled cache for testing
        
        # Simulate many cache operations
        for i in range(10000):
            cache.set(f"key_{i}", {"value": i})
            cache.get(f"key_{i}")
        
        # shouldn't crash or leak memory

@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration."""
    
    def test_config_loading(self):
        """Test configuration loads correctly."""
        from arbihedron.config import arbihedron.config as config
        
        assert config.exchange is not None
        assert config.trading is not None
        assert config.risk is not None
        assert config.alerts is not None
        
        # Verify default values
        assert config.risk.enable_paper_trading is True

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])