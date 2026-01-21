# Arbihedron Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    ARBIHEDRON SYSTEM                     │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌──────────────┐   ┌──────────────┐
│  Main Bot     │   │   Monitor    │   │   Config     │
│  Orchestrator │   │   Dashboard  │   │   Manager    │
└───────┬───────┘   └──────────────┘   └──────────────┘
        │
        ├─────────────┬──────────────┬──────────────┐
        ▼             ▼              ▼              ▼
┌──────────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│  Arbitrage   │ │Exchange │ │  Trade   │ │  Risk    │
│  Engine      │ │ Client  │ │ Executor │ │ Manager  │
└──────────────┘ └─────────┘ └──────────┘ └──────────┘
        │             │              │
        └─────────────┴──────────────┘
                      │
              ┌───────┴────────┐
              ▼                ▼
        ┌──────────┐    ┌──────────┐
        │ Exchange │    │ Exchange │
        │ API      │    │ WebSocket│
        └──────────┘    └──────────┘
```

## Component Responsibilities

### 1. Main Bot Orchestrator (`main.py`)

The bot orchestrates:
- Initialises all components
- Manages event loop
- Coordinates shutdown
- Signal handling (SIGTERM, SIGINT)

### 2. Exchange Client (`exchange_client.py`)
- Connects to exchange APIs via CCXT
- Fetches market data and tickers
- Executes orders
- Manages rate limiting
- Handles authentication
- Provides order book data

### 3. Arbitrage Engine (`arbitrage_engine.py`)
- Discovers triangular trading paths
- Calculates profit opportunities
- Evaluates risk scores
- Generates market snapshots
- Maintains trading pair graph

### 4. Trade Executor (`executor.py`)
- Executes arbitrage sequences
- Manages order placement
- Calculates actual profits
- Tracks slippage
- Enforces rate limits
- Maintains execution history

### 5. Monitor (`monitor.py`)
- Real-time dashboard display
- Rich terminal UI
- Statistics tracking
- Opportunity logging
- Performance metrics

### 6. Configuration (`config.py`)
- Environment variable management
- Configuration validation
- Settings schema with Pydantic
- Default values

### 7. Models (`models.py`)
- Data structures
- Trading pair representation
- Opportunity models
- Execution records

## Data Flow

### Opportunity Discovery Flow
```
1. Exchange Client
   ↓ Fetch market data
2. Arbitrage Engine
   ↓ Calculate opportunities
3. Risk Manager
   ↓ Evaluate risk
4. Trade Executor
   ↓ Execute trades
5. Monitor
   ↓ Display results
```

### Execution Flow
```
Start Trade
    ↓
Check Rate Limits
    ↓
Validate Opportunity
    ↓
Execute Step 1: A → B
    ↓
Execute Step 2: B → C
    ↓
Execute Step 3: C → A
    ↓
Calculate Profit
    ↓
Update Statistics
    ↓
End Trade
```

## Key Algorithms

### Triangular Path Discovery
```python
1. Load all trading pairs from exchange
2. Build currency adjacency graph
3. For each base currency:
   a. Find all connected currencies (1 hop)
   b. For each connected currency:
      - Find currencies 2 hops away
      - Check if path back to base exists
   c. Store valid triangular paths
4. Return all unique paths
```

### Profit Calculation
```python
amount = start_amount

for each step in path:
    if buying:
        amount = amount / ask_price
        amount = amount * (1 - fee)
    else:
        amount = amount * bid_price
        amount = amount * (1 - fee)

profit = amount - start_amount
profit_pct = (profit / start_amount) * 100
```

### Risk Scoring
```python
risk_score = 0

# Spread risk
risk_score += average_spread * 10

# Liquidity risk
if min_volume < 10000:
    risk_score += 20
elif min_volume < 50000:
    risk_score += 10

# Complexity risk
risk_score += 5

return min(risk_score, 100)
```

## Performance Considerations

### Latency Optimisation
- Parallel ticker fetching with `asyncio.gather()`
- Connection pooling in CCXT
- Market order execution (fast)
- Minimal data processing

### Memory Management
- Limited execution history
- Efficient data structures
- Periodic cleanup of old records

### Rate Limiting
- CCXT's built-in rate limiter
- Custom hourly trade limits
- Exponential backoff on errors

## Error Handling

### Exchange Errors
- API rate limits → Wait and retry
- Network errors → Exponential backoff
- Invalid orders → Skip and log

### Execution Errors
- Partial fills → Calculate actual profit
- Order rejection → Mark as failed
- Timeout → Cancel and retry

### System Errors
- Memory issues → Cleanup old data
- File I/O errors → Log to console
- Configuration errors → Fail fast

## Security Considerations

### API Key Protection
- Never commit `.env` to git
- Use environment variables
- Restrict API key permissions
- Separate keys for paper/live trading

### Exchange Security
- Enable 2FA on exchange account
- Whitelist IP addresses
- Use read-only keys for monitoring
- Limit withdrawal permissions

### Code Security
- Input validation
- Safe type conversions
- Exception handling
- Audit logging

## Scalability

### Horizontal Scaling
- Run multiple instances on different exchanges
- Distribute path scanning across processes
- Use message queues for coordination

### Vertical Scaling
- Optimise data structures
- Use C extensions for hot paths
- Implement WebSocket streaming
- Database for historical data

## Testing Strategy

Comprehensive test suite with 90%+ coverage. See individual test files in `tests/` directory.

### Unit Tests
- Model validation and data structures
- Configuration parsing and validation
- Utility functions and calculations
- Algorithm accuracy

### Integration Tests
- Exchange client connectivity
- Path discovery and validation
- Opportunity scanning and detection
- Execution simulation
- Cache and database operations

### End-to-End Tests
- Full bot lifecycle
- Error recovery and circuit breakers
- Graceful shutdown and cleanup
- Performance benchmarks and profiling

### Running Tests
```bash
pytest                          # Run all tests
pytest --cov=. --cov-report=html  # With coverage
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
```

See [INFRASTRUCTURE.md](../docs/INFRASTRUCTURE.md) for detailed testing guide.

## Monitoring & Logging

### Metrics to Track
- Opportunities per hour
- Execution success rate
- Average slippage
- Total profit/loss
- API call latency
- Cache hit rates
- Circuit breaker states

### Logging Levels
- DEBUG: Detailed execution flow
- INFO: Opportunities and executions
- WARNING: Rate limits, low liquidity
- ERROR: Failed trades, API errors
- SUCCESS: Successful executions

See [logs.md](logs.md) for logging configuration.

---

**This architecture prioritises:**
- Speed (high-frequency execution)
- Safety (paper trading, risk management)
- Reliability (error handling, logging)
- Maintainability (modular design)
