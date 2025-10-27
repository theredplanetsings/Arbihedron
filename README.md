# Arbihedron

High-frequency triangular arbitrage system for cryptocurrency markets. Detects and exploits price discrepancies through circular trading paths (A to B to C to A) within single exchanges.

Paper trading mode enabled by default.

## Features

- Real-time market monitoring across multiple exchanges
- Triangular arbitrage opportunity detection
- Risk management with configurable thresholds
- Paper trading mode (default)
- Performance analytics and backtesting
- RESTful API service
- Database persistence (SQLite)
- Email alerts for significant opportunities

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

- Python 3.9+
- Exchange API keys (optional for paper trading)

### Installation

```bash
# Clone the repository
git clone https://github.com/theredplanetsings/Arbihedron.git
cd Arbihedron

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
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
MAX_POSITION_SIZE=1000      # £1000 per trade
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
./arbi start      # Start as background service
./arbi status     # Check service status
./arbi logs       # View logs
./arbi stop       # Stop service
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
├── main.py                 # Main orchestrator
├── config.py              # Configuration management
├── models.py              # Data models
├── exchange_client.py     # Exchange API integration
├── arbitrage_engine.py    # Core arbitrage detection
├── executor.py            # Trade execution engine
├── monitor.py             # Real-time monitoring & UI
├── backtest.py            # Backtesting framework
├── database.py            # SQLite persistence layer
├── analytics.py           # Performance analytics
├── alerts.py              # Email/Slack notifications
├── health_monitor.py      # HTTP health endpoints
├── arbihedron_service.py  # Service wrapper with auto-restart
├── arbi                   # Service control script
├── utils.py               # Utility functions
├── examples.py            # Usage examples
└── requirements.txt       # Dependencies
```

## Usage Examples

### Basic Opportunity Scan

```python
import asyncio
from exchange_client import ExchangeClient
from arbitrage_engine import ArbitrageEngine

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
| `MAX_POSITION_SIZE` | Maximum GBP per trade | 1000 |
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
- Low volume pairs penalised
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

# Reduce position size to £500
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
- `GET /metrics` - System metrics (CPU, RAM, uptime)
- `GET /status` - Trading statistics

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

## Disclaimer

This software is for educational purposes only. Cryptocurrency trading carries significant risk.

**Key risks:** Market volatility, execution delays, slippage, API failures, exchange downtime

**Best practices:** Start with paper trading, test thoroughly, use small position sizes, monitor closely

## Advanced Features

### Backtesting

```bash
python backtest.py
```

Simulates trading on historical market data.

### Service Control

```bash
./arbi start      # Start background service
./arbi stop       # Stop service
./arbi restart    # Restart service
./arbi status     # Check status
./arbi logs       # View logs
./arbi install    # Install as LaunchAgent (macOS)
./arbi uninstall  # Remove LaunchAgent
```

### Testing

```bash
python test.py            # Test core components
python test_database.py   # Test persistence
python test_alerts.py     # Test notifications
```

## Contributing

Contributions welcome. Areas for improvement:
- WebSocket integration for faster data
- Machine learning for opportunity prediction
- Advanced risk models
- Additional exchanges
- Cross-exchange arbitrage
- Improved execution algorithms

## Licence

MIT Licence

## Acknowledgements

- [CCXT](https://github.com/ccxt/ccxt) for exchange integration
- [Rich](https://github.com/Textualize/rich) for terminal UI