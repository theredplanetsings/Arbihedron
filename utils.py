#!/usr/bin/env python3
"""Utility functions for Arbihedron."""
from typing import List, Tuple
from datetime import datetime

def format_currency(amount: float, decimals: int = 2) -> str:
    """Format currency amount."""
    return f"${amount:,.{decimals}f}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage value."""
    return f"{value:.{decimals}f}%"

def calculate_compound_rate(
    buy_rate: float,
    sell_rate: float,
    fees: List[float]
) -> float:
    """Calculate compound rate through multiple trades."""
    rate = 1.0
    
    for i, fee in enumerate(fees):
        if i % 2 == 0:  # Buy
            rate /= buy_rate
            rate *= (1 - fee)
        else:  # Sell
            rate *= sell_rate
            rate *= (1 - fee)
    
    return rate

def validate_trading_pair(symbol: str) -> bool:
    """Validate trading pair symbol format."""
    if '/' not in symbol:
        return False
    
    parts = symbol.split('/')
    return len(parts) == 2 and all(len(p) > 0 for p in parts)

def get_execution_time_ms() -> float:
    """Get current timestamp in milliseconds."""
    return datetime.now().timestamp() * 1000

def parse_symbol(symbol: str) -> Tuple[str, str]:
    """Parse trading pair symbol into base and quote."""
    if '/' in symbol:
        base, quote = symbol.split('/')
        return base, quote
    return None, None

def calculate_position_size(
    balance: float,
    max_risk: float,
    leverage: float = 1.0
) -> float:
    """Calculate safe position size."""
    return balance * max_risk * leverage

def format_path(path: List[str]) -> str:
    """Format trading path for display."""
    return " → ".join(path)

def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.0
) -> float:
    """Calculate Sharpe ratio for returns."""
    if not returns or len(returns) < 2:
        return 0.0
    
    import numpy as np
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate
    
    if np.std(excess_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(excess_returns)