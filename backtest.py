#!/usr/bin/env python3
"""Backtesting module for triangular arbitrage strategies."""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
from loguru import logger
from rich.console import Console
from rich.table import Table


class ArbitrageBacktest:
    """Backtest triangular arbitrage strategies."""
    
    def __init__(self, exchange_name: str = "kraken"):
        """Initialise backtester."""
        self.exchange_name = exchange_name
        self.exchange = None
        self.engine = None
        self.trades = []
    
    async def run_historical_test(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0
    ) -> Dict:
        """Run backtest on historical data."""
        # Initialize components if needed
        if self.engine is None:
            from exchange_client import ExchangeClient
            from arbitrage_engine import ArbitrageEngine
            from config import config
            
            self.exchange = ExchangeClient(config.exchange)
            self.engine = ArbitrageEngine(self.exchange, config.trading)
            await self.engine.initialize()
        
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        logger.warning("Note: Using current market data as historical data not available")
        
        capital = initial_capital
        num_simulations = 100
        
        for i in range(num_simulations):
            # Scan for opportunities
            snapshot = await self.engine.scan_opportunities()
            
            if snapshot.opportunities:
                # Simulate executing best opportunity
                best_opp = snapshot.opportunities[0]
                
                # Simulate execution with slippage
                simulated_slippage = 0.1  # 0.1% slippage
                actual_profit = best_opp.expected_profit * (1 - simulated_slippage / 100)
                
                capital += actual_profit
                
                self.trades.append({
                    'timestamp': snapshot.timestamp,
                    'path': str(best_opp.path.path),
                    'expected_profit': best_opp.expected_profit,
                    'actual_profit': actual_profit,
                    'capital': capital
                })
                
                logger.info(f"Sim {i+1}: Profit ${actual_profit:.2f} | Capital: ${capital:.2f}")
            
            # Wait between simulations
            await asyncio.sleep(0.5)
        
        # Calculate results
        results = self._calculate_results(initial_capital, capital)
        self._display_results(results)
        
        return results
    
    def _calculate_results(self, initial_capital: float, final_capital: float) -> Dict:
        """Calculate backtest results."""
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        if self.trades:
            df = pd.DataFrame(self.trades)
            
            return {
                'initial_capital': initial_capital,
                'final_capital': final_capital,
                'total_return': total_return,
                'total_trades': len(self.trades),
                'profitable_trades': len(df[df['actual_profit'] > 0]),
                'avg_profit_per_trade': df['actual_profit'].mean(),
                'max_profit': df['actual_profit'].max(),
                'min_profit': df['actual_profit'].min(),
                'total_profit': df['actual_profit'].sum(),
                'win_rate': (len(df[df['actual_profit'] > 0]) / len(df)) * 100
            }
        
        return {
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'total_trades': 0
        }
    
    def _display_results(self, results: Dict):
        """Display backtest results."""
        table = Table(title="Backtest Results", show_header=True, header_style="bold magenta")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")
        
        table.add_row("Initial Capital", f"${results['initial_capital']:,.2f}")
        table.add_row("Final Capital", f"${results['final_capital']:,.2f}")
        table.add_row("Total Return", f"{results['total_return']:.2f}%")
        table.add_row("Total Trades", str(results.get('total_trades', 0)))
        
        if 'profitable_trades' in results:
            table.add_row("Profitable Trades", str(results['profitable_trades']))
            table.add_row("Win Rate", f"{results['win_rate']:.2f}%")
            table.add_row("Avg Profit/Trade", f"${results['avg_profit_per_trade']:.2f}")
            table.add_row("Max Profit", f"${results['max_profit']:.2f}")
            table.add_row("Total Profit", f"${results['total_profit']:.2f}")
        
        self.console.print(table)


async def main():
    """Run backtest."""
    from exchange_client import ExchangeClient
    from arbitrage_engine import ArbitrageEngine
    from config import config
    
    exchange = ExchangeClient(config.exchange)
    engine = ArbitrageEngine(exchange, config.trading)
    
    await engine.initialize()
    
    backtester = ArbitrageBacktest(config.exchange.name)
    
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    try:
        results = await backtester.run_historical_test(start_date, end_date)
    except KeyboardInterrupt:
        logger.info("Backtest interrupted by user")
    finally:
        if backtester.exchange:
            backtester.exchange.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBacktest stopped by user")
