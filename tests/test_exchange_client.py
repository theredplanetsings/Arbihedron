"""Tests for the exchange client module."""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from exchange_client import ExchangeClient
from config import ExchangeConfig
from models import TradingPair, TradeDirection

class TestExchangeClient:
    """Test suite for exchange client functionality."""
    
    @pytest.fixture
    def exchange_config(self):
        """Create test exchange configuration."""
        return ExchangeConfig(
            name="kraken",
            api_key="test_key",
            api_secret="test_secret",
            testnet=True
        )
    
    @pytest.fixture
    def mock_ccxt_exchange(self):
        """Create mock CCXT exchange."""
        mock = MagicMock()
        mock.load_markets = Mock(return_value={
            'BTC/USDT': {'id': 'BTCUSDT', 'symbol': 'BTC/USDT', 'taker': 0.001},
            'ETH/USDT': {'id': 'ETHUSDT', 'symbol': 'ETH/USDT', 'taker': 0.001},
            'ETH/BTC': {'id': 'ETHBTC', 'symbol': 'ETH/BTC', 'taker': 0.001}
        })
        mock.fetch_ticker = Mock(return_value={
            'bid': 50000.0,
            'ask': 50100.0,
            'bidVolume': 10.0,
            'askVolume': 8.0
        })
        mock.fetch_balance = Mock(return_value={
            'BTC': {'free': 1.5, 'used': 0.0, 'total': 1.5}
        })
        mock.create_buy_order = Mock(return_value={
            'id': 'test_buy_123',
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'amount': 0.1,
            'price': 50000.0,
            'status': 'closed',
            'filled': 0.1,
            'average': 50000.0
        })
        mock.create_sell_order = Mock(return_value={
            'id': 'test_sell_123',
            'symbol': 'BTC/USDT',
            'side': 'sell',
            'amount': 0.1,
            'price': 50000.0,
            'status': 'closed',
            'filled': 0.1,
            'average': 50000.0
        })
        mock.set_sandbox_mode = Mock()
        return mock
    
    def test_initialization(self, exchange_config):
        """Test exchange client initialisation."""
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_exchange_class.return_value = MagicMock()
            
            client = ExchangeClient(exchange_config)
            
            assert client.config == exchange_config
            assert client.exchange is not None
            assert isinstance(client.markets, dict)
    
    def test_initialization_testnet_mode(self, exchange_config):
        """Test initialisation with testnet mode enabled."""
        exchange_config.testnet = True
        
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_instance = MagicMock()
            mock_instance.set_sandbox_mode = Mock()
            mock_exchange_class.return_value = mock_instance
            
            client = ExchangeClient(exchange_config)
            
            mock_instance.set_sandbox_mode.assert_called_once_with(True)
    
    def test_initialization_live_mode(self, exchange_config):
        """Test initialisation with live mode."""
        exchange_config.testnet = False
        
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_instance = MagicMock()
            mock_exchange_class.return_value = mock_instance
            
            client = ExchangeClient(exchange_config)
            
            assert client.exchange is not None
    
    @pytest.mark.asyncio
    async def test_load_markets(self, exchange_config, mock_ccxt_exchange):
        """Test loading markets from exchange."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            client = ExchangeClient(exchange_config)
            markets = await client.load_markets()
            
            assert len(markets) == 3
            assert 'BTC/USDT' in markets
            assert 'ETH/USDT' in markets
    
    @pytest.mark.asyncio
    async def test_load_markets_failure(self, exchange_config):
        """Test handling of market loading failure."""
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_instance = MagicMock()
            mock_instance.load_markets = Mock(side_effect=Exception("API error"))
            mock_exchange_class.return_value = mock_instance
            
            client = ExchangeClient(exchange_config)
            markets = await client.load_markets()
            
            assert markets == {}
    
    @pytest.mark.asyncio
    async def test_fetch_ticker_success(self, exchange_config, mock_ccxt_exchange):
        """Test successful ticker fetch."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            client = ExchangeClient(exchange_config)
            
            ticker = await client.fetch_ticker('BTC/USDT')
            
            assert ticker is not None
            assert ticker.symbol == 'BTC/USDT'
            assert ticker.base == 'BTC'
            assert ticker.quote == 'USDT'
            assert ticker.bid == 50000.0
            assert ticker.ask == 50100.0
    
    @pytest.mark.asyncio
    async def test_fetch_ticker_missing_data(self, exchange_config):
        """Test ticker fetch with missing bid/ask data."""
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_instance = MagicMock()
            mock_instance.fetch_ticker = Mock(return_value={'symbol': 'BTC/USDT'})
            mock_exchange_class.return_value = mock_instance
            
            client = ExchangeClient(exchange_config)
            ticker = await client.fetch_ticker('BTC/USDT')
            
            assert ticker is None
    
    @pytest.mark.asyncio
    async def test_fetch_ticker_failure(self, exchange_config):
        """Test ticker fetch failure handling."""
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_instance = MagicMock()
            mock_instance.fetch_ticker = Mock(side_effect=Exception("Network error"))
            mock_exchange_class.return_value = mock_instance
            
            client = ExchangeClient(exchange_config)
            ticker = await client.fetch_ticker('BTC/USDT')
            
            assert ticker is None
    
    @pytest.mark.asyncio
    async def test_fetch_tickers_batch(self, exchange_config, mock_ccxt_exchange):
        """Test batch ticker fetching."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            client = ExchangeClient(exchange_config)
            
            symbols = ['BTC/USDT', 'ETH/USDT', 'ETH/BTC']
            tickers = await client.fetch_tickers_batch(symbols)
            
            assert len(tickers) == 3
            assert all(isinstance(t, TradingPair) for t in tickers)
    
    @pytest.mark.asyncio
    async def test_get_balance_success(self, exchange_config, mock_ccxt_exchange):
        """Test successful balance retrieval."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            client = ExchangeClient(exchange_config)
            
            balance = await client.get_balance('BTC')
            
            assert balance == 1.5
    
    @pytest.mark.asyncio
    async def test_get_balance_missing_currency(self, exchange_config, mock_ccxt_exchange):
        """Test balance retrieval for non-existent currency."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            client = ExchangeClient(exchange_config)
            
            balance = await client.get_balance('XYZ')
            
            assert balance == 0.0
    
    @pytest.mark.asyncio
    async def test_get_balance_failure(self, exchange_config):
        """Test balance retrieval failure handling."""
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_instance = MagicMock()
            mock_instance.fetch_balance = Mock(side_effect=Exception("Auth error"))
            mock_exchange_class.return_value = mock_instance
            
            client = ExchangeClient(exchange_config)
            balance = await client.get_balance('BTC')
            
            assert balance == 0.0
    
    @pytest.mark.asyncio
    async def test_execute_order_paper_trading(self, exchange_config, mock_ccxt_exchange):
        """Test order execution in paper trading mode."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            with patch('exchange_client.config.risk.enable_paper_trading', True):
                client = ExchangeClient(exchange_config)
                
                order = await client.execute_order(
                    'BTC/USDT',
                    TradeDirection.BUY,
                    0.1,
                    50000.0
                )
                
                assert order['id'] == 'paper_trade'
                assert order['status'] == 'closed'
    
    @pytest.mark.asyncio
    async def test_execute_buy_order_live(self, exchange_config, mock_ccxt_exchange):
        """Test live buy order execution."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            with patch('exchange_client.config.risk.enable_paper_trading', False):
                client = ExchangeClient(exchange_config)
                
                order = await client.execute_order(
                    'BTC/USDT',
                    TradeDirection.BUY,
                    0.1,
                    50000.0
                )
                
                assert order['id'] == 'test_buy_123'
                assert order['side'] == 'buy'
    
    @pytest.mark.asyncio
    async def test_execute_sell_order_live(self, exchange_config, mock_ccxt_exchange):
        """Test live sell order execution."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            with patch('exchange_client.config.risk.enable_paper_trading', False):
                client = ExchangeClient(exchange_config)
                
                order = await client.execute_order(
                    'BTC/USDT',
                    TradeDirection.SELL,
                    0.1,
                    50000.0
                )
                
                assert order['id'] == 'test_sell_123'
                assert order['side'] == 'sell'
    
    @pytest.mark.asyncio
    async def test_execute_order_failure(self, exchange_config):
        """Test order execution failure handling."""
        with patch('exchange_client.ccxt.kraken') as mock_exchange_class:
            mock_instance = MagicMock()
            mock_instance.create_buy_order = Mock(side_effect=Exception("Insufficient funds"))
            mock_exchange_class.return_value = mock_instance
            
            with patch('exchange_client.config.risk.enable_paper_trading', False):
                client = ExchangeClient(exchange_config)
                
                with pytest.raises(Exception):
                    await client.execute_order(
                        'BTC/USDT',
                        TradeDirection.BUY,
                        0.1,
                        50000.0
                    )
    
    def test_get_trading_fee_with_market_data(self, exchange_config, mock_ccxt_exchange):
        """Test getting trading fee from market data."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            client = ExchangeClient(exchange_config)
            client.markets = {'BTC/USDT': {'taker': 0.002}}
            
            fee = client.get_trading_fee('BTC/USDT')
            
            assert fee == 0.002
    
    def test_get_trading_fee_default(self, exchange_config, mock_ccxt_exchange):
        """Test getting default trading fee when market data unavailable."""
        with patch('exchange_client.ccxt.kraken', return_value=mock_ccxt_exchange):
            client = ExchangeClient(exchange_config)
            
            fee = client.get_trading_fee('UNKNOWN/PAIR')
            
            assert fee == 0.001