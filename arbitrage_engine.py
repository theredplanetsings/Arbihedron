"""Core triangular arbitrage detection engine."""
import asyncio
from typing import List, Set, Dict, Tuple, TYPE_CHECKING
from itertools import permutations
from datetime import datetime
from loguru import logger
from models import (
    TradingPair, TriangularPath, ArbitrageOpportunity,
    TradeDirection, MarketSnapshot
)
from config import config, TradingConfig

# import after models to avoid circular dependency issues
if TYPE_CHECKING:
    from exchange_client import ExchangeClient
else:
    ExchangeClient = None


class ArbitrageEngine:
    """Detects and analyses triangular arbitrage opportunities."""
    
    def __init__(
        self, 
        exchange_client: ExchangeClient, 
        config: TradingConfig
    ):
        """Initialise arbitrage engine."""
        self.exchange = exchange_client
        self.base_currencies = set(config.base_currencies)
        self.trading_pairs_map: Dict[str, TradingPair] = {}
        self.triangular_paths: List[List[str]] = []
        
    async def initialize(self):
        """Initialise the engine by discovering triangular paths."""
        await self.exchange.load_markets()
        self._discover_triangular_paths()
        logger.info(f"Discovered {len(self.triangular_paths)} triangular paths")
    
    def _discover_triangular_paths(self):
        """Discover all possible triangular arbitrage paths."""
        # get all available trading pairs
        available_pairs = set()
        currency_graph: Dict[str, Set[str]] = {}
        
        for symbol in self.exchange.markets.keys():
            try:
                base, quote = symbol.split('/')
                available_pairs.add((base, quote))
                
                # build a graph of which currencies connect to each other
                if base not in currency_graph:
                    currency_graph[base] = set()
                if quote not in currency_graph:
                    currency_graph[quote] = set()
                
                currency_graph[base].add(quote)
                currency_graph[quote].add(base)
                
            except ValueError:
                continue
        
        # find triangular paths starting from each base currency
        paths = set()
        
        for start_currency in self.base_currencies:
            if start_currency not in currency_graph:
                continue
            
            # find all currencies we can reach from start
            for mid_currency in currency_graph[start_currency]:
                if mid_currency == start_currency:
                    continue
                
                # find currencies that can complete the triangle back to start
                for end_currency in currency_graph.get(mid_currency, set()):
                    if end_currency == start_currency or end_currency == mid_currency:
                        continue
                    
                    # check if we can get back to where we started
                    if start_currency in currency_graph.get(end_currency, set()):
                        path = (start_currency, mid_currency, end_currency, start_currency)
                        paths.add(path)
        
        self.triangular_paths = [list(path) for path in paths]
        logger.info(f"Found {len(self.triangular_paths)} valid triangular paths")
    
    def _get_symbol_and_direction(
        self, from_currency: str, to_currency: str
    ) -> Tuple[str, TradeDirection]:
        """Determine trading pair symbol and direction."""
        # try the direct pair first
        symbol_direct = f"{from_currency}/{to_currency}"
        symbol_inverse = f"{to_currency}/{from_currency}"
        
        if symbol_direct in self.trading_pairs_map:
            return symbol_direct, TradeDirection.BUY
        elif symbol_inverse in self.trading_pairs_map:
            return symbol_inverse, TradeDirection.SELL
        else:
            return None, None
    
    def _calculate_path_profit(
        self, path: List[str], start_amount: float = 1.0
    ) -> TriangularPath:
        """Calculate profit for a triangular path."""
        amount = start_amount
        pairs_used = []
        directions_used = []
        total_fees = 0.0
        
        # simulate trades along the path
        for i in range(len(path) - 1):
            from_curr = path[i]
            to_curr = path[i + 1]
            
            symbol, direction = self._get_symbol_and_direction(from_curr, to_curr)
            
            if not symbol or symbol not in self.trading_pairs_map:
                # path isn't available right now
                return None
            
            pair = self.trading_pairs_map[symbol]
            pairs_used.append(pair)
            directions_used.append(direction)
            
            # work out the trade details
            fee_rate = self.exchange.get_trading_fee(symbol)
            
            if direction == TradeDirection.BUY:
                # buying base with quote (spending to_curr to get from_curr)
                # we have 'amount' of from_curr (quote), buying to_curr (base)
                price = pair.ask  # pay ask price when buying
                if price == 0:
                    return None
                amount_before_fee = amount / price
                fee = amount_before_fee * fee_rate
                amount = amount_before_fee - fee
            else:
                # selling base for quote (selling from_curr to get to_curr)
                # we have 'amount' of from_curr (base), selling for to_curr (quote)
                price = pair.bid  # receive bid price when selling
                amount_before_fee = amount * price
                fee = amount_before_fee * fee_rate
                amount = amount_before_fee - fee
            
            total_fees += fee * price if direction == TradeDirection.SELL else fee
        
        # work out how much we made (or lost)
        profit_amount = amount - start_amount
        profit_percentage = (profit_amount / start_amount) * 100
        
        return TriangularPath(
            path=path,
            pairs=pairs_used,
            directions=directions_used,
            profit_percentage=profit_percentage,
            profit_amount=profit_amount,
            start_amount=start_amount,
            fees_total=total_fees
        )
    
    async def scan_opportunities(self) -> MarketSnapshot:
        """Scan for arbitrage opportunities across all triangular paths."""
        timestamp = datetime.now()
        
        # figure out which symbols we need to check
        symbols_needed = set()
        for path in self.triangular_paths:
            for i in range(len(path) - 1):
                from_curr = path[i]
                to_curr = path[i + 1]
                symbols_needed.add(f"{from_curr}/{to_curr}")
                symbols_needed.add(f"{to_curr}/{from_curr}")
        
        # grab all the current prices
        symbols_list = [s for s in symbols_needed if s in self.exchange.markets]
        trading_pairs = await self.exchange.fetch_tickers_batch(symbols_list)
        
        # update our map with fresh data
        self.trading_pairs_map = {pair.symbol: pair for pair in trading_pairs}
        
        # check each path for profitable opportunities
        opportunities = []
        
        for path in self.triangular_paths:
            triangular_path = self._calculate_path_profit(
                path, 
                start_amount=config.trading.max_position_size
            )
            
            if triangular_path and triangular_path.profit_percentage > 0:
                # figure out how risky this looks
                risk_score = self._calculate_risk_score(triangular_path)
                
                # check if it's worth executing
                executable = triangular_path.profit_percentage >= config.trading.min_profit_threshold
                
                opportunity = ArbitrageOpportunity(
                    path=triangular_path,
                    timestamp=timestamp,
                    expected_profit=triangular_path.profit_amount,
                    risk_score=risk_score,
                    executable=executable,
                    reason="Meets profit threshold" if executable else "Below threshold"
                )
                
                if executable:
                    opportunities.append(opportunity)
        
        # sort by best profit first
        opportunities.sort(key=lambda x: x.path.profit_percentage, reverse=True)
        
        logger.info(f"Found {len(opportunities)} executable opportunities")
        
        return MarketSnapshot(
            timestamp=timestamp,
            pairs=trading_pairs,
            opportunities=opportunities
        )
    
    def _calculate_risk_score(self, path: TriangularPath) -> float:
        """Calculate risk score for a path (0-100, lower is better)."""
        risk = 0.0
        
        # wider spreads = more risk
        avg_spread = sum(p.spread for p in path.pairs) / len(path.pairs)
        risk += avg_spread * 10
        
        # low liquidity = more risk
        min_volume = min(p.bid_volume + p.ask_volume for p in path.pairs)
        if min_volume < 10000:
            risk += 20
        elif min_volume < 50000:
            risk += 10
        
        # triangular paths always have 3 steps
        risk += 5
        
        return min(risk, 100.0)
