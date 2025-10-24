# Arbihedron 🔺

High-frequency triangular arbitrage system for cryptocurrency markets.

**Paper trading by default** - runs in simulation mode until you explicitly enable live trading.

Detects and exploits price discrepancies through circular trading paths (A→B→C→A), capturing profit opportunities within single exchanges.

## Features

- **Triangular arbitrage detection** - discovers profitable circular trading paths
- **Real-time market scanning** - high-frequency price monitoring
- **Multi-exchange support** - Binance, Coinbase, Kraken via CCXT
- **Risk management** - position sizing, slippage tolerance, rate limiting
- **Paper trading mode** - test strategies without risking capital
- **Live dashboard** - real-time monitoring with Rich terminal UI
- **Backtesting engine** - test strategies on historical data
- **Monitoring & alerts** - email/Slack notifications, health endpoints
- **Persistence layer** - SQLite database for trade history and analytics

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
# exchange configuration
EXCHANGE_NAME=binance
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here

# trading parameters
MIN_PROFIT_THRESHOLD=0.5    # minimum 0.5% profit
MAX_POSITION_SIZE=1000      # $1000 per trade
SLIPPAGE_TOLERANCE=0.1      # 0.1% slippage

# safety first
ENABLE_PAPER_TRADING=true   # keep true for testing

# alerts (optional)
ALERT_EMAIL=your@email.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
```

### Running the Bot

**Paper trading mode (default):**

Runs in simulation mode by default - no real money at risk:
- discovers real market opportunities
- simulates trade execution
- calculates potential profits
- no actual orders placed

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
./arbi start      # start as background service
./arbi status     # check service status
./arbi logs       # view logs
./arbi stop       # stop service
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
├── main.py                 # main bot orchestrator
├── config.py              # configuration management
├── models.py              # data models
├── exchange_client.py     # exchange API integration
├── arbitrage_engine.py    # core arbitrage detection
├── executor.py            # trade execution engine
├── monitor.py             # real-time monitoring & UI
├── backtest.py            # backtesting framework
├── database.py            # SQLite persistence layer
├── analytics.py           # performance analytics
├── alerts.py              # email/Slack notifications
├── health_monitor.py      # HTTP health endpoints
├── arbihedron_service.py  # service wrapper with auto-restart
├── arbi                   # service control script
├── utils.py               # utility functions
├── examples.py            # usage examples
└── requirements.txt       # dependencies
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

Trading parameters configured via `.env` or `config.py`.

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

Core trading logic parameters:

**Signal generation** (`arbitrage_engine.py`):
- **Buy signal**: `profit_percentage >= MIN_PROFIT_THRESHOLD`
- **Minimum profit**: 0.5% (configurable)
- **After fees**: profit calculated post-fees

**Risk scoring** (`arbitrage_engine.py`):
- **Spread risk**: wider bid-ask spreads increase risk
- **Liquidity risk**: low volume pairs penalised
- **Path complexity**: triangular paths base +5 risk
- **Risk range**: 0-100 (lower is better)

**Execution rules** (`executor.py`):
- **Rate limiting**: max 100 trades/hour
- **Order type**: market orders
- **Sequential execution**: 3-leg trades in order
- **Validation**: re-checks before execution

### Modifying Trading Parameters

**Edit `.env` (recommended):**
```bash
# increase profit threshold to 1%
MIN_PROFIT_THRESHOLD=1.0

# reduce position size to $500
MAX_POSITION_SIZE=500

# tighten rate limiting
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
    risk += avg_spread * 10  # adjust multiplier
    
    min_volume = min(p.bid_volume + p.ask_volume for p in path.pairs)
    if min_volume < 5000:    # adjust threshold
        risk += 30           # adjust penalty
```

**Base currencies** (`config.py`):
```python
base_currencies: List[str] = Field(
    default=["BTC", "ETH", "BNB", "USDT", "USDC", "SOL"]
)
```

## Risk Management

Safety features:

- paper trading mode - test without real money
- position limits - maximum size per trade
- rate limiting - prevents over-trading
- slippage protection - accounts for execution costs
- fee calculation - includes all trading fees
- risk scoring - evaluates opportunity safety
- auto-restart - recovers from crashes
- health monitoring - tracks system status

## Monitoring & Alerts

**Health endpoints:**
- `GET /health` - basic health check
- `GET /metrics` - system metrics (CPU, RAM, uptime)
- `GET /status` - detailed status with trading stats

**Notifications:**
- email alerts via SMTP
- Slack webhooks
- configurable alert types (startup, crash, opportunities, executions)
- quiet hours support
- rate limiting

**Analytics:**
- trade history in SQLite database
- performance metrics
- profit/loss tracking
- session-based analytics

**View data:**
```bash
python view_data.py          # interactive data browser
python analytics.py          # generate reports
```

## Performance Tracking

Tracked metrics:
- total trades executed
- success rate
- total profit/loss
- average profit per trade
- average slippage
- sharpe ratio
- opportunities per hour

## Disclaimer

This software is for educational purposes only.

Cryptocurrency trading carries significant risk. Never trade with money you cannot afford to lose.

**Key risks:**
- market volatility
- execution delays (latency)
- slippage exceeding estimates
- API failures
- exchange downtime
- network congestion

**Always:**
- start with paper trading
- test thoroughly
- use small position sizes
- monitor closely
- understand exchange fees
- implement proper risk management

## Advanced Features

### Backtesting

```bash
python backtest.py
```

Simulates trading on historical market data.

### Service Control

```bash
./arbi start      # start background service
./arbi stop       # stop service
./arbi restart    # restart service
./arbi status     # check status
./arbi logs       # view logs
./arbi install    # install as LaunchAgent (macOS)
./arbi uninstall  # remove LaunchAgent
```

### Testing

```bash
python test.py            # test core components
python test_database.py   # test persistence
python test_alerts.py     # test notifications
```

## Contributing

Contributions welcome. Areas for improvement:
- WebSocket integration for faster data
- machine learning for opportunity prediction
- advanced risk models
- additional exchanges
- cross-exchange arbitrage
- improved execution algorithms

## Licence

MIT Licence

## Acknowledgements

- [CCXT](https://github.com/ccxt/ccxt) for exchange integration
- [Rich](https://github.com/Textualize/rich) for terminal UI

---

🔺