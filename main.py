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
from database import ArbihedronDatabase

class ArbihedronBot:
    """Main arbitrage bot orchestrator."""
    def __init__(self):
        """Initialise the bot."""
        self.config = config
        
        # initialises the database for persistence
        self.db = ArbihedronDatabase()
        self.session_id = None
        
        # monitoring components (set by service wrapper)
        self.alert_manager = None
        self.health_monitor = None
        
        # gets all the main components set up
        self.exchange = ExchangeClient(config.exchange)
        self.engine = ArbitrageEngine(self.exchange, config.trading)
        self.executor = TradeExecutor(self.exchange, config.risk, self.db)
        self.monitor = ArbitrageMonitor(self.db)
        self.console = Console()
        
        # configures logging to file
        logger.add(
            "logs/arbihedron_{time}.log",
            rotation="1 day",
            retention="7 days",
            level=config.log_level
        )
    
    def set_monitoring(self, alert_manager=None, health_monitor=None):
        """Set monitoring components (called by service wrapper)."""
        self.alert_manager = alert_manager
        self.health_monitor = health_monitor
        if self.health_monitor:
            logger.info("Health monitoring enabled")
    
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
            
            # creates a new session in the database
            session_config = {
                'min_profit_threshold': config.trading.min_profit_threshold,
                'max_position_size': config.trading.max_position_size,
                'slippage_tolerance': config.trading.slippage_tolerance,
                'base_currencies': config.trading.base_currencies
            }
            self.session_id = self.db.create_session(
                exchange=config.exchange.name,
                mode=mode,
                config=session_config
            )
            
            # passes session ID to components that need it
            self.executor.set_session_id(self.session_id)
            self.monitor.set_session_id(self.session_id)
            
            logger.success(f"Initialisation complete - Session ID: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Initialisation failed: {e}")
            raise
    
    async def scan_and_execute_loop(self):
        """Main loop: scan for opportunities and execute."""
        scan_interval = 1.0  # checks for opportunities every second
        
        while self.running:
            try:
                scan_start = datetime.now()
                
                # scans for arbitrage opportunities
                snapshot = await self.engine.scan_opportunities()
                self.monitor.update_snapshot(snapshot)
                
                # records the activity for health monitor
                if self.health_monitor:
                    self.health_monitor.record_activity()
                    self.health_monitor.set_active_exchanges(len(snapshot.prices))
                
                # records the scan performance
                scan_latency = (datetime.now() - scan_start).total_seconds() * 1000
                self.db.save_system_metrics(
                    self.session_id,
                    scan_latency,
                    len(snapshot.opportunities)
                )
                
                # executes the best ones we find
                for opportunity in snapshot.opportunities[:3]:  # just take top 3
                    if opportunity.executable:
                        self.monitor.log_opportunity(opportunity)
                        
                        # records opportunity for health monitor
                        if self.health_monitor:
                            self.health_monitor.record_opportunity()
                        
                        # sends opportunity alert
                        if self.alert_manager:
                            try:
                                await self.alert_manager.alert_opportunity(
                                    path=opportunity.path.display_path(),
                                    profit_pct=opportunity.profit_percentage,
                                    volume=opportunity.volume,
                                    exchanges=list(set(pair.exchange for pair in opportunity.path.pairs))
                                )
                            except Exception as e:
                                logger.error(f"Failed to send opportunity alert: {e}")
                        
                        # runs the trade
                        execution = await self.executor.execute_opportunity(opportunity)
                        self.monitor.log_execution(execution)
                        
                        # records execution for health monitor
                        if self.health_monitor:
                            self.health_monitor.record_execution()
                        
                        # sends execution alert
                        if self.alert_manager and execution:
                            try:
                                await self.alert_manager.alert_execution(
                                    path=opportunity.path.display_path(),
                                    profit_pct=opportunity.profit_percentage,
                                    final_balance=getattr(execution, 'final_balance', 0),
                                    success=getattr(execution, 'success', False)
                                )
                            except Exception as e:
                                logger.error(f"Failed to send execution alert: {e}")
                        
                        # brief pause inbetween trades
                        await asyncio.sleep(0.1)
                
                # waits before scanning again
                await asyncio.sleep(scan_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
                # records error for health monitor
                if self.health_monitor:
                    self.health_monitor.record_error(str(e))
                
                await asyncio.sleep(5)  # gives it a bit longer if something went wrong
    
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
            # gets everything started
            await self.initialize()
            
            # runs both the scanning and display at the same time
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
        
        # closes the exchange connection properly
        self.exchange.close()
        
        # ends the database session
        if self.session_id:
            self.db.end_session(self.session_id)
        
        # shows the final stats
        stats = self.executor.get_statistics()
        
        self.console.print("\n[bold cyan]Final Statistics:[/]")
        self.console.print(f"Total Trades: {stats['total_trades']}")
        self.console.print(f"Successful: {stats['successful_trades']}")
        self.console.print(f"Total Profit: ${stats['total_profit']:.2f}")
        
        # exports all the data to CSV
        try:
            export_path = self.db.export_to_csv()
            self.console.print(f"\n[green]Data exported to: {export_path}[/]")
            
            # also exports the session report
            report_path = self.db.export_session_report(self.session_id)
            self.console.print(f"[green]Session report: {report_path}[/]")
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
        
        # closes database
        self.db.close()
        
        logger.success("Shutdown complete")

async def main():
    """Main entry point."""
    bot = ArbihedronBot()
    
    # handles ctrl+c and kill signals gracefully
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(bot.shutdown())
        )
    
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())