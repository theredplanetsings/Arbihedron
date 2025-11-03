"""Analytics and reporting module for Arbihedron."""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import json
from database import ArbihedronDatabase
class ArbihedronAnalytics:
    """Generate analytics and reports from trading data."""
    
    def __init__(self, db: ArbihedronDatabase):
        """Initialise analytics."""
        self.db = db or ArbihedronDatabase()
    
    def get_overall_stats(self) -> Dict:
        """Get overall statistics across all sessions."""
        cursor = self.db.conn.cursor()
        
        # our session stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                SUM(total_opportunities) as total_opportunities,
                SUM(total_trades) as total_trades,
                SUM(total_profit) as total_profit,
                MIN(start_time) as first_session,
                MAX(COALESCE(end_time, start_time)) as last_session
            FROM sessions
        """)
        session_stats = dict(cursor.fetchone())
        
        # our execution stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_executions,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_executions,
                AVG(actual_profit) as avg_profit,
                MAX(actual_profit) as max_profit,
                MIN(actual_profit) as min_profit,
                AVG(slippage) as avg_slippage,
                AVG(execution_time_ms) as avg_execution_time
            FROM executions
        """)
        exec_stats = dict(cursor.fetchone())
        
        # calculate the success rate
        if exec_stats['total_executions']:
            success_rate = (exec_stats['successful_executions'] / 
                          exec_stats['total_executions'] * 100)
        else:
            success_rate = 0
        
        # calculate the runtime
        if session_stats['first_session'] and session_stats['last_session']:
            first = datetime.fromisoformat(session_stats['first_session'])
            last = datetime.fromisoformat(session_stats['last_session'])
            runtime = last - first
        else:
            runtime = timedelta(0)
        
        return {
            'total_sessions': session_stats['total_sessions'] or 0,
            'total_opportunities': session_stats['total_opportunities'] or 0,
            'total_trades': session_stats['total_trades'] or 0,
            'total_executions': exec_stats['total_executions'] or 0,
            'successful_executions': exec_stats['successful_executions'] or 0,
            'success_rate': success_rate,
            'total_profit': session_stats['total_profit'] or 0.0,
            'avg_profit': exec_stats['avg_profit'] or 0.0,
            'max_profit': exec_stats['max_profit'] or 0.0,
            'min_profit': exec_stats['min_profit'] or 0.0,
            'avg_slippage': exec_stats['avg_slippage'] or 0.0,
            'avg_execution_time': exec_stats['avg_execution_time'] or 0.0,
            'total_runtime_hours': runtime.total_seconds() / 3600,
            'first_session': session_stats['first_session'],
            'last_session': session_stats['last_session']
        }
    
    def get_daily_stats(self) -> List[Dict]:
        """Get daily aggregated statistics."""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(executed_at) as date,
                COUNT(*) as trades,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                SUM(actual_profit) as profit,
                AVG(slippage) as avg_slippage
            FROM executions
            GROUP BY DATE(executed_at)
            ORDER BY date
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_hourly_distribution(self) -> List[Dict]:
        """Get trading activity by hour of day."""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                CAST(strftime('%H', executed_at) AS INTEGER) as hour,
                COUNT(*) as trades,
                AVG(actual_profit) as avg_profit
            FROM executions
            GROUP BY hour
            ORDER BY hour
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_top_opportunities(self, limit: int = 10) -> List[Dict]:
        """Get top N opportunities by profit percentage."""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                path,
                profit_percentage,
                expected_profit,
                risk_score,
                detected_at,
                executable
            FROM opportunities
            ORDER BY profit_percentage DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_exchange_comparison(self) -> List[Dict]:
        """Compare performance across exchanges."""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                s.exchange,
                COUNT(DISTINCT s.id) as sessions,
                SUM(s.total_opportunities) as opportunities,
                SUM(s.total_trades) as trades,
                SUM(s.total_profit) as profit,
                AVG(CASE 
                    WHEN s.total_trades > 0 
                    THEN CAST(e.successful_count AS FLOAT) / s.total_trades 
                    ELSE 0 
                END) * 100 as success_rate
            FROM sessions s
            LEFT JOIN (
                SELECT session_id, 
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_count
                FROM executions
                GROUP BY session_id
            ) e ON s.id = e.session_id
            GROUP BY s.exchange
            ORDER BY profit DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_profit_trends(self, days: int = 30) -> List[Dict]:
        """Get profit trends over last N days."""
        cursor = self.db.conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT 
                DATE(executed_at) as date,
                SUM(actual_profit) as daily_profit,
                COUNT(*) as trades,
                AVG(actual_profit) as avg_profit_per_trade
            FROM executions
            WHERE executed_at >= ?
            GROUP BY DATE(executed_at)
            ORDER BY date
        """, (cutoff_date,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_path_analysis(self) -> List[Dict]:
        """Analyze most profitable currency paths."""
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                path,
                COUNT(*) as occurrences,
                AVG(profit_percentage) as avg_profit_pct,
                MAX(profit_percentage) as max_profit_pct,
                SUM(CASE WHEN executable THEN 1 ELSE 0 END) as executable_count
            FROM opportunities
            GROUP BY path
            HAVING COUNT(*) >= 3
            ORDER BY avg_profit_pct DESC
            LIMIT 20
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_metrics(self) -> Dict:
        """Calculate key performance metrics."""
        overall = self.get_overall_stats()
        
        # calculate the additional metrics
        if overall['total_opportunities'] > 0:
            executable_rate = (overall['total_executions'] / 
                             overall['total_opportunities'] * 100)
        else:
            executable_rate = 0
        
        if overall['total_runtime_hours'] > 0:
            opportunities_per_hour = (overall['total_opportunities'] / 
                                     overall['total_runtime_hours'])
            trades_per_hour = (overall['total_trades'] / 
                              overall['total_runtime_hours'])
        else:
            opportunities_per_hour = 0
            trades_per_hour = 0
        
        return {
            'executable_rate': executable_rate,
            'opportunities_per_hour': opportunities_per_hour,
            'trades_per_hour': trades_per_hour,
            'profit_per_hour': (overall['total_profit'] / 
                               overall['total_runtime_hours'] 
                               if overall['total_runtime_hours'] > 0 else 0),
            'avg_profit_per_trade': overall['avg_profit'],
            'success_rate': overall['success_rate'],
            'uptime_hours': overall['total_runtime_hours']
        }
    
    def generate_chart_data(self) -> Dict:
        """Generate data formatted for charts."""
        daily_stats = self.get_daily_stats()
        hourly_dist = self.get_hourly_distribution()
        
        # format for charts
        chart_data = {
            'daily_profit': {
                'labels': [d['date'] for d in daily_stats],
                'data': [d['profit'] or 0 for d in daily_stats]
            },
            'daily_trades': {
                'labels': [d['date'] for d in daily_stats],
                'data': [d['trades'] for d in daily_stats]
            },
            'hourly_activity': {
                'labels': [f"{h['hour']:02d}:00" for h in hourly_dist],
                'data': [h['trades'] for h in hourly_dist]
            },
            'success_rate_daily': {
                'labels': [d['date'] for d in daily_stats],
                'data': [
                    (d['successful'] / d['trades'] * 100) 
                    if d['trades'] > 0 else 0 
                    for d in daily_stats
                ]
            }
        }
        
        return chart_data
    
    def export_analytics_json(self, output_file: str = None) -> str:
        """Export complete analytics to JSON."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"exports/analytics_{timestamp}.json"
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        analytics = {
            'generated_at': datetime.now().isoformat(),
            'overall_stats': self.get_overall_stats(),
            'performance_metrics': self.get_performance_metrics(),
            'daily_stats': self.get_daily_stats(),
            'hourly_distribution': self.get_hourly_distribution(),
            'top_opportunities': self.get_top_opportunities(20),
            'exchange_comparison': self.get_exchange_comparison(),
            'profit_trends': self.get_profit_trends(30),
            'path_analysis': self.get_path_analysis(),
            'chart_data': self.generate_chart_data()
        }
        
        with open(output_file, 'w') as f:
            json.dump(analytics, f, indent=2, default=str)
        
        return output_file