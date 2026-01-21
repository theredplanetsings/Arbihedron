"""Data models for triangular arbitrage."""
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime
from enum import Enum

class TradeDirection(Enum):
    """Trade direction enumeration."""
    BUY = "buy"
    SELL = "sell"

@dataclass
class TradingPair:
    """Represents a trading pair."""
    symbol: str
    base: str
    quote: str
    bid: float
    ask: float
    bid_volume: float
    ask_volume: float
    timestamp: datetime
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread percentage."""
        return ((self.ask - self.bid) / self.bid) * 100 if self.bid > 0 else 0

@dataclass
class TriangularPath:
    """Represents a triangular arbitrage path."""
    path: List[str]  # e.g., ['BTC', 'ETH', 'USDT', 'BTC']
    pairs: List[TradingPair]
    directions: List[TradeDirection]
    profit_percentage: float
    profit_amount: float
    start_amount: float
    fees_total: float
    
    def __str__(self) -> str:
        """String representation of the path."""
        path_str = " → ".join(self.path)
        return f"{path_str} | Profit: {self.profit_percentage:.4f}% (${self.profit_amount:.2f})"

@dataclass
class ArbitrageOpportunity:
    """Represents a detected arbitrage opportunity."""
    path: TriangularPath
    timestamp: datetime
    expected_profit: float
    risk_score: float
    executable: bool
    reason: str = ""
    
    def is_profitable(self, min_threshold: float) -> bool:
        """Check if opportunity meets minimum profit threshold."""
        return self.path.profit_percentage >= min_threshold

@dataclass
class TradeExecution:
    """Represents an executed trade."""
    opportunity: ArbitrageOpportunity
    executed_at: datetime
    actual_profit: float
    slippage: float
    success: bool
    trades: List[dict]
    error_message: str = ""

@dataclass
class MarketSnapshot:
    """Snapshot of market data."""
    timestamp: datetime
    pairs: List[TradingPair]
    opportunities: List[ArbitrageOpportunity]
    
    def get_pair(self, symbol: str) -> TradingPair | None:
        """Get trading pair by symbol."""
        return next((p for p in self.pairs if p.symbol == symbol), None)