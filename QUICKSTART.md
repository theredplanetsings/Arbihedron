# Arbihedron Quick Start Guide

## Get Started in 5 Minutes

### Step 1: Setup
```bash
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Setup configuration files
- Create necessary directories

### Step 2: Configure
Edit `.env` file:
```bash
nano .env
```

**Minimal Configuration:**
```bash
EXCHANGE_NAME=binance
ENABLE_PAPER_TRADING=true
MIN_PROFIT_THRESHOLD=0.5
MAX_POSITION_SIZE=1000
```

**Important:** Keep `ENABLE_PAPER_TRADING=true` for testing!

### Step 3: Test the Setup
```bash
source venv/bin/activate
python test.py
```

This validates your installation without making real trades.

### Step 4: Run Simple Example
```bash
python examples.py
```

See what opportunities the bot can find!

### Step 5: Run the Full Bot
```bash
python main.py
```

Watch the live dashboard showing opportunities in real-time.

## Understanding the Output

### Dashboard View
```
┌─────────────────────────────────────────────┐
│ Top Opportunities                            │
├─────────────────────────────────────────────┤
│ Path: BTC → ETH → USDT → BTC               │
│ Profit: 0.6500% ($6.50)                    │
│ Risk: 25.3                                  │
│ Status: ✓                                   │
└─────────────────────────────────────────────┘
```

**What this means:**
- **Path**: The sequence of trades
- **Profit %**: Expected profit percentage after fees
- **Profit $**: Dollar amount based on position size
- **Risk**: Lower is better (0-100 scale)
- **Status**: Tick = executable, Cross = below threshold

## Common Tasks

### Change Exchange
Edit `.env`:
```bash
EXCHANGE_NAME=coinbase  # or kraken, binance, etc.
```

### Adjust Profit Threshold
```bash
MIN_PROFIT_THRESHOLD=1.0  # Only execute if > 1% profit
```

### Change Position Size
```bash
MAX_POSITION_SIZE=500  # Trade with $500 max
```

### Enable Live Trading (⚠️ USE WITH CAUTION)
1. Get API keys from your exchange
2. Add to `.env`:
```bash
API_KEY=your_key_here
API_SECRET=your_secret_here
ENABLE_PAPER_TRADING=false
```

## Backtesting

Test your strategy on recent market data:
```bash
python backtest.py
```

This simulates 100 trading cycles and shows:
- Total return
- Win rate
- Average profit per trade
- Maximum profit
- Total profit

## Safety Checklist

Before going live:

- [ ] Test in paper trading mode for at least 24 hours
- [ ] Understand all configuration parameters
- [ ] Set reasonable position sizes (start small!)
- [ ] Have proper API key permissions
- [ ] Monitor the first few trades closely
- [ ] Have a stop-loss strategy
- Never invest more than you can afford to lose

## Troubleshooting

### "Import ccxt could not be resolved"
```bash
pip install -r requirements.txt
```

```

### "Failed to initialise exchange"

**Solution:**

### "No opportunities found"
- This is normal! Arbitrage opportunities are rare
- Try lowering `MIN_PROFIT_THRESHOLD`
- Check if markets are volatile enough
- Ensure exchange has sufficient trading pairs

### Rate limiting errors
- Reduce `MAX_TRADES_PER_HOUR`
- Add delays between scans
- Use websockets (advanced)

## Optimisation Tips

### For High-Frequency Trading:
1. Use websockets instead of REST API (requires modification)
2. Reduce scan interval in `main.py`
3. Use VPS near exchange servers (reduce latency)
4. Implement order book analysis

### For Better Profitability:
1. Monitor gas fees / trading fees
2. Focus on high-liquidity pairs
3. Adjust profit threshold based on volatility
4. Use limit orders (slower but better prices)

### For Risk Management:
1. Start with very small positions
2. Set strict daily loss limits
3. Monitor slippage carefully
4. Implement circuit breakers

## Learn More

### Key Files:
- `main.py` - Main bot orchestrator
- `arbitrage_engine.py` - Core detection logic
- `executor.py` - Trade execution
- `examples.py` - Simple usage examples

### Understanding Triangular Arbitrage:
1. Read about currency triangles
2. Study exchange fee structures
3. Learn about slippage and market impact
4. Understand order book depth

## Getting Help

1. Check the main README.md
2. Review examples.py
3. Run test.py to validate setup
4. Check exchange API documentation
5. Open an issue on GitHub

## Next Steps

Once comfortable with basic operation:
1. Implement custom trading strategies
2. Add more exchanges
3. Optimise execution speed
4. Build machine learning models
5. Implement cross-exchange arbitrage

---

**Remember: Start small, test thoroughly, trade responsibly!** 🔺
