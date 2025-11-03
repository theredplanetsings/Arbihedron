"""
Arbihedron Alert System
Handles notifications via Email (SMTP) and Slack webhooks.
"""
import smtplib
import asyncio
import aiohttp
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    """Configuration for alert system."""
    # our email settings
    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_recipients: List[str] = None
    
    # slack settings
    slack_enabled: bool = False
    slack_webhook_url: str = ""
    
    # alert thresholds
    min_profit_threshold: float = 0.5  # Min profit % to alert
    max_alerts_per_hour: int = 10
    quiet_hours_start: time = time(23, 0)  # 11 PM
    quiet_hours_end: time = time(7, 0)    # 7 AM
    
    # the alert types enabled
    alert_on_startup: bool = True
    alert_on_shutdown: bool = False
    alert_on_crash: bool = True
    alert_on_restart: bool = True
    alert_on_opportunity: bool = True
    alert_on_execution: bool = True
    alert_on_health_issues: bool = True
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []

class AlertManager:
    """Manages alert notifications via Email and Slack."""
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.alert_count = 0
        self.alert_reset_time = datetime.now()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize async resources."""
        if self.config.slack_enabled:
            self.session = aiohttp.ClientSession()
            
    async def cleanup(self):
        """Cleanup async resources."""
        if self.session:
            await self.session.close()
            
    def _is_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours."""
        now = datetime.now().time()
        start = self.config.quiet_hours_start
        end = self.config.quiet_hours_end
        
        if start < end:
            return start <= now <= end
        else:  # quiet hours span midnight
            return now >= start or now <= end
            
    def _can_send_alert(self, force: bool = False) -> bool:
        """Check if we can send an alert (respects rate limits and quiet hours)."""
        if force:
            return True
            
        # check during quiet hours
        if self._is_quiet_hours():
            logger.info("Skipping alert during quiet hours")
            return False
            
        # resets counter if hour has passed
        if (datetime.now() - self.alert_reset_time).seconds >= 3600:
            self.alert_count = 0
            self.alert_reset_time = datetime.now()
            
        # check the rate limit
        if self.alert_count >= self.config.max_alerts_per_hour:
            logger.warning("Alert rate limit exceeded")
            return False
            
        return True
        
    def _increment_alert_count(self):
        """Increment alert counter."""
        self.alert_count += 1
        
    def _send_email_sync(self, subject: str, body: str, html: bool = False):
        """Send email notification (synchronous)."""
        if not self.config.email_enabled:
            return
            
        if not self.config.email_recipients:
            logger.warning("No email recipients configured")
            return
            
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[Arbihedron] {subject}"
            msg['From'] = self.config.smtp_user
            msg['To'] = ", ".join(self.config.email_recipients)
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
                
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
                
            logger.info(f"Email sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
    async def _send_slack(self, message: str, color: str = "good"):
        """Send Slack notification."""
        if not self.config.slack_enabled or not self.session:
            return
            
        try:
            payload = {
                "attachments": [{
                    "color": color,
                    "text": message,
                    "footer": "Arbihedron Alert System",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            async with self.session.post(
                self.config.slack_webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info("Slack notification sent")
                else:
                    logger.error(f"Slack notification failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            
    async def send_alert(
        self,
        alert_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        force: bool = False,
        color: str = "good"
    ):
        """Send alert via all enabled channels."""
        if not self._can_send_alert(force):
            return
            
        # formats message with details
        full_message = f"**{alert_type}**\n{message}"
        if details:
            full_message += "\n\n**Details:**\n"
            for key, value in details.items():
                full_message += f"• {key}: {value}\n"
                
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message += f"\n_Time: {timestamp}_"
        
        # sends via email (in thread pool to avoid blocking)
        if self.config.email_enabled:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email_sync,
                alert_type,
                full_message.replace("**", "").replace("_", "")
            )
            
        # sends via Slack
        if self.config.slack_enabled:
            await self._send_slack(full_message, color)
            
        self._increment_alert_count()
        
    async def alert_startup(self, version: str = "1.0"):
        """Alert on bot startup."""
        if not self.config.alert_on_startup:
            return
            
        await self.send_alert(
            "Bot Started",
            "Arbihedron has started successfully.",
            details={
                "Version": version,
                "Status": "Running"
            },
            color="good"
        )
        
    async def alert_shutdown(self, reason: str = "Manual"):
        """Alert on bot shutdown."""
        if not self.config.alert_on_shutdown:
            return
            
        await self.send_alert(
            "Bot Stopped",
            "Arbihedron has been shut down.",
            details={
                "Reason": reason,
                "Status": "Stopped"
            },
            color="warning"
        )
        
    async def alert_crash(self, error: str, restart_count: int = 0):
        """Alert on bot crash."""
        if not self.config.alert_on_crash:
            return
            
        await self.send_alert(
            "Bot Crashed",
            "Arbihedron has crashed unexpectedly!",
            details={
                "Error": error[:200],  # truncates long errors
                "Restart Count": restart_count,
                "Status": "Will attempt restart" if restart_count < 10 else "Max restarts reached"
            },
            force=True,  # will always send crash alerts
            color="danger"
        )
        
    async def alert_restart(self, restart_count: int):
        """Alert on bot restart."""
        if not self.config.alert_on_restart:
            return
            
        await self.send_alert(
            "Bot Restarted",
            "Arbihedron has been automatically restarted after a crash.",
            details={
                "Restart Count": restart_count,
                "Status": "Running"
            },
            color="warning"
        )
        
    async def alert_opportunity(
        self,
        path: str,
        profit_pct: float,
        volume: float,
        exchanges: List[str]
    ):
        """Alert on arbitrage opportunity found."""
        if not self.config.alert_on_opportunity:
            return
            
        # only alerts if profit meets threshold
        if profit_pct < self.config.min_profit_threshold:
            return
            
        await self.send_alert(
            "Opportunity Found",
            f"Profitable arbitrage opportunity detected: {profit_pct:.2f}% profit",
            details={
                "Path": path,
                "Profit": f"{profit_pct:.2f}%",
                "Volume": f"${volume:.2f}",
                "Exchanges": ", ".join(exchanges)
            },
            color="good"
        )
        
    async def alert_execution(
        self,
        path: str,
        profit_pct: float,
        final_balance: float,
        success: bool
    ):
        """Alert on trade execution."""
        if not self.config.alert_on_execution:
            return
            
        status = "✅ Success" if success else "❌ Failed"
        color = "good" if success else "danger"
        
        await self.send_alert(
            f" Execution {status}",
            f"Trade execution completed with {status.lower()}",
            details={
                "Path": path,
                "Profit": f"{profit_pct:.2f}%",
                "Final Balance": f"${final_balance:.2f}",
                "Status": status
            },
            color=color
        )
        
    async def alert_health_issue(
        self,
        issue_type: str,
        description: str,
        severity: str = "warning"
    ):
        """Alert on health issues."""
        if not self.config.alert_on_health_issues:
            return
            
        color = "warning" if severity == "warning" else "danger"
        
        await self.send_alert(
            f"Health Issue",
            description,
            details={
                "Issue Type": issue_type,
                "Severity": severity.upper()
            },
            force=(severity == "critical"),
            color=color
        )
        
    async def test_notifications(self) -> Dict[str, bool]:
        """Test all notification channels."""
        results = {
            "email": False,
            "slack": False
        }
        
        # tests email
        if self.config.email_enabled:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self._send_email_sync,
                    "Test Notification",
                    "This is a test notification from Arbihedron. If you receive this, email alerts are working correctly!"
                )
                results["email"] = True
            except Exception as e:
                logger.error(f"Email test failed: {e}")
                
        # tests Slack
        if self.config.slack_enabled:
            try:
                await self._send_slack(
                    "🧪 **Test Notification**\n\nThis is a test notification from Arbihedron. If you receive this, Slack alerts are working correctly!",
                    color="good"
                )
                results["slack"] = True
            except Exception as e:
                logger.error(f"Slack test failed: {e}")
                
        return results

# a convenience function for quick alerts
async def send_quick_alert(message: str, alert_type: str = "INFO"):
    """Send a quick alert using default config (for debugging)."""
    from config import ALERT_CONFIG
    manager = AlertManager(ALERT_CONFIG)
    await manager.initialize()
    try:
        await manager.send_alert(alert_type, message)
    finally:
        await manager.cleanup()