"""Comprehensive unit tests for performance monitoring."""
import pytest
import time
from performance import (
    PerformanceMetrics,
    PerformanceMonitor,
    OperationTimer,
    RateLimiter,
    performance_monitor,
)


class TestPerformanceMetrics:
    """Test performance metrics data structure."""
    
    def test_initial_state(self):
        """Test initial metrics state."""
        metrics = PerformanceMetrics()
        
        assert metrics.total_operations == 0
        assert metrics.total_duration == 0.0
        assert metrics.successful_operations == 0
        assert metrics.failed_operations == 0
        assert metrics.average_duration == 0.0
        assert metrics.success_rate == 0.0
    
    def test_update_success(self):
        """Test updating metrics with successful operation."""
        metrics = PerformanceMetrics()
        
        metrics.update(0.5, success=True)
        
        assert metrics.total_operations == 1
        assert metrics.total_duration == 0.5
        assert metrics.successful_operations == 1
        assert metrics.failed_operations == 0
        assert metrics.average_duration == 0.5
        assert metrics.success_rate == 1.0
    
    def test_update_failure(self):
        """Test updating metrics with failed operation."""
        metrics = PerformanceMetrics()
        
        metrics.update(0.3, success=False)
        
        assert metrics.total_operations == 1
        assert metrics.failed_operations == 1
        assert metrics.success_rate == 0.0
    
    def test_multiple_updates(self):
        """Test multiple metric updates."""
        metrics = PerformanceMetrics()
        
        metrics.update(0.1, success=True)
        metrics.update(0.2, success=True)
        metrics.update(0.3, success=False)
        
        assert metrics.total_operations == 3
        assert metrics.successful_operations == 2
        assert metrics.failed_operations == 1
        assert metrics.average_duration == pytest.approx(0.2)
        assert metrics.success_rate == pytest.approx(0.666, rel=0.01)
    
    def test_min_max_duration(self):
        """Test min and max duration tracking."""
        metrics = PerformanceMetrics()
        
        metrics.update(0.5)
        metrics.update(0.1)
        metrics.update(0.8)
        
        assert metrics.min_duration == 0.1
        assert metrics.max_duration == 0.8
    
    def test_recent_average(self):
        """Test recent moving average."""
        metrics = PerformanceMetrics()
        
        for i in range(10):
            metrics.update(i * 0.1)
        
        assert len(metrics.recent_durations) == 10
        assert metrics.recent_average > 0


class TestPerformanceMonitor:
    """Test performance monitor functionality."""
    
    def test_initialization(self):
        """Test monitor initialization."""
        monitor = PerformanceMonitor()
        
        assert isinstance(monitor.metrics, dict)
        assert monitor.start_time > 0
    
    def test_record_operation(self):
        """Test recording operations."""
        monitor = PerformanceMonitor()
        
        monitor.record_operation("test_op", 0.5, success=True)
        
        metrics = monitor.get_metrics("test_op")
        assert metrics['total_operations'] == 1
        assert metrics['average_duration'] == 0.5
        assert metrics['success_rate'] == 1.0
    
    def test_measure_context_manager(self):
        """Test operation measurement context manager."""
        monitor = PerformanceMonitor()
        
        with monitor.measure("test_operation"):
            time.sleep(0.1)
        
        metrics = monitor.get_metrics("test_operation")
        assert metrics['total_operations'] == 1
        assert metrics['average_duration'] >= 0.1
        assert metrics['successful'] == 1
    
    def test_measure_with_exception(self):
        """Test measurement with exception."""
        monitor = PerformanceMonitor()
        
        try:
            with monitor.measure("failing_op"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        metrics = monitor.get_metrics("failing_op")
        assert metrics['total_operations'] == 1
        assert metrics['failed'] == 1
        assert metrics['success_rate'] == 0.0
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        monitor = PerformanceMonitor()
        
        monitor.record_operation("op1", 0.1)
        monitor.record_operation("op2", 0.2)
        
        all_metrics = monitor.get_metrics()
        assert 'op1' in all_metrics
        assert 'op2' in all_metrics
    
    def test_system_metrics(self):
        """Test system metrics collection."""
        monitor = PerformanceMonitor()
        
        sys_metrics = monitor.get_system_metrics()
        
        assert 'cpu_percent' in sys_metrics
        assert 'memory_mb' in sys_metrics
        assert 'memory_percent' in sys_metrics
        assert 'num_threads' in sys_metrics
        assert 'uptime_seconds' in sys_metrics
        
        assert sys_metrics['memory_mb'] > 0
        assert sys_metrics['uptime_seconds'] >= 0
    
    def test_get_summary(self):
        """Test comprehensive summary."""
        monitor = PerformanceMonitor()
        
        monitor.record_operation("op1", 0.1, success=True)
        monitor.record_operation("op2", 0.2, success=False)
        
        summary = monitor.get_summary()
        
        assert 'uptime_seconds' in summary
        assert 'total_operations' in summary
        assert 'total_successes' in summary
        assert 'total_failures' in summary
        assert 'overall_success_rate' in summary
        assert 'operations' in summary
        assert 'system' in summary
        
        assert summary['total_operations'] == 2
        assert summary['total_successes'] == 1
        assert summary['total_failures'] == 1


class TestOperationTimer:
    """Test operation timer context manager."""
    
    def test_timer_measures_duration(self):
        """Test timer measures operation duration."""
        monitor = PerformanceMonitor()
        timer = OperationTimer(monitor, "test_op")
        
        with timer:
            time.sleep(0.1)
        
        metrics = monitor.get_metrics("test_op")
        assert metrics['average_duration'] >= 0.1
    
    def test_timer_marks_failure_on_exception(self):
        """Test timer marks operation as failed on exception."""
        monitor = PerformanceMonitor()
        
        try:
            with OperationTimer(monitor, "failing_op"):
                raise ValueError("Test")
        except ValueError:
            pass
        
        metrics = monitor.get_metrics("failing_op")
        assert metrics['failed'] == 1
        assert metrics['successful'] == 0


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def test_initial_calls_allowed(self):
        """Test initial calls are allowed."""
        limiter = RateLimiter(max_calls=5, time_window=1)
        
        for _ in range(5):
            assert limiter.is_allowed() is True
    
    def test_calls_blocked_after_limit(self):
        """Test calls are blocked after limit."""
        limiter = RateLimiter(max_calls=3, time_window=1)
        
        for _ in range(3):
            assert limiter.is_allowed() is True
        
        assert limiter.is_allowed() is False
    
    def test_calls_allowed_after_window(self):
        """Test calls allowed after time window expires."""
        limiter = RateLimiter(max_calls=2, time_window=1)
        
        # Use up calls
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is True
        assert limiter.is_allowed() is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        assert limiter.is_allowed() is True
    
    def test_wait_if_needed(self):
        """Test wait_if_needed blocks when at limit."""
        limiter = RateLimiter(max_calls=2, time_window=1)
        
        # Use up calls
        limiter.is_allowed()
        limiter.is_allowed()
        
        # This should wait
        start = time.time()
        wait_time = limiter.wait_if_needed()
        duration = time.time() - start
        
        assert wait_time >= 0
        assert duration >= wait_time
    
    def test_get_stats(self):
        """Test rate limiter statistics."""
        limiter = RateLimiter(max_calls=5, time_window=60)
        
        limiter.is_allowed()
        limiter.is_allowed()
        
        stats = limiter.get_stats()
        
        assert stats['current_calls'] == 2
        assert stats['max_calls'] == 5
        assert stats['time_window'] == 60
        assert stats['utilization'] == pytest.approx(0.4)


class TestIntegration:
    """Integration tests for performance monitoring."""
    
    def test_multiple_operations_tracking(self):
        """Test tracking multiple operations."""
        monitor = PerformanceMonitor()
        
        # Simulate various operations
        with monitor.measure("fetch_data"):
            time.sleep(0.05)
        
        with monitor.measure("process_data"):
            time.sleep(0.03)
        
        with monitor.measure("fetch_data"):
            time.sleep(0.04)
        
        # Check fetch_data metrics
        fetch_metrics = monitor.get_metrics("fetch_data")
        assert fetch_metrics['total_operations'] == 2
        assert fetch_metrics['success_rate'] == 1.0
        
        # Check process_data metrics
        process_metrics = monitor.get_metrics("process_data")
        assert process_metrics['total_operations'] == 1
        
        # Check summary
        summary = monitor.get_summary()
        assert summary['total_operations'] == 3
        assert summary['total_successes'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
