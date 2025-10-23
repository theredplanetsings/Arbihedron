"""Real-time monitoring and display for arbitrage opportunities."""
import asyncio
from datetime import datetime
from typing import List
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from loguru import logger
from models import ArbitrageOpportunity, MarketSnapshot


class ArbitrageMonitor:
    """Monitors and displays arbitrage opportunities in real-time."""
    
    def __init__(self):
        """Initialise monitor."""
        self.console = Console()
        self.latest_snapshot: MarketSnapshot = None
        self.total_opportunities_found = 0
        self.start_time = datetime.now()
    
    def create_dashboard(self, snapshot: MarketSnapshot, stats: dict) -> Layout:
        """Create rich dashboard layout."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="opportunities", ratio=2),
            Layout(name="stats", size=10)
        )
        
        # Header
        runtime = datetime.now() - self.start_time
        header_text = (
            f"🔺 ARBIHEDRON - Triangular Arbitrage Monitor\n"
            f"Runtime: {runtime} | "
            f"Opportunities Found: {self.total_opportunities_found}"
        )
        layout["header"].update(Panel(header_text, style="bold cyan"))
        
        # Opportunities table
        if snapshot and snapshot.opportunities:
            opps_table = self._create_opportunities_table(snapshot.opportunities[:10])
            layout["opportunities"].update(Panel(opps_table, title="Top Opportunities"))
        else:
            layout["opportunities"].update(
                Panel("No opportunities detected...", title="Top Opportunities")
            )
        
        # Statistics
        stats_table = self._create_stats_table(stats)
        layout["stats"].update(Panel(stats_table, title="Execution Statistics"))
        
        return layout
    
    def _create_opportunities_table(
        self, opportunities: List[ArbitrageOpportunity]
    ) -> Table:
        """Create table of opportunities."""
        table = Table(show_header=True, header_style="bold magenta")
        
        table.add_column("Path", style="cyan", width=25)
        table.add_column("Profit %", justify="right", style="green")
        table.add_column("Profit $", justify="right", style="green")
        table.add_column("Risk", justify="right")
        table.add_column("Status", justify="centre")
        
        for opp in opportunities:
            path_str = " → ".join(opp.path.path)
            
            profit_color = "green" if opp.path.profit_percentage > 1.0 else "yellow"
            risk_color = "green" if opp.risk_score < 30 else "yellow" if opp.risk_score < 60 else "red"
            status = "OK" if opp.executable else "NO"
            status_color = "green" if opp.executable else "red"
            
            table.add_row(
                path_str,
                f"[{profit_color}]{opp.path.profit_percentage:.4f}%[/]",
                f"[{profit_color}]${opp.expected_profit:.2f}[/]",
                f"[{risk_color}]{opp.risk_score:.1f}[/]",
                f"[{status_color}]{status}[/]"
            )
        
        return table
    
    def _create_stats_table(self, stats: dict) -> Table:
        """Create statistics table."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")
        
        table.add_row("Total Trades", str(stats.get('total_trades', 0)))
        table.add_row("Successful", str(stats.get('successful_trades', 0)))
        table.add_row(
            "Success Rate", 
            f"{stats.get('success_rate', 0):.2f}%"
        )
        table.add_row(
            "Total Profit", 
            f"${stats.get('total_profit', 0):.2f}"
        )
        table.add_row(
            "Avg Profit", 
            f"${stats.get('avg_profit', 0):.2f}"
        )
        table.add_row(
            "Avg Slippage", 
            f"{stats.get('avg_slippage', 0):.2f}%"
        )
        
        return table
    
    def update_snapshot(self, snapshot: MarketSnapshot):
        """Update latest market snapshot."""
        self.latest_snapshot = snapshot
        if snapshot.opportunities:
            self.total_opportunities_found += len(snapshot.opportunities)
    
    def log_opportunity(self, opportunity: ArbitrageOpportunity):
        """Print opportunity to console."""
        self.console.print(
            f"Opportunity: {opportunity.path} | "
            f"Profit: {opportunity.path.profit_percentage:.4f}% (${opportunity.expected_profit:.2f}) | "
            f"Risk: {opportunity.risk_score:.1f}"
        )
    
    def log_execution(self, execution):
        """Log a trade execution."""
        if execution.success:
            logger.success(
                f"Execution successful: ${execution.actual_profit:.2f} profit "
                f"(Slippage: {execution.slippage:.2f}%)"
            )
        else:
            logger.error(f"Execution failed: {execution.error_message}")
