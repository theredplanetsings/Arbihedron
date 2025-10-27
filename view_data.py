#!/usr/bin/env python3
"""View and analyze historical data from the database."""
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from database import ArbihedronDatabase
def show_sessions(db: ArbihedronDatabase):
    """Display all trading sessions."""
    console = Console()
    sessions = db.get_all_sessions()
    
    if not sessions:
        console.print("[yellow]No sessions found[/]")
        return
    
    table = Table(title="Trading Sessions", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Start Time", style="green")
    table.add_column("Duration", style="yellow")
    table.add_column("Exchange", style="magenta")
    table.add_column("Mode", style="blue")
    table.add_column("Opportunities", justify="right")
    table.add_column("Trades", justify="right")
    table.add_column("Profit", justify="right", style="green")
    table.add_column("Status", style="cyan")
    
    for session in sessions:
        start = datetime.fromisoformat(session['start_time'])
        if session['end_time']:
            end = datetime.fromisoformat(session['end_time'])
            duration = str(end - start).split('.')[0]  # remove microseconds
        else:
            duration = "In Progress"
        
        table.add_row(
            str(session['id']),
            start.strftime("%Y-%m-%d %H:%M:%S"),
            duration,
            session['exchange'],
            session['mode'],
            str(session['total_opportunities']),
            str(session['total_trades']),
            f"${session['total_profit']:.2f}",
            session['status']
        )
    
    console.print(table)


def show_session_details(db: ArbihedronDatabase, session_id: int):
    """Display detailed statistics for a specific session."""
    console = Console()
    stats = db.get_session_stats(session_id)
    
    if not stats:
        console.print(f"[red]Session {session_id} not found[/]")
        return
    
    # Session overview
    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]Session #{session_id} Details[/]\n\n"
        f"[green]Exchange:[/] {stats['exchange']}\n"
        f"[green]Mode:[/] {stats['mode']}\n"
        f"[green]Start:[/] {stats['start_time']}\n"
        f"[green]End:[/] {stats['end_time'] or 'In Progress'}\n"
        f"[green]Status:[/] {stats['status']}\n",
        title="Session Info"
    ))
    
    # Statistics
    stats_table = Table(title="Performance Metrics", show_header=False)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", justify="right", style="yellow")
    
    stats_table.add_row("Total Opportunities Detected", str(stats['total_opportunities']))
    stats_table.add_row("Total Trades Executed", str(stats['total_trades']))
    stats_table.add_row("Successful Trades", str(stats['successful_trades']))
    stats_table.add_row("Success Rate", f"{stats['success_rate']:.2f}%")
    stats_table.add_row("Total Profit", f"${stats['total_profit']:.2f}")
    stats_table.add_row("Average Profit per Trade", f"${stats['avg_profit']:.2f}")
    stats_table.add_row("Average Slippage", f"{stats['avg_slippage']:.2f}%")
    
    console.print(stats_table)
    
    # Gets the top opportunities
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT path, profit_percentage, expected_profit, executable
        FROM opportunities
        WHERE session_id = ?
        ORDER BY profit_percentage DESC
        LIMIT 10
    """, (session_id,))
    
    top_opps = cursor.fetchall()
    
    if top_opps:
        opp_table = Table(title="Top 10 Opportunities", show_header=True)
        opp_table.add_column("Path", style="cyan")
        opp_table.add_column("Profit %", justify="right", style="green")
        opp_table.add_column("Expected $", justify="right", style="green")
        opp_table.add_column("Executable", justify="center")
        
        for opp in top_opps:
            opp_table.add_row(
                opp['path'],
                f"{opp['profit_percentage']:.4f}%",
                f"${opp['expected_profit']:.2f}",
                "ok:" if opp['executable'] else "no:"
            )
        
        console.print("\n")
        console.print(opp_table)


def export_session(db: ArbihedronDatabase, session_id: int):
    """Export a session to JSON."""
    console = Console()
    try:
        report_path = db.export_session_report(session_id)
        console.print(f"[green]Session report exported to: {report_path}[/]")
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/]")


def export_all(db: ArbihedronDatabase):
    """Export all data to CSV."""
    console = Console()
    try:
        export_path = db.export_to_csv()
        console.print(f"[green]All data exported to: {export_path}[/]")
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/]")


def show_summary(db: ArbihedronDatabase):
    """Show overall summary across all sessions."""
    console = Console()
    cursor = db.conn.cursor()
    
    # Overall stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_sessions,
            SUM(total_opportunities) as total_opps,
            SUM(total_trades) as total_trades,
            SUM(total_profit) as total_profit
        FROM sessions
    """)
    overall = cursor.fetchone()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_execs,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
            AVG(actual_profit) as avg_profit,
            MIN(executed_at) as first_trade,
            MAX(executed_at) as last_trade
        FROM executions
    """)
    exec_stats = cursor.fetchone()
    
    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]Overall Performance Summary[/]\n\n"
        f"[green]Total Sessions:[/] {overall['total_sessions']}\n"
        f"[green]Total Opportunities:[/] {overall['total_opps'] or 0}\n"
        f"[green]Total Trades:[/] {overall['total_trades'] or 0}\n"
        f"[green]Successful Trades:[/] {exec_stats['successful'] or 0}\n"
        f"[green]Success Rate:[/] {(exec_stats['successful'] / exec_stats['total_execs'] * 100 if exec_stats['total_execs'] else 0):.2f}%\n"
        f"[green]Total Profit:[/] ${overall['total_profit'] or 0:.2f}\n"
        f"[green]Avg Profit per Trade:[/] ${exec_stats['avg_profit'] or 0:.2f}\n"
        f"[green]First Trade:[/] {exec_stats['first_trade'] or 'N/A'}\n"
        f"[green]Last Trade:[/] {exec_stats['last_trade'] or 'N/A'}\n",
        title="Statistics"
    ))

def main():
    """Main entry point."""
    console = Console()
    db = ArbihedronDatabase()
    
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/]")
        console.print("  python view_data.py sessions              - List all sessions")
        console.print("  python view_data.py session <id>          - View session details")
        console.print("  python view_data.py export <id>           - Export session to JSON")
        console.print("  python view_data.py export-all            - Export all data to CSV")
        console.print("  python view_data.py summary               - Show overall summary")
        return
    
    command = sys.argv[1]
    
    if command == "sessions":
        show_sessions(db)
    elif command == "session" and len(sys.argv) > 2:
        session_id = int(sys.argv[2])
        show_session_details(db, session_id)
    elif command == "export" and len(sys.argv) > 2:
        session_id = int(sys.argv[2])
        export_session(db, session_id)
    elif command == "export-all":
        export_all(db)
    elif command == "summary":
        show_summary(db)
    else:
        console.print("[red]Invalid command[/]")
    
    db.close()


if __name__ == "__main__":
    main()