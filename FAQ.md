# Arbihedron FAQ and Troubleshooting

## Frequently Asked Questions

### General Questions

**Q: What is triangular arbitrage?**
A: Triangular arbitrage exploits price discrepancies between three currency pairs. For example, if you can trade BTC → ETH → USDT → BTC and end up with more BTC than you started with, that's arbitrage profit.

**Q: How much can I make with this bot?**
A: Arbitrage opportunities are typically small (0.1-2% per trade) and rare. Profitability depends on:
- Market volatility
- Exchange fees
- Execution speed
- Position size
- Competition from other bots

**Q: Is this legal?**
A: Yes, arbitrage is a legitimate trading strategy. However, check your exchange's terms of service regarding automated trading.

**Q: Do I need programming experience?**
A: Basic command line knowledge is needed. The bot is pre-configured to work out-of-the-box.

**Q: How much capital do I need?**
A: Start with small amounts ($100-$1000) in paper trading mode. Real trading requires enough capital to cover:
- Trading fees
- Potential losses
- Multiple simultaneous positions

### Technical Questions

**Q: Which exchanges are supported?**
A: Any exchange supported by CCXT library, including:
- Binance
- Coinbase Pro
- Kraken
- KuCoin
- Bitfinex
- Many more...

**Q: How fast does the bot execute trades?**
A: Execution speed depends on:
- Your internet connection
- Distance to exchange servers
- Exchange API response times
- Current market conditions

Typically 0.5-2 seconds per complete arbitrage cycle.

**Q: Can I run this on a Raspberry Pi?**
A: Yes, but performance may be limited. Recommended: VPS with good network connectivity.

**Q: Does it work 24/7?**
A: Yes, but you should monitor it regularly and implement proper error handling.

**Q: What about network latency?**
A: Lower latency = better. Consider:
- VPS near exchange servers
- Fast internet connection
- WebSocket implementation (advanced)

### Configuration Questions

**Q: What's a good profit threshold?**
A: Start with 0.5-1.0%. Lower thresholds = more opportunities but higher risk of losses due to slippage.

**Q: How do I choose position size?**
A: Start small (1-5% of capital). Increase gradually as you gain confidence.

**Q: Should I use market or limit orders?**
A: Market orders are faster (important for arbitrage) but may have worse prices. The bot uses market orders by default.

**Q: How many trades per hour is safe?**
A: Start with 10-20. Most exchanges have rate limits around 1000-5000 requests per minute.

## Troubleshooting

### Installation Issues

**Problem: "Python not found"**
```bash
# Install Python 3.9+
# macOS:
brew install python3

# Linux:
sudo apt-get install python3.9

# Windows: Download from python.org
```

**Problem: "pip: command not found"**
```bash
python3 -m ensurepip --upgrade
```

**Problem: "Permission denied" on setup.sh**
```bash
chmod +x setup.sh
./setup.sh
```

### Exchange Connection Issues


### 5. Exchange connection fails

**Problem: "Failed to initialise exchange"**

**Causes:**

**Solutions:**
1. Increase `MIN_PROFIT_PERCENTAGE`
2. Add slippage buffer
3. Optimise calculations

### 9. Can I run multiple bots?

**Problem: "Rate limit exceeded"**

Solutions:
1. Increase delays between requests
2. Enable `enableRateLimit: true` in CCXT
3. Lower `MAX_TRADES_PER_HOUR`
4. Check exchange-specific limits

**Problem: "Invalid API signature"**

Solutions:
1. Regenerate API keys
2. Check for spaces in `.env` file
3. Verify time sync on your machine
4. Some exchanges require IP whitelisting

### Trading Issues

**Problem: "No opportunities found"**

This is normal! Arbitrage opportunities are rare. Try:
1. Lower `MIN_PROFIT_THRESHOLD`
2. Wait for more volatile markets
3. Add more currency pairs
4. Check if markets are active
5. Verify sufficient liquidity

**Problem: "Order rejected: Insufficient balance"**

Solutions:
1. Deposit more funds
2. Lower `MAX_POSITION_SIZE`
3. Check if balance is locked in other orders
4. Verify you're trading the right asset

**Problem: "High slippage"**

Causes:
- Low liquidity pairs
- Large position sizes
- High market volatility
- Network delays

Solutions:
- Trade high-liquidity pairs only
- Reduce position size
- Increase `SLIPPAGE_TOLERANCE`
- Use limit orders (slower)

**Problem: "Execution too slow"**

Solutions:
1. Use VPS near exchange
2. Optimise code paths
3. Implement WebSocket
4. Reduce logging
5. Use compiled languages for critical paths

### Data Issues

**Problem: "Stale price data"**

Solutions:
1. Reduce scan interval
2. Implement WebSocket streaming
3. Check network connection
4. Verify exchange API is responding

**Problem: "Missing trading pairs"**

Solutions:
1. Check if pairs exist on exchange
2. Verify market is active
3. Update market cache
4. Check for trading restrictions

### Performance Issues

**Problem: "High CPU usage"**

Solutions:
1. Increase scan interval
2. Reduce number of paths
3. Optimise calculations
4. Limit trading pairs

**Problem: "Memory leaks"**

Solutions:
1. Clear execution history periodically
2. Limit stored market data
3. Update dependencies
4. Check for circular references

**Problem: "Bot crashes"**

Solutions:
1. Check logs for errors
2. Implement better error handling
3. Use supervisord or systemd
4. Add health checks
5. Monitor system resources

### Display Issues

**Problem: "Dashboard not rendering"**

Solutions:
1. Terminal may not support rich UI
2. Try different terminal emulator
3. Update Rich library
4. Check terminal width/height

**Problem: "Log files too large"**

Solutions:
1. Logs auto-rotate daily
2. Adjust retention period
3. Lower log level to INFO/WARNING
4. Use log aggregation service

## Error Messages Explained

### "Insufficient funds"
You don't have enough balance for the trade. Lower position size or add funds.

### "Order would immediately match and take"
Exchange doesn't allow certain order types. Use market orders.

### "Symbol not found"
Trading pair doesn't exist or isn't active. Check exchange markets.

### "Timestamp is too far from server time"
Your system clock is out of sync. Sync with NTP server.

### "IP address not whitelisted"
Add your IP to exchange API whitelist in account settings.

### "Invalid API key"
Check `.env` file for correct key/secret. Regenerate if needed.

## Best Practices

### Safety
- Start with paper trading
- Test thoroughly before live trading
- Use small position sizes initially
- Set stop losses
- Monitor regularly
- Keep API keys secure
- Enable 2FA on exchange

### Performance
- Use high-quality VPS
- Monitor latency
- Optimise network path
- Keep dependencies updated
- Profile code regularly
- Cache market data efficiently

### Risk Management
- Diversify across pairs
- Never risk more than you can lose
- Set daily loss limits
- Calculate fees accurately
- Account for slippage
- Monitor position concentration

## Getting More Help

1. **Check documentation**: Read README.md, QUICKSTART.md, ARCHITECTURE.md
2. **Run tests**: `python test.py` to diagnose issues
3. **Check logs**: `tail -f logs/arbihedron_*.log`
4. **Exchange docs**: Review your exchange's API documentation
5. **CCXT docs**: https://docs.ccxt.com/
6. **GitHub issues**: Search existing issues or open new one

## Useful Commands

```bash
# Check Python version
python3 --version

# View logs
tail -f logs/arbihedron_*.log

# Search for errors
grep ERROR logs/*.log

# Test configuration
python test.py

# Check dependencies
pip list

# Update dependencies
pip install -r requirements.txt --upgrade

# Monitor system resources
htop

# Check network latency
ping api.binance.com
```

## Advanced Debugging

### Enable debug logging
In `.env`:
```bash
LOG_LEVEL=DEBUG
```

### Run with verbose output
```bash
python -u main.py | tee output.log
```

### Profile performance
```python
import cProfile
cProfile.run('asyncio.run(bot.run())')
```

### Monitor API calls
Check CCXT verbose mode:
```python
exchange.verbose = True
```

## Still Need Help?

If you've tried everything and still have issues:

1. Gather information:
   - Python version
   - OS and version
   - Exchange being used
   - Complete error message
   - Relevant logs
   - Configuration (hide API keys!)

2. Create detailed issue report on GitHub

3. Include steps to reproduce

4. Attach relevant logs

---

**Remember: Most issues are configuration-related. Double-check your `.env` file!**
