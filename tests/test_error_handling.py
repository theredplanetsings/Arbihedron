"""Comprehensive unit tests for error handling utilities."""
import pytest
import time
import asyncio
from error_handling import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError,
    retry_with_backoff,
    async_retry_with_backoff,
    ErrorHandler,
    SafeExecutor,
)

class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3, name="test")
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, name="test")
        
        def failing_func():
            raise ValueError("Test error")
        
        # Fail 3 times to open circuit
        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3
        
        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            cb.call(failing_func)
    
    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, name="test")
        
        def failing_func():
            raise ValueError("Test error")
        
        def success_func():
            return "recovered"
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.01)
        
        # Should enter half-open and succeed
        result = cb.call(success_func)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_manual_reset(self):
        """Test manual reset of circuit breaker."""
        cb = CircuitBreaker(failure_threshold=2, name="test")
        
        def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Manual reset
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_async(self):
        """Test circuit breaker with async functions."""
        cb = CircuitBreaker(failure_threshold=2, name="test_async")
        
        async def success_func():
            await asyncio.sleep(0.001)
            return "async_success"
        
        result = await cb.call_async(success_func)
        assert result == "async_success"
        assert cb.state == CircuitState.CLOSED


class TestRetryDecorator:
    """Test retry with backoff decorator."""
    
    def test_retry_succeeds_first_attempt(self):
        """Test retry when function succeeds on first attempt."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_succeeds_after_failures(self):
        """Test retry succeeds after initial failures."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.001)
        def eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = eventual_success()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausts_attempts(self):
        """Test retry fails after max attempts."""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, initial_delay=0.001)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert call_count == 3  # Initial + 2 retries
    
    def test_retry_exponential_backoff(self):
        """Test exponential backoff timing."""
        start_time = time.time()
        call_count = 0
        
        @retry_with_backoff(
            max_retries=2,
            initial_delay=0.001,
            backoff_factor=2.0,
        )
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test")
        
        with pytest.raises(ValueError):
            failing_func()
        
        duration = time.time() - start_time
        # Should be at least 0.1 + 0.2 = 0.3 seconds
        assert duration >= 0.3
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_retry_succeeds(self):
        """Test async retry decorator."""
        call_count = 0
        
        @async_retry_with_backoff(max_retries=2, initial_delay=0.001)
        async def async_eventual_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not yet")
            await asyncio.sleep(0.05)
            return "async_success"
        
        result = await async_eventual_success()
        assert result == "async_success"
        assert call_count == 2


class TestErrorHandler:
    """Test error handler functionality."""
    
    def test_get_circuit_breaker(self):
        """Test getting or creating circuit breakers."""
        handler = ErrorHandler()
        
        cb1 = handler.get_circuit_breaker("api1")
        cb2 = handler.get_circuit_breaker("api2")
        cb1_again = handler.get_circuit_breaker("api1")
        
        assert cb1 is not cb2
        assert cb1 is cb1_again
        assert cb1.name == "api1"
        assert cb2.name == "api2"
    
    def test_record_error(self):
        """Test error recording."""
        handler = ErrorHandler()
        
        handler.record_error("NetworkError")
        handler.record_error("NetworkError")
        handler.record_error("TimeoutError")
        
        stats = handler.get_error_stats()
        assert stats['total_errors'] == 3
        assert stats['error_types']['NetworkError'] == 2
        assert stats['error_types']['TimeoutError'] == 1
    
    def test_reset_all_circuits(self):
        """Test resetting all circuit breakers."""
        handler = ErrorHandler()
        
        cb1 = handler.get_circuit_breaker("api1", failure_threshold=1)
        cb2 = handler.get_circuit_breaker("api2", failure_threshold=1)
        
        # Open both circuits
        def failing():
            raise ValueError("Test")
        
        with pytest.raises(ValueError):
            cb1.call(failing)
        with pytest.raises(ValueError):
            cb2.call(failing)
        
        assert cb1.state == CircuitState.OPEN
        assert cb2.state == CircuitState.OPEN
        
        # Reset all
        handler.reset_all_circuits()
        
        assert cb1.state == CircuitState.CLOSED
        assert cb2.state == CircuitState.CLOSED

class TestSafeExecutor:
    """Test safe executor functionality."""
    
    def test_execute_with_fallback_primary_succeeds(self):
        """Test fallback when primary succeeds."""
        def primary():
            return "primary_result"
        
        def fallback():
            return "fallback_result"
        
        result = SafeExecutor.execute_with_fallback(primary, fallback)
        assert result == "primary_result"
    
    def test_execute_with_fallback_primary_fails(self):
        """Test fallback when primary fails."""
        def primary():
            raise ValueError("Primary failed")
        
        def fallback():
            return "fallback_result"
        
        result = SafeExecutor.execute_with_fallback(primary, fallback)
        assert result == "fallback_result"
    
    def test_execute_with_fallback_both_fail(self):
        """Test when both primary and fallback fail."""
        def primary():
            raise ValueError("Primary failed")
        
        def fallback():
            raise RuntimeError("Fallback failed")
        
        with pytest.raises(RuntimeError):
            SafeExecutor.execute_with_fallback(primary, fallback)
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_async(self):
        """Test async fallback execution."""
        async def primary():
            raise ValueError("Primary failed")
        
        async def fallback():
            await asyncio.sleep(0.05)
            return "async_fallback"
        
        result = await SafeExecutor.execute_with_fallback_async(primary, fallback)
        assert result == "async_fallback"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])