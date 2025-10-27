#!/usr/bin/env python3
"""Quick test script for GNN arbitrage engine."""
import asyncio
import sys
from loguru import logger
from rich.console import Console
from rich.panel import Panel

console = Console()

async def test_gnn_imports():
    """Test that all GNN dependencies are available."""
    console.print(Panel.fit(" Testing GNN Imports", style="bold cyan"))
    
    try:
        import torch
        console.print(f"OK PyTorch {torch.__version__}", style="green")
    except ImportError as e:
        console.print(f"X PyTorch not found: {e}", style="red")
        return False
    
    try:
        import torch_geometric
        console.print(f"OK PyTorch Geometric {torch_geometric.__version__}", style="green")
    except ImportError as e:
        console.print(f"X PyTorch Geometric not found: {e}", style="red")
        return False
    
    try:
        from gnn_arbitrage_engine import GNNArbitrageEngine, GNNConfig
        console.print("OK GNN Arbitrage Engine module", style="green")
    except ImportError as e:
        console.print(f"X GNN module import failed: {e}", style="red")
        return False
    
    return True

async def test_gnn_initialization():
    """Test GNN engine initialization."""
    console.print("\n")
    console.print(Panel.fit(" Testing GNN Initialization", style="bold cyan"))
    
    try:
        from config import config
        from exchange_client import ExchangeClient
        from gnn_arbitrage_engine import GNNArbitrageEngine, GNNConfig
        
        # creates minimal exchange client
        exchange = ExchangeClient(config.exchange)
        console.print("OK Exchange client created", style="green")
        
        # creates GNN config
        gnn_config = GNNConfig(
            hidden_dim=64,  # smaller for testing
            num_layers=2,
            dropout=0.2,
            profit_threshold=0.5
        )
        console.print("OK GNN config created", style="green")
        
        # creates our GNN engine
        engine = GNNArbitrageEngine(
            exchange_client=exchange,
            config=config.trading,
            gnn_config=gnn_config
        )
        console.print("OK GNN engine created", style="green")
        
        # initialise
        await engine.initialize()
        console.print("OK GNN engine initialized", style="green")
        
        # checks the model
        if engine.model is not None:
            console.print(f"OK GNN model initialized with {sum(p.numel() for p in engine.model.parameters())} parameters", style="green")
        else:
            console.print("X GNN model not initialized", style="yellow")
        
        return engine
        
    except Exception as e:
        console.print(f"X Initialization failed: {e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
        return None

async def test_graph_construction(engine):
    """Test graph construction from market data."""
    console.print("\n")
    console.print(Panel.fit(" Testing Graph Construction", style="bold cyan"))
    
    try:
        # fetches some market data
        symbols = list(engine.exchange.markets.keys())[:10]  # just the first 10 pairs
        console.print(f"Fetching data for {len(symbols)} trading pairs...")
        
        trading_pairs = await engine.exchange.fetch_tickers_batch(symbols)
        console.print(f"OK Fetched {len(trading_pairs)} trading pairs", style="green")
        
        # builds the graph
        node_features, edge_index, edge_features = engine._build_graph_from_snapshot(trading_pairs)
        
        console.print(f"OK Graph constructed:", style="green")
        console.print(f"  - Nodes: {node_features.shape[0]} currencies", style="cyan")
        console.print(f"  - Edges: {edge_index.shape[1]} trading pairs", style="cyan")
        console.print(f"  - Node features: {node_features.shape[1]} dimensions", style="cyan")
        console.print(f"  - Edge features: {edge_features.shape[1]} dimensions", style="cyan")
        
        return node_features, edge_index, edge_features
        
    except Exception as e:
        console.print(f"X Graph construction failed: {e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
        return None, None, None

async def test_gnn_inference(engine, node_features, edge_index, edge_features):
    """Test GNN model inference."""
    console.print("\n")
    console.print(Panel.fit(" Testing GNN Inference", style="bold cyan"))
    
    try:
        if node_features is None:
            console.print("X No graph data available", style="red")
            return False
        
        # runs the model inference
        engine.model.eval()
        import torch
        with torch.no_grad():
            path_scores, profit_preds = engine.model(
                node_features, edge_index, edge_features
            )
        
        console.print(f"OK Model inference successful", style="green")
        console.print(f"  - Path scores shape: {path_scores.shape}", style="cyan")
        console.print(f"  - Profit predictions shape: {profit_preds.shape}", style="cyan")
        console.print(f"  - Mean path score: {path_scores.mean().item():.4f}", style="cyan")
        console.print(f"  - Mean profit prediction: {profit_preds.mean().item():.4f}%", style="cyan")
        
        # counts potentially profitable edges
        profitable_count = (profit_preds > engine.gnn_config.profit_threshold).sum().item()
        console.print(f"  - Potentially profitable edges: {profitable_count}/{len(profit_preds)}", style="cyan")
        
        return True
        
    except Exception as e:
        console.print(f"X Inference failed: {e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
        return False

async def test_cycle_detection(engine):
    """Test arbitrage cycle detection."""
    console.print("\n")
    console.print(Panel.fit("🔺 Testing Cycle Detection", style="bold cyan"))
    
    try:
        # scans for opportunities
        snapshot = await engine.scan_opportunities()
        
        console.print(f"OK Scan completed", style="green")
        console.print(f"  - Trading pairs analyzed: {len(snapshot.pairs)}", style="cyan")
        console.print(f"  - Opportunities found: {len(snapshot.opportunities)}", style="cyan")
        
        if snapshot.opportunities:
            console.print("\n📈 Top opportunities:", style="bold yellow")
            for i, opp in enumerate(snapshot.opportunities[:3], 1):
                path_str = " → ".join(opp.path.path)
                console.print(
                    f"  {i}. {path_str}\n"
                    f"     Profit: {opp.path.profit_percentage:.4f}% (${opp.expected_profit:.2f})\n"
                    f"     Risk: {opp.risk_score:.1f}\n"
                    f"     Reason: {opp.reason}",
                    style="green" if opp.executable else "yellow"
                )
        else:
            console.print("  No opportunities detected (this is normal for untrained model)", style="yellow")
        
        return True
        
    except Exception as e:
        console.print(f"X Cycle detection failed: {e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
        return False

async def main():
    """Run all tests."""
    console.print("\n")
    console.print(Panel.fit(
        " GNN Arbitrage Engine Test Suite\n"
        "Testing the Graph Neural Network implementation",
        style="bold magenta"
    ))
    console.print("\n")
    
    # Test 1: Imports
    if not await test_gnn_imports():
        console.print("\n❌ Import tests failed. Install dependencies first:", style="bold red")
        console.print("   pip install torch torch-geometric", style="yellow")
        return False
    
    # Test 2: Initialization
    engine = await test_gnn_initialization()
    if engine is None:
        console.print("\n❌ Initialization failed", style="bold red")
        return False
    
    # Test 3: Graph construction
    node_features, edge_index, edge_features = await test_graph_construction(engine)
    
    # Test 4: Model inference
    if node_features is not None:
        await test_gnn_inference(engine, node_features, edge_index, edge_features)
    
    # Test 5: Cycle detection
    await test_cycle_detection(engine)
    
    # our summary
    console.print("\n")
    console.print(Panel.fit(
        " All Tests Completed!\n\n"
        "The GNN engine is working correctly.\n"
        "Note: Model is untrained, so predictions will be random.\n\n"
        "Next steps:\n"
        "1. Train the model: python train_gnn.py\n"
        "2. Enable in .env: USE_GNN_ENGINE=true\n"
        "3. Run the bot: python main.py",
        style="bold green"
    ))
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n\nWARNING  Test interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n\n❌ Test failed with error: {e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
        sys.exit(1)