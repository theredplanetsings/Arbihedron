"""
Arbihedron - High-frequency triangular arbitrage system for cryptocurrency markets.
"""

from .config import config
from .models import TradingPair, TriangularPath, ArbitrageOpportunity, TradeDirection
from .utils import (
    format_currency,
    format_percentage,
    validate_trading_pair,
    parse_symbol,
)

__version__ = "1.0.0"
__all__ = [
    "config",
    "TradingPair",
    "TriangularPath",
    "ArbitrageOpportunity",
    "TradeDirection",
    "format_currency",
    "format_percentage",
    "validate_trading_pair",
    "parse_symbol",
]
