#!/usr/bin/env python3
"""Test the database persistence layer."""
from datetime import datetime
from database import ArbihedronDatabase
from models import ArbitrageOpportunity, TradeExecution, TriangularPath, TradingPair, TradeDirection
def test_basic_operations():
    """Test basic database operations."""
    print("Testing arbihedron database...")
    
    # initialise database
    db = ArbihedronDatabase()
    
    # creates a test session
    config = {
        'min_profit_threshold': 0.5,
        'max_position_size': 1000,
        'slippage_tolerance': 0.1
    }
    session_id = db.create_session(
        exchange="kraken",
        mode="PAPER TRADING",
        config=config
    )
    print(f"session created: {session_id}")
    
    # creates a mock opportunity
    path = TriangularPath(
        path=["BTC", "ETH", "USDT", "BTC"],
        pairs=[
            TradingPair("BTC/ETH", "BTC", "ETH", 0.05, 0.051, 100.0, 100.0, datetime.now()),
            TradingPair("ETH/USDT", "ETH", "USDT", 2000, 2001, 50.0, 50.0, datetime.now()),
            TradingPair("USDT/BTC", "USDT", "BTC", 0.00003, 0.000031, 10000.0, 10000.0, datetime.now())
        ],
        directions=[TradeDirection.BUY, TradeDirection.BUY, TradeDirection.BUY],
        profit_percentage=0.5,
        profit_amount=50.0,
        start_amount=1000.0,
        fees_total=1.5
    )
    
    opportunity = ArbitrageOpportunity(
        path=path,
        timestamp=datetime.now(),
        expected_profit=50.0,
        risk_score=25.0,
        executable=True,
        reason="Test opportunity"
    )
    
    opp_id = db.save_opportunity(session_id, opportunity)
    print(f"opportunity saved: {opp_id}")
    
    # creates mock execution
    execution = TradeExecution(
        opportunity=opportunity,
        executed_at=datetime.now(),
        actual_profit=48.5,
        slippage=0.03,
        success=True,
        trades=[
            {
                'step': 1,
                'symbol': 'BTC/ETH',
                'direction': 'buy',
                'amount': 1.0,
                'price': 0.051
            }
        ],
        error_message=None
    )
    
    exec_id = db.save_execution(session_id, execution, opp_id)
    print(f"execution saved: {exec_id}")
    
    # saves the metrics
    db.save_system_metrics(session_id, 125.5, 5)
    print("system metrics saved")
    
    # gets the session stats
    stats = db.get_session_stats(session_id)
    print(f"\nsession stats retrieved:")
    print(f"  - Opportunities: {stats['total_opportunities']}")
    print(f"  - Trades: {stats['total_trades']}")
    print(f"  - Success Rate: {stats['success_rate']:.2f}%")
    print(f"  - Total Profit: ${stats['total_profit']:.2f}")
    
    # ends our session
    db.end_session(session_id)
    print("\nsession ended")
    
    # exports data
    export_path = db.export_to_csv("exports/test")
    print(f"data exported to: {export_path}")
    
    report_path = db.export_session_report(session_id, "exports/test/session_report.json")
    print(f"session report exported to: {report_path}")
    
    # closes database
    db.close()
    print("\nall tests passed!")

if __name__ == "__main__":
    test_basic_operations()