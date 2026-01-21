"""GNN-based triangular arbitrage detection engine using Graph Neural Networks.

This module implements a novel approach to detecting arbitrage opportunities by
representing the currency exchange network as a graph and leveraging Graph Neural
Networks to identify profitable trading paths more efficiently than traditional methods.

Based on research from:
- "Graph Learning for Foreign Exchange Rate Prediction and Statistical Arbitrage" (arXiv:2508.14784v1)
- "Efficient Triangular Arbitrage Detection via Graph Neural Networks"

Key advantages:
1. Reduced computational complexity compared to exhaustive search
2. Better captures complex multi-currency relationships
3. Learns patterns from historical data
4. Can predict opportunities before they fully materialize
5. Handles dynamic market conditions more efficiently
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv, global_mean_pool
from torch_geometric.data import Data, Batch
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from loguru import logger
from dataclasses import dataclass

from arbihedron.models import TradingPair, TriangularPath, ArbitrageOpportunity, TradeDirection, MarketSnapshot
from arbihedron.config import TradingConfig
@dataclass
class GNNConfig:
    """Configuration for GNN arbitrage detection."""
    hidden_dim: int = 128
    num_layers: int = 3
    dropout: float = 0.2
    learning_rate: float = 0.001
    use_attention: bool = True  # Uses GAT instead of GCN
    profit_threshold: float = 0.0001  # Minimum profit percentage (very low for testing)
    
    # Deep Q-Learning parameters
    gamma: float = 0.99  # Discount factor
    epsilon: float = 0.1  # Exploration rate
    batch_size: int = 32
class CurrencyGraphEncoder(nn.Module):
    """Encodes currency exchange rates as graph node and edge features.
    
    Represents currencies as nodes and exchange rates as edges in a directed graph.
    Node features include interest rates and historical currency values.
    Edge features include bid/ask prices, spreads, and volume.
    """
    
    def __init__(self, node_feature_dim: int, edge_feature_dim: int):
        super().__init__()
        self.node_feature_dim = node_feature_dim
        self.edge_feature_dim = edge_feature_dim
        
    def encode_node_features(
        self, 
        currency: str, 
        interest_rate: float,
        historical_values: List[float]
    ) -> torch.Tensor:
        """Encode currency node features including interest rates and historical values."""
        # uses moving averages of different windows as in the paper
        features = [interest_rate]
        
        # adds moving averages over different lookback windows
        lookback_windows = [1, 3, 5, 10, 15, 20]
        for window in lookback_windows:
            if len(historical_values) >= window:
                features.append(np.mean(historical_values[-window:]))
            else:
                features.append(0.0)
                
        return torch.tensor(features, dtype=torch.float32)
    
    def encode_edge_features(
        self, 
        pair: TradingPair,
        historical_rates: List[float]
    ) -> torch.Tensor:
        """Encode exchange rate edge features including prices, spreads, and volume."""
        features = [
            np.log(pair.bid + 1e-8),  # Log-transform to handle scale
            np.log(pair.ask + 1e-8),
            pair.spread,
            np.log(pair.bid_volume + 1.0),
            np.log(pair.ask_volume + 1.0),
            pair.timestamp.timestamp() if pair.timestamp else 0.0
        ]
        
        # adds historical rate changes
        if len(historical_rates) >= 2 and historical_rates[-2] != 0:
            rate_change = historical_rates[-1] / (historical_rates[-2] + 1e-8)
            features.append(np.log(rate_change + 1e-8))
        else:
            features.append(0.0)
            
        return torch.tensor(features, dtype=torch.float32)

class ArbitrageGNN(nn.Module):
    """Graph Neural Network for detecting triangular arbitrage opportunities.
    
    Architecture:
    1. Node and edge embeddings from currency/exchange rate features
    2. Multiple graph convolution layers to capture multi-hop relationships
    3. Edge-level predictions for profitability of each potential trade
    4. Graph-level pooling to identify complete arbitrage cycles
    
    Uses attention mechanism (GAT) to learn which currency relationships are most
    important for identifying profitable opportunities.
    """
    
    def __init__(self, config: GNNConfig, node_dim: int, edge_dim: int):
        super().__init__()
        self.config = config
        
        # the input projections
        self.node_encoder = nn.Linear(node_dim, config.hidden_dim)
        self.edge_encoder = nn.Linear(edge_dim, config.hidden_dim)
        
        # graph convolution layers
        if config.use_attention:
            # uses Graph Attention Networks for better relationship learning
            self.convs = nn.ModuleList([
                GATConv(
                    config.hidden_dim, 
                    config.hidden_dim // 4,  # heads * out_channels = hidden_dim
                    heads=4,
                    dropout=config.dropout,
                    edge_dim=config.hidden_dim
                )
                for _ in range(config.num_layers)
            ])
        else:
            # Standard Graph Convolution
            self.convs = nn.ModuleList([
                GCNConv(config.hidden_dim, config.hidden_dim)
                for _ in range(config.num_layers)
            ])
        
        # Edges updates networks
        self.edge_updates = nn.ModuleList([
            nn.Sequential(
                nn.Linear(config.hidden_dim * 3, config.hidden_dim),  # src, edge, dst
                nn.ReLU(),
                nn.Dropout(config.dropout),
                nn.Linear(config.hidden_dim, config.hidden_dim)
            )
            for _ in range(config.num_layers)
        ])
        
        # Output heads
        self.path_predictor = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim // 2, 1),  # our profit score
            nn.Sigmoid()  # normalised profit probability
        )
        
        self.profit_regressor = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim // 2, 1),  # expected profit percentage
            nn.Sigmoid()  # Output 0-1, will scale to 0-5% range
        )
        
        # Profit scaling: model outputs 0-1, we scale to realistic profit range
        self.profit_scale = 5.0  # max expected profit percentage (5%)
        
    def forward(
        self, 
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_features: torch.Tensor,
        batch: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass through the GNN.
        
        Args:
            node_features: [num_nodes, node_dim] currency features
            edge_index: [2, num_edges] graph connectivity
            edge_features: [num_edges, edge_dim] exchange rate features
            batch: [num_nodes] batch assignment for multiple graphs
            
        Returns:
            path_scores: [num_edges] probability of profitable arbitrage via this edge
            profit_predictions: [num_edges] expected profit percentage
        """
        # encodes inputs
        x = F.relu(self.node_encoder(node_features))
        edge_attr = F.relu(self.edge_encoder(edge_features))
        
        # message passing through graph layers
        for i, conv in enumerate(self.convs):
            # updates node embeddings
            if self.config.use_attention:
                x = conv(x, edge_index, edge_attr=edge_attr)
            else:
                x = conv(x, edge_index)
            x = F.relu(x)
            x = F.dropout(x, p=self.config.dropout, training=self.training)
            
            # updates edge embeddings based on connected nodes
            src, dst = edge_index
            edge_input = torch.cat([x[src], edge_attr, x[dst]], dim=-1)
            edge_attr = self.edge_updates[i](edge_input)
            edge_attr = F.relu(edge_attr)
        
        # predicts profitability for each edge (potential trade)
        path_scores = self.path_predictor(edge_attr).squeeze(-1)
        profit_predictions_raw = self.profit_regressor(edge_attr).squeeze(-1)
        
        # scales the profit predictions from [0,1] to [0, profit_scale]
        # this constrains predictions to realistic range (0-5%)
        profit_predictions = profit_predictions_raw * self.profit_scale
        
        return path_scores, profit_predictions
    
    def detect_arbitrage_cycles(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_features: torch.Tensor,
        currency_map: Dict[str, int]
    ) -> List[Tuple[List[int], float]]:
        """Detect triangular arbitrage cycles in the graph.
        
        Uses the learned edge probabilities to identify the most promising
        3-currency cycles that could yield profitable arbitrage.
        
        Returns:
            List of (path, expected_profit) tuples
        """
        self.eval()
        with torch.no_grad():
            path_scores, profit_preds = self.forward(
                node_features, edge_index, edge_features
            )
        # builds the adjacency list for cycle detection
        num_nodes = node_features.shape[0]
        adj_list = {i: [] for i in range(num_nodes)}
        
        logger.info(f" Building adjacency list with {num_nodes} nodes and {edge_index.shape[1]} edges")
        
        for idx in range(edge_index.shape[1]):
            src = edge_index[0, idx].item()
            dst = edge_index[1, idx].item()
            score = path_scores[idx].item()
            profit = profit_preds[idx].item()
            
            adj_list[src].append((dst, idx, score, profit))
        
        # finds all triangular cycles (3-hop paths back to start)
        cycles = []
        
        # debug: track all predictions
        all_cycle_profits = []
        
        for start_node in range(num_nodes):
            # All 2-hop paths from start
            for mid1, edge1_idx, score1, profit1 in adj_list[start_node]:
                if mid1 == start_node:
                    continue
                    
                for mid2, edge2_idx, score2, profit2 in adj_list[mid1]:
                    if mid2 == start_node or mid2 == mid1:
                        continue
                    
                    # check if we can get back to start
                    for end, edge3_idx, score3, profit3 in adj_list[mid2]:
                        if end == start_node:
                            # we found a triangular cycle!
                            cycle_score = score1 * score2 * score3
                            cycle_profit = profit1 + profit2 + profit3
                            
                            all_cycle_profits.append(cycle_profit)
                            
                            # only includes if above threshold
                            if cycle_profit > self.config.profit_threshold:
                                path = [start_node, mid1, mid2, start_node]
                                cycles.append((path, cycle_profit, cycle_score))
        
        # debug logging
        if all_cycle_profits:
            logger.info(f" GNN analyzed {len(all_cycle_profits)} triangular cycles")
            logger.info(f"   Profit predictions - min: {min(all_cycle_profits):.4f}%, "
                       f"max: {max(all_cycle_profits):.4f}%, "
                       f"mean: {np.mean(all_cycle_profits):.4f}%")
            logger.info(f"   Cycles above threshold ({self.config.profit_threshold}%): {len(cycles)}")
        else:
            logger.warning("No triangular cycles found in graph!")
        
        # sorts by expected profit
        cycles.sort(key=lambda x: x[1], reverse=True)
        
        return cycles


class GNNArbitrageEngine:
    """Main engine for GNN-based arbitrage detection.
    
    Integrates the GNN model with the existing exchange infrastructure,
    maintains historical data for training, and provides a compatible interface
    with the traditional arbitrage engine.
    """
    
    def __init__(
        self, 
        exchange_client,
        config: TradingConfig,
        gnn_config: Optional[GNNConfig] = None,
        model_path: Optional[str] = None
    ):
        """Initialize the GNN arbitrage engine."""
        self.exchange = exchange_client
        self.config = config
        self.gnn_config = gnn_config or GNNConfig()
        
        self.currency_map: Dict[str, int] = {}
        self.reverse_currency_map: Dict[int, str] = {}
        self.pair_map: Dict[str, TradingPair] = {}
        self.triangular_paths: List[List[str]] = []  # our discovered triangular paths
        
        # historical data for feature computation
        self.historical_rates: Dict[str, List[float]] = {}
        self.historical_values: Dict[str, List[float]] = {}
        
        # initialise the model (will be created after seeing data dimensions)
        self.model: Optional[ArbitrageGNN] = None
        self.graph_encoder = None
        self.optimizer = None
        
        # load the pre-trained model if path provided
        if model_path:
            self.load_model(model_path)
            
        logger.info("GNN Arbitrage Engine initialized")
    
    async def initialize(self):
        """Initialize the engine by loading markets and setting up currency mapping."""
        await self.exchange.load_markets()
        self._build_currency_map()
        self._discover_triangular_paths()  # Discover triangular paths
        self._initialize_model()
        logger.info(f"Initialized with {len(self.currency_map)} currencies")
    
    def _discover_triangular_paths(self):
        """Discover all valid triangular arbitrage paths (same as traditional engine)."""
        # builds the currency graph
        currency_graph = {}
        for symbol in self.exchange.markets.keys():
            try:
                base, quote = symbol.split('/')
                if base not in currency_graph:
                    currency_graph[base] = set()
                if quote not in currency_graph:
                    currency_graph[quote] = set()
                currency_graph[base].add(quote)
                currency_graph[quote].add(base)
            except ValueError:
                continue
        
        # finds any triangular paths - ONLY starting from base currencies (like traditional engine)
        base_currencies = set(self.config.base_currencies)
        paths = set()
        for start_currency in base_currencies:
            if start_currency not in currency_graph:
                continue
            for mid_currency in currency_graph[start_currency]:
                if mid_currency == start_currency:
                    continue
                for end_currency in currency_graph.get(mid_currency, set()):
                    if end_currency == start_currency or end_currency == mid_currency:
                        continue
                    if start_currency in currency_graph.get(end_currency, set()):
                        path = (start_currency, mid_currency, end_currency, start_currency)
                        paths.add(path)
        
        self.triangular_paths = [list(path) for path in paths]
        logger.info(f"GNN discovered {len(self.triangular_paths)} triangular paths")
    
    def _build_currency_map(self):
        """Build mapping from currency symbols to node indices."""
        currencies = set()
        
        for symbol in self.exchange.markets.keys():
            try:
                base, quote = symbol.split('/')
                currencies.add(base)
                currencies.add(quote)
            except ValueError:
                continue
        
        # create the bidirectional mapping
        for idx, currency in enumerate(sorted(currencies)):
            self.currency_map[currency] = idx
            self.reverse_currency_map[idx] = currency
    
    def _initialize_model(self):
        """Initialize the GNN model with appropriate dimensions."""
        # Node features: interest rate + 6 moving averages
        node_dim = 7
        
        # Edge features: log(bid), log(ask), spread, log(bid_vol), log(ask_vol), timestamp, rate_change
        edge_dim = 7
        
        self.graph_encoder = CurrencyGraphEncoder(node_dim, edge_dim)
        self.model = ArbitrageGNN(
            self.gnn_config, 
            node_dim=node_dim, 
            edge_dim=edge_dim
        )
        
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.gnn_config.learning_rate
        )
        
        logger.info(f"GNN model initialized with {node_dim}D nodes, {edge_dim}D edges")
    
    def _build_graph_from_snapshot(
        self, 
        trading_pairs: List[TradingPair]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Convert trading pairs into graph representation.
        
        Returns:
            node_features: [num_currencies, node_dim]
            edge_index: [2, num_pairs]
            edge_features: [num_pairs, edge_dim]
        """
        num_currencies = len(self.currency_map)
        node_features = torch.zeros((num_currencies, 7))
        
        # builds node features (using dummy interest rates for now)
        for currency, idx in self.currency_map.items():
            interest_rate = 0.01  # Default, should be fetched from real data
            historical = self.historical_values.get(currency, [1.0])
            
            node_features[idx] = self.graph_encoder.encode_node_features(
                currency, interest_rate, historical
            )
        
        # builds edge index and features
        edge_list_src = []
        edge_list_dst = []
        edge_features_list = []
        
        for pair in trading_pairs:
            try:
                base, quote = pair.symbol.split('/')
                src_idx = self.currency_map[base]
                dst_idx = self.currency_map[quote]
                
                historical = self.historical_rates.get(pair.symbol, [pair.bid])
                edge_feat = self.graph_encoder.encode_edge_features(pair, historical)
                
                # adds forward edge (base -> quote using ASK price)
                edge_list_src.append(src_idx)
                edge_list_dst.append(dst_idx)
                edge_features_list.append(edge_feat)
                
                # adds reverse edge (quote -> base using BID price)
                # create inverted features for the reverse direction
                reverse_feat = edge_feat.clone()
                # swa[s] bid/ask for reverse direction
                reverse_feat[0], reverse_feat[1] = edge_feat[1], edge_feat[0]  # Swap log(bid) and log(ask)
                
                edge_list_src.append(dst_idx)
                edge_list_dst.append(src_idx)
                edge_features_list.append(reverse_feat)
                
                # s tores for future use
                self.pair_map[pair.symbol] = pair
                
            except (ValueError, KeyError):
                continue
        
        edge_index = torch.tensor(
            [edge_list_src, edge_list_dst], 
            dtype=torch.long
        )
        edge_features = torch.stack(edge_features_list)
        
        logger.info(f"Built graph: {len(self.currency_map)} nodes, {edge_index.shape[1]} edges (bidirectional)")
        
        return node_features, edge_index, edge_features
    
    async def scan_opportunities(self) -> MarketSnapshot:
        """Scan for arbitrage opportunities using the GNN model."""
        timestamp = datetime.now()
        # only fetches symbols that are part of discovered triangular paths
        # (same optimisation as traditional engine)
        symbols_needed = set()
        for path in self.triangular_paths:
            for i in range(len(path) - 1):
                from_curr = path[i]
                to_curr = path[i + 1]
                symbols_needed.add(f"{from_curr}/{to_curr}")
                symbols_needed.add(f"{to_curr}/{from_curr}")
        
        # onles fetches symbols that exist in the exchange
        symbols_list = [s for s in symbols_needed if s in self.exchange.markets]
        trading_pairs = await self.exchange.fetch_tickers_batch(symbols_list)
        
        # updates the historical data
        self._update_historical_data(trading_pairs)
        
        # builds the graph representation
        node_features, edge_index, edge_features = self._build_graph_from_snapshot(
            trading_pairs
        )
        
        # runs the GNN inference
        if self.model is None:
            logger.warning("Model not initialized, skipping GNN scan")
            return MarketSnapshot(
                timestamp=timestamp,
                pairs=trading_pairs,
                opportunities=[]
            )
        
        cycles = self.model.detect_arbitrage_cycles(
            node_features,
            edge_index,
            edge_features,
            self.currency_map
        )
        
        # converts cycles to ArbitrageOpportunity objects
        opportunities = []
        for path_indices, expected_profit, confidence in cycles[:10]:  # Top 10
            # converts indices back to currency symbols
            path_currencies = [
                self.reverse_currency_map[idx] for idx in path_indices
            ]
            
            # builds TriangularPath object
            triangular_path = self._build_triangular_path(
                path_currencies, 
                expected_profit
            )
            
            if triangular_path:
                risk_score = self._calculate_risk_score(triangular_path)
                executable = expected_profit >= self.config.min_profit_threshold
                
                opportunity = ArbitrageOpportunity(
                    path=triangular_path,
                    timestamp=timestamp,
                    expected_profit=triangular_path.profit_amount,
                    risk_score=risk_score,
                    executable=executable,
                    reason=f"GNN prediction (confidence: {confidence:.3f})"
                )
                
                opportunities.append(opportunity)
        
        logger.info(f"GNN found {len(opportunities)} opportunities")
        
        return MarketSnapshot(
            timestamp=timestamp,
            pairs=trading_pairs,
            opportunities=opportunities
        )
    
    def _update_historical_data(self, trading_pairs: List[TradingPair]):
        """Update historical price data for feature computation."""
        for pair in trading_pairs:
            if pair.symbol not in self.historical_rates:
                self.historical_rates[pair.symbol] = []
            
            mid_price = (pair.bid + pair.ask) / 2
            self.historical_rates[pair.symbol].append(mid_price)
            
            # keeps only recent history (e.g., last 30 data points)
            if len(self.historical_rates[pair.symbol]) > 30:
                self.historical_rates[pair.symbol] = self.historical_rates[pair.symbol][-30:]
    
    def _build_triangular_path(
        self, 
        path: List[str], 
        profit_pct: float
    ) -> Optional[TriangularPath]:
        """Build a TriangularPath object from currency path."""
        pairs_used = []
        directions_used = []
        
        for i in range(len(path) - 1):
            from_curr = path[i]
            to_curr = path[i + 1]
            
            # tries to find the trading pair
            symbol_direct = f"{from_curr}/{to_curr}"
            symbol_inverse = f"{to_curr}/{from_curr}"
            
            if symbol_direct in self.pair_map:
                pairs_used.append(self.pair_map[symbol_direct])
                directions_used.append(TradeDirection.BUY)
            elif symbol_inverse in self.pair_map:
                pairs_used.append(self.pair_map[symbol_inverse])
                directions_used.append(TradeDirection.SELL)
            else:
                return None
        
        start_amount = self.config.max_position_size
        profit_amount = start_amount * (profit_pct / 100)
        
        return TriangularPath(
            path=path,
            pairs=pairs_used,
            directions=directions_used,
            profit_percentage=profit_pct,
            profit_amount=profit_amount,
            start_amount=start_amount,
            fees_total=0.0  # Simplified for now
        )
    
    def _calculate_risk_score(self, path: TriangularPath) -> float:
        """Calculate risk score for a path."""
        risk = 0.0
        
        # Spread risk
        avg_spread = sum(p.spread for p in path.pairs) / len(path.pairs)
        risk += avg_spread * 10
        
        # Liquidity risk
        min_volume = min(p.bid_volume + p.ask_volume for p in path.pairs)
        if min_volume < 10000:
            risk += 20
        elif min_volume < 50000:
            risk += 10
        
        # Path complexity (always 3 for triangular)
        risk += 5
        
        return min(risk, 100.0)
    
    def train_step(
        self, 
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_features: torch.Tensor,
        actual_profits: torch.Tensor
    ) -> float:
        """Perform one training step.
        
        Args:
            node_features, edge_index, edge_features: Graph data
            actual_profits: [num_edges] ground truth profits observed
            
        Returns:
            Loss value
        """
        self.model.train()
        self.optimizer.zero_grad()
        
        path_scores, profit_preds = self.model(
            node_features, edge_index, edge_features
        )
        
        # Loss combines binary classification (profitable or not) and regression (profit amount)
        profitable = (actual_profits > self.gnn_config.profit_threshold).float()
        classification_loss = F.binary_cross_entropy(path_scores, profitable)
        
        regression_loss = F.mse_loss(profit_preds, actual_profits)
        
        # Combined loss with relaxed formulation as in paper
        loss = classification_loss + 0.5 * regression_loss
        
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def save_model(self, path: str):
        """Save the trained model to disk."""
        if self.model is None:
            logger.warning("No model to save")
            return
            
        torch.save({
            'model_state': self.model.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'currency_map': self.currency_map,
            'config': self.gnn_config
        }, path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load a pre-trained model from disk."""
        # Uses weights_only=False since we need to load the config object
        # This is safe since we trust our own trained models
        checkpoint = torch.load(path, weights_only=False)
        
        self.currency_map = checkpoint['currency_map']
        self.reverse_currency_map = {v: k for k, v in self.currency_map.items()}
        self.gnn_config = checkpoint['config']
        
        self._initialize_model()
        self.model.load_state_dict(checkpoint['model_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
        
        logger.info(f"Model loaded from {path}")