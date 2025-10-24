# Arbihedron 🔺

**High-frequency triangular arbitrage system for cryptocurrency and forex markets**

> **PAPER TRADING BY DEFAULT** - This system starts in simulation mode. No real trades are executed until you explicitly enable live trading and provide API keys with trading permissions.

Arbihedron automatically detects and exploits price discrepancies in currency pairs through circular trading paths (A→B→C→A), capturing low-risk profit opportunities within single exchanges.

## Features

- **Triangular Arbitrage Detection** - Automatically discovers profitable circular trading paths
- **Real-time Market Scanning** - High-frequency price monitoring across multiple trading pairs
- **Multi-Exchange Support** - Works with Binance, Coinbase, Kraken, and more (via CCXT)
- **Risk Management** - Built-in position sizing, slippage tolerance, and rate limiting
- **Paper Trading Mode** - Test strategies without risking real capital
- **Live Dashboard** - Beautiful real-time monitoring with Rich terminal UI
- **Backtesting Engine** - Test strategies on historical data
- **Automated Execution** - Fast order execution with minimal latency

## How It Works

Triangular arbitrage exploits price inefficiencies between three currency pairs:

```
BTC/USDT → ETH/BTC → ETH/USDT → BTC/USDT
```

If the compound exchange rate after fees exceeds 1.0, there's a profit opportunity!

**Example:**
1. Start with 1 BTC
2. Trade BTC → ETH at current rate
3. Trade ETH → USDT at current rate  
4. Trade USDT → BTC at current rate
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

2. Edit `.env` with your settings:
```bash
# Exchange Configuration
EXCHANGE_NAME=binance
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here

# Trading Parameters
MIN_PROFIT_THRESHOLD=0.5    # Minimum 0.5% profit
MAX_POSITION_SIZE=1000      # $1000 per trade
SLIPPAGE_TOLERANCE=0.1      # 0.1% slippage

# Safety First!
ENABLE_PAPER_TRADING=true   # KEEP THIS TRUE FOR TESTING
```

### Running the Bot

**Paper Trading Mode (DEFAULT - Recommended for testing):**

The bot runs in **simulation mode** by default. No real money is at risk:
- Discovers real market opportunities
- Simulates trade execution
- Calculates potential profits
- No actual orders are placed

```bash
python main.py
```

**Simple Example:**
```bash
python examples.py
```

**Backtesting:**
```bash
python backtest.py
```

**CAUTION: Switching to LIVE Trading (Advanced Users Only):**

Only enable live trading after thorough testing:
1. Obtain API keys from your exchange with **trading permissions**
2. Set `ENABLE_PAPER_TRADING=false` in `.env`
3. Add your real `API_KEY` and `API_SECRET`
4. Start with small position sizes
5. Monitor closely for the first 24 hours

## Project Structure

```
Arbihedron/
├── main.py                 # Main bot orchestrator
├── config.py              # Configuration management
├── models.py              # Data models
├── exchange_client.py     # Exchange API integration
├── arbitrage_engine.py    # Core arbitrage detection
├── executor.py            # Trade execution engine
├── monitor.py             # Real-time monitoring & UI
├── backtest.py            # Backtesting framework
├── utils.py               # Utility functions
├── examples.py            # Usage examples
├── requirements.txt       # Python dependencies
└── .env.example          # Configuration template
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

All trading parameters can be configured via environment variables in `.env` or directly in `config.py`.

### Environment Variables (`.env` file)

| Parameter | Description | Default | Location |
|-----------|-------------|---------|----------|
| `EXCHANGE_NAME` | Exchange to use (binance, kraken, etc.) | kraken | `.env` |
| `MIN_PROFIT_THRESHOLD` | Minimum profit % to execute trade | 0.5 | `.env` |
| `MAX_POSITION_SIZE` | Maximum USD per trade | 1000 | `.env` |
| `SLIPPAGE_TOLERANCE` | Expected slippage % | 0.1 | `.env` |
| `ENABLE_PAPER_TRADING` | Paper trading mode (true/false) | true | `.env` |
| `MAX_TRADES_PER_HOUR` | Maximum trades allowed per hour | 100 | `.env` |
| `STOP_LOSS_PERCENTAGE` | Stop loss threshold % | 2.0 | `.env` |

### Trading Algorithm Parameters

The core trading logic uses these key parameters:

**Signal Generation** (`arbitrage_engine.py` - line 196):
- **BUY SIGNAL**: Triggered when `profit_percentage >= MIN_PROFIT_THRESHOLD`
- **Minimum Profit**: 0.5% (configurable via `MIN_PROFIT_THRESHOLD`)
- **After Fees**: Profit calculated after all exchange fees

**Risk Scoring** (`arbitrage_engine.py` - line 220):
- **Spread Risk**: Wider bid-ask spreads increase risk score
- **Liquidity Risk**: Low volume pairs (<$10k) get +20 risk, medium (<$50k) get +10
- **Path Complexity**: Triangular paths have base +5 risk
- **Risk Range**: 0-100 (lower is better)

**Execution Rules** (`executor.py`):
- **Rate Limiting**: Max 100 trades/hour (prevents over-trading)
- **Order Type**: Market orders for speed
- **Sequential Execution**: 3-leg trades executed in order
- **Validation**: Re-checks opportunity before execution

### How to Change Trading Parameters

**Option 1: Edit `.env` file (Recommended)**
```bash
# Increase profit threshold to 1%
MIN_PROFIT_THRESHOLD=1.0

# Reduce position size to $500
MAX_POSITION_SIZE=500

# Tighten rate limiting
MAX_TRADES_PER_HOUR=50
```

**Option 2: Edit `config.py` directly**
```python
class TradingConfig(BaseModel):
    min_profit_threshold: float = Field(default=1.0)  # Change here
    max_position_size: float = Field(default=500)     # Or here
```

**Option 3: Modify Risk Scoring** (`arbitrage_engine.py` line 220+)
```python
def _calculate_risk_score(self, path: TriangularPath) -> float:
    risk = 0.0
    
    # Adjust these multipliers to change risk sensitivity
    avg_spread = sum(p.spread for p in path.pairs) / len(path.pairs)
    risk += avg_spread * 10  # Lower = less spread-sensitive
    
    # Modify volume thresholds
    min_volume = min(p.bid_volume + p.ask_volume for p in path.pairs)
    if min_volume < 5000:   # Change threshold here
        risk += 30          # Increase penalty for low liquidity
```

### Base Currencies for Triangular Paths

Edit in `config.py`:
```python
base_currencies: List[str] = Field(
    default=["BTC", "ETH", "BNB", "USDT", "USDC", "SOL"]  # Add/remove currencies
)
```

## Risk Management

**Important Safety Features:**

- Paper Trading Mode - Test without real money
- Position Limits - Maximum size per trade
- Rate Limiting - Prevents over-trading
- Slippage Protection - Accounts for execution costs
- Fee Calculation - Includes all trading fees
- Risk Scoring - Evaluates opportunity safety

## Performance Metrics

The bot tracks:
- Total trades executed
- Success rate
- Total profit/loss
- Average profit per trade
- Average slippage
- Sharpe ratio

## Disclaimer

**This software is for educational purposes only.**

Cryptocurrency trading carries significant risk. Never trade with money you cannot afford to lose. Past performance does not guarantee future results.

**Key Risks:**
- Market volatility
- Execution delays (latency)
- Slippage exceeding estimates
- API failures
- Exchange downtime
- Network congestion

**Always:**
- Start with paper trading
- Test thoroughly before going live
- Use small position sizes
- Monitor closely
- Understand exchange fees
- Have proper risk management

## Advanced Features

### Custom Trading Pairs

## Advanced Configuration

Edit `config.py` to customise base currencies:

```python

### Backtesting

```bash
python backtest.py
```

Simulates trading on recent market data to evaluate strategy performance.

### Multi-Exchange Arbitrage

While this version focuses on single-exchange triangular arbitrage, the architecture can be extended for cross-exchange arbitrage.

## Contributing

Contributions welcome! Areas for improvement:
- WebSocket integration for faster data
- Machine learning for opportunity prediction
- Advanced risk models
- More exchanges
- Cross-exchange arbitrage
- Improved execution algorithms

## Licence

MIT Licence - see LICENCE file

## Acknowledgements

- Built with [CCXT](https://github.com/ccxt/ccxt) for exchange integration
- Uses [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Inspired by high-frequency trading research

## Support

For questions or issues:
- Open an issue on GitHub
- Check existing documentation
- Review examples.py for usage patterns

---

**Remember: Trade responsibly and never risk more than you can afford to lose!** 🔺