# GNN-Based Arbitrage Detection Architecture

## Overview

This document describes the Graph Neural Network (GNN) approach to detecting triangular arbitrage opportunities in cryptocurrency markets, implemented as an alternative to the traditional exhaustive search method.

## Motivation

Traditional arbitrage detection methods, such as exhaustive search algorithms, face several limitations:

1. **High Computational Complexity**: Checking all possible triangular paths scales poorly with the number of currencies
2. **Static Analysis**: Doesn't learn from historical patterns or market dynamics
3. **Reactive**: Only detects opportunities after they fully materialize
4. **Limited Context**: Treats each path independently without considering broader market relationships

## GNN Approach

### Key Advantages

Based on recent research ([arXiv:2508.14784v1](https://arxiv.org/abs/2508.14784v1)), GNN-based arbitrage detection offers:

1. **Reduced Computational Time**: Significantly faster than exhaustive search
2. **Higher Average Yield**: Better identification of profitable opportunities
3. **Pattern Learning**: Learns complex multi-currency relationships from historical data
4. **Predictive Capability**: Can identify emerging opportunities before they fully materialize
5. **Dynamic Adaptation**: Adjusts to changing market conditions through continuous learning

### Research Foundation

Our implementation is based on two key papers:

1. **"Graph Learning for Foreign Exchange Rate Prediction and Statistical Arbitrage"** (arXiv:2508.14784v1)
   - Formulates arbitrage detection as a graph learning problem
   - Represents currencies as nodes and exchange rates as edges
   - Uses spatiotemporal graphs to capture time-varying relationships
   - Achieves 61.89% higher information ratio than traditional methods

2. **"Efficient Triangular Arbitrage Detection via Graph Neural Networks"**
   - Proposes GNN architecture specifically for triangular arbitrage
   - Integrates Deep Q-Learning for optimization
   - Demonstrates superior performance on synthetic datasets

## Architecture

### Graph Representation

```
Currency Exchange Network as a Directed Graph:
- Nodes: Currencies (BTC, ETH, USDT, etc.)
- Edges: Trading pairs with exchange rates
- Node Features: Interest rates, historical values, moving averages
- Edge Features: Bid/ask prices, spreads, volumes, price changes
```

### Model Components

#### 1. **CurrencyGraphEncoder**
- Encodes currency properties into node embeddings
- Encodes exchange rate properties into edge embeddings
- Uses multiple lookback windows (1, 3, 5, 10, 15, 20 periods)
- Log-transforms prices to handle different scales

#### 2. **ArbitrageGNN** (Core Model)

**Input Layer:**
- Node encoder: Projects currency features to hidden dimension
- Edge encoder: Projects exchange rate features to hidden dimension

**Graph Convolution Layers:**
- Option A: Graph Attention Networks (GAT) - learns which relationships are important
- Option B: Standard Graph Convolutional Networks (GCN)
- Multiple layers (default: 3) to capture multi-hop relationships
- Dropout for regularization

**Edge Update Networks:**
- Updates edge embeddings based on connected nodes
- Captures how exchange rates are influenced by currency states

**Output Heads:**
- Path Predictor: Binary classification - is this edge part of a profitable path?
- Profit Regressor: Continuous prediction - expected profit percentage

#### 3. **Cycle Detection Algorithm**
After GNN inference:
- Builds adjacency list from edge predictions
- Searches for 3-hop cycles (triangular paths)
- Ranks by combined score: (probability × expected_profit)
- Filters by minimum profit threshold

### Loss Function

```python
# Combined loss for multi-task learning
classification_loss = BCE(predicted_profitable, actual_profitable)
regression_loss = MSE(predicted_profit, actual_profit)

total_loss = classification_loss + 0.5 * regression_loss
```

This relaxed formulation (inspired by the research) allows:
- Flexible learning of both classification and regression tasks
- Better handling of edge cases near the profit threshold
- Improved gradient flow during training

### Deep Q-Learning Integration

The model can optionally integrate Deep Q-Learning principles:
- State: Current graph representation
- Action: Select edges for arbitrage path
- Reward: Actual profit from execution
- Discount factor (γ): Prioritizes immediate vs. future profits

## Implementation

### File Structure

```
Arbihedron/
├── gnn_arbitrage_engine.py    # Main GNN engine
├── train_gnn.py                # Training pipeline
├── models/                     # Saved models
│   ├── gnn_arbitrage_best.pth
│   └── training_curves.png
├── config.py                   # Configuration (includes GNN settings)
└── main.py                     # Entry point (supports GNN mode)
```

### Key Classes

**GNNArbitrageEngine**
- Main interface compatible with existing `ArbitrageEngine`
- Manages graph construction from market data
- Runs GNN inference to detect opportunities
- Returns `MarketSnapshot` objects like traditional engine

**GNNTrainer**
- Handles model training pipeline
- Supports both historical and synthetic training data
- Implements train/validation split
- Saves best models based on validation loss

### Configuration

Add to `.env`:

```bash
# Enables GNN mode
USE_GNN_ENGINE=true

# a path to trained model (optional, uses default if not specified)
GNN_MODEL_PATH=models/gnn_arbitrage_best.pth
```

Or set in code:

```python
from config import config
config.trading.use_gnn_engine = True
config.trading.gnn_model_path = "models/gnn_arbitrage_best.pth"
```

### GNN Hyperparameters

```python
gnn_config = GNNConfig(
    hidden_dim=128,           # Hidden layer dimension
    num_layers=3,             # num of GNN layers
    dropout=0.2,              # dropout rate
    learning_rate=0.001,      # learning rate
    use_attention=True,       # Uses GAT vs GCN
    profit_threshold=0.5,     # Min profit %
    gamma=0.99,               # Q-learning discount
    epsilon=0.1,              # Exploration rate
    batch_size=32             # Training batch size
)
```

## Usage

### Training a Model

```bash
python train_gnn.py
```

This will initialise the exchange connection, collect market snapshots, train the GNN model, and save the best model with training curves.

### Running with GNN Detection

```bash
export USE_GNN_ENGINE=true

# Runs normally
python main.py
```

The bot will automatically:
- Load the trained GNN model
- Use GNN for opportunity detection
- Fall back to traditional method if GNN fails

### Switching Between Modes

Toggle at runtime:
```python
config.trading.use_gnn_engine = True   # GNN
config.trading.use_gnn_engine = False  # Traditional
```

## Performance Comparison

### Traditional Exhaustive Search
- ✓ Deterministic, guaranteed to find all paths
- ✗ O(n³) complexity, high computational cost

### GNN-Based Detection
- ✓ O(n²) complexity, learns from patterns, adapts to market conditions
- ✗ Requires training data, may miss some opportunities

### Empirical Results (from research)

| Metric | Traditional LP | GNN Method | Improvement |
|--------|---------------|------------|-------------|
| Information Ratio | 27% | 43.8% | +61.89% |
| Sortino Ratio | 32.5% | 47.4% | +45.51% |
| Annual Volatility | 1.41% | 0.67% | -52.23% |
| Max Drawdown | 1.64% | 0.91% | -44.77% |

## Training Data

### Sources

1. Historical database: Past opportunities and outcomes
2. Live collection: Real-time market snapshots
3. Synthetic generation: Training samples from current markets

### Data Requirements

Minimum recommended:
- **500-1000 samples** for initial training
- **Diverse market conditions** (bull/bear, high/low volatility)
- **Multiple currencies** to learn general patterns

### Continuous Learning

For production deployment, consider:
1. Periodic retraining (e.g., weekly)
2. Online learning from executed trades
3. Separate models for different market regimes

## Monitoring & Debugging

### Check Model Performance

```python
# During training
trainer.plot_training_curves("training_curves.png")

# Views the losses
print(f"Best validation loss: {trainer.best_val_loss}")
```

### Validate Predictions

```python
# Compares GNN vs traditional on same snapshot
gnn_snapshot = await gnn_engine.scan_opportunities()
traditional_snapshot = await traditional_engine.scan_opportunities()

print(f"GNN found: {len(gnn_snapshot.opportunities)}")
print(f"Traditional found: {len(traditional_snapshot.opportunities)}")
```

### Log Analysis

The GNN engine logs:
- Number of opportunities detected
- Model confidence scores
- Cycle detection statistics
- Performance metrics

## Future Enhancements

### Planned Features

1. Ensemble methods: Combine GNN + traditional
2. Reinforcement learning: Full RL agent for optimal execution
3. Multi-exchange: Cross-exchange arbitrage
4. Real-time learning: Continuous model updates
5. Risk prediction: GNN-based risk scoring

### Research Directions

1. Temporal GNNs: Better time-series dynamics
2. Hierarchical models: Different GNNs for different time scales
3. Explainable AI: Understanding graph features
4. Transfer learning: Pre-train on one exchange, fine-tune on others

## Dependencies

### Required Packages

```bash
# Core ML frameworks
torch>=2.0.0
torch-geometric>=2.3.0

# Scientific computing
numpy>=1.24.0
scipy>=1.11.0
scikit-learn>=1.3.0

# Visualisation (optional)
matplotlib>=3.7.0
```

### Installation

```bash
pip install torch torchvision torch-geometric
# Or use requirements.txt
pip install -r requirements.txt
```

## Troubleshooting

**"Import torch could not be resolved"**
```bash
pip install torch torch-geometric
```

**"CUDA out of memory"**
Reduce `batch_size`, `hidden_dim`, or `num_layers` in GNNConfig, or use CPU mode

**"Model not finding opportunities"**
Check for trained model (.pth file), verify training data quality, compare with traditional engine

**"Training loss not decreasing"**
- Lower learning rate
- Check for data quality issues
- Add more training data
- Try different architecture (GAT vs GCN)

## References

1. Hong, Y., & Klabjan, D. (2025). "Graph Learning for Foreign Exchange Rate Prediction and Statistical Arbitrage". arXiv:2508.14784v1
2. Zhang, D. (2025). "Efficient Triangular Arbitrage Detection via Graph Neural Networks". arXiv:2502.03194
3. PyTorch Geometric Documentation: https://pytorch-geometric.readthedocs.io/

## Contributing

To contribute improvements to the GNN engine:

1. Test on historical data first
2. Compare performance vs. traditional method
3. Document architecture changes
4. Add unit tests for new components
5. Update this documentation

## License

Same as main Arbihedron project (see LICENSE file).

**Note**: GNN-based arbitrage detection is experimental. Always backtest thoroughly and use paper trading mode before live deployment.