"""Train GNN on real arbitrage opportunities from traditional engine.

This script collects actual profitable arbitrage cycles detected by the
traditional engine and uses them to train the GNN model, ensuring the
model learns real market patterns instead of synthetic data.
"""

import asyncio
import torch
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from gnn_arbitrage_engine import GNNArbitrageEngine, GNNConfig
from arbitrage_engine import ArbitrageEngine
from exchange_client import ExchangeClient
from database import ArbihedronDatabase
from config import config
from models import TradingPair

console = Console()


class RealDataGNNTrainer:
    """Trainer that uses real arbitrage opportunities."""
    
    def __init__(
        self,
        traditional_engine: ArbitrageEngine,
        gnn_engine: GNNArbitrageEngine,
        db: ArbihedronDatabase
    ):
        self.traditional_engine = traditional_engine
        self.gnn_engine = gnn_engine
        self.db = db
        self.training_samples = []
        self.validation_split = 0.2
        
        # Initialize optimizer
        self.optimizer = torch.optim.Adam(
            self.gnn_engine.model.parameters(),
            lr=0.001
        )
        
    async def collect_real_opportunities(
        self, 
        num_scans: int = 100,
        wait_between_scans: int = 60
    ):
        """Collect real arbitrage opportunities from market.
        
        Args:
            num_scans: Number of market scans to perform
            wait_between_scans: Seconds to wait between scans (default 60s = 1 min)
        """
        logger.info(f" Collecting real arbitrage data from {num_scans} market scans...")
        logger.info(f"   This will take approximately {num_scans * wait_between_scans / 60:.1f} minutes")
        console.print()
        
        opportunities_found = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"[cyan]Scanning markets...",
                total=num_scans
            )
            
            for scan_num in range(num_scans):
                try:
                    # Scan market with traditional engine (finds real opportunities)
                    snapshot = await self.traditional_engine.scan_opportunities()
                    
                    if snapshot.opportunities:
                        opportunities_found += len(snapshot.opportunities)
                        
                        # Build GNN graph representation
                        node_features, edge_index, edge_features = \
                            self.gnn_engine._build_graph_from_snapshot(snapshot.pairs)
                        
                        # Create labels: mark edges involved in profitable paths
                        profits = torch.zeros(edge_index.shape[1])
                        
                        for opp in snapshot.opportunities:
                            # Mark each edge in the profitable path
                            for pair in opp.path.pairs:
                                try:
                                    base, quote = pair.symbol.split('/')
                                    src_idx = self.gnn_engine.currency_map[base]
                                    dst_idx = self.gnn_engine.currency_map[quote]
                                    
                                    # Find matching edges
                                    for edge_i in range(edge_index.shape[1]):
                                        if (edge_index[0, edge_i] == src_idx and 
                                            edge_index[1, edge_i] == dst_idx):
                                            # Mark this edge as profitable
                                            profits[edge_i] = opp.path.profit_percentage
                                            break
                                except (ValueError, KeyError):
                                    continue
                        
                        # Save training sample
                        self.training_samples.append((
                            node_features,
                            edge_index,
                            edge_features,
                            profits
                        ))
                        
                        progress.console.print(
                            f"   [green]OK[/green] Scan {scan_num + 1}: Found {len(snapshot.opportunities)} opportunities "
                            f"(total: {opportunities_found})"
                        )
                    else:
                        progress.console.print(
                            f"   [dim]o[/dim] Scan {scan_num + 1}: No opportunities"
                        )
                    
                    progress.update(task, advance=1)
                    
                    # Wait before next scan (unless last scan)
                    if scan_num < num_scans - 1:
                        await asyncio.sleep(wait_between_scans)
                        
                except Exception as e:
                    logger.error(f"Error during scan {scan_num + 1}: {e}")
                    progress.update(task, advance=1)
                    continue
        
        console.print()
        logger.info(f" Collected {len(self.training_samples)} market snapshots with {opportunities_found} total opportunities")
        
        if len(self.training_samples) < 10:
            logger.warning(f"WARNING  Only {len(self.training_samples)} samples collected. Consider:")
            logger.warning(f"   1. Running more scans (increase num_scans)")
            logger.warning(f"   2. Waiting longer between scans (increase wait_between_scans)")
            logger.warning(f"   3. Checking if traditional engine is finding opportunities")
        
        return len(self.training_samples)
    
    def split_data(self) -> Tuple[List[Tuple], List[Tuple]]:
        """Split data into training and validation sets."""
        if not self.training_samples:
            raise ValueError("No training samples collected!")
        
        split_idx = int(len(self.training_samples) * (1 - self.validation_split))
        
        # Shuffle data
        indices = np.random.permutation(len(self.training_samples))
        shuffled = [self.training_samples[i] for i in indices]
        
        train_data = shuffled[:split_idx]
        val_data = shuffled[split_idx:]
        
        logger.info(f" Split: {len(train_data)} train, {len(val_data)} validation")
        return train_data, val_data
    
    def train_epoch(self, train_data: List[Tuple]) -> float:
        """Train for one epoch."""
        self.gnn_engine.model.train()
        total_loss = 0.0
        
        # Maximum profit for normalization (5%)
        MAX_PROFIT = 5.0
        
        for node_features, edge_index, edge_features, profit_labels in train_data:
            self.optimizer.zero_grad()
            
            path_scores, profit_preds = self.gnn_engine.model(
                node_features, edge_index, edge_features
            )
            
            # Classification: is edge part of profitable path?
            is_profitable = (profit_labels > 0).float()
            class_loss = torch.nn.functional.binary_cross_entropy(
                path_scores, is_profitable
            )
            
            # Regression: predict profit percentage
            # Model outputs are already scaled to [0, 5] range by profit_scale
            # Compare directly to raw profit labels
            profitable_mask = profit_labels > 0
            if profitable_mask.sum() > 0:
                regression_loss = torch.nn.functional.mse_loss(
                    profit_preds[profitable_mask],
                    profit_labels[profitable_mask]
                )
            else:
                regression_loss = torch.tensor(0.0)
            
            loss = class_loss + 0.1 * regression_loss
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(train_data)
    
    def validate(self, val_data: List[Tuple]) -> float:
        """Validate the model."""
        self.gnn_engine.model.eval()
        total_loss = 0.0
        
        with torch.no_grad():
            for node_features, edge_index, edge_features, profit_labels in val_data:
                path_scores, profit_preds = self.gnn_engine.model(
                    node_features, edge_index, edge_features
                )
                
                is_profitable = (profit_labels > 0).float()
                class_loss = torch.nn.functional.binary_cross_entropy_with_logits(
                    path_scores, is_profitable
                )
                
                # Regression loss - compare model outputs (0-5 range) directly to profit labels
                profitable_mask = profit_labels > 0
                if profitable_mask.sum() > 0:
                    regression_loss = torch.nn.functional.mse_loss(
                        profit_preds[profitable_mask],
                        profit_labels[profitable_mask]
                    )
                else:
                    regression_loss = torch.tensor(0.0)
                
                loss = class_loss + 0.1 * regression_loss
                total_loss += loss.item()
        
        return total_loss / len(val_data)
    
    def train(
        self,
        epochs: int = 50,
        patience: int = 10
    ) -> dict:
        """Train the GNN model.
        
        Args:
            epochs: Number of training epochs
            patience: Early stopping patience
            
        Returns:
            Training history
        """
        logger.info(f" Starting training for {epochs} epochs...")
        console.print()
        
        train_data, val_data = self.split_data()
        
        best_val_loss = float('inf')
        patience_counter = 0
        history = {'train_loss': [], 'val_loss': []}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task(
                "[cyan]Training GNN...",
                total=epochs
            )
            
            for epoch in range(epochs):
                train_loss = self.train_epoch(train_data)
                val_loss = self.validate(val_data)
                
                history['train_loss'].append(train_loss)
                history['val_loss'].append(val_loss)
                
                # Save best model
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    self.gnn_engine.save_model("models/gnn_arbitrage_best.pth")
                    progress.console.print(
                        f"   [green]OK[/green] Epoch {epoch + 1}: "
                        f"train_loss={train_loss:.4f}, val_loss={val_loss:.4f} (best)"
                    )
                else:
                    patience_counter += 1
                    progress.console.print(
                        f"   [dim]o[/dim] Epoch {epoch + 1}: "
                        f"train_loss={train_loss:.4f}, val_loss={val_loss:.4f}"
                    )
                
                progress.update(task, advance=1)
                
                # Early stopping
                if patience_counter >= patience:
                    progress.console.print(
                        f"\n   [yellow]WARNING[/yellow] Early stopping triggered (no improvement for {patience} epochs)"
                    )
                    break
        
        console.print()
        logger.info(f" Training complete! Best validation loss: {best_val_loss:.4f}")
        return history


async def main():
    """Main training script."""
    console.print()
    console.print("[bold cyan] GNN Training on Real Market Data[/bold cyan]")
    console.print()
    
    # Initialize components
    logger.info(" Initializing engines...")
    exchange = ExchangeClient(config.exchange)
    db = ArbihedronDatabase()  # Uses default path "data/arbihedron.db"
    
    # Traditional engine (to find real opportunities)
    traditional_engine = ArbitrageEngine(exchange, config.trading)
    await traditional_engine.initialize()
    logger.info("OK Traditional engine ready")
    
    # GNN engine
    gnn_config = GNNConfig(hidden_dim=128, num_layers=3)
    gnn_engine = GNNArbitrageEngine(exchange, config.trading, gnn_config)
    await gnn_engine.initialize()
    logger.info("OK GNN engine ready")
    
    console.print()
    
    # Create trainer
    trainer = RealDataGNNTrainer(traditional_engine, gnn_engine, db)
    
    # Collect real data
    console.print("[bold]Phase 1: Data Collection[/bold]")
    console.print("Collecting real arbitrage opportunities from live markets...")
    console.print()
    
    # Start with fewer scans for faster testing (increase for production)
    num_samples = await trainer.collect_real_opportunities(
        num_scans=50,  # 50 scans
        wait_between_scans=30  # 30 seconds between scans = ~25 minutes total
    )
    
    if num_samples == 0:
        logger.error("❌ No training samples collected! Cannot train.")
        logger.error("   Possible reasons:")
        logger.error("   1. No arbitrage opportunities in current market")
        logger.error("   2. Market data fetch failed")
        logger.error("   3. Traditional engine configuration issue")
        return
    
    # Train model
    console.print("[bold]Phase 2: Model Training[/bold]")
    console.print(f"Training GNN on {num_samples} real market snapshots...")
    console.print()
    
    history = trainer.train(epochs=100, patience=15)
    
    # Summary
    console.print()
    console.print("[bold green] Training Pipeline Complete![/bold green]")
    console.print()
    console.print(f" Final Results:")
    console.print(f"   • Training samples: {num_samples}")
    console.print(f"   • Best validation loss: {min(history['val_loss']):.4f}")
    console.print(f"   • Model saved: models/gnn_arbitrage_best.pth")
    console.print()
    console.print("[bold cyan]Next Steps:[/bold cyan]")
    console.print("   1. Run: python compare_engines.py")
    console.print("   2. Check if GNN now finds real opportunities")
    console.print("   3. If not, collect more data (increase num_scans)")
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
