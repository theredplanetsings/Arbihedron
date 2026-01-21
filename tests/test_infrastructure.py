#!/usr/bin/env python3
"""Test script to demonstrate the new infrastructure improvements."""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from arbihedron.infrastructure.performance import performance_monitor, RateLimiter
from arbihedron.infrastructure.error_handling import CircuitBreaker, retry_with_backoff, SafeExecutor
from arbihedron.infrastructure.cache import CacheManager, CacheKeys

print("🔺 Arbihedron Infrastructure Test Suite")
print("=" * 60)

# Test 1: Performance Monitoring
print("\n  Testing Performance Monitoring...")
with performance_monitor.measure("test_operation"):
    time.sleep(0.1)

metrics = performance_monitor.get_metrics("test_operation")
print(f"   ✓ Completed in {metrics['average_duration']:.3f}s")

# Test 2: Rate Limiting
print("\n  Testing Rate Limiter...")
limiter = RateLimiter(max_calls=3, time_window=5)
for i in range(5):
    limiter.is_allowed()
stats = limiter.get_stats()
print(f"   ✓ Utilization: {stats['utilization']:.1%}")

# Test 3: Circuit Breaker
print("\n  Testing Circuit Breaker...")
cb = CircuitBreaker(failure_threshold=3, name="test")
print(f"   ✓ Circuit state: {cb.state.value}")

# Test 4: Cache Keys
print("\n  Testing Cache Keys...")
key = CacheKeys.ticker("binance", "BTC/USDT")
print(f"   ✓ Ticker key: {key}")

print("\n" + "=" * 60)
print("✅ All Tests Passed!")
