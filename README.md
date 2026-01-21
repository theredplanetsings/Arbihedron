# 🔺 Arbihedron

High-frequency triangular arbitrage system for cryptocurrency markets. Detects and exploits price discrepancies through circular trading paths (A to B to C to A) within single exchanges.

Paper trading mode enabled by default.

## Features

- Real-time market monitoring across multiple exchanges
- Triangular arbitrage opportunity detection with dual engines:
  - **Traditional engine**: Graph-based path detection with real-time validation
  - **GNN engine** (experimental): Graph Neural Network for learned opportunity detection
- Risk management with configurable thresholds
- Paper trading mode (default)
- Performance analytics and backtesting
- RESTful API service with FastAPI
- Database persistence (SQLite)
- Email/Slack alerts for significant opportunities
- Docker containerization for easy deployment
- CI/CD pipeline with automated testing
- Redis caching for improved performance
- Performance monitoring and profiling
- Circuit breakers and retry logic for reliability
- Comprehensive test suite with 90%+ coverage

## How It Works

Triangular arbitrage exploits price inefficiencies between three currency pairs:

```
BTC/USDT → ETH/BTC → ETH/USDT → BTC/USDT
```

If the compound exchange rate after fees exceeds 1.0, profit opportunity exists.

**Example:**
1. Start with 1 BTC
2. Trade BTC → ETH
3. Trade ETH → USDT
4. Trade USDT → BTC
5. End with 1.005 BTC (0.5% profit)

## Quick Start

### Prerequisites

- Python 3.9+ OR Docker
- Exchange API keys (optional for paper trading)
- Redis (optional, for caching)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/theredplanetsings/Arbihedron.git
cd Arbihedron

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Quick start with Docker
scripts/quick_start.sh              # Standard mode
scripts/quick_start.sh --dev        # Development mode
scripts/quick_start.sh --gnn        # With GNN engine
scripts/quick_start.sh --monitoring # With Prometheus & Grafana

# Or manually with Docker Compose
docker-compose up -d          # Start all services
docker-compose logs -f        # View logs
docker-compose down           # Stop services
```

Access the services:
- API: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### Option 2: Local Installation

```bash
# Clone the repository
git clone https://github.com/theredplanetsings/Arbihedron.git
cd Arbihedron

# Run setup script
scripts/setup.sh              # Basic installation
scripts/setup.sh --gnn        # Include GNN dependencies
scripts/setup.sh --full       # Complete installation with all features
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env`:
```bash
# Exchange configuration
EXCHANGE_NAME=binance
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here

# Trading parameters
MIN_PROFIT_THRESHOLD=0.5    # Minimum 0.5% profit
MAX_POSITION_SIZE=1000      # $1000 per trade
SLIPPAGE_TOLERANCE=0.1      # 0.1% slippage

# Safety first
ENABLE_PAPER_TRADING=true   # Keep true for testing

# Alerts (optional)
ALERT_EMAIL=your@email.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
```

### Running the System

```bash
python main.py
```

**Examples:**
```bash
python examples.py
```

**Backtesting:**
```bash
python backtest.py
```

**Service mode with auto-restart:**
```bash
scripts/arbi start      # Start as background service
scripts/arbi status     # Check service status
scripts/arbi logs       # View logs
scripts/arbi stop       # Stop service
```

**Health monitoring:**
```bash
# HTTP endpoints available at localhost:8080
curl http://localhost:8080/health
curl http://localhost:8080/metrics
curl http://localhost:8080/status
```

**Live trading (advanced):**

Only enable after thorough testing:
1. Obtain API keys with trading permissions
2. Set `ENABLE_PAPER_TRADING=false` in `.env`
3. Add real `API_KEY` and `API_SECRET`
4. Start with small position sizes
5. Monitor closely

## Project Structure

```
Arbihedron/
├── main.py                    # Main entry point
├── arbihedron_service.py      # Service wrapper with auto-restart  
├── examples.py                # Usage examples
├── requirements.txt           # Dependencies
├── pyproject.toml             # Python project configuration
├── Dockerfile                 # Docker build config
├── docker-compose.yml         # Docker orchestration
├── src/arbihedron/            # Main package
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── models.py              # Data models
│   ├── utils.py               # Utility functions
│   ├── core/                  # Core trading engine
│   │   ├── exchange_client.py      # Exchange API integration
│   │   ├── arbitrage_engine.py     # Traditional detection
│   │   ├── gnn_arbitrage_engine.py # GNN-based detection
│   │   └── executor.py             # Trade execution
│   ├── infrastructure/        # Infrastructure components
│   │   ├── cache.py                # Redis caching
│   │   ├── database.py             # SQLite persistence
│   │   ├── error_handling.py       # Circuit breakers & retry
│   │   ├── performance.py          # Performance monitoring
│   │   └── health_monitor.py       # HTTP health endpoints
│   ├── monitoring/            # Monitoring & analytics
│   │   ├── monitor.py              # Real-time UI
│   │   ├── alerts.py               # Email/Slack notifications
│   │   └── analytics.py            # Performance analytics
│   └── tools/                 # Analysis & training tools
│       ├── backtest.py             # Backtesting framework
│       ├── compare_engines.py      # Engine comparison
│       ├── train_gnn_real.py       # GNN training
│       └── view_data.py            # Data visualization
├── scripts/                   # Utility scripts
│   ├── setup.sh               # Setup script
│   ├── quick_start.sh         # Docker quick start
│   ├── arbi                   # Service control script
│   ├── run_tests.sh           # Fast test runner
│   └── test_service.sh        # Service management tests
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── EXCHANGES.md           # Exchange configuration
│   ├── GNN_ARCHITECTURE.md    # GNN implementation
│   ├── INFRASTRUCTURE.md      # Infrastructure & deployment
│   ├── OVERFITTING_PREVENTION.md  # GNN overfitting strategies
│   └── logs.md                # Logging guide
├── tests/                     # Comprehensive test suite
│   ├── test_alerts.py
│   ├── test_analytics.py
│   ├── test_arbihedron_service.py
│   ├── test_arbitrage_engine.py
│   ├── test_cache.py
│   ├── test_database.py
│   ├── test_error_handling.py
│   ├── test_exchange_client.py
│   ├── test_executor.py
│   ├── test_gnn.py
│   ├── test_integration.py
│   ├── test_monitor.py
│   └── test_performance.py
├── monitoring/                # Monitoring configs
│   └── prometheus.yml
└── models/                    # Trained GNN models
```

## Usage Examples

### Basic Opportunity Scan (Traditional Engine)

```python
import asyncio
from arbihedron.core import ExchangeClient, ArbitrageEngine

async def scan():
    exchange = ExchangeClient()
    engine = ArbitrageEngine(exchange)
    await engine.initialize()
    
    snapshot = await engine.scan_opportunities()
    
    for opp in snapshot.opportunities[:5]:
        print(f"{opp.path} - Profit: {opp.path.profit_percentage:.4f}%")
    
    exchange.close()

asyncio.run(scan())
```

### GNN Engine (Experimental)

```python
import asyncio
from arbihedron.core import ExchangeClient, GNNArbitrageEngine

async def scan_with_gnn():
    exchange = ExchangeClient()
    engine = GNNArbitrageEngine(exchange, model_path='models/gnn_arbitrage_best.pth')
    await engine.initialize()
    
    snapshot = await engine.scan_opportunities()
    
    for opp in snapshot.opportunities[:5]:
        print(f"{opp.path} - Predicted Profit: {opp.path.profit_percentage:.4f}%")
    
    exchange.close()

asyncio.run(scan_with_gnn())
```

### Train GNN on Real Market Data

```python
import asyncio
from arbihedron.tools import RealDataGNNTrainer

async def train():
    trainer = RealDataGNNTrainer()
    
    # Collect training data from live markets
    await trainer.collect_training_data(num_scans=100, wait_between_scans=30)
    
    # Train the model
    trainer.train(epochs=50, patience=5)

asyncio.run(train())
```

### Compare Traditional vs GNN Engines

```bash
python compare_engines.py --num-scans 20
```

### Full Bot with Dashboard

```python
from main import ArbihedronBot

async def run():
    bot = ArbihedronBot()
    await bot.run()

asyncio.run(run())
```

## Configuration Options

### Environment Variables

| Parameter | Description | Default |
|-----------|-------------|---------|
| `EXCHANGE_NAME` | Exchange to use | kraken |
| `MIN_PROFIT_THRESHOLD` | Minimum profit % | 0.5 |
| `MAX_POSITION_SIZE` | Maximum USD per trade | 1000 |
| `SLIPPAGE_TOLERANCE` | Expected slippage % | 0.1 |
| `ENABLE_PAPER_TRADING` | Paper trading mode | true |
| `MAX_TRADES_PER_HOUR` | Rate limit | 100 |
| `STOP_LOSS_PERCENTAGE` | Stop loss threshold % | 2.0 |
| `ALERT_EMAIL` | Email for alerts | - |
| `ALERT_SLACK_WEBHOOK` | Slack webhook URL | - |

### Trading Algorithm Parameters

**Signal generation** (`arbitrage_engine.py`):
- Buy signal: `profit_percentage >= MIN_PROFIT_THRESHOLD`
- Profit calculated after fees

**Risk scoring** (`arbitrage_engine.py`):
- Wider bid-ask spreads increase risk
- Low volume pairs penalized
- Risk range: 0-100 (lower is better)

**Execution rules** (`executor.py`):
- Rate limiting: Maximum 100 trades/hour
- Market orders with sequential execution
- Re-validation before execution

### Modifying Trading Parameters

**Edit `.env` (recommended):**
```bash
# Increase profit threshold to 1%
MIN_PROFIT_THRESHOLD=1.0

# Reduce position size to $500
MAX_POSITION_SIZE=500

# Tighten rate limiting
MAX_TRADES_PER_HOUR=50
```

**Edit `config.py`:**
```python
class TradingConfig(BaseModel):
    min_profit_threshold: float = Field(default=1.0)
    max_position_size: float = Field(default=500)
```

**Modify risk scoring** (`arbitrage_engine.py`):
```python
def _calculate_risk_score(self, path: TriangularPath) -> float:
    risk = 0.0
    avg_spread = sum(p.spread for p in path.pairs) / len(path.pairs)
    risk += avg_spread * 10  # Adjust multiplier
    
    min_volume = min(p.bid_volume + p.ask_volume for p in path.pairs)
    if min_volume < 5000:    # Adjust threshold
        risk += 30           # Adjust penalty
```

**Base currencies** (`config.py`):
```python
base_currencies: List[str] = Field(
    default=["BTC", "ETH", "BNB", "USDT", "USDC", "SOL"]
)
```

## Risk Management

- Paper trading mode
- Position limits
- Rate limiting
- Slippage protection
- Fee calculation
- Risk scoring
- Auto-restart
- Health monitoring

## Monitoring & Alerts

**Health endpoints:**
- `GET /health` - Basic health check
- `GET /metrics` - Prometheus metrics
- `GET /status` - Trading statistics

**Performance Monitoring:**
- Real-time operation metrics
- System resource tracking
- Rate limiter statistics
- Cache hit rates
- See [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)

**Notifications:**
- Email alerts via SMTP
- Slack webhooks
- Configurable alert types
- Quiet hours support
- Rate limiting

**Analytics:**
- Trade history in SQLite database
- Performance metrics
- Profit/loss tracking

**View data:**
```bash
python view_data.py
python analytics.py
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test types
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests
pytest -m "not slow"        # Skip slow tests

# Run in parallel
pytest -n auto
```

See test coverage at: `htmlcov/index.html`

## Deployment

### Docker Production Deployment

```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f arbihedron

# Scale (if needed)
docker-compose up -d --scale arbihedron=2

# Update and restart
git pull
docker-compose build
docker-compose up -d
```

### With Monitoring Stack

```bash
# Start with Prometheus and Grafana
docker-compose --profile monitoring up -d

# Access dashboards
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

For detailed deployment guide, see [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)

## Disclaimer

This software is for educational purposes only. Cryptocurrency trading carries significant risk.

**Key risks:** Market volatility, execution delays, slippage, API failures, exchange downtime

**Best practices:** Start with paper trading, test thoroughly, use small position sizes, monitor closely

## Advanced Features

### Graph Neural Network (GNN) Engine

The GNN engine uses Graph Attention Networks (GAT) to learn arbitrage opportunity detection from real market data. See [docs/GNN_ARCHITECTURE.md](docs/GNN_ARCHITECTURE.md) for detailed documentation.

**Architecture:**
- 3 GAT layers with 128 hidden dimensions
- Node features: price, volume, volatility, spread
- Edge features: exchange rates, fees, liquidity
- Profit regression head with sigmoid activation

**Training:**
```bash
# Collect data and train
python train_gnn_real.py --num-scans 100 --epochs 50

# Compare engines
python compare_engines.py --num-scans 20
```

**Status:** Experimental - Model predictions need tuning for production use

### Backtesting

```bash
python backtest.py
```

Simulates trading on historical market data.

### Service Control

```bash
scripts/arbi start      # Start background service
scripts/arbi stop       # Stop service
scripts/arbi restart    # Restart service
scripts/arbi status     # Check status
scripts/arbi logs       # View logs
scripts/arbi install    # Install as LaunchAgent (macOS)
scripts/arbi uninstall  # Remove LaunchAgent
```

## Contributing

Contributions welcome. Areas for improvement:
- WebSocket integration for faster data
- GNN model improvements (hyperparameter tuning, feature engineering)
- Advanced risk models
- Additional exchanges
- Cross-exchange arbitrage
- Improved execution algorithms
- GNN profit prediction calibration

## License

MIT License

## Acknowledgments

- [CCXT](https://github.com/ccxt/ccxt) for exchange integration
- [Rich](https://github.com/Textualize/rich) for terminal UI
- [PyTorch](https://pytorch.org/) and [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/) for GNN implementation