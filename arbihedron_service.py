#!/usr/bin/env python3
"""Service wrapper for Arbihedron with auto-restart and health monitoring."""
import asyncio
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from loguru import logger
from main import ArbihedronBot
from alerts import AlertManager
from health_monitor import HealthMonitor
from config import ALERT_CONFIG, HEALTH_CONFIG

class ArbihedronService:
    """Service wrapper with health monitoring and auto-restart."""
    
    def __init__(self):
        """Initialise service."""
        self.bot = None
        self.alert_manager = None
        self.health_monitor = None
        self.running = True
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_window = 3600  # 1 hour
        self.restart_times = []
        self.last_health_check = time.time()
        self.health_check_interval = 60  # 1 minute
        
        # sets up service logging
        log_path = Path("logs/service")
        log_path.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            "logs/service/arbihedron_service_{time}.log",
            rotation="1 day",
            retention="30 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        
        # sets up signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        
        logger.info("Arbihedron Service initialized")
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def _should_restart(self) -> bool:
        """Check if we should restart based on restart limits."""
        now = time.time()
        
        # cleans the old restart times outside the window
        self.restart_times = [
            t for t in self.restart_times 
            if now - t < self.restart_window
        ]
        
        # checks if we've exceeded max restarts in the window
        if len(self.restart_times) >= self.max_restarts:
            logger.error(
                f"Exceeded {self.max_restarts} restarts in "
                f"{self.restart_window}s window. Giving up."
            )
            return False
        
        return True
    
    def _record_restart(self):
        """Record a restart attempt."""
        self.restart_times.append(time.time())
        self.restart_count += 1
    
    async def _run_bot_with_monitoring(self):
        """Run the bot with health monitoring."""
        try:
            logger.info("Starting Arbihedron bot...")
            
            # initialises alert manager
            if ALERT_CONFIG.email_enabled or ALERT_CONFIG.slack_enabled:
                self.alert_manager = AlertManager(ALERT_CONFIG)
                await self.alert_manager.initialize()
                logger.info("Alert manager initialised")
                
                # Send startup alert
                await self.alert_manager.alert_startup(version="1.0")
            
            # initialises health monitor
            if HEALTH_CONFIG.enabled:
                self.health_monitor = HealthMonitor(
                    port=HEALTH_CONFIG.port,
                    alert_manager=self.alert_manager
                )
                await self.health_monitor.initialize()
                logger.info(f"Health monitor started on port {HEALTH_CONFIG.port}")
            
            # initialises and run bot
            self.bot = ArbihedronBot()
            
            # passes in monitoring components to bot
            if hasattr(self.bot, 'set_monitoring'):
                self.bot.set_monitoring(self.alert_manager, self.health_monitor)
            
            # runs the bot
            await self.bot.run()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.running = False
        except Exception as e:
            logger.error(f"Bot crashed with error: {e}", exc_info=True)
            
            # sends out crash alert
            if self.alert_manager:
                try:
                    await self.alert_manager.alert_crash(str(e), self.restart_count)
                except Exception as alert_error:
                    logger.error(f"Failed to send crash alert: {alert_error}")
            
            raise
        finally:
            # cleanup!
            if self.bot:
                try:
                    await self.bot.shutdown()
                except Exception as e:
                    logger.error(f"Error during bot shutdown: {e}")
            
            if self.health_monitor:
                try:
                    await self.health_monitor.cleanup()
                except Exception as e:
                    logger.error(f"Error during health monitor cleanup: {e}")
            
            if self.alert_manager:
                try:
                    await self.alert_manager.cleanup()
                except Exception as e:
                    logger.error(f"Error during alert manager cleanup: {e}")

    async def run(self):
        """Main service loop with auto-restart."""
        logger.info("Arbihedron Service starting...")
        logger.info(f"Max restarts: {self.max_restarts} per {self.restart_window}s")
        
        while self.running:
            try:
                # runs the bot
                await self._run_bot_with_monitoring()
                
                # if we've gotten here bot is stopped normally
                if self.running:
                    logger.warning("Bot stopped unexpectedly, checking restart policy...")
                    
                    if self._should_restart():
                        self._record_restart()
                        logger.info(
                            f"Restarting bot (attempt {self.restart_count})... "
                            f"Waiting 5 seconds..."
                        )
                        # sends the restart alert
                        if self.alert_manager:
                            try:
                                await self.alert_manager.alert_restart(self.restart_count)
                            except Exception as e:
                                logger.error(f"Failed to send restart alert: {e}")
                        
                        await asyncio.sleep(5)
                    else:
                        logger.error("Restart limit exceeded, stopping service")
                        self.running = False
                else:
                    logger.info("Service stopped normally")
                    
            except Exception as e:
                logger.error(f"Service error: {e}", exc_info=True)
                
                # sends the crash alert
                if self.alert_manager:
                    try:
                        await self.alert_manager.alert_crash(str(e), self.restart_count)
                    except Exception as alert_error:
                        logger.error(f"Failed to send crash alert: {alert_error}")
                
                if self.running and self._should_restart():
                    self._record_restart()
                    logger.info(
                        f"Restarting after error (attempt {self.restart_count})... "
                        f"Waiting 10 seconds..."
                    )
                    await asyncio.sleep(10)
                else:
                    logger.error("Stopping service due to errors")
                    self.running = False
        
        logger.info("Arbihedron Service stopped")
        logger.info(f"Total restarts during this session: {self.restart_count}")

async def main():
    """Entry point for service."""
    service = ArbihedronService()
    await service.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Service failed: {e}", exc_info=True)
        sys.exit(1)