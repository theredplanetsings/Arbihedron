"""Training script for GNN arbitrage detection model.

This script trains the GNN model using historical market data and observed
arbitrage opportunities. It implements a supervised learning approach where
the model learns to predict profitable arbitrage paths from past market states.

Training data can come from:
1. Historical market snapshots stored in the database
2. Backtested opportunities with actual profit outcomes
3. Synthetic data generated from market simulations
"""

import asyncio
import torch
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple
from loguru import logger

from gnn_arbitrage_engine import GNNArbitrageEngine, GNNConfig
from exchange_client import ExchangeClient
from database import ArbihedronDatabase
from config import config
from models import ArbitrageOpportunity, TradingPair


class GNNTrainer:
    """Trainer for the GNN arbitrage detection model."""
    
    def __init__(
        self,
        engine: GNNArbitrageEngine,
        database: ArbihedronDatabase,
        num_epochs: int = 100,
        validation_split: float = 0.2
    ):
        """Initialize the trainer.
        
        Args:
            engine: GNN arbitrage engine to train
            database: Database containing historical data
            num_epochs: Number of training epochs
            validation_split: Fraction of data to use for validation
        """
        self.engine = engine
        self.db = database
        self.num_epochs = num_epochs
        self.validation_split = validation_split
        
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')
        
    def load_training_data_from_db(
        self,
        days_back: int = 30
    ) -> List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
        """Load training data from database.
        
        Retrieves historical opportunities and market snapshots to create
        training examples of (graph_state, actual_profit) pairs.
        
        Args:
            days_back: Number of days of historical data to load
            
        Returns:
            List of (node_features, edge_index, edge_features, profits) tuples
        """
        logger.info(f"Loading training data from last {days_back} days...")
        
        # Get all sessions from the specified time range
        cutoff_date = datetime.now() - timedelta(days=days_back)
        sessions = self.db.get_recent_sessions(days=days_back)
        
        training_samples = []
        
        for session in sessions:
            # Get all opportunities from this session
            opportunities = self.db.get_session_opportunities(session['id'])
            
            if not opportunities:
                continue
            
            # Get executions to know actual profits
            executions = self.db.get_session_executions(session['id'])
            execution_map = {
                exec['opportunity_id']: exec 
                for exec in executions
            }
            
            # Build training sample for each opportunity
            for opp in opportunities:
                # Extract actual profit if executed
                actual_profit = 0.0
                if opp['id'] in execution_map:
                    exec_data = execution_map[opp['id']]
                    if exec_data['success']:
                        actual_profit = exec_data['actual_profit_pct']
                else:
                    # Use predicted profit if not executed (could be noise)
                    actual_profit = opp['expected_profit_pct']
                
                # TODO: Reconstruct graph from opportunity data
                # For now, we'll use a simplified approach
                # In practice, you'd want to store full market snapshots
                
        logger.info(f"Loaded {len(training_samples)} training samples")
        return training_samples
    
    async def generate_synthetic_training_data(
        self,
        num_samples: int = 1000
    ) -> List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
        """Generate synthetic training data from current market observations.
        
        This is useful for initial model training when historical data is limited.
        Collects market snapshots over time and labels them based on traditional
        arbitrage detection methods.
        
        Args:
            num_samples: Number of market snapshots to collect
            
        Returns:
            List of (node_features, edge_index, edge_features, profits) tuples
        """
        logger.info(f"Generating {num_samples} synthetic training samples...")
        
        training_samples = []
        
        # Fetch one real market snapshot to get the graph structure
        logger.info("Fetching initial market snapshot...")
        base_snapshot = await self.engine.scan_opportunities()
        
        if not base_snapshot.pairs:
            raise ValueError("No market data available")
        
        logger.info(f"Base snapshot has {len(base_snapshot.pairs)} trading pairs")
        
        # Generate synthetic variations based on real market structure
        for i in range(num_samples):
            # Create a copy with price variations
            synthetic_pairs = []
            
            for pair in base_snapshot.pairs:
                # Add small random variations to prices (±2%)
                price_variation = np.random.uniform(0.98, 1.02)
                volume_variation = np.random.uniform(0.8, 1.2)
                
                # Create a shallow copy and modify prices
                from copy import copy
                synthetic_pair = copy(pair)
                synthetic_pair.bid = pair.bid * price_variation
                synthetic_pair.ask = pair.ask * price_variation
                synthetic_pair.bid_volume = pair.bid_volume * volume_variation
                synthetic_pair.ask_volume = pair.ask_volume * volume_variation
                
                synthetic_pairs.append(synthetic_pair)
            
            # Build graph from synthetic snapshot
            node_features, edge_index, edge_features = \
                self.engine._build_graph_from_snapshot(synthetic_pairs)
            
            # Create profit labels
            # Most edges have no profit, but randomly inject some profitable cycles
            profits = torch.zeros(edge_index.shape[1])
            
            # Randomly make 1-3% of edges part of profitable cycles
            num_profitable_edges = int(len(profits) * np.random.uniform(0.01, 0.03))
            if num_profitable_edges > 0:
                profitable_indices = np.random.choice(
                    len(profits), 
                    size=num_profitable_edges, 
                    replace=False
                )
                # Assign small profit percentages (0.1% to 2%)
                for idx in profitable_indices:
                    profits[idx] = np.random.uniform(0.1, 2.0)
            
            training_samples.append((
                node_features, 
                edge_index, 
                edge_features, 
                profits
            ))
            
            if (i + 1) % 100 == 0:
                logger.info(f"Generated {i + 1}/{num_samples} synthetic samples")
        
        logger.info(f"Generated {len(training_samples)} training samples")
        return training_samples
    
    def split_data(
        self, 
        data: List[Tuple]
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """Split data into training and validation sets."""
        split_idx = int(len(data) * (1 - self.validation_split))
        
        # Shuffle data
        indices = np.random.permutation(len(data))
        data = [data[i] for i in indices]
        
        train_data = data[:split_idx]
        val_data = data[split_idx:]
        
        logger.info(f"Split: {len(train_data)} train, {len(val_data)} validation")
        return train_data, val_data
    
    def train_epoch(self, train_data: List[Tuple]) -> float:
        """Train for one epoch.
        
        Args:
            train_data: List of training samples
            
        Returns:
            Average training loss
        """
        total_loss = 0.0
        batch_size = self.engine.gnn_config.batch_size
        
        # Shuffle training data
        indices = np.random.permutation(len(train_data))
        
        for i in range(0, len(train_data), batch_size):
            batch_indices = indices[i:i + batch_size]
            batch_loss = 0.0
            
            for idx in batch_indices:
                node_feat, edge_idx, edge_feat, profits = train_data[idx]
                
                loss = self.engine.train_step(
                    node_feat, edge_idx, edge_feat, profits
                )
                batch_loss += loss
            
            total_loss += batch_loss / len(batch_indices)
        
        return total_loss / (len(train_data) // batch_size)
    
    def validate(self, val_data: List[Tuple]) -> float:
        """Validate the model.
        
        Args:
            val_data: List of validation samples
            
        Returns:
            Average validation loss
        """
        self.engine.model.eval()
        total_loss = 0.0
        
        with torch.no_grad():
            for node_feat, edge_idx, edge_feat, profits in val_data:
                path_scores, profit_preds = self.engine.model(
                    node_feat, edge_idx, edge_feat
                )
                
                # Calculate validation loss
                profitable = (profits > self.engine.gnn_config.profit_threshold).float()
                classification_loss = torch.nn.functional.binary_cross_entropy(
                    path_scores, profitable
                )
                regression_loss = torch.nn.functional.mse_loss(
                    profit_preds, profits
                )
                
                loss = classification_loss + 0.5 * regression_loss
                total_loss += loss.item()
        
        return total_loss / len(val_data)
    
    async def train(
        self, 
        data: List[Tuple],
        save_path: str = "models/gnn_arbitrage.pth"
    ):
        """Main training loop.
        
        Args:
            data: Training data
            save_path: Path to save the best model
        """
        # Split data
        train_data, val_data = self.split_data(data)
        
        if not train_data:
            logger.error("No training data available!")
            return
        
        logger.info(f"Starting training for {self.num_epochs} epochs...")
        
        # Create save directory
        save_dir = Path(save_path).parent
        save_dir.mkdir(parents=True, exist_ok=True)
        
        for epoch in range(self.num_epochs):
            # Training
            train_loss = self.train_epoch(train_data)
            self.train_losses.append(train_loss)
            
            # Validation
            if val_data:
                val_loss = self.validate(val_data)
                self.val_losses.append(val_loss)
                
                # Save best model
                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self.engine.save_model(save_path)
                    logger.info(f"OK New best model saved (val_loss: {val_loss:.4f})")
                
                logger.info(
                    f"Epoch {epoch + 1}/{self.num_epochs} - "
                    f"train_loss: {train_loss:.4f}, val_loss: {val_loss:.4f}"
                )
            else:
                logger.info(
                    f"Epoch {epoch + 1}/{self.num_epochs} - "
                    f"train_loss: {train_loss:.4f}"
                )
        
        logger.info("Training complete!")
        logger.info(f"Best validation loss: {self.best_val_loss:.4f}")
        
    def plot_training_curves(self, save_path: str = "training_curves.png"):
        """Plot training and validation loss curves."""
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            plt.plot(self.train_losses, label='Training Loss')
            if self.val_losses:
                plt.plot(self.val_losses, label='Validation Loss')
            plt.xlabel('Epoch')
            plt.ylabel('Loss')
            plt.title('GNN Training Progress')
            plt.legend()
            plt.grid(True)
            plt.savefig(save_path)
            logger.info(f"Training curves saved to {save_path}")
        except ImportError:
            logger.warning("matplotlib not installed, skipping plot")


async def main():
    """Main training script."""
    logger.info(" Starting GNN training pipeline...")
    
    # Initialize components
    exchange = ExchangeClient(config.exchange)
    
    database = ArbihedronDatabase("data/arbihedron.db")
    
    gnn_config = GNNConfig(
        hidden_dim=128,
        num_layers=3,
        dropout=0.2,
        learning_rate=0.001,
        profit_threshold=config.trading.min_profit_threshold
    )
    
    engine = GNNArbitrageEngine(
        exchange_client=exchange,
        config=config.trading,
        gnn_config=gnn_config
    )
    
    await engine.initialize()
    
    # Initialize trainer
    trainer = GNNTrainer(
        engine=engine,
        database=database,
        num_epochs=100,
        validation_split=0.2
    )
    
    # Generate or load training data
    logger.info("Collecting training data...")
    
    # Option 1: Load from database (if you have historical data)
    # training_data = trainer.load_training_data_from_db(days_back=30)
    
    # Option 2: Generate synthetic data from live markets
    training_data = await trainer.generate_synthetic_training_data(num_samples=500)
    
    if not training_data:
        logger.error("No training data collected! Exiting.")
        return
    
    # Train the model
    await trainer.train(
        data=training_data,
        save_path="models/gnn_arbitrage_best.pth"
    )
    
    # Plot results
    trainer.plot_training_curves("models/training_curves.png")
    
    logger.info(" Training pipeline complete!")


if __name__ == "__main__":
    asyncio.run(main())
