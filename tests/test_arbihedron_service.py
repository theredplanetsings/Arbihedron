"""Tests for the arbihedron service wrapper."""
import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from arbihedron_service import ArbihedronService
from alerts import AlertManager, AlertConfig
from health_monitor import HealthMonitor
from config import HealthConfig

class TestArbihedronService:
    """Test suite for service wrapper functionality."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        with patch('arbihedron_service.AlertManager'):
            with patch('arbihedron_service.HealthMonitor'):
                with patch('arbihedron_service.ArbihedronBot'):
                    return ArbihedronService()
    
    def test_initialization(self, service):
        """Test service initialisation."""
        assert service.bot is None
        assert service.alert_manager is None
        assert service.health_monitor is None
        assert service.running is True
        assert service.restart_count == 0
        assert service.max_restarts == 10
        assert len(service.restart_times) == 0
    
    def test_handle_shutdown(self, service):
        """Test shutdown signal handling."""
        service._handle_shutdown(15, None)
        
        assert service.running is False
    
    def test_should_restart_within_limit(self, service):
        """Test restart check when within limits."""
        service.restart_times = []
        
        result = service._should_restart()
        
        assert result is True
    
    def test_should_restart_at_limit(self, service):
        """Test restart check when at limit."""
        current_time = time.time()
        service.restart_times = [current_time - 100 for _ in range(10)]
        
        result = service._should_restart()
        
        assert result is False
    
    def test_should_restart_cleans_old_times(self, service):
        """Test that old restart times are cleaned up."""
        current_time = time.time()
        service.restart_times = [
            current_time - 5000,
            current_time - 100,
            current_time - 50
        ]
        
        service._should_restart()
        
        assert len(service.restart_times) == 2
    
    def test_record_restart(self, service):
        """Test recording a restart attempt."""
        initial_count = service.restart_count
        initial_times_len = len(service.restart_times)
        
        service._record_restart()
        
        assert service.restart_count == initial_count + 1
        assert len(service.restart_times) == initial_times_len + 1
    
    @pytest.mark.asyncio
    async def test_run_bot_with_monitoring_no_alerts(self):
        """Test running bot without alerts configured."""
        with patch('arbihedron_service.ALERT_CONFIG') as mock_alert_config:
            mock_alert_config.email_enabled = False
            mock_alert_config.slack_enabled = False
            
            with patch('arbihedron_service.HEALTH_CONFIG') as mock_health_config:
                mock_health_config.enabled = False
                
                with patch('arbihedron_service.ArbihedronBot') as mock_bot_class:
                    mock_bot = MagicMock()
                    mock_bot.initialize = AsyncMock()
                    mock_bot.run = AsyncMock()
                    mock_bot_class.return_value = mock_bot
                    
                    service = ArbihedronService()
                    service.running = False
                    
                    await service._run_bot_with_monitoring()
                    
                    assert service.alert_manager is None
                    assert service.health_monitor is None
    
    @pytest.mark.asyncio
    async def test_run_bot_with_alerts_enabled(self):
        """Test running bot with alerts enabled."""
        with patch('arbihedron_service.ALERT_CONFIG') as mock_alert_config:
            mock_alert_config.email_enabled = True
            mock_alert_config.slack_enabled = False
            
            with patch('arbihedron_service.HEALTH_CONFIG') as mock_health_config:
                mock_health_config.enabled = False
                
                with patch('arbihedron_service.AlertManager') as mock_alert_class:
                    mock_alert = MagicMock()
                    mock_alert.initialize = AsyncMock()
                    mock_alert.alert_startup = AsyncMock()
                    mock_alert_class.return_value = mock_alert
                    
                    with patch('arbihedron_service.ArbihedronBot') as mock_bot_class:
                        mock_bot = MagicMock()
                        mock_bot.initialize = AsyncMock()
                        mock_bot.run = AsyncMock()
                        mock_bot_class.return_value = mock_bot
                        
                        service = ArbihedronService()
                        service.running = False
                        
                        await service._run_bot_with_monitoring()
                        
                        assert service.alert_manager is not None
    
    @pytest.mark.asyncio
    async def test_run_bot_with_health_monitoring_enabled(self):
        """Test running bot with health monitoring enabled."""
        with patch('arbihedron_service.ALERT_CONFIG') as mock_alert_config:
            mock_alert_config.email_enabled = False
            mock_alert_config.slack_enabled = False
            
            with patch('arbihedron_service.HEALTH_CONFIG') as mock_health_config:
                mock_health_config.enabled = True
                mock_health_config.port = 8080
                
                with patch('arbihedron_service.HealthMonitor') as mock_health_class:
                    mock_health = MagicMock()
                    mock_health.initialize = AsyncMock()
                    mock_health_class.return_value = mock_health
                    
                    with patch('arbihedron_service.ArbihedronBot') as mock_bot_class:
                        mock_bot = MagicMock()
                        mock_bot.initialize = AsyncMock()
                        mock_bot.run = AsyncMock()
                        mock_bot_class.return_value = mock_bot
                        
                        service = ArbihedronService()
                        service.running = False
                        
                        await service._run_bot_with_monitoring()
                        
                        assert service.health_monitor is not None
    
    @pytest.mark.asyncio
    async def test_run_bot_handles_exceptions(self):
        """Test that bot exceptions are handled gracefully."""
        with patch('arbihedron_service.ALERT_CONFIG') as mock_alert_config:
            mock_alert_config.email_enabled = False
            mock_alert_config.slack_enabled = False
            
            with patch('arbihedron_service.HEALTH_CONFIG') as mock_health_config:
                mock_health_config.enabled = False
                
                with patch('arbihedron_service.ArbihedronBot') as mock_bot_class:
                    mock_bot = MagicMock()
                    mock_bot.initialize = AsyncMock(side_effect=Exception("Init error"))
                    mock_bot_class.return_value = mock_bot
                    
                    service = ArbihedronService()
                    
                    with pytest.raises(Exception):
                        await service._run_bot_with_monitoring()


class TestServiceRestartLogic:
    """Test service restart functionality."""
    
    def test_restart_times_window(self):
        """Test that restart window is correctly enforced."""
        service = ArbihedronService()
        current_time = time.time()
        
        service.restart_times = [
            current_time - 3700,
            current_time - 3600,
            current_time - 100
        ]
        
        result = service._should_restart()
        
        assert result is True
        assert len(service.restart_times) < 3
    
    def test_multiple_restarts_within_window(self):
        """Test handling of multiple restarts within time window."""
        service = ArbihedronService()
        
        for i in range(5):
            service._record_restart()
        
        assert service.restart_count == 5
        assert len(service.restart_times) == 5
        assert service._should_restart() is True
    
    def test_max_restarts_prevents_further_restarts(self):
        """Test that max restarts limit is enforced."""
        service = ArbihedronService()
        current_time = time.time()
        
        service.restart_times = [current_time - 100 for _ in range(10)]
        
        result = service._should_restart()
        
        assert result is False


class TestServiceEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_service_initialization_creates_log_directory(self):
        """Test that service creates log directory on init."""
        from pathlib import Path
        
        with patch('arbihedron_service.AlertManager'):
            with patch('arbihedron_service.HealthMonitor'):
                with patch('arbihedron_service.ArbihedronBot'):
                    service = ArbihedronService()
                    
                    log_path = Path("logs/service")
                    assert log_path.exists()
    
    def test_signal_handler_registered(self):
        """Test that signal handlers are properly registered."""
        import signal
        
        with patch('arbihedron_service.AlertManager'):
            with patch('arbihedron_service.HealthMonitor'):
                with patch('arbihedron_service.ArbihedronBot'):
                    with patch('signal.signal') as mock_signal:
                        service = ArbihedronService()
                        
                        calls = mock_signal.call_args_list
                        signal_numbers = [call[0][0] for call in calls]
                        
                        assert signal.SIGTERM in signal_numbers
                        assert signal.SIGINT in signal_numbers
    
    @pytest.mark.asyncio
    async def test_bot_cleanup_on_error(self):
        """Test that resources are cleaned up on error."""
        with patch('arbihedron_service.ALERT_CONFIG') as mock_alert_config:
            mock_alert_config.email_enabled = True
            mock_alert_config.slack_enabled = False
            
            with patch('arbihedron_service.HEALTH_CONFIG') as mock_health_config:
                mock_health_config.enabled = True
                mock_health_config.port = 8080
                
                with patch('arbihedron_service.AlertManager') as mock_alert_class:
                    mock_alert = MagicMock()
                    mock_alert.initialize = AsyncMock()
                    mock_alert.cleanup = AsyncMock()
                    mock_alert.alert_startup = AsyncMock()
                    mock_alert_class.return_value = mock_alert
                    
                    with patch('arbihedron_service.HealthMonitor') as mock_health_class:
                        mock_health = MagicMock()
                        mock_health.initialize = AsyncMock()
                        mock_health.cleanup = AsyncMock()
                        mock_health_class.return_value = mock_health
                        
                        with patch('arbihedron_service.ArbihedronBot') as mock_bot_class:
                            mock_bot = MagicMock()
                            mock_bot.initialize = AsyncMock()
                            mock_bot.run = AsyncMock(side_effect=Exception("Bot error"))
                            mock_bot_class.return_value = mock_bot
                            
                            service = ArbihedronService()
                            
                            with pytest.raises(Exception):
                                await service._run_bot_with_monitoring()


class TestServiceIntegration:
    """Integration tests for service functionality."""
    
    @pytest.mark.asyncio
    async def test_full_service_lifecycle(self):
        """Test complete service start-run-stop lifecycle."""
        with patch('arbihedron_service.ALERT_CONFIG') as mock_alert_config:
            mock_alert_config.email_enabled = False
            mock_alert_config.slack_enabled = False
            
            with patch('arbihedron_service.HEALTH_CONFIG') as mock_health_config:
                mock_health_config.enabled = False
                
                with patch('arbihedron_service.ArbihedronBot') as mock_bot_class:
                    mock_bot = MagicMock()
                    mock_bot.initialize = AsyncMock()
                    
                    async def mock_run():
                        await asyncio.sleep(0.001)
                    
                    mock_bot.run = mock_run
                    mock_bot_class.return_value = mock_bot
                    
                    service = ArbihedronService()
                    service.running = False
                    
                    await service._run_bot_with_monitoring()
                    
                    assert service.bot is not None
    
    def test_restart_counter_increments_correctly(self):
        """Test that restart counter increments properly."""
        service = ArbihedronService()
        
        initial_count = service.restart_count
        
        for i in range(3):
            service._record_restart()
        
        assert service.restart_count == initial_count + 3
    
    def test_restart_limit_message(self, capsys):
        """Test that restart limit message is logged."""
        service = ArbihedronService()
        current_time = time.time()
        
        service.restart_times = [current_time - 50 for _ in range(10)]
        
        result = service._should_restart()
        
        assert result is False