"""Database persistence layer for Arbihedron."""
import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger
from models import ArbitrageOpportunity, TradeExecution

class ArbihedronDatabase:
    """Handles all data persistence for the arbitrage bot."""
    
    def __init__(self, db_path: str = "data/arbihedron.db"):
        """Initialise database connection."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Sessions table - tracks every bot run
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                exchange TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                total_opportunities INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0.0,
                config_json TEXT
            )
        """)
        
        # Opportunities table - every detected opportunity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                detected_at TIMESTAMP NOT NULL,
                path TEXT NOT NULL,
                profit_percentage REAL NOT NULL,
                expected_profit REAL NOT NULL,
                risk_score REAL NOT NULL,
                executable BOOLEAN NOT NULL,
                reason TEXT,
                details_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # Executions table - actual trades executed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                opportunity_id INTEGER,
                executed_at TIMESTAMP NOT NULL,
                success BOOLEAN NOT NULL,
                actual_profit REAL NOT NULL,
                slippage REAL NOT NULL,
                execution_time_ms INTEGER,
                trades_json TEXT,
                error_message TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
            )
        """)
        
        # System metrics table - performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                recorded_at TIMESTAMP NOT NULL,
                scan_latency_ms REAL,
                opportunities_per_scan INTEGER,
                memory_usage_mb REAL,
                cpu_usage_percent REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def create_session(self, exchange: str, mode: str, config: dict) -> int:
        """Create a new trading session."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (start_time, exchange, mode, config_json)
            VALUES (?, ?, ?, ?)
        """, (datetime.now(), exchange, mode, json.dumps(config)))
        self.conn.commit()
        session_id = cursor.lastrowid
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def end_session(self, session_id: int):
        """Mark a session as completed."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET end_time = ?, status = 'completed'
            WHERE id = ?
        """, (datetime.now(), session_id))
        self.conn.commit()
        logger.info(f"Session {session_id} ended")
    
    def save_opportunity(self, session_id: int, opportunity: ArbitrageOpportunity) -> int:
        """Save a detected arbitrage opportunity."""
        cursor = self.conn.cursor()
        
        path_str = " → ".join(opportunity.path.path)
        details = {
            'start_amount': opportunity.path.start_amount,
            'profit_amount': opportunity.path.profit_amount,
            'fees_total': opportunity.path.fees_total,
            'pairs': [p.symbol for p in opportunity.path.pairs],
            'directions': [d.value for d in opportunity.path.directions]
        }
        
        cursor.execute("""
            INSERT INTO opportunities (
                session_id, detected_at, path, profit_percentage,
                expected_profit, risk_score, executable, reason, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            opportunity.timestamp,
            path_str,
            opportunity.path.profit_percentage,
            opportunity.expected_profit,
            opportunity.risk_score,
            opportunity.executable,
            opportunity.reason,
            json.dumps(details)
        ))
        self.conn.commit()
        
        # updates the session counters
        cursor.execute("""
            UPDATE sessions 
            SET total_opportunities = total_opportunities + 1
            WHERE id = ?
        """, (session_id,))
        self.conn.commit()
        
        return cursor.lastrowid
    
    def save_execution(
        self, 
        session_id: int, 
        execution: TradeExecution,
        opportunity_id: Optional[int] = None
    ) -> int:
        """Save a trade execution."""
        cursor = self.conn.cursor()
        
        execution_time = (
            (datetime.now() - execution.executed_at).total_seconds() * 1000
            if execution.executed_at else 0
        )
        
        cursor.execute("""
            INSERT INTO executions (
                session_id, opportunity_id, executed_at, success,
                actual_profit, slippage, execution_time_ms,
                trades_json, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            opportunity_id,
            execution.executed_at or datetime.now(),
            execution.success,
            execution.actual_profit,
            execution.slippage,
            execution_time,
            json.dumps(execution.trades),
            execution.error_message
        ))
        self.conn.commit()
        
        # updates our session stats
        cursor.execute("""
            UPDATE sessions 
            SET total_trades = total_trades + 1,
                total_profit = total_profit + ?
            WHERE id = ?
        """, (execution.actual_profit, session_id))
        self.conn.commit()
        
        return cursor.lastrowid
    
    def save_system_metrics(
        self, 
        session_id: int,
        scan_latency: float,
        opportunities_count: int
    ):
        """Save system performance metrics."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO system_metrics (
                session_id, recorded_at, scan_latency_ms, opportunities_per_scan
            ) VALUES (?, ?, ?, ?)
        """, (session_id, datetime.now(), scan_latency, opportunities_count))
        self.conn.commit()
    
    def get_session_stats(self, session_id: int) -> Dict:
        """Get statistics for a specific session."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()
        
        if not session:
            return {}
        
        # gets the execution success rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                AVG(actual_profit) as avg_profit,
                SUM(actual_profit) as total_profit,
                AVG(slippage) as avg_slippage
            FROM executions WHERE session_id = ?
        """, (session_id,))
        exec_stats = cursor.fetchone()
        
        return {
            'session_id': session['id'],
            'start_time': session['start_time'],
            'end_time': session['end_time'],
            'exchange': session['exchange'],
            'mode': session['mode'],
            'status': session['status'],
            'total_opportunities': session['total_opportunities'],
            'total_trades': exec_stats['total'] or 0,
            'successful_trades': exec_stats['successful'] or 0,
            'success_rate': (
                (exec_stats['successful'] / exec_stats['total'] * 100)
                if exec_stats['total'] else 0
            ),
            'total_profit': exec_stats['total_profit'] or 0.0,
            'avg_profit': exec_stats['avg_profit'] or 0.0,
            'avg_slippage': exec_stats['avg_slippage'] or 0.0
        }
    
    def get_all_sessions(self) -> List[Dict]:
        """Get all trading sessions."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY start_time DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def export_to_csv(self, output_dir: str = "exports"):
        """Export all data to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # exports the sessions
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions")
        sessions = cursor.fetchall()
        
        with open(output_path / f"sessions_{timestamp}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([desc[0] for desc in cursor.description])
            writer.writerows(sessions)
        
        # exports the opportunities
        cursor.execute("SELECT * FROM opportunities")
        opportunities = cursor.fetchall()
        
        with open(output_path / f"opportunities_{timestamp}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([desc[0] for desc in cursor.description])
            writer.writerows(opportunities)
        
        # exports the executions
        cursor.execute("SELECT * FROM executions")
        executions = cursor.fetchall()
        
        with open(output_path / f"executions_{timestamp}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([desc[0] for desc in cursor.description])
            writer.writerows(executions)
        
        logger.info(f"Data exported to {output_path}")
        return output_path
    
    def export_session_report(self, session_id: int, output_file: str = None):
        """Export a detailed report for a specific session."""
        if output_file is None:
            output_file = f"exports/session_{session_id}_report.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        stats = self.get_session_stats(session_id)
        
        # gets the top opportunities
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM opportunities 
            WHERE session_id = ? 
            ORDER BY profit_percentage DESC 
            LIMIT 10
        """, (session_id,))
        top_opps = [dict(row) for row in cursor.fetchall()]
        
        # gets all the executions
        cursor.execute("""
            SELECT * FROM executions 
            WHERE session_id = ?
            ORDER BY executed_at
        """, (session_id,))
        executions = [dict(row) for row in cursor.fetchall()]
        
        report = {
            'session': stats,
            'top_opportunities': top_opps,
            'executions': executions,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Session report exported to {output_path}")
        return output_path
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")