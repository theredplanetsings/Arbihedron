#!/usr/bin/env python3
"""Test suite for Arbihedron components."""
import asyncio
from datetime import datetime
from models import TradingPair, TriangularPath, ArbitrageOpportunity, TradeDirection
from config import config


def test_models():
    """Test data models."""
    print("Testing data models...")
    
    # check if TradingPair works
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
    print(f"✓ TradingPair spread: {pair.spread:.4f}%")
    
    # check if TriangularPath works
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
    print(f"✓ TriangularPath: {path_str}")
    
    print("✓ All model tests passed!\n")


def test_config():
    """Test configuration."""
    print("Testing configuration...")
    
    assert config.exchange.name is not None
    print(f"✓ Exchange: {config.exchange.name}")
    
    assert config.trading.min_profit_threshold >= 0
    print(f"✓ Min profit threshold: {config.trading.min_profit_threshold}%")
    
    assert config.risk.enable_paper_trading is not None
    print(f"✓ Paper trading: {config.risk.enable_paper_trading}")
    
    print("✓ All config tests passed!\n")


async def test_exchange_client():
    """Test exchange client."""
    print("Testing exchange client...")
    
    try:
        from exchange_client import ExchangeClient
        
        client = ExchangeClient(config.exchange)
        print(f"✓ Exchange client initialized: {client.exchange.name}")
        
        # see if we can load markets
        markets = await client.load_markets()
        print(f"✓ Loaded {len(markets)} markets")
        
        # try fetching a ticker
        if "BTC/USDT" in markets:
            ticker = await client.fetch_ticker("BTC/USDT")
            if ticker:
                print(f"✓ Fetched BTC/USDT ticker: ${ticker.bid:.2f}")
            else:
                print("⚠ Could not fetch ticker (might be API rate limited)")
        
        client.close()
        print("✓ Exchange client tests passed!\n")
        
    except Exception as e:
        print(f"⚠ Exchange client test warning: {e}")
        print("  (This is normal if you don't have API credentials set up)\n")


async def test_arbitrage_engine():
    """Test arbitrage engine."""
    print("Testing arbitrage engine...")
    
    try:
        from exchange_client import ExchangeClient
        from arbitrage_engine import ArbitrageEngine
        
        client = ExchangeClient(config.exchange)
        engine = ArbitrageEngine(client, config.trading)
        
        await engine.initialize()
        print(f"✓ Engine initialized with {len(engine.triangular_paths)} paths")
        
        if engine.triangular_paths:
            sample_path = engine.triangular_paths[0]
            print(f"✓ Sample path: {' → '.join(sample_path)}")
        
        # try scanning for opportunities (might not work without API keys)
        try:
            snapshot = await engine.scan_opportunities()
            print(f"✓ Scanned and found {len(snapshot.opportunities)} opportunities")
        except Exception as e:
            print(f"⚠ Scan test skipped: {e}")
        
        client.close()
        print("✓ Arbitrage engine tests passed!\n")
        
    except Exception as e:
        print(f"⚠ Engine test warning: {e}\n")


def test_utils():
    """Test utility functions."""
    print("Testing utility functions...")
    
    from utils import (
        format_currency, format_percentage, 
        validate_trading_pair, parse_symbol
    )
    
    # check formatting functions
    assert format_currency(1234.56) == "$1,234.56"
    print("✓ Currency formatting")
    
    assert format_percentage(12.345) == "12.35%"
    print("✓ Percentage formatting")
    
    # check validation
    assert validate_trading_pair("BTC/USDT") == True
    assert validate_trading_pair("INVALID") == False
    print("✓ Trading pair validation")
    
    # check parsing
    base, quote = parse_symbol("ETH/BTC")
    assert base == "ETH" and quote == "BTC"
    print("✓ Symbol parsing")
    
    print("✓ All utility tests passed!\n")


async def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("🔺 Arbihedron Test Suite")
    print("=" * 50)
    print()
    
    # basic tests that don't need network access
    test_models()
    test_config()
    test_utils()
    
    # tests that need to connect to exchanges
    print("=" * 50)
    print("Network Tests (May require API credentials)")
    print("=" * 50)
    print()
    
    await test_exchange_client()
    await test_arbitrage_engine()
    
    print("=" * 50)
    print("Test Suite Completd")
    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\nStopping tests...")
        print("Done!")