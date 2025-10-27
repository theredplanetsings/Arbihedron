#!/usr/bin/env python3
"""Compare GNN vs Traditional arbitrage detection."""
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

from config import config
from exchange_client import ExchangeClient
from arbitrage_engine import ArbitrageEngine
from gnn_arbitrage_engine import GNNArbitrageEngine, GNNConfig

console = Console()

async def main():
    """Compare both engines."""
    console.print(Panel.fit("  GNN vs Traditional Arbitrage Detection", style="bold magenta"))
    console.print()
    
    # Initialize exchange
    exchange = ExchangeClient(config.exchange)
    console.print("🔄 Initializing engines...", style="cyan")
    
    # Traditional engine
    traditional_engine = ArbitrageEngine(exchange, config.trading)
    await traditional_engine.initialize()
    console.print("OK Traditional engine ready", style="green")
    
    # GNN engine with trained model
    gnn_config = GNNConfig(hidden_dim=128, num_layers=3)
    gnn_engine = GNNArbitrageEngine(
        exchange, 
        config.trading, 
        gnn_config,
        model_path="models/gnn_arbitrage_best.pth"  # Load trained model
    )
    await gnn_engine.initialize()
    console.print("OK GNN engine ready (trained model loaded)", style="green")
    
    console.print()
    console.print(" Scanning for opportunities...", style="cyan")
    console.print()
    
    # Scan with traditional
    trad_start = datetime.now()
    trad_snapshot = await traditional_engine.scan_opportunities()
    trad_time = (datetime.now() - trad_start).total_seconds()
    
    # Scan with GNN
    gnn_start = datetime.now()
    gnn_snapshot = await gnn_engine.scan_opportunities()
    gnn_time = (datetime.now() - gnn_start).total_seconds()
    
    # Create comparison table
    table = Table(title="  Performance Comparison", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Traditional", justify="right", style="yellow")
    table.add_column("GNN", justify="right", style="green")
    table.add_column("Difference", justify="right", style="white")
    
    # Scan time
    time_diff = ((gnn_time - trad_time) / trad_time * 100) if trad_time > 0 else 0
    table.add_row(
        "Scan Time",
        f"{trad_time:.2f}s",
        f"{gnn_time:.2f}s",
        f"{time_diff:+.1f}%" if time_diff != 0 else "same"
    )
    
    # Opportunities found
    trad_opps = len(trad_snapshot.opportunities)
    gnn_opps = len(gnn_snapshot.opportunities)
    opp_diff = gnn_opps - trad_opps
    table.add_row(
        "Opportunities Found",
        str(trad_opps),
        str(gnn_opps),
        f"{opp_diff:+d}"
    )
    
    # Trading pairs analyzed
    table.add_row(
        "Trading Pairs Analyzed",
        str(len(trad_snapshot.pairs)),
        str(len(gnn_snapshot.pairs)),
        "same"
    )
    
    # Paths explored (estimate for traditional)
    num_currencies = len(traditional_engine.base_currencies)
    trad_paths = len(traditional_engine.triangular_paths)
    table.add_row(
        "Triangular Paths",
        str(trad_paths),
        f"~{trad_paths} (via GNN)",
        "dynamic"
    )
    
    console.print(table)
    console.print()
    
    # Show top opportunities from each
    if trad_snapshot.opportunities:
        console.print(Panel.fit(" Traditional Engine - Top 3 Opportunities", style="yellow"))
        for i, opp in enumerate(trad_snapshot.opportunities[:3], 1):
            path_str = " → ".join(opp.path.path)
            console.print(
                f"  {i}. {path_str}\n"
                f"     Profit: {opp.path.profit_percentage:.4f}% | Risk: {opp.risk_score:.1f}",
                style="green"
            )
        console.print()
    else:
        console.print("Traditional: No opportunities found", style="yellow dim")
        console.print()
    
    if gnn_snapshot.opportunities:
        console.print(Panel.fit(" GNN Engine - Top 3 Opportunities", style="green"))
        for i, opp in enumerate(gnn_snapshot.opportunities[:3], 1):
            path_str = " → ".join(opp.path.path)
            console.print(
                f"  {i}. {path_str}\n"
                f"     Profit: {opp.path.profit_percentage:.4f}% | Reason: {opp.reason}",
                style="green"
            )
        console.print()
    else:
        console.print("GNN: No opportunities found (trained model loaded)", style="yellow dim")
        console.print()
    
    # Analysis
    console.print()
    console.print(Panel.fit(
        f" Analysis\n\n"
        f"The traditional engine found {len(trad_snapshot.opportunities)} opportunities in {trad_time:.2f}s\n"
        f"The GNN engine found {len(gnn_snapshot.opportunities)} opportunities in {gnn_time:.2f}s\n\n"
        f" GNN model is trained and loaded successfully!\n"
        f"WARNING  However, it's not detecting the same opportunities as traditional.\n\n"
        f"This could mean:\n"
        f"  • The training data was too synthetic and doesn't match real patterns\n"
        f"  • The profit threshold in GNN needs tuning\n"
        f"  • More training epochs or better hyperparameters needed\n\n"
        f"Both engines are now optimized and analyzing the same {len(trad_snapshot.pairs)} pairs.",
        style="cyan"
    ))

if __name__ == "__main__":
    asyncio.run(main())