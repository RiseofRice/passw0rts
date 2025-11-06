"""
Unit tests for DaemonManager
"""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from passw0rts.utils.daemon_manager import DaemonManager


class TestDaemonManager:
    """Test DaemonManager class"""
    
    def test_initialization(self):
        """Test DaemonManager initialization"""
        daemon = DaemonManager()
        
        assert daemon.pid_file == Path.home() / ".passw0rts" / "daemon.pid"
        assert daemon.log_file == Path.home() / ".passw0rts" / "daemon.log"
        assert daemon.system in ['Linux', 'Darwin', 'Windows']
    
    def test_is_running_no_pid_file(self, tmp_path):
        """Test is_running returns False when no PID file exists"""
        daemon = DaemonManager()
        daemon.pid_file = tmp_path / "daemon.pid"
        
        assert not daemon.is_running()
    
    def test_is_running_invalid_pid(self, tmp_path):
        """Test is_running returns False with invalid PID"""
        daemon = DaemonManager()
        daemon.pid_file = tmp_path / "daemon.pid"
        
        # Write invalid PID
        daemon.pid_file.write_text("invalid")
        
        assert not daemon.is_running()
        assert not daemon.pid_file.exists()  # Should be cleaned up
    
    def test_is_running_nonexistent_process(self, tmp_path):
        """Test is_running returns False when process doesn't exist"""
        daemon = DaemonManager()
        daemon.pid_file = tmp_path / "daemon.pid"
        
        # Write PID that doesn't exist
        daemon.pid_file.write_text("999999")
        
        assert not daemon.is_running()
        assert not daemon.pid_file.exists()  # Should be cleaned up
    
    def test_get_pid_no_file(self, tmp_path):
        """Test get_pid returns None when no PID file exists"""
        daemon = DaemonManager()
        daemon.pid_file = tmp_path / "daemon.pid"
        
        assert daemon.get_pid() is None
    
    def test_get_pid_invalid(self, tmp_path):
        """Test get_pid returns None with invalid PID file"""
        daemon = DaemonManager()
        daemon.pid_file = tmp_path / "daemon.pid"
        
        daemon.pid_file.write_text("invalid")
        
        assert daemon.get_pid() is None
    
    def test_get_pid_valid(self, tmp_path):
        """Test get_pid returns valid PID"""
        daemon = DaemonManager()
        daemon.pid_file = tmp_path / "daemon.pid"
        
        daemon.pid_file.write_text("12345")
        
        assert daemon.get_pid() == 12345
    
    @patch('subprocess.Popen')
    def test_start_creates_pid_file(self, mock_popen, tmp_path):
        """Test start creates PID file"""
        daemon = DaemonManager()
        daemon.pid_file = tmp_path / "daemon.pid"
        daemon.log_file = tmp_path / "daemon.log"
        
        # Mock the Popen process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        with patch.object(daemon, 'is_running', return_value=False):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                pid = daemon.start()
                
                assert pid == 12345
    
    def test_start_already_running(self):
        """Test start raises error when daemon is already running"""
        daemon = DaemonManager()
        
        with patch.object(daemon, 'is_running', return_value=True):
            with pytest.raises(RuntimeError, match="already running"):
                daemon.start()
    
    @patch('os.kill')
    def test_stop_not_running(self, mock_kill):
        """Test stop raises error when daemon is not running"""
        daemon = DaemonManager()
        
        with patch.object(daemon, 'is_running', return_value=False):
            with pytest.raises(RuntimeError, match="not running"):
                daemon.stop()
    
    def test_get_logs_no_file(self, tmp_path):
        """Test get_logs with no log file"""
        daemon = DaemonManager()
        daemon.log_file = tmp_path / "daemon.log"
        
        logs = daemon.get_logs()
        
        assert "No log file found" in logs
    
    def test_get_logs_with_content(self, tmp_path):
        """Test get_logs returns log content"""
        daemon = DaemonManager()
        daemon.log_file = tmp_path / "daemon.log"
        
        # Create log file with content
        log_content = "\n".join([f"Line {i}" for i in range(100)])
        daemon.log_file.write_text(log_content)
        
        # Get last 10 lines
        logs = daemon.get_logs(lines=10)
        
        assert "Line 99" in logs
        assert "Line 90" in logs
        assert "Line 0" not in logs
    
    def test_service_install_unsupported_platform(self):
        """Test service install raises error on unsupported platform"""
        daemon = DaemonManager()
        daemon.system = 'UnsupportedOS'
        
        with pytest.raises(NotImplementedError):
            daemon.install_service()
    
    def test_service_uninstall_unsupported_platform(self):
        """Test service uninstall raises error on unsupported platform"""
        daemon = DaemonManager()
        daemon.system = 'UnsupportedOS'
        
        with pytest.raises(NotImplementedError):
            daemon.uninstall_service()


class TestDaemonManagerSystemSpecific:
    """Test platform-specific functionality"""
    
    @patch('subprocess.run')
    @patch('platform.system', return_value='Linux')
    def test_install_systemd_service(self, mock_system, mock_run, tmp_path):
        """Test systemd service installation"""
        daemon = DaemonManager()
        
        # Mock service file path
        with patch.object(Path, 'home', return_value=tmp_path):
            service_file = daemon._install_systemd_service(
                host='127.0.0.1',
                port=5000,
                storage_path=None,
                auto_start=False
            )
            
            assert 'passw0rts-web.service' in service_file
            # Verify systemd reload was called
            assert any('daemon-reload' in str(call) for call in mock_run.call_args_list)
    
    @patch('subprocess.run')
    @patch('platform.system', return_value='Linux')
    def test_uninstall_systemd_service(self, mock_system, mock_run, tmp_path):
        """Test systemd service uninstallation"""
        daemon = DaemonManager()
        
        with patch.object(Path, 'home', return_value=tmp_path):
            # Create a dummy service file
            service_dir = tmp_path / ".config" / "systemd" / "user"
            service_dir.mkdir(parents=True, exist_ok=True)
            service_file = service_dir / "passw0rts-web.service"
            service_file.write_text("[Unit]\nDescription=Test")
            
            daemon._uninstall_systemd_service()
            
            # Verify service was stopped and disabled
            assert any('stop' in str(call) for call in mock_run.call_args_list)
            assert any('disable' in str(call) for call in mock_run.call_args_list)
    
    @patch('subprocess.run')
    @patch('platform.system', return_value='Darwin')
    def test_install_launchd_service(self, mock_system, mock_run, tmp_path):
        """Test launchd service installation"""
        daemon = DaemonManager()
        
        with patch.object(Path, 'home', return_value=tmp_path):
            plist_file = daemon._install_launchd_service(
                host='127.0.0.1',
                port=5000,
                storage_path=None,
                auto_start=False
            )
            
            assert '.plist' in plist_file
            assert Path(plist_file).exists()
    
    @patch('subprocess.run')
    @patch('platform.system', return_value='Darwin')
    def test_uninstall_launchd_service(self, mock_system, mock_run, tmp_path):
        """Test launchd service uninstallation"""
        daemon = DaemonManager()
        
        with patch.object(Path, 'home', return_value=tmp_path):
            # Create a dummy plist file
            plist_dir = tmp_path / "Library" / "LaunchAgents"
            plist_dir.mkdir(parents=True, exist_ok=True)
            plist_file = plist_dir / "com.passw0rts.web.plist"
            plist_file.write_text("<?xml version='1.0'?>")
            
            daemon._uninstall_launchd_service()
            
            # Verify unload was called
            assert any('unload' in str(call) for call in mock_run.call_args_list)
    
    @patch('subprocess.run')
    @patch('platform.system', return_value='Windows')
    def test_install_windows_service(self, mock_system, mock_run):
        """Test Windows service installation"""
        daemon = DaemonManager()
        
        task_name = daemon._install_windows_service(
            host='127.0.0.1',
            port=5000,
            storage_path=None,
            auto_start=False
        )
        
        assert task_name == 'Passw0rtsWeb'
        # Verify schtasks was called
        assert any('schtasks' in str(call) for call in mock_run.call_args_list)
    
    @patch('subprocess.run')
    @patch('platform.system', return_value='Windows')
    def test_uninstall_windows_service(self, mock_system, mock_run):
        """Test Windows service uninstallation"""
        daemon = DaemonManager()
        
        daemon._uninstall_windows_service()
        
        # Verify schtasks delete was called
        assert any('delete' in str(call) for call in mock_run.call_args_list)
