#!/usr/bin/env python3
"""Test alert notifications for Arbihedron."""
import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from alerts import AlertManager
from config import ALERT_CONFIG

async def test_alert_system():
    """Test all alert channels."""
    console = Console()
    
    console.print("\n[bold cyan]Testing Arbihedron Alert System[/bold cyan]\n")
    
    # shows us configurations
    console.print(Panel(
        f"[yellow]Email:[/yellow] {'ok: Enabled' if ALERT_CONFIG.email_enabled else 'no: Disabled'}\n"
        f"[yellow]  SMTP Host:[/yellow] {ALERT_CONFIG.smtp_host}\n"
        f"[yellow]  SMTP Port:[/yellow] {ALERT_CONFIG.smtp_port}\n"
        f"[yellow]  SMTP User:[/yellow] {ALERT_CONFIG.smtp_user}\n"
        f"[yellow]  Recipients:[/yellow] {', '.join(ALERT_CONFIG.email_recipients) if ALERT_CONFIG.email_recipients else 'None'}\n"
        f"\n"
        f"[yellow]Slack:[/yellow] {'ok: Enabled' if ALERT_CONFIG.slack_enabled else 'no: Disabled'}\n"
        f"[yellow]  Webhook:[/yellow] {'Configured' if ALERT_CONFIG.slack_webhook_url else 'Not configured'}\n"
        f"\n"
        f"[yellow]Settings:[/yellow]\n"
        f"[yellow]  Min Profit Alert:[/yellow] {ALERT_CONFIG.min_profit_threshold}%\n"
        f"[yellow]  Max Alerts/Hour:[/yellow] {ALERT_CONFIG.max_alerts_per_hour}\n"
        f"[yellow]  Quiet Hours:[/yellow] {ALERT_CONFIG.quiet_hours_start.strftime('%H:%M')} - {ALERT_CONFIG.quiet_hours_end.strftime('%H:%M')}",
        title="Current Configuration",
        border_style="blue"
    ))
    
    # checks if any alerts are enabled
    if not ALERT_CONFIG.email_enabled and not ALERT_CONFIG.slack_enabled:
        console.print("\n[red]❌ No alert channels are enabled![/red]")
        console.print("\n[yellow]To enable alerts:[/yellow]")
        console.print("  1. Run: [cyan]./arbi config-alerts[/cyan]")
        console.print("  2. Or edit your .env file directly")
        console.print("\n[yellow]Email setup (Gmail example):[/yellow]")
        console.print("  EMAIL_ENABLED=true")
        console.print("  SMTP_HOST=smtp.gmail.com")
        console.print("  SMTP_PORT=587")
        console.print("  SMTP_USER=your-email@gmail.com")
        console.print("  SMTP_PASSWORD=your-app-password  # Use App Password, not regular password!")
        console.print("  EMAIL_RECIPIENTS=recipient@example.com")
        console.print("\n[yellow]Slack setup:[/yellow]")
        console.print("  SLACK_ENABLED=true")
        console.print("  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        console.print("\n[dim]Tip: For Gmail, you need to create an App Password:[/dim]")
        console.print("[dim]  https://support.google.com/accounts/answer/185833[/dim]")
        return
    
    # initialise alert manager
    console.print("\n[cyan]Initialising alert manager...[/cyan]")
    manager = AlertManager(ALERT_CONFIG)
    await manager.initialize()
    
    try:
        # tests all of the channels
        console.print("\n[cyan]Sending test notifications...[/cyan]")
        console.print("[dim](This may take a few seconds)[/dim]\n")
        
        results = await manager.test_notifications()
        
        # shows us results
        console.print("\n[bold]Test Results:[/bold]")
        
        if ALERT_CONFIG.email_enabled:
            if results['email']:
                console.print("  [green]ok:[/green] Email: [green]SUCCESS[/green]")
                console.print(f"    [dim]Test email sent to: {', '.join(ALERT_CONFIG.email_recipients)}[/dim]")
            else:
                console.print("  [red]no:[/red] Email: [red]FAILED[/red]")
                console.print("    [yellow]Check your SMTP settings and credentials[/yellow]")
                console.print("    [dim]For Gmail: Make sure you're using an App Password[/dim]")
        
        if ALERT_CONFIG.slack_enabled:
            if results['slack']:
                console.print("  [green]ok:[/green] Slack: [green]SUCCESS[/green]")
                console.print("    [dim]Test message sent to your Slack channel[/dim]")
            else:
                console.print("  [red]no:[/red] Slack: [red]FAILED[/red]")
                console.print("    [yellow]Check your webhook URL[/yellow]")
        
        # tests different alert types
        if any(results.values()):
            console.print("\n[cyan]Testing different alert types...[/cyan]\n")
            
            # tests the opportunity alert
            console.print("  Testing opportunity alert...")
            await manager.alert_opportunity(
                path="BTC → ETH → BNB",
                profit_pct=1.23,
                volume=1000.0,
                exchanges=["Binance", "Kraken"]
            )
            await asyncio.sleep(1)
            
            # tests the execution alert
            console.print("  Testing execution alert...")
            await manager.alert_execution(
                path="BTC → ETH → BNB",
                profit_pct=1.23,
                final_balance=1012.30,
                success=True
            )
            await asyncio.sleep(1)
            
            # tests the health alert
            console.print("  Testing health alert...")
            await manager.alert_health_issue(
                issue_type="Test",
                description="This is a test health alert",
                severity="warning"
            )
            
            console.print("\n[green]ok: All test alerts sent![/green]")
            console.print("[dim]Check your email/Slack to verify receipt[/dim]")
        else:
            console.print("\n[red]No successful channels to test alert types with[/red]")
        
    finally:
        await manager.cleanup()
    
    console.print("\n[bold green]Alert system test complete![/bold green]\n")

def main():
    """Entry point."""
    try:
        asyncio.run(test_alert_system())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()