"""Configuration management for Arbihedron."""
import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class ExchangeConfig(BaseModel):
    """Exchange configuration."""
    name: str = Field(default_factory=lambda: os.getenv("EXCHANGE_NAME", "kraken"))
    api_key: str = Field(default_factory=lambda: os.getenv("API_KEY", ""))
    api_secret: str = Field(default_factory=lambda: os.getenv("API_SECRET", ""))
    testnet: bool = Field(default=False)  # Most exchanges don't have testnet


class TradingConfig(BaseModel):
    """Trading parameters configuration."""
    min_profit_threshold: float = Field(
        default_factory=lambda: float(os.getenv("MIN_PROFIT_THRESHOLD", "0.5"))
    )
    max_position_size: float = Field(
        default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE", "1000"))
    )
    slippage_tolerance: float = Field(
        default_factory=lambda: float(os.getenv("SLIPPAGE_TOLERANCE", "0.1"))
    )
    base_currencies: List[str] = Field(
        default=["BTC", "ETH", "BNB", "USDT", "USDC"]
    )


class RiskConfig(BaseModel):
    """Risk management configuration."""
    enable_paper_trading: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_PAPER_TRADING", "true").lower() == "true"
    )
    max_trades_per_hour: int = Field(
        default_factory=lambda: int(os.getenv("MAX_TRADES_PER_HOUR", "100"))
    )
    stop_loss_percentage: float = Field(
        default_factory=lambda: float(os.getenv("STOP_LOSS_PERCENTAGE", "2.0"))
    )


class Config(BaseModel):
    """Main application configuration."""
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


# Global config instance
config = Config()
