"""Tests for the analytics module."""
import pytest
from datetime import datetime, timedelta
from database import ArbihedronDatabase
from analytics import ArbihedronAnalytics
from models import (
    ArbitrageOpportunity, TradeExecution, TriangularPath,
    TradingPair, TradeDirection
)

class TestArbihedronAnalytics:
    """Test suite for analytics functionality."""
    
    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary test database."""
        db_path = tmp_path / "test.db"
        db = ArbihedronDatabase(str(db_path))
        return db
    
    @pytest.fixture
    def analytics(self, db):
        """Create analytics instance with test database."""
        return ArbihedronAnalytics(db)
    
    @pytest.fixture
    def sample_session(self, db):
        """Create sample session data."""
        config = {
            'min_profit_threshold': 0.5,
            'max_position_size': 1000
        }
        session_id = db.create_session(
            exchange="kraken",
            mode="PAPER",
            config=config
        )
        return session_id
    
    @pytest.fixture
    def sample_opportunity(self):
        """Create sample opportunity."""
        path = TriangularPath(
            path=["BTC", "ETH", "USDT", "BTC"],
            pairs=[
                TradingPair("BTC/ETH", "BTC", "ETH", 0.05, 0.051, 100, 100, datetime.now()),
                TradingPair("ETH/USDT", "ETH", "USDT", 2000, 2001, 50, 50, datetime.now()),
                TradingPair("USDT/BTC", "USDT", "BTC", 0.00003, 0.000031, 10000, 10000, datetime.now())
            ],
            directions=[TradeDirection.BUY, TradeDirection.BUY, TradeDirection.BUY],
            profit_percentage=0.5,
            profit_amount=50.0,
            start_amount=1000.0,
            fees_total=1.5
        )
        
        return ArbitrageOpportunity(
            path=path,
            timestamp=datetime.now(),
            expected_profit=50.0,
            risk_score=25.0,
            executable=True,
            reason="Test opportunity"
        )
    
    def test_get_overall_stats_empty_db(self, analytics):
        """Test overall stats with empty database."""
        stats = analytics.get_overall_stats()
        
        assert stats['total_sessions'] == 0
        assert stats['total_opportunities'] == 0
        assert stats['total_trades'] == 0
        assert stats['total_profit'] == 0.0
        assert stats['success_rate'] == 0.0
    
    def test_get_overall_stats_with_data(self, analytics, db, sample_session, sample_opportunity):
        """Test overall stats with session and execution data."""
        db.save_opportunity(sample_session, sample_opportunity)
        
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=45.0,
            slippage=10.0,
            success=True,
            trades=[],
            error_message=""
        )
        db.save_execution(sample_session, execution)
        
        stats = analytics.get_overall_stats()
        
        assert stats['total_sessions'] == 1
        assert stats['total_executions'] == 1
        assert stats['successful_executions'] == 1
        assert stats['success_rate'] == 100.0
        assert stats['total_profit'] > 0
    
    def test_get_daily_stats_empty(self, analytics):
        """Test daily stats with no data."""
        daily_stats = analytics.get_daily_stats()
        assert daily_stats == []
    
    def test_get_daily_stats_with_data(self, analytics, db, sample_session, sample_opportunity):
        """Test daily stats with execution data."""
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=45.0,
            slippage=10.0,
            success=True,
            trades=[],
            error_message=""
        )
        db.save_execution(sample_session, execution)
        
        daily_stats = analytics.get_daily_stats()
        
        assert len(daily_stats) == 1
        assert daily_stats[0]['trades'] == 1
        assert daily_stats[0]['successful'] == 1
    
    def test_get_hourly_distribution(self, analytics, db, sample_session, sample_opportunity):
        """Test hourly distribution of trades."""
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=45.0,
            slippage=10.0,
            success=True,
            trades=[],
            error_message=""
        )
        db.save_execution(sample_session, execution)
        
        hourly = analytics.get_hourly_distribution()
        
        assert len(hourly) > 0
        current_hour = datetime.now().hour
        assert any(h['hour'] == current_hour for h in hourly)
    
    def test_get_path_analysis(self, analytics, db, sample_session, sample_opportunity):
        """Test path analysis."""
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=45.0,
            slippage=10.0,
            success=True,
            trades=[],
            error_message=""
        )
        db.save_execution(sample_session, execution)
        
        path_analysis = analytics.get_path_analysis()
        
        assert isinstance(path_analysis, list)
    
    def test_get_top_opportunities(self, analytics, db, sample_session, sample_opportunity):
        """Test top opportunities retrieval."""
        db.save_opportunity(sample_session, sample_opportunity)
        
        top_opps = analytics.get_top_opportunities(limit=5)
        
        assert isinstance(top_opps, list)
    
    def test_get_performance_metrics(self, analytics, db, sample_session, sample_opportunity):
        """Test performance metrics generation."""
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=45.0,
            slippage=10.0,
            success=True,
            trades=[],
            error_message=""
        )
        db.save_execution(sample_session, execution)
        
        metrics = analytics.get_performance_metrics()
        
        assert isinstance(metrics, dict)
    
    def test_export_analytics_json(self, analytics, db, sample_session, tmp_path):
        """Test JSON export functionality."""
        output_path = str(tmp_path / "test_analytics.json")
        
        result = analytics.export_analytics_json(output_path)
        
        assert result is not None
    
    def test_get_profit_trends(self, analytics, db, sample_session, sample_opportunity):
        """Test profit trends generation."""
        execution = TradeExecution(
            opportunity=sample_opportunity,
            executed_at=datetime.now(),
            actual_profit=45.0,
            slippage=10.0,
            success=True,
            trades=[],
            error_message=""
        )
        db.save_execution(sample_session, execution)
        
        trends = analytics.get_profit_trends(days=7)
        
        assert isinstance(trends, list)


class TestAnalyticsEdgeCases:
    """Test edge cases and error handling."""
    
    def test_analytics_with_none_database(self):
        """Test analytics initialisation with None database."""
        analytics = ArbihedronAnalytics(None)
        assert analytics.db is not None
    
    def test_stats_with_failed_executions(self, tmp_path):
        """Test stats calculation with failed executions."""
        db = ArbihedronDatabase(str(tmp_path / "test.db"))
        analytics = ArbihedronAnalytics(db)
        
        session_id = db.create_session("kraken", "PAPER", {})
        
        path = TriangularPath(
            path=["BTC", "ETH", "USDT", "BTC"],
            pairs=[],
            directions=[],
            profit_percentage=0.5,
            profit_amount=50.0,
            start_amount=1000.0,
            fees_total=1.5
        )
        
        opp = ArbitrageOpportunity(
            path=path,
            timestamp=datetime.now(),
            expected_profit=50.0,
            risk_score=25.0,
            executable=True,
            reason="Test"
        )
        
        failed_exec = TradeExecution(
            opportunity=opp,
            executed_at=datetime.now(),
            actual_profit=-10.0,
            slippage=0.0,
            success=False,
            trades=[],
            error_message="API error"
        )
        db.save_execution(session_id, failed_exec)
        
        stats = analytics.get_overall_stats()
        
        assert stats['total_executions'] == 1
        assert stats['successful_executions'] == 0
        assert stats['success_rate'] == 0.0
    
    def test_nonexistent_session_data(self, tmp_path):
        """Test handling of nonexistent session."""
        db = ArbihedronDatabase(str(tmp_path / "test.db"))
        analytics = ArbihedronAnalytics(db)
        
        top_opps = analytics.get_top_opportunities()
        
        assert isinstance(top_opps, list)