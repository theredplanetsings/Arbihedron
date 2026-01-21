"""Exchange client for interacting with crypto exchanges."""
import ccxt
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from arbihedron.models import TradingPair, TradeDirection
from arbihedron.config import config, ExchangeConfig

class ExchangeClient:
    """Handles all exchange interactions."""
    
    def __init__(self, config: ExchangeConfig):
        """Initialise exchange client."""
        self.config = config
        self.exchange = None
        self.markets = {}
        self._initialize_exchange()
    
    def _initialize_exchange(self):
        """Initialise CCXT exchange instance."""
        try:
            exchange_class = getattr(ccxt, self.config.name)
            self.exchange = exchange_class({
                'apiKey': self.config.api_key,
                'secret': self.config.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            })
            
            # enables sandbox/testnet if the exchange supports it
            if self.config.testnet:
                try:
                    self.exchange.set_sandbox_mode(True)
                    logger.info("Exchange client initialised in TESTNET mode")
                except Exception as e:
                    logger.info(f"Exchange client initialised in LIVE mode (testnet not supported)")
            else:
                logger.warning("Exchange client initialised in LIVE mode")
            
        except Exception as e:
            logger.error(f"Failed to initialise exchange: {e}")
            raise
    
    async def load_markets(self):
        """Load available markets from exchange."""
        try:
            self.markets = await asyncio.to_thread(self.exchange.load_markets)
            logger.info(f"Loaded {len(self.markets)} markets from {self.config.name}")
            return self.markets
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            return {}
    
    async def fetch_ticker(self, symbol: str) -> Optional[TradingPair]:
        """Fetch ticker data for a specific symbol."""
        try:
            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            
            if not ticker or 'bid' not in ticker or 'ask' not in ticker:
                return None
            
            base, quote = symbol.split('/')
            
            return TradingPair(
                symbol=symbol,
                base=base,
                quote=quote,
                bid=float(ticker['bid']) if ticker['bid'] else 0,
                ask=float(ticker['ask']) if ticker['ask'] else 0,
                bid_volume=float(ticker.get('bidVolume', 0)),
                ask_volume=float(ticker.get('askVolume', 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.debug(f"Failed to fetch ticker for {symbol}: {e}")
            return None
    
    async def fetch_tickers_batch(self, symbols: List[str]) -> List[TradingPair]:
        """Fetch multiple tickers in parallel."""
        tasks = [self.fetch_ticker(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # filters out the failures and get just the good ones
        valid_pairs = [r for r in results if isinstance(r, TradingPair)]
        logger.debug(f"Fetched {len(valid_pairs)}/{len(symbols)} tickers")
        
        return valid_pairs
    
    async def get_balance(self, currency: str) -> float:
        """Get available balance for a currency."""
        try:
            balance = await asyncio.to_thread(self.exchange.fetch_balance)
            return float(balance.get(currency, {}).get('free', 0))
        except Exception as e:
            logger.error(f"Failed to fetch balance for {currency}: {e}")
            return 0.0
    
    async def execute_order(
        self,
        symbol: str,
        side: TradeDirection,
        amount: float,
        price: Optional[float] = None
    ) -> Dict:
        """Execute a trade order."""
        try:
            if config.risk.enable_paper_trading:
                logger.info(f"[PAPER] {side.value.upper()} {amount} {symbol} @ {price}")
                return {
                    'id': 'paper_trade',
                    'symbol': symbol,
                    'side': side.value,
                    'amount': amount,
                    'price': price,
                    'status': 'closed',
                    'filled': amount
                }
            
            order_type = 'limit' if price else 'market'
            
            if side == TradeDirection.BUY:
                order = await asyncio.to_thread(
                    self.exchange.create_buy_order,
                    symbol, order_type, amount, price
                )
            else:
                order = await asyncio.to_thread(
                    self.exchange.create_sell_order,
                    symbol, order_type, amount, price
                )
            
            logger.info(f"Order executed: {order['id']} - {side.value} {amount} {symbol}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to execute order: {e}")
            raise
    
    def get_trading_fee(self, symbol: str) -> float:
        """Get trading fee for a symbol."""
        try:
            if symbol in self.markets:
                return float(self.markets[symbol].get('taker', 0.001))
            return 0.001  # default to 0.1% if we can't find it
        except Exception as e:
            logger.debug(f"Failed to get fee for {symbol}: {e}")
            return 0.001
    
    async def get_order_book(self, symbol: str, limit: int = 5) -> Dict:
        """Get order book for a symbol."""
        try:
            order_book = await asyncio.to_thread(
                self.exchange.fetch_order_book, symbol, limit
            )
            return order_book
        except Exception as e:
            logger.debug(f"Failed to fetch order book for {symbol}: {e}")
            return {'bids': [], 'asks': []}
    
    def close(self):
        """Close exchange connection."""
        if self.exchange:
            try:
                if hasattr(self.exchange, 'close'):
                    self.exchange.close()
                logger.info("Exchange connection closed")
            except Exception as e:
                logger.debug(f"Error closing exchange: {e}")