# Infrastructure, Performance & Testing Improvements

This document describes the infrastructure, performance, and testing improvements made to Arbihedron.

## 🐳 Docker Containerization

### Features
- Multi-stage Docker builds for development, production, testing, and GNN-enabled deployments
- Docker Compose orchestration with Redis caching
- Health checks and auto-restart policies
- Separate profiles for development, production, and monitoring

### Usage

**Standard Deployment:**
```bash
docker-compose up -d
```

**Development Mode with Hot Reload:**
```bash
docker-compose --profile dev up
```

**GNN-Enabled Mode:**
```bash
docker-compose --profile gnn up arbihedron-gnn
```

**With Monitoring (Prometheus & Grafana):**
```bash
docker-compose --profile monitoring up
```

**View Logs:**
```bash
docker-compose logs -f arbihedron
```

**Rebuild Containers:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Accessing Services
- Arbihedron API: http://localhost:8000
- GNN Engine: http://localhost:8001
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Redis: localhost:6379

##  CI/CD Pipeline

### GitHub Actions Workflows

The CI/CD pipeline automatically runs on every push and pull request:

1. **Linting & Code Quality**
   - Black formatting check
   - isort import sorting
   - Flake8 linting
   - MyPy type checking

2. **Security Scanning**
   - Safety dependency vulnerability check
   - Bandit security analysis

3. **Testing**
   - Unit tests with coverage (Python 3.9, 3.10, 3.11)
   - Integration tests with Redis
   - Performance benchmarks
   - Coverage reporting to Codecov

4. **Docker Build & Push**
   - Multi-architecture builds
   - Automatic tagging (latest, version, branch)
   - Push to GitHub Container Registry

5. **Performance Monitoring**
   - Benchmark tracking over time
   - Performance regression detection

### Manual Workflow Trigger
```bash
# Trigger workflow manually from GitHub UI or:
gh workflow run ci-cd.yml
```

### Required Secrets
Configure these in GitHub repository settings:
- `GITHUB_TOKEN` (automatically provided)
- Optional: `SLACK_WEBHOOK` for notifications
- Optional: `CODECOV_TOKEN` for coverage reporting

##  Performance Monitoring

### PerformanceMonitor

Track operation performance and system metrics:

```python
from performance import performance_monitor

# Measure operation time
with performance_monitor.measure("fetch_data"):
    data = await exchange.fetch_ticker(symbol)

# Get metrics
metrics = performance_monitor.get_metrics("fetch_data")
print(f"Average: {metrics['average_duration']:.3f}s")
print(f"Success rate: {metrics['success_rate']:.1%}")

# Get system metrics
sys_metrics = performance_monitor.get_system_metrics()
print(f"CPU: {sys_metrics['cpu_percent']:.1f}%")
print(f"Memory: {sys_metrics['memory_mb']:.1f} MB")

# Log comprehensive summary
performance_monitor.log_summary()
```

### Rate Limiting

Prevent API rate limit violations:

```python
from performance import RateLimiter

# Allow max 10 calls per 60 seconds
limiter = RateLimiter(max_calls=10, time_window=60)

# Check if call is allowed
if limiter.is_allowed():
    result = await api_call()

# Or wait automatically
limiter.wait_if_needed()
result = await api_call()

# Get statistics
stats = limiter.get_stats()
print(f"Utilization: {stats['utilization']:.1%}")
```

## 💾 Redis Caching

### CacheManager

Reduce API calls with intelligent caching:

```python
from cache import CacheManager, CacheKeys

# Initialize cache
cache = CacheManager(host="localhost", port=6379)

# Basic operations
cache.set("key", {"data": "value"}, ttl=60)
value = cache.get("key")
cache.delete("key")

# Pattern deletion
cache.delete_pattern("ticker:*")

# Cache statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Total keys: {stats['total_keys']}")
```

### Cache Decorator

Automatically cache function results:

```python
from cache import cache_result

class ExchangeClient:
    def __init__(self):
        self.cache_manager = CacheManager()
    
    @cache_result(ttl=30, key_prefix="ticker")
    def fetch_ticker(self, symbol):
        # This result will be cached for 30 seconds
        return self._fetch_from_api(symbol)
```

### Standard Cache Keys

```python
from cache import CacheKeys

# Consistent key generation
ticker_key = CacheKeys.ticker("binance", "BTC/USDT")
orderbook_key = CacheKeys.orderbook("kraken", "ETH/BTC")
opportunity_key = CacheKeys.opportunity("binance", "BTC-ETH-USDT")
```

##  Error Handling

### Circuit Breaker

Prevent cascading failures:

```python
from error_handling import CircuitBreaker

# Create circuit breaker
cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    name="exchange_api"
)

# Synchronous call
try:
    result = cb.call(api_function, arg1, arg2)
except CircuitBreakerError:
    print("Circuit is open, service unavailable")

# Async call
result = await cb.call_async(async_api_function, arg1)

# Check state
state = cb.get_state()
print(f"State: {state['state']}, Failures: {state['failure_count']}")
```

### Retry with Backoff

Automatically retry failed operations:

```python
from error_handling import retry_with_backoff, async_retry_with_backoff

# Sync decorator
@retry_with_backoff(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    exceptions=(ConnectionError, TimeoutError)
)
def fetch_data():
    return requests.get(url)

# Async decorator
@async_retry_with_backoff(max_retries=3, initial_delay=1.0)
async def fetch_data_async():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### Safe Executor

Execute with fallback:

```python
from error_handling import SafeExecutor

# Try primary, use fallback on failure
result = SafeExecutor.execute_with_fallback(
    primary=lambda: api_v2.fetch_data(),
    fallback=lambda: api_v1.fetch_data()
)

# Async version
result = await SafeExecutor.execute_with_fallback_async(
    primary=async_primary_func,
    fallback=async_fallback_func
)
```

### Global Error Handler

```python
from error_handling import error_handler

# Get circuit breaker
cb = error_handler.get_circuit_breaker("api", failure_threshold=5)

# Record errors
error_handler.record_error("ConnectionError")

# Get statistics
stats = error_handler.get_error_stats()
print(f"Total errors: {stats['total_errors']}")

# Reset all circuits
error_handler.reset_all_circuits()
```

## 🧪 Testing

### Running Tests

**All tests:**
```bash
pytest
```

**Unit tests only:**
```bash
pytest -m unit
```

**Integration tests:**
```bash
pytest -m integration
```

**With coverage:**
```bash
pytest --cov=. --cov-report=html
```

**Specific test file:**
```bash
pytest tests/test_error_handling.py -v
```

**Parallel execution:**
```bash
pytest -n auto
```

### Test Markers

Tests are organized with markers:
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.benchmark` - Performance benchmarks
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.requires_redis` - Needs Redis
- `@pytest.mark.requires_exchange` - Needs exchange API

### Coverage Reports

After running tests with coverage:
- Terminal: Immediate summary
- HTML: `htmlcov/index.html`
- XML: `coverage.xml` (for CI/CD)

##  Monitoring & Observability

### Prometheus Metrics

The system exposes Prometheus-compatible metrics:

```python
# Custom metrics can be added
from prometheus_client import Counter, Histogram

opportunities_found = Counter(
    'arbitrage_opportunities_found',
    'Number of arbitrage opportunities found'
)

execution_time = Histogram(
    'trade_execution_seconds',
    'Time spent executing trades'
)
```

Access metrics at: http://localhost:8000/metrics

### Grafana Dashboards

Pre-configured dashboards monitor:
- Opportunity detection rate
- Success/failure rates
- API call latency
- System resources
- Cache hit rates
- Circuit breaker states

Access at: http://localhost:3000

### Logging

Enhanced structured logging with loguru:

```python
from loguru import logger

logger.info("Operation completed", operation="detect", duration=0.5)
logger.warning("Rate limit approaching", current=8, max=10)
logger.error("API call failed", error=str(e), retry_count=3)
```

##  Performance Optimization Tips

1. **Enable Redis Caching**
   ```bash
   # In .env
   REDIS_ENABLED=true
   REDIS_HOST=localhost
   ```

2. **Use Connection Pooling**
   - Reuse HTTP connections
   - Configure appropriate pool sizes

3. **Adjust Rate Limits**
   ```python
   # Match exchange limits
   limiter = RateLimiter(max_calls=100, time_window=60)
   ```

4. **Monitor Performance**
   ```python
   # Regular monitoring
   if metrics['average_duration'] > 1.0:
       logger.warning("Performance degradation detected")
   ```

5. **Circuit Breaker Tuning**
   ```python
   # Adjust based on service reliability
   cb = CircuitBreaker(
       failure_threshold=10,  # More tolerant
       recovery_timeout=30    # Faster recovery
   )
   ```

##  Configuration

Add to `.env`:

```bash
# Redis Configuration
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Performance
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_METRICS_EXPORT=true

# Error Handling
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
MAX_RETRY_ATTEMPTS=3

# Monitoring
PROMETHEUS_PORT=9090
METRICS_ENABLED=true
```

## 📋 Best Practices

1. **Always use paper trading first**
2. **Monitor system resources**
3. **Set appropriate rate limits**
4. **Enable caching for frequently accessed data**
5. **Use circuit breakers for external services**
6. **Add retry logic for transient failures**
7. **Log important operations with context**
8. **Run integration tests before deployment**
9. **Review performance metrics regularly**
10. **Keep dependencies updated and secure**

##  Troubleshooting

### Docker Issues

**Container won't start:**
```bash
docker-compose logs arbihedron
docker-compose down -v
docker-compose up -d
```

**Port already in use:**
```bash
# Change port in docker-compose.yml
ports:
  - "8080:8000"  # Host:Container
```

### Redis Connection Issues

**Redis not connecting:**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

### Test Failures

**Import errors:**
```bash
pip install -r requirements.txt
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Redis required tests failing:**
```bash
# Skip Redis tests
pytest -m "not requires_redis"
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Redis Documentation](https://redis.io/docs/)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)
