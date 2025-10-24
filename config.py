"""Configuration management for Arbihedron."""
import os
from typing import List
from datetime import time
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class ExchangeConfig(BaseModel):
    """Exchange configuration."""
    name: str = Field(default_factory=lambda: os.getenv("EXCHANGE_NAME", "kraken"))
    api_key: str = Field(default_factory=lambda: os.getenv("API_KEY", ""))
    api_secret: str = Field(default_factory=lambda: os.getenv("API_SECRET", ""))
    testnet: bool = Field(default=False)  # most exchanges don't have testnet


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


class AlertConfig(BaseModel):
    """Alert and notification configuration."""
    # Email settings
    email_enabled: bool = Field(
        default_factory=lambda: os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    )
    smtp_host: str = Field(
        default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com")
    )
    smtp_port: int = Field(
        default_factory=lambda: int(os.getenv("SMTP_PORT", "587"))
    )
    smtp_user: str = Field(
        default_factory=lambda: os.getenv("SMTP_USER", "")
    )
    smtp_password: str = Field(
        default_factory=lambda: os.getenv("SMTP_PASSWORD", "")
    )
    email_recipients: List[str] = Field(
        default_factory=lambda: os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else []
    )
    
    # Slack settings
    slack_enabled: bool = Field(
        default_factory=lambda: os.getenv("SLACK_ENABLED", "false").lower() == "true"
    )
    slack_webhook_url: str = Field(
        default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", "")
    )
    
    # Alert thresholds
    min_profit_threshold: float = Field(
        default_factory=lambda: float(os.getenv("ALERT_MIN_PROFIT", "0.5"))
    )
    max_alerts_per_hour: int = Field(
        default_factory=lambda: int(os.getenv("MAX_ALERTS_PER_HOUR", "10"))
    )
    quiet_hours_start: time = Field(
        default=time(23, 0)  # 11 PM
    )
    quiet_hours_end: time = Field(
        default=time(7, 0)  # 7 AM
    )
    
    # Alert types enabled
    alert_on_startup: bool = Field(
        default_factory=lambda: os.getenv("ALERT_ON_STARTUP", "true").lower() == "true"
    )
    alert_on_shutdown: bool = Field(
        default_factory=lambda: os.getenv("ALERT_ON_SHUTDOWN", "false").lower() == "true"
    )
    alert_on_crash: bool = Field(
        default_factory=lambda: os.getenv("ALERT_ON_CRASH", "true").lower() == "true"
    )
    alert_on_restart: bool = Field(
        default_factory=lambda: os.getenv("ALERT_ON_RESTART", "true").lower() == "true"
    )
    alert_on_opportunity: bool = Field(
        default_factory=lambda: os.getenv("ALERT_ON_OPPORTUNITY", "false").lower() == "true"
    )
    alert_on_execution: bool = Field(
        default_factory=lambda: os.getenv("ALERT_ON_EXECUTION", "true").lower() == "true"
    )
    alert_on_health_issues: bool = Field(
        default_factory=lambda: os.getenv("ALERT_ON_HEALTH", "true").lower() == "true"
    )

class HealthConfig(BaseModel):
    """Health monitoring configuration."""
    enabled: bool = Field(
        default_factory=lambda: os.getenv("HEALTH_ENABLED", "true").lower() == "true"
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("HEALTH_PORT", "8080"))
    )
    max_error_rate: float = Field(
        default_factory=lambda: float(os.getenv("MAX_ERROR_RATE", "0.1"))
    )
    max_memory_mb: int = Field(
        default_factory=lambda: int(os.getenv("MAX_MEMORY_MB", "1000"))
    )
    max_cpu_percent: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CPU_PERCENT", "80"))
    )
    max_inactive_minutes: int = Field(
        default_factory=lambda: int(os.getenv("MAX_INACTIVE_MINUTES", "10"))
    )

class Config(BaseModel):
    """Main application configuration."""
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    health: HealthConfig = Field(default_factory=HealthConfig)
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

# single global config instance that everything uses
config = Config()

# Convenience exports for backward compatibility
ALERT_CONFIG = config.alerts
HEALTH_CONFIG = config.health