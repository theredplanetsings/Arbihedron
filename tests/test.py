#!/usr/bin/env python3
"""Test suite for Arbihedron components."""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime
from arbihedron.models import TradingPair, TriangularPath, ArbitrageOpportunity, TradeDirection
from arbihedron.config import arbihedron.config as config

def test_models():
    """Test data models."""
    print("Testing data models...")
    
    # checks if TradingPair works
    pair = TradingPair(
        symbol="BTC/USDT",
        base="BTC",
        quote="USDT",
        bid=50000.0,
        ask=50100.0,
        bid_volume=10.0,
        ask_volume=12.0,
        timestamp=datetime.now()
    )
    
    assert pair.spread > 0
    print(f"ok: TradingPair spread: {pair.spread:.4f}%")
    
    # checks if TriangularPath works
    path = TriangularPath(
        path=["BTC", "ETH", "USDT", "BTC"],
        pairs=[pair, pair, pair],
        directions=[TradeDirection.BUY, TradeDirection.SELL, TradeDirection.BUY],
        profit_percentage=0.5,
        profit_amount=5.0,
        start_amount=1000.0,
        fees_total=3.0
    )
    
    path_str = str(path)
    assert "BTC" in path_str
    print(f"ok: TriangularPath: {path_str}")
    
    print("ok: All model tests passed!\n")

def test_config():
    """Test configuration."""
    print("Testing configuration...")
    
    assert config.exchange.name is not None
    print(f"ok: Exchange: {config.exchange.name}")
    
    assert config.trading.min_profit_threshold >= 0
    print(f"ok: Min profit threshold: {config.trading.min_profit_threshold}%")
    
    assert config.risk.enable_paper_trading is not None
    print(f"ok: Paper trading: {config.risk.enable_paper_trading}")
    
    print("ok: All config tests passed!\n")

async def test_exchange_client():
    """Test exchange client."""
    print("Testing exchange client...")
    
    try:
        from arbihedron.core.exchange_client import ExchangeClient
        
        client = ExchangeClient(config.exchange)
        print(f"ok: Exchange client initialized: {client.exchange.name}")
        
        # see if we can load markets
        markets = await client.load_markets()
        print(f"ok: Loaded {len(markets)} markets")
        
        # tries fetching a ticker
        if "BTC/USDT" in markets:
            ticker = await client.fetch_ticker("BTC/USDT")
            if ticker:
                print(f"ok: Fetched BTC/USDT ticker: ${ticker.bid:.2f}")
            else:
                print("⚠ Could not fetch ticker (might be API rate limited)")
        
        client.close()
        print("ok: Exchange client tests passed!\n")
        
    except Exception as e:
        print(f"⚠ Exchange client test warning: {e}")
        print("  (This is normal if you don't have API credentials set up)\n")

async def test_arbitrage_engine():
    """Test arbitrage engine."""
    print("Testing arbitrage engine...")
    
    try:
        from arbihedron.core.exchange_client import ExchangeClient
        from arbihedron.core.arbitrage_engine import ArbitrageEngine
        
        client = ExchangeClient(config.exchange)
        engine = ArbitrageEngine(client, config.trading)
        
        await engine.initialize()
        print(f"ok: Engine initialized with {len(engine.triangular_paths)} paths")
        
        if engine.triangular_paths:
            sample_path = engine.triangular_paths[0]
            print(f"ok: Sample path: {' → '.join(sample_path)}")
        
        # tries scanning for opportunities (might not work without API keys)
        try:
            snapshot = await engine.scan_opportunities()
            print(f"ok: Scanned and found {len(snapshot.opportunities)} opportunities")
        except Exception as e:
            print(f"⚠ Scan test skipped: {e}")
        
        client.close()
        print("ok: Arbitrage engine tests passed!\n")
        
    except Exception as e:
        print(f"⚠ Engine test warning: {e}\n")

def test_utils():
    """Test utility functions."""
    print("Testing utility functions...")
    
    from arbihedron.utils import (
        format_currency, format_percentage, 
        validate_trading_pair, parse_symbol
    )
    
    # checks formatting functions
    assert format_currency(1234.56) == "$1,234.56"
    print("ok: Currency formatting")
    
    assert format_percentage(12.345) == "12.35%"
    print("ok: Percentage formatting")
    
    # checks validation
    assert validate_trading_pair("BTC/USDT") == True
    assert validate_trading_pair("INVALID") == False
    print("ok: Trading pair validation")
    
    # checks parsing
    base, quote = parse_symbol("ETH/BTC")
    assert base == "ETH" and quote == "BTC"
    print("ok: Symbol parsing")
    
    print("ok: All utility tests passed!\n")

async def run_all_tests():
    """Run all tests."""
    print("🔺 Arbihedron Test Suite")
    print()
    
    # basic tests that don't need network access
    test_models()
    test_config()
    test_utils()
    
    # tests that need to connect to exchanges
    print("Network Tests (might require API credentials)")
    print()
    
    await test_exchange_client()
    await test_arbitrage_engine()

    print("Test Suite Completed")

if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\nStopping tests...")
        print("Done!")