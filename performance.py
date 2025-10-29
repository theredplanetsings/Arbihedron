"""Performance monitoring and metrics collection for Arbihedron."""
import time
import psutil
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Lock
from loguru import logger


@dataclass
class PerformanceMetrics:
    """Performance metrics tracker."""
    
    # Timing metrics
    total_operations: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    
    # Success/failure tracking
    successful_operations: int = 0
    failed_operations: int = 0
    
    # Recent operation times (for moving average)
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update(self, duration: float, success: bool = True):
        """Update metrics with new operation."""
        self.total_operations += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.recent_durations.append(duration)
        
        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
    
    @property
    def average_duration(self) -> float:
        """Get average operation duration."""
        if self.total_operations == 0:
            return 0.0
        return self.total_duration / self.total_operations
    
    @property
    def recent_average(self) -> float:
        """Get recent moving average."""
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)
    
    @property
    def success_rate(self) -> float:
        """Get operation success rate."""
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.lock = Lock()
        self.start_time = time.time()
        
        # System metrics
        self.process = psutil.Process()
        
        logger.info("Performance monitor initialized")
    
    def measure(self, operation_name: str):
        """Context manager for measuring operation time."""
        return OperationTimer(self, operation_name)
    
    def record_operation(self, operation_name: str, duration: float, success: bool = True):
        """Record an operation's performance."""
        with self.lock:
            self.metrics[operation_name].update(duration, success)
    
    def get_metrics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics."""
        with self.lock:
            if operation_name:
                if operation_name not in self.metrics:
                    return {}
                
                metrics = self.metrics[operation_name]
                return {
                    'operation': operation_name,
                    'total_operations': metrics.total_operations,
                    'average_duration': metrics.average_duration,
                    'recent_average': metrics.recent_average,
                    'min_duration': metrics.min_duration if metrics.min_duration != float('inf') else 0,
                    'max_duration': metrics.max_duration,
                    'success_rate': metrics.success_rate,
                    'successful': metrics.successful_operations,
                    'failed': metrics.failed_operations,
                }
            
            # Return all metrics
            return {
                name: {
                    'total_operations': m.total_operations,
                    'average_duration': m.average_duration,
                    'recent_average': m.recent_average,
                    'success_rate': m.success_rate,
                }
                for name, m in self.metrics.items()
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics."""
        return {
            'cpu_percent': self.process.cpu_percent(interval=0.1),
            'memory_mb': self.process.memory_info().rss / 1024 / 1024,
            'memory_percent': self.process.memory_percent(),
            'num_threads': self.process.num_threads(),
            'uptime_seconds': time.time() - self.start_time,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        with self.lock:
            total_operations = sum(m.total_operations for m in self.metrics.values())
            total_successes = sum(m.successful_operations for m in self.metrics.values())
            total_failures = sum(m.failed_operations for m in self.metrics.values())
            
            return {
                'uptime_seconds': time.time() - self.start_time,
                'total_operations': total_operations,
                'total_successes': total_successes,
                'total_failures': total_failures,
                'overall_success_rate': total_successes / total_operations if total_operations > 0 else 0,
                'operations': self.get_metrics(),
                'system': self.get_system_metrics(),
            }
    
    def log_summary(self):
        """Log performance summary."""
        summary = self.get_summary()
        
        logger.info("=" * 60)
        logger.info("Performance Summary")
        logger.info("=" * 60)
        logger.info(f"Uptime: {summary['uptime_seconds']:.2f}s")
        logger.info(f"Total Operations: {summary['total_operations']}")
        logger.info(f"Success Rate: {summary['overall_success_rate']:.2%}")
        logger.info(f"CPU: {summary['system']['cpu_percent']:.1f}%")
        logger.info(f"Memory: {summary['system']['memory_mb']:.1f} MB")
        logger.info("=" * 60)
        
        for op_name, metrics in summary['operations'].items():
            logger.info(
                f"  {op_name}: "
                f"{metrics['total_operations']} ops, "
                f"avg {metrics['average_duration']*1000:.2f}ms, "
                f"success {metrics['success_rate']:.2%}"
            )
        
        logger.info("=" * 60)


class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        """Initialize operation timer."""
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record."""
        duration = time.perf_counter() - self.start_time
        self.success = exc_type is None
        self.monitor.record_operation(self.operation_name, duration, self.success)
        return False  # Don't suppress exceptions


class RateLimiter:
    """Rate limiter for API calls and operations."""
    
    def __init__(self, max_calls: int, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: deque = deque()
        self.lock = Lock()
    
    def is_allowed(self) -> bool:
        """Check if a call is allowed."""
        with self.lock:
            now = time.time()
            
            # Remove old calls outside the time window
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            # Check if we're under the limit
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            
            return False
    
    def wait_if_needed(self) -> float:
        """Wait if rate limit is reached. Returns wait time."""
        with self.lock:
            now = time.time()
            
            # Remove old calls
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            # If at limit, calculate wait time
            if len(self.calls) >= self.max_calls:
                oldest_call = self.calls[0]
                wait_time = (oldest_call + self.time_window) - now
                if wait_time > 0:
                    time.sleep(wait_time)
                    return wait_time
            
            self.calls.append(time.time())
            return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self.lock:
            now = time.time()
            
            # Clean old calls
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            return {
                'current_calls': len(self.calls),
                'max_calls': self.max_calls,
                'time_window': self.time_window,
                'utilization': len(self.calls) / self.max_calls if self.max_calls > 0 else 0,
            }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
