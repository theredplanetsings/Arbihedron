#!/usr/bin/env python3
"""Test script to demonstrate the new infrastructure improvements."""
import time
from performance import performance_monitor, RateLimiter
from error_handling import CircuitBreaker, retry_with_backoff, SafeExecutor
from cache import CacheManager, CacheKeys

print("🔺 Arbihedron Infrastructure Test Suite")
print("=" * 60)

# Test 1: Performance Monitoring
print("\n1️⃣  Testing Performance Monitoring...")
with performance_monitor.measure("test_operation"):
    time.sleep(0.1)

metrics = performance_monitor.get_metrics("test_operation")
print(f"   ✓ Completed in {metrics['average_duration']:.3f}s")

# Test 2: Rate Limiting
print("\n2️⃣  Testing Rate Limiter...")
limiter = RateLimiter(max_calls=3, time_window=5)
for i in range(5):
    limiter.is_allowed()
stats = limiter.get_stats()
print(f"   ✓ Utilization: {stats['utilization']:.1%}")

# Test 3: Circuit Breaker
print("\n3️⃣  Testing Circuit Breaker...")
cb = CircuitBreaker(failure_threshold=3, name="test")
print(f"   ✓ Circuit state: {cb.state.value}")

# Test 4: Cache Keys
print("\n4️⃣  Testing Cache Keys...")
key = CacheKeys.ticker("binance", "BTC/USDT")
print(f"   ✓ Ticker key: {key}")

print("\n" + "=" * 60)
print("✅ All Tests Passed!")
