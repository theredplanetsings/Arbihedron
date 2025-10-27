"""
Arbihedron Health Monitor
Provides HTTP health check endpoint and system health tracking.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from aiohttp import web
import psutil
import os

logger = logging.getLogger(__name__)

@dataclass
class HealthMetrics:
    """System health metrics."""
    uptime_seconds: float = 0
    last_activity: Optional[datetime] = None
    total_opportunities: int = 0
    total_executions: int = 0
    total_errors: int = 0
    error_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    active_exchanges: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    restart_count: int = 0
    health_status: str = "healthy"  # healthy, degraded, unhealthy
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "uptime_seconds": self.uptime_seconds,
            "uptime_formatted": self._format_uptime(),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "total_opportunities": self.total_opportunities,
            "total_executions": self.total_executions,
            "total_errors": self.total_errors,
            "error_rate": round(self.error_rate, 4),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "active_exchanges": self.active_exchanges,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "restart_count": self.restart_count,
            "health_status": self.health_status
        }
        
    def _format_uptime(self) -> str:
        """Format uptime as human-readable string."""
        days = int(self.uptime_seconds // 86400)
        hours = int((self.uptime_seconds % 86400) // 3600)
        minutes = int((self.uptime_seconds % 3600) // 60)
        seconds = int(self.uptime_seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)

class HealthMonitor:
    """Monitors system health and provides HTTP health check endpoint."""
    
    def __init__(self, port: int = 8080, alert_manager=None):
        self.port = port
        self.alert_manager = alert_manager
        self.metrics = HealthMetrics()
        self.start_time = datetime.now()
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self.process = psutil.Process(os.getpid())
        
        # the thresholds for health checks
        self.max_error_rate = 0.1  # 10% error rate
        self.max_memory_mb = 1000  # 1GB
        self.max_cpu_percent = 80  # 80% CPU
        self.max_inactive_minutes = 10  # 10 minutes without activity
        
    async def start(self):
        """Initialise health monitor and start HTTP server."""
        # sets up HTTP app
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check_handler)
        self.app.router.add_get('/metrics', self.metrics_handler)
        self.app.router.add_get('/status', self.status_handler)
        
        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()
        
        logger.info(f"Health monitor listening on http://localhost:{self.port}")
        
        # beigns monitoring tasks
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
        
    async def cleanup(self):
        """Cleanup resources."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
                
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
            
    async def _monitor_loop(self):
        """Periodic health monitoring loop."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                await self._update_system_metrics()
                await self._check_health_issues()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            
    async def _update_system_metrics(self):
        """Update system resource metrics."""
        try:
            self.metrics.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            self.metrics.memory_usage_mb = self.process.memory_info().rss / 1024 / 1024
            self.metrics.cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # calculates the error rate
            total_ops = self.metrics.total_opportunities + self.metrics.total_executions
            if total_ops > 0:
                self.metrics.error_rate = self.metrics.total_errors / total_ops
            else:
                self.metrics.error_rate = 0.0
                
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
            
    async def _check_health_issues(self):
        """Check for health issues and send alerts."""
        issues = []
        severity = "warning"
        
        # checks error rate
        if self.metrics.error_rate > self.max_error_rate:
            issues.append(f"High error rate: {self.metrics.error_rate:.1%}")
            severity = "critical"
            
        # checks memory usage
        if self.metrics.memory_usage_mb > self.max_memory_mb:
            issues.append(f"High memory usage: {self.metrics.memory_usage_mb:.0f}MB")
            severity = "critical"
            
        # checks CPU usage
        if self.metrics.cpu_percent > self.max_cpu_percent:
            issues.append(f"High CPU usage: {self.metrics.cpu_percent:.0f}%")
            
        # checks activity
        if self.metrics.last_activity:
            inactive_minutes = (datetime.now() - self.metrics.last_activity).total_seconds() / 60
            if inactive_minutes > self.max_inactive_minutes:
                issues.append(f"No activity for {inactive_minutes:.0f} minutes")
                
        # updates our health status
        if issues:
            if severity == "critical":
                self.metrics.health_status = "unhealthy"
            else:
                self.metrics.health_status = "degraded"
                
            # sends alert
            if self.alert_manager:
                await self.alert_manager.alert_health_issue(
                    "System Health Check",
                    "; ".join(issues),
                    severity=severity
                )
        else:
            self.metrics.health_status = "healthy"
            
    def record_activity(self):
        """Record activity timestamp."""
        self.metrics.last_activity = datetime.now()
        
    def record_opportunity(self):
        """Record opportunity found."""
        self.metrics.total_opportunities += 1
        self.record_activity()
        
    def record_execution(self):
        """Record execution attempt."""
        self.metrics.total_executions += 1
        self.record_activity()
        
    def record_error(self, error: str):
        """Record error."""
        self.metrics.total_errors += 1
        self.metrics.last_error = error[:200]  # truncates
        self.metrics.last_error_time = datetime.now()
        self.record_activity()
        
    def record_restart(self):
        """Record service restart."""
        self.metrics.restart_count += 1
        
    def set_active_exchanges(self, count: int):
        """Set number of active exchanges."""
        self.metrics.active_exchanges = count
        
    async def health_check_handler(self, request: web.Request) -> web.Response:
        """Simple health check endpoint (returns 200 if healthy)."""
        if self.metrics.health_status == "healthy":
            return web.Response(text="OK", status=200)
        elif self.metrics.health_status == "degraded":
            return web.Response(text="DEGRADED", status=200)
        else:
            return web.Response(text="UNHEALTHY", status=503)
            
    async def metrics_handler(self, request: web.Request) -> web.Response:
        """Return detailed metrics as JSON."""
        await self._update_system_metrics()
        return web.json_response(self.metrics.to_dict())
        
    async def status_handler(self, request: web.Request) -> web.Response:
        """Return human-readable status page."""
        await self._update_system_metrics()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Arbihedron Health Status</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: monospace; margin: 40px; background: #1e1e1e; color: #d4d4d4; }}
                .healthy {{ color: #4ec9b0; }}
                .degraded {{ color: #ce9178; }}
                .unhealthy {{ color: #f48771; }}
                .metric {{ margin: 10px 0; }}
                .label {{ color: #9cdcfe; }}
                h1 {{ color: #4ec9b0; }}
            </style>
        </head>
        <body>
            <h1>Arbihedron Health Status</h1>
            <div class="metric">
                <span class="label">Status:</span> 
                <span class="{self.metrics.health_status}">{self.metrics.health_status.upper()}</span>
            </div>
            <div class="metric">
                <span class="label">Uptime:</span> {self.metrics._format_uptime()}
            </div>
            <div class="metric">
                <span class="label">Last Activity:</span> 
                {self.metrics.last_activity.strftime('%Y-%m-%d %H:%M:%S') if self.metrics.last_activity else 'Never'}
            </div>
            <div class="metric">
                <span class="label">Opportunities Found:</span> {self.metrics.total_opportunities}
            </div>
            <div class="metric">
                <span class="label">Executions:</span> {self.metrics.total_executions}
            </div>
            <div class="metric">
                <span class="label">Errors:</span> {self.metrics.total_errors} 
                ({self.metrics.error_rate:.1%} rate)
            </div>
            <div class="metric">
                <span class="label">Memory Usage:</span> {self.metrics.memory_usage_mb:.1f} MB
            </div>
            <div class="metric">
                <span class="label">CPU Usage:</span> {self.metrics.cpu_percent:.1f}%
            </div>
            <div class="metric">
                <span class="label">Active Exchanges:</span> {self.metrics.active_exchanges}
            </div>
            <div class="metric">
                <span class="label">Restart Count:</span> {self.metrics.restart_count}
            </div>
            {f'<div class="metric"><span class="label">Last Error:</span> {self.metrics.last_error}</div>' if self.metrics.last_error else ''}
            <hr>
            <p style="color: #858585;">Auto-refreshes every 30 seconds</p>
        </body>
        </html>
        """
        
        return web.Response(text=html, content_type='text/html')