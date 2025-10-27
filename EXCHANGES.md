# Exchange Configuration Guide

## Overview

Arbihedron supports 100+ exchanges through CCXT. However, some exchanges have geographic restrictions, testnet limitations, or require specific setup.

## Recommended Exchanges

### For Testing (No Geographic Restrictions)

| Exchange | Testnet? | API Key Needed? | Notes |
|----------|----------|-----------------|-------|
| **Kraken** | No | No (public) | Best for testing, no restrictions |
| **Coinbase** | No | No (public) | Good US support |
| **Bitfinex** | No | No (public) | Good liquidity |
| **KuCoin** | Yes | No (public) | Good for testing |
| **OKX** | Yes | No (public) | Formerly OKEx |

### For Production

| Exchange | Fees | Liquidity | API Limit |
|----------|------|-----------|-----------|
| **Binance** | 0.1% | Very High | 1200/min |
| **Coinbase Pro** | 0.5% | High | 10/sec |
| **Kraken** | 0.16-0.26% | High | 15/sec |
| **KuCoin** | 0.1% | Medium | 30/sec |
| **Bitfinex** | 0.2% | High | 90/min |

## Current Issue: Binance Geographic Restriction

You're seeing this error:
```
Service unavailable from a restricted location according to 'b. Eligibility'
```

### Solutions:

#### Option 1: Use Kraken (Recommended)
```bash
EXCHANGE_NAME=kraken
ENABLE_PAPER_TRADING=true
```

#### Option 2: Use Coinbase
```bash
EXCHANGE_NAME=coinbase
ENABLE_PAPER_TRADING=true
```

#### Option 3: Use KuCoin
```bash
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
```

**Pros:**
- No geographic restrictions
- High liquidity
- Works without API keys

**Cons:**
- No testnet
- Lower rate limits

### Coinbase / Coinbase Pro
```bash
EXCHANGE_NAME=coinbase
```

**Pros:** US-friendly, regulated, good liquidity

**Cons:** Higher fees (0.5%), stricter rate limits

### KuCoin
```bash
EXCHANGE_NAME=kucoin
```

**Pros:** Has testnet, wide coin selection, lower fees

**Cons:** Lower liquidity, more complex API

### Binance (If Accessible)
```bash
EXCHANGE_NAME=binance
API_KEY=your_key
API_SECRET=your_secret
```

**Pros:** Highest liquidity, lowest fees (0.1%), most trading pairs

**Cons:** Geographic restrictions, requires VPN in some areas

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

## API Key Setup

### Getting API Keys

1. **Binance**: Account → API Management
2. **Kraken**: Settings → API
3. **Coinbase**: Settings → API
4. **KuCoin**: Account → API Management

### Required Permissions

For arbitrage trading, you need:
- **Read** - View account balance
- **Trade** - Place spot orders
- **Withdraw** - NOT needed (safer)
- **Transfer** - NOT needed

### Security Best Practices

1. IP Whitelist - Restrict API to your IP
2. Enable two-factor authentication
3. Use separate keys for testing/production
4. Only enable required permissions
5. Rotate keys periodically

## Troubleshooting

### "Service unavailable from restricted location"
Use Kraken, Coinbase, or KuCoin instead

### "Invalid API key"
Check for spaces in .env file, regenerate keys, verify permissions

### "Rate limit exceeded"
Reduce MAX_TRADES_PER_HOUR in .env

### "No trading pairs found"
Exchange may be down, try different exchange

### "Insufficient balance"
Use smaller position size or stay in paper trading mode

## Quick Fix

To resolve geographic restrictions:

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

Markets should load successfully.

## Exchange Comparison

| Feature | Binance | Kraken | Coinbase | KuCoin |
|---------|---------|--------|----------|--------|
| Geographic Restrictions | Yes | No | No | No |
| Testnet | Yes | No | No | Yes |
| Liquidity | Very High | High | High | Medium |
| Fees | 0.1% | 0.16% | 0.5% | 0.1% |
| Best For | High-volume | Testing | US traders | Variety |

## Multi-Exchange Strategy

Monitor multiple exchanges to increase arbitrage opportunities:

```python
# In config.py
exchanges = ['kraken', 'coinbase', 'kucoin']
```
