"""Trade execution engine for arbitrage opportunities."""
import asyncio
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from loguru import logger
from models import (
    ArbitrageOpportunity, TradeExecution, TradeDirection
)
from config import config, RiskConfig

if TYPE_CHECKING:
    from exchange_client import ExchangeClient


class TradeExecutor:
    """Executes triangular arbitrage trades."""
    
    def __init__(self, exchange_client: 'ExchangeClient', config: RiskConfig):
        """Initialise trade executor."""
        self.exchange = exchange_client
        self.execution_history = []
        self.trades_this_hour = 0
        self.last_reset = datetime.now()
    
    async def execute_opportunity(
        self, opportunity: ArbitrageOpportunity
    ) -> TradeExecution:
        """Execute a triangular arbitrage opportunity."""
        execution_start = datetime.now()
        
        # make sure we're not hitting rate limits
        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded, skipping trade")
            return TradeExecution(
                opportunity=opportunity,
                executed_at=execution_start,
                actual_profit=0.0,
                slippage=0.0,
                success=False,
                trades=[],
                error_message="Rate limit exceeded"
            )
        
        # double check the opportunity is still good
        if not opportunity.executable:
            logger.warning(f"Opportunity no longer executable: {opportunity.reason}")
            return TradeExecution(
                opportunity=opportunity,
                executed_at=execution_start,
                actual_profit=0.0,
                slippage=0.0,
                success=False,
                trades=[],
                error_message=opportunity.reason
            )
        
        # run through the trades one by one
        trades_executed = []
        current_amount = opportunity.path.start_amount
        success = True
        error_message = ""
        
        try:
            for i, (pair, direction) in enumerate(
                zip(opportunity.path.pairs, opportunity.path.directions)
            ):
                logger.info(
                    f"Step {i+1}/3: {direction.value.upper()} {pair.symbol} "
                    f"with {current_amount:.4f}"
                )
                
                # work out how much to trade
                if direction == TradeDirection.BUY:
                    # buying base with quote currency
                    trade_amount = current_amount / pair.ask
                    price = pair.ask
                else:
                    # selling base for quote currency
                    trade_amount = current_amount
                    price = pair.bid
                
                # execute the order
                order = await self.exchange.execute_order(
                    symbol=pair.symbol,
                    side=direction,
                    amount=trade_amount,
                    price=None  # use market orders for speed
                )
                
                trades_executed.append({
                    'step': i + 1,
                    'symbol': pair.symbol,
                    'direction': direction.value,
                    'amount': trade_amount,
                    'price': price,
                    'order_id': order.get('id'),
                    'status': order.get('status')
                })
                
                # figure out how much we have now for the next trade
                filled_amount = float(order.get('filled', trade_amount))
                
                if direction == TradeDirection.BUY:
                    current_amount = filled_amount
                else:
                    # for sell orders, we get quote currency back
                    avg_price = float(order.get('average', price))
                    current_amount = filled_amount * avg_price
                
                # take fees into account
                fee_rate = self.exchange.get_trading_fee(pair.symbol)
                current_amount *= (1 - fee_rate)
                
                logger.info(f"After step {i+1}: {current_amount:.4f}")
            
            # see how much we actually made
            actual_profit = current_amount - opportunity.path.start_amount
            slippage = (
                (actual_profit - opportunity.expected_profit) / 
                opportunity.expected_profit * 100
            ) if opportunity.expected_profit > 0 else 0
            
            logger.info(
                f"Arbitrage completed! Profit: ${actual_profit:.2f} "
                f"(Slippage: {slippage:.2f}%)"
            )
            
        except Exception as e:
            success = False
            error_message = str(e)
            actual_profit = current_amount - opportunity.path.start_amount
            slippage = 0.0
            logger.error(f"Execution failed: {e}")
        
        # Create execution record
        execution = TradeExecution(
            opportunity=opportunity,
            executed_at=execution_start,
            actual_profit=actual_profit,
            slippage=slippage,
            success=success,
            trades=trades_executed,
            error_message=error_message
        )
        
        self.execution_history.append(execution)
        self.trades_this_hour += 1
        
        return execution
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        
        # reset the counter every hour
        if (now - self.last_reset).total_seconds() > 3600:
            self.trades_this_hour = 0
            self.last_reset = now
        
        return self.trades_this_hour < config.risk.max_trades_per_hour
    
    def get_statistics(self) -> dict:
        """Get execution statistics."""
        if not self.execution_history:
            return {
                'total_trades': 0,
                'successful_trades': 0,
                'total_profit': 0.0,
                'avg_profit': 0.0,
                'success_rate': 0.0
            }
        
        successful = [e for e in self.execution_history if e.success]
        total_profit = sum(e.actual_profit for e in successful)
        
        return {
            'total_trades': len(self.execution_history),
            'successful_trades': len(successful),
            'total_profit': total_profit,
            'avg_profit': total_profit / len(successful) if successful else 0.0,
            'success_rate': len(successful) / len(self.execution_history) * 100,
            'avg_slippage': sum(e.slippage for e in successful) / len(successful) if successful else 0.0
        }
