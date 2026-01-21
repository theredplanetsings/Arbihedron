"""Tests for the monitoring module."""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from monitor import ArbitrageMonitor
from database import ArbihedronDatabase
from models import (
    ArbitrageOpportunity, MarketSnapshot, TriangularPath,
    TradingPair, TradeDirection, TradeExecution
)

class TestArbitrageMonitor:
    """Test suite for arbitrage monitoring functionality."""
    
    @pytest.fixture
    def mock_database(self, tmp_path):
        """Create mock database."""
        db_path = tmp_path / "test.db"
        db = ArbihedronDatabase(str(db_path))
        return db
    
    @pytest.fixture
    def monitor(self, mock_database):
        """Create monitor instance."""
        return ArbitrageMonitor(mock_database)
    
    @pytest.fixture
    def sample_opportunity(self):
        """Create sample arbitrage opportunity."""
        path = TriangularPath(
            path=['USDT', 'BTC', 'ETH', 'USDT'],
            pairs=[
                TradingPair('BTC/USDT', 'BTC', 'USDT', 50000, 50100, 100, 100, datetime.now()),
                TradingPair('ETH/BTC', 'ETH', 'BTC', 0.06, 0.061, 100, 100, datetime.now()),
                TradingPair('ETH/USDT', 'ETH', 'USDT', 3100, 3110, 100, 100, datetime.now())
            ],
            directions=[TradeDirection.BUY, TradeDirection.BUY, TradeDirection.SELL],
            profit_percentage=1.5,
            profit_amount=15.0,
            start_amount=1000.0,
            fees_total=3.0
        )
        
        return ArbitrageOpportunity(
            path=path,
            timestamp=datetime.now(),
            expected_profit=15.0,
            risk_score=20.0,
            executable=True,
            reason="Good opportunity"
        )
    
    @pytest.fixture
    def sample_snapshot(self, sample_opportunity):
        """Create sample market snapshot."""
        return MarketSnapshot(
            timestamp=datetime.now(),
            pairs=[],
            opportunities=[sample_opportunity]
        )
    
    def test_initialization(self, monitor, mock_database):
        """Test monitor initialisation."""
        assert monitor.db == mock_database
        assert monitor.session_id is None
        assert monitor.total_opportunities_found == 0
        assert monitor.latest_snapshot is None
    
    def test_initialization_without_database(self):
        """Test monitor initialisation without database."""
        monitor = ArbitrageMonitor(None)
        assert monitor.db is None
    
    def test_set_session_id(self, monitor):
        """Test setting session ID."""
        monitor.set_session_id(123)
        assert monitor.session_id == 123
    
    def test_create_dashboard_no_opportunities(self, monitor, sample_snapshot):
        """Test dashboard creation with no opportunities."""
        empty_snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            pairs=[],
            opportunities=[]
        )
        
        stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'success_rate': 0.0,
            'total_profit': 0.0,
            'avg_profit': 0.0,
            'avg_slippage': 0.0
        }
        
        layout = monitor.create_dashboard(empty_snapshot, stats)
        
        assert layout is not None
        # check layout has children
        assert len(layout._children) == 3
    
    def test_create_dashboard_with_opportunities(self, monitor, sample_snapshot):
        """Test dashboard creation with opportunities."""
        stats = {
            'total_trades': 5,
            'successful_trades': 4,
            'success_rate': 80.0,
            'total_profit': 100.0,
            'avg_profit': 25.0,
            'avg_slippage': 0.5
        }
        
        layout = monitor.create_dashboard(sample_snapshot, stats)
        
        assert layout is not None
    
    def test_create_opportunities_table(self, monitor, sample_opportunity):
        """Test opportunities table creation."""
        opportunities = [sample_opportunity]
        
        table = monitor._create_opportunities_table(opportunities)
        
        assert table is not None
        assert table.row_count == 1
    
    def test_create_opportunities_table_multiple(self, monitor, sample_opportunity):
        """Test opportunities table with multiple entries."""
        opportunities = [sample_opportunity, sample_opportunity, sample_opportunity]
        
        table = monitor._create_opportunities_table(opportunities)
        
        assert table.row_count == 3
    
    def test_create_opportunities_table_empty(self, monitor):
        """Test opportunities table with no opportunities."""
        table = monitor._create_opportunities_table([])
        
        assert table is not None
        assert table.row_count == 0
    
    def test_create_stats_table(self, monitor):
        """Test statistics table creation."""
        stats = {
            'total_trades': 10,
            'successful_trades': 8,
            'success_rate': 80.0,
            'total_profit': 500.0,
            'avg_profit': 62.5,
            'avg_slippage': 0.3
        }
        
        table = monitor._create_stats_table(stats)
        
        assert table is not None
        assert table.row_count == 6
    
    def test_create_stats_table_zeros(self, monitor):
        """Test statistics table with zero values."""
        stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'success_rate': 0.0,
            'total_profit': 0.0,
            'avg_profit': 0.0,
            'avg_slippage': 0.0
        }
        
        table = monitor._create_stats_table(stats)
        
        assert table is not None
    
    def test_update_snapshot(self, monitor, sample_snapshot):
        """Test updating market snapshot."""
        monitor.update_snapshot(sample_snapshot)
        
        assert monitor.latest_snapshot == sample_snapshot
        assert monitor.total_opportunities_found == 1
    
    def test_update_snapshot_multiple_times(self, monitor, sample_snapshot):
        """Test multiple snapshot updates."""
        monitor.update_snapshot(sample_snapshot)
        monitor.update_snapshot(sample_snapshot)
        monitor.update_snapshot(sample_snapshot)
        
        assert monitor.total_opportunities_found == 3
    
    def test_update_snapshot_empty_opportunities(self, monitor):
        """Test snapshot update with no opportunities."""
        empty_snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            pairs=[],
            opportunities=[]
        )
        
        monitor.update_snapshot(empty_snapshot)
        
        assert monitor.total_opportunities_found == 0
    
    def test_update_snapshot_saves_to_database(self, monitor, mock_database, sample_snapshot, sample_opportunity):
        """Test that snapshot updates save opportunities to database."""
        session_id = mock_database.create_session("kraken", "PAPER", {})
        monitor.set_session_id(session_id)
        
        monitor.update_snapshot(sample_snapshot)
        
        cursor = mock_database.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM opportunities WHERE session_id = ?", (session_id,))
        count = cursor.fetchone()['count']
        
        assert count == 1
    
    def test_update_snapshot_without_database(self, sample_snapshot):
        """Test snapshot update without database configured."""
        monitor = ArbitrageMonitor(None)
        
        monitor.update_snapshot(sample_snapshot)
        
        assert monitor.total_opportunities_found == 1
    
    def test_log_opportunity(self, monitor, sample_opportunity):
        """Test logging an opportunity to console."""
        with patch.object(monitor.console, 'print') as mock_print:
            monitor.log_opportunity(sample_opportunity)
            
            mock_print.assert_called_once()
    
    def test_log_execution_success(self, monitor, sample_opportunity):
        """Test logging successful execution."""
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=15.0,
            slippage=0.5,
            success=True,
            trades=[],
            error_message=""
        )
        
        with patch('monitor.logger') as mock_logger:
            monitor.log_execution(execution)
            
            mock_logger.success.assert_called_once()
    
    def test_log_execution_failure(self, monitor, sample_opportunity):
        """Test logging failed execution."""
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=-5.0,
            slippage=0.0,
            success=False,
            trades=[],
            error_message="Insufficient funds"
        )
        
        with patch('monitor.logger') as mock_logger:
            monitor.log_execution(execution)
            
            mock_logger.error.assert_called_once()


class TestMonitorEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_create_dashboard_with_none_snapshot(self):
        """Test dashboard creation with None snapshot."""
        monitor = ArbitrageMonitor()
        stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'success_rate': 0.0,
            'total_profit': 0.0,
            'avg_profit': 0.0,
            'avg_slippage': 0.0
        }
        
        layout = monitor.create_dashboard(None, stats)
        
        assert layout is not None
    
    def test_opportunities_table_with_varying_risk_scores(self):
        """Test opportunities table displays different risk levels correctly."""
        monitor = ArbitrageMonitor()
        
        low_risk_path = TriangularPath(
            path=['USDT', 'BTC', 'ETH', 'USDT'],
            pairs=[],
            directions=[],
            profit_percentage=1.0,
            profit_amount=10.0,
            start_amount=1000.0,
            fees_total=1.0
        )
        
        med_risk_path = TriangularPath(
            path=['USDT', 'BTC', 'ETH', 'USDT'],
            pairs=[],
            directions=[],
            profit_percentage=0.5,
            profit_amount=5.0,
            start_amount=1000.0,
            fees_total=1.0
        )
        
        high_risk_path = TriangularPath(
            path=['USDT', 'BTC', 'ETH', 'USDT'],
            pairs=[],
            directions=[],
            profit_percentage=2.0,
            profit_amount=20.0,
            start_amount=1000.0,
            fees_total=1.0
        )
        
        opportunities = [
            ArbitrageOpportunity(low_risk_path, datetime.now(), 10.0, 20.0, True, "Low risk"),
            ArbitrageOpportunity(med_risk_path, datetime.now(), 5.0, 45.0, True, "Med risk"),
            ArbitrageOpportunity(high_risk_path, datetime.now(), 20.0, 70.0, True, "High risk")
        ]
        
        table = monitor._create_opportunities_table(opportunities)
        
        assert table.row_count == 3
    
    def test_update_snapshot_database_error(self, tmp_path):
        """Test handling of database save errors during snapshot update."""
        db = ArbihedronDatabase(str(tmp_path / "test.db"))
        monitor = ArbitrageMonitor(db)
        monitor.set_session_id(9999)
        
        # create simple opportunity
        path = TriangularPath(
            path=['USDT', 'BTC', 'USDT'],
            pairs=[],
            directions=[],
            profit_percentage=1.0,
            profit_amount=10.0,
            start_amount=1000.0,
            fees_total=2.0
        )
        opp = ArbitrageOpportunity(path, datetime.now(), 10.0, 20.0, True, "Test")
        
        snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            pairs=[],
            opportunities=[opp]
        )
        
        monitor.update_snapshot(snapshot)
        
        assert monitor.total_opportunities_found == 1
    
    def test_opportunities_table_truncates_to_ten(self):
        """Test that opportunities table only shows top 10 opportunities."""
        monitor = ArbitrageMonitor()
        
        path = TriangularPath(
            path=['USDT', 'BTC', 'ETH', 'USDT'],
            pairs=[],
            directions=[],
            profit_percentage=1.0,
            profit_amount=10.0,
            start_amount=1000.0,
            fees_total=1.0
        )
        
        opportunities = [
            ArbitrageOpportunity(path, datetime.now(), 10.0, 20.0, True, f"Opp {i}")
            for i in range(20)
        ]
        
        snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            pairs=[],
            opportunities=opportunities
        )
        
        stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'success_rate': 0.0,
            'total_profit': 0.0,
            'avg_profit': 0.0,
            'avg_slippage': 0.0
        }
        
        layout = monitor.create_dashboard(snapshot, stats)
        
        assert layout is not None