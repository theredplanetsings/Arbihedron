#!/usr/bin/env python3
"""Simple example showing how to use Arbihedron."""
import asyncio
from exchange_client import ExchangeClient
from arbitrage_engine import ArbitrageEngine
from config import config


async def simple_scan_example():
    """Simple example: scan for opportunities."""
    print("🔺 Arbihedron - Simple Scan Example\n")
    
    # set everything up
    exchange = ExchangeClient()
    engine = ArbitrageEngine(exchange)
    
    print("Initialising engine...")
    await engine.initialize()
    
    print(f"Discovered {len(engine.triangular_paths)} triangular paths")
    print(f"Scanning for opportunities...\n")
    
    # do a quick scan
    snapshot = await engine.scan_opportunities()
    
    print(f"Found {len(snapshot.opportunities)} opportunities\n")
    
    # show the best ones
    for i, opp in enumerate(snapshot.opportunities[:5], 1):
        path_str = " → ".join(opp.path.path)
        print(f"{i}. {path_str}")
        print(f"   Expected profit: ${opp.expected_profit:.2f}")
        print(f"   Risk score: {opp.risk_score:.1f}")
        print(f"   Executable: {'Yes' if opp.executable else 'No'}")
        print()
    
    # clean up
    exchange.close()
    print("Done!")


async def continuous_monitoring_example():
    """Example: continuous monitoring."""
    print("🔺 Arbihedron - Continuous Monitoring Example\n")
    print("Press Ctrl+C to stop...\n")
    
    exchange = ExchangeClient()
    engine = ArbitrageEngine(exchange)
    
    await engine.initialize()
    
    try:
        scan_count = 0
        while True:
            scan_count += 1
            snapshot = await engine.scan_opportunities()
            
            if snapshot.opportunities:
                best = snapshot.opportunities[0]
                path_str = " → ".join(best.path.path)
                print(
                    f"Scan #{scan_count} | Best: {path_str} | "
                    f"Profit: {best.path.profit_percentage:.4f}%"
                )
            else:
                print(f"Scan #{scan_count} | No opportunities found")
            
            await asyncio.sleep(5)  # check every 5 seconds
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        exchange.close()


if __name__ == "__main__":
    # run a quick scan
    asyncio.run(simple_scan_example())
    
    # uncomment this to keep scanning continuously
    # asyncio.run(continuous_monitoring_example())
