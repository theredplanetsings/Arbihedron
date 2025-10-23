# Exchange Configuration Guide

## Overview

Arbihedron supports 100+ exchanges through CCXT. However, some exchanges have geographic restrictions, testnet limitations, or require specific setup.

## Recommended Exchanges

### For Testing (No Geo-Restrictions)

| Exchange | Testnet | API Required | Notes |
|----------|---------|--------------|-------|
| **Kraken** | ❌ No | ❌ No (public) | Best for testing, no restrictions |
| **Coinbase** | ❌ No | ❌ No (public) | Good US support |
| **Bitfinex** | ❌ No | ❌ No (public) | Good liquidity |
| **KuCoin** | ✅ Yes | ❌ No (public) | Good for testing |
| **OKX** | ✅ Yes | ❌ No (public) | Formerly OKEx |

### For Production

| Exchange | Fees | Liquidity | API Limit |
|----------|------|-----------|-----------|
| **Binance** | 0.1% | Very High | 1200/min |
| **Coinbase Pro** | 0.5% | High | 10/sec |
| **Kraken** | 0.16-0.26% | High | 15/sec |
| **KuCoin** | 0.1% | Medium | 30/sec |
| **Bitfinex** | 0.2% | High | 90/min |

## Current Issue: Binance Geo-Restriction

You're seeing this error:
```
Service unavailable from a restricted location according to 'b. Eligibility'
```

### Solutions:

#### Option 1: Use Kraken (Recommended for Testing)
```bash
# Edit .env
EXCHANGE_NAME=kraken
ENABLE_PAPER_TRADING=true
```

#### Option 2: Use Coinbase
```bash
# Edit .env
EXCHANGE_NAME=coinbase
ENABLE_PAPER_TRADING=true
```

#### Option 3: Use KuCoin
```bash
# Edit .env
EXCHANGE_NAME=kucoin
ENABLE_PAPER_TRADING=true
```

#### Option 4: Use VPN/Proxy (For Binance)
```python
# Add to exchange_client.py initialisation:
'proxies': {
    'http': 'http://your-proxy:port',
    'https': 'https://your-proxy:port',
}
```

## Exchange-Specific Configuration

### Kraken
```bash
EXCHANGE_NAME=kraken
# No API key needed for market data
```

**Pros:**
- No geo-restrictions
- Good for testing
- High liquidity
- Works without API keys (public data)

**Cons:**
- No testnet
- Lower rate limits

### Coinbase / Coinbase Pro
```bash
EXCHANGE_NAME=coinbase
# or
EXCHANGE_NAME=coinbasepro
```

**Pros:**
- US-friendly
- Regulated
- Good liquidity
- Works without API keys

**Cons:**
- Higher fees (0.5%)
- Stricter rate limits

### KuCoin
```bash
EXCHANGE_NAME=kucoin
```

**Pros:**
- Has testnet
- Wide coin selection
- Lower fees
- Works without API keys

**Cons:**
- Lower liquidity than Binance
- More complex API

### Binance (If Accessible)
```bash
EXCHANGE_NAME=binance
API_KEY=your_key
API_SECRET=your_secret
```

**Pros:**
- Highest liquidity
- Lowest fees (0.1%)
- Most trading pairs
- Has testnet

**Cons:**
- Geo-restricted in some locations
- Requires VPN in restricted areas

## Testing Without API Keys

Most exchanges allow fetching **public market data** without API keys:

```bash
# In .env - Leave these empty or remove them
# API_KEY=
# API_SECRET=
ENABLE_PAPER_TRADING=true
```

This allows you to:
- Fetch ticker prices
- Get order book data
- Discover arbitrage opportunities
- Cannot execute real trades (paper trading only)

## Complete Setup Examples

### Example 1: Kraken (No API Keys)
```bash
# .env
EXCHANGE_NAME=kraken
ENABLE_PAPER_TRADING=true
MIN_PROFIT_THRESHOLD=0.5
MAX_POSITION_SIZE=1000
```

Run:
```bash
python examples.py
```

### Example 2: KuCoin with Testnet
```bash
# .env
EXCHANGE_NAME=kucoin
API_KEY=your_testnet_key
API_SECRET=your_testnet_secret
ENABLE_PAPER_TRADING=true
```

### Example 3: Multiple Exchanges (Advanced)
Create separate config files:
```bash
# .env.kraken
EXCHANGE_NAME=kraken

# .env.coinbase
EXCHANGE_NAME=coinbase

# .env.kucoin
EXCHANGE_NAME=kucoin
```

Run with specific config:
```bash
python main.py --config .env.kraken
```

## API Key Setup (When Ready for Live Trading)

### Getting API Keys

1. **Binance**: Account → API Management → Create API
2. **Kraken**: Settings → API → Generate New Key
3. **Coinbase**: Settings → API → New API Key
4. **KuCoin**: Account → API Management → Create API

### Required Permissions

For arbitrage trading, you need:
- **Read** - View account balance
- **Trade** - Place spot orders
- **Withdraw** - NOT needed (safer)
- **Transfer** - NOT needed

### Security Best Practices

1. **IP Whitelist** - Restrict API to your IP
2. **2FA** - Enable two-factor authentication
3. **Separate Keys** - Different keys for testing/production
4. **Limited Permissions** - Only enable what you need
5. **Regular Rotation** - Change keys periodically

## Troubleshooting

### "Service unavailable from restricted location"
**Solution:** Use Kraken, Coinbase, or KuCoin instead of Binance

### "Invalid API key"
**Solution:** 
1. Check for spaces in .env file
2. Regenerate keys
3. Verify permissions

### "Rate limit exceeded"
**Solution:**
```bash
# In .env
MAX_TRADES_PER_HOUR=50  # Reduce from 100
```

### "No trading pairs found"
**Solution:**
1. Exchange may be down
2. Try different exchange
3. Check exchange status page

### "Insufficient balance"
**Solution:**
1. Use smaller position size
2. Deposit more funds
3. Stay in paper trading mode

## Quick Fix for Your Current Issue

**Right now, to get it working:**

```bash
# Edit .env file
nano .env
```

Change this line:
```bash
EXCHANGE_NAME=kraken  # Change from binance to kraken
```

Then run:
```bash
python test.py
python examples.py
```

You should see markets load successfully!

## Exchange Comparison

| Feature | Binance | Kraken | Coinbase | KuCoin |
|---------|---------|--------|----------|--------|
| Geo-Restrictions | Yes | No | No | No |
| Testnet | Yes | No | No | Yes |
| No-API Testing | Yes | Yes | Yes | Yes |
| Liquidity | Very High | High | High | Medium |
| Fees | 0.1% | 0.16% | 0.5% | 0.1% |
| Best For | High-volume | Testing | US traders | Variety |

## Recommended: Multi-Exchange Strategy

For best results, monitor multiple exchanges:

```python
# In config.py (advanced)
exchanges = ['kraken', 'coinbase', 'kucoin']
```

This increases your chances of finding arbitrage opportunities!

## Next Steps

1. Change `EXCHANGE_NAME=kraken` in `.env`
2. Run `python test.py` again
3. Run `python examples.py` to see opportunities
4. Once working, try other exchanges
5. When ready for live trading, get API keys

---

**TL;DR: Change to Kraken to fix the geo-restriction issue!**
