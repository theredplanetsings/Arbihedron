#!/usr/bin/env python3
"""Main entry point for Arbihedron triangular arbitrage bot."""
import asyncio
import signal
from datetime import datetime
from loguru import logger
from rich.live import Live
from rich.console import Console

from config import config
from exchange_client import ExchangeClient
from arbitrage_engine import ArbitrageEngine
from executor import TradeExecutor
from monitor import ArbitrageMonitor


class ArbihedronBot:
    """Main arbitrage bot orchestrator."""
    
    def __init__(self):
        """Initialise the bot."""
        self.config = load_config()
        
        # Initialise components
        self.exchange = ExchangeClient()
        self.engine = ArbitrageEngine(self.exchange)
        self.executor = TradeExecutor(self.exchange)
        self.monitor = ArbitrageMonitor()
        
        # Setup logging
        logger.add(
            "logs/arbihedron_{time}.log",
            rotation="1 day",
            retention="7 days",
            level=config.log_level
        )
    
    async def initialize(self):
        """Initialise all components."""
        logger.info("Initialising Arbihedron...")
        
        try:
            await self.engine.initialize()
            
            mode = "PAPER TRADING" if config.risk.enable_paper_trading else "LIVE TRADING"
            logger.warning(f"Mode: {mode}")
            logger.info(f"Exchange: {config.exchange.name}")
            logger.info(f"Min Profit Threshold: {config.trading.min_profit_threshold}%")
            logger.info(f"Max Position Size: ${config.trading.max_position_size}")
            
            logger.success("Initialisation complete")
            
        except Exception as e:
            logger.error(f"Initialisation failed: {e}")
            raise
    
    async def scan_and_execute_loop(self):
        """Main loop: scan for opportunities and execute."""
        scan_interval = 1.0  # Scan every second for high-frequency
        
        while self.running:
            try:
                # Scan for opportunities
                snapshot = await self.engine.scan_opportunities()
                self.monitor.update_snapshot(snapshot)
                
                # Execute top opportunities
                for opportunity in snapshot.opportunities[:3]:  # Top 3
                    if opportunity.executable:
                        self.monitor.log_opportunity(opportunity)
                        
                        # Execute the trade
                        execution = await self.executor.execute_opportunity(opportunity)
                        self.monitor.log_execution(execution)
                        
                        # Small delay between executions
                        await asyncio.sleep(0.1)
                
                # Wait before next scan
                await asyncio.sleep(scan_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def display_loop(self):
        """Display loop: update dashboard."""
        with Live(
            self.monitor.create_dashboard(None, {}),
            console=self.console,
            refresh_per_second=2
        ) as live:
            while self.running:
                try:
                    stats = self.executor.get_statistics()
                    dashboard = self.monitor.create_dashboard(
                        self.monitor.latest_snapshot,
                        stats
                    )
                    live.update(dashboard)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Display error: {e}")
                    await asyncio.sleep(1)
    
    async def run(self):
        """Run the bot."""
        self.running = True
        
        try:
            # Initialise
            await self.initialize()
            
            # Run both loops concurrently
            await asyncio.gather(
                self.scan_and_execute_loop(),
                self.display_loop()
            )
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down Arbihedron...")
        self.running = False
        
        # Close exchange connection
        self.exchange.close()
        
        # Print final statistics
        stats = self.executor.get_statistics()
        
        self.console.print("\n[bold cyan]Final Statistics:[/]")
        self.console.print(f"Total Trades: {stats['total_trades']}")
        self.console.print(f"Successful: {stats['successful_trades']}")
        self.console.print(f"Total Profit: ${stats['total_profit']:.2f}")
        
        logger.success("Shutdown complete")


async def main():
    """Main entry point."""
    bot = ArbihedronBot()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(bot.shutdown())
        )
    
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
