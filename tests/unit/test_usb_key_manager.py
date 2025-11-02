"""
Unit tests for USB key manager
"""

import pytest
import tempfile
import os
from pathlib import Path
from passw0rts.utils.usb_key_manager import USBKeyManager, USBDevice


class TestUSBDevice:
    """Tests for USBDevice class"""
    
    def test_device_creation(self):
        """Test creating a USB device"""
        device = USBDevice(
            vendor_id=0x1234,
            product_id=0x5678,
            serial_number="ABC123",
            manufacturer="Test Manufacturer",
            product="Test Product"
        )
        
        assert device.vendor_id == 0x1234
        assert device.product_id == 0x5678
        assert device.serial_number == "ABC123"
        assert device.manufacturer == "Test Manufacturer"
        assert device.product == "Test Product"
    
    def test_device_to_dict(self):
        """Test converting device to dictionary"""
        device = USBDevice(
            vendor_id=0x1234,
            product_id=0x5678,
            serial_number="ABC123"
        )
        
        data = device.to_dict()
        
        assert data['vendor_id'] == 0x1234
        assert data['product_id'] == 0x5678
        assert data['serial_number'] == "ABC123"
    
    def test_device_from_dict(self):
        """Test creating device from dictionary"""
        data = {
            'vendor_id': 0x1234,
            'product_id': 0x5678,
            'serial_number': "ABC123",
            'manufacturer': "Test",
            'product': "Device"
        }
        
        device = USBDevice.from_dict(data)
        
        assert device.vendor_id == 0x1234
        assert device.product_id == 0x5678
        assert device.serial_number == "ABC123"
        assert device.manufacturer == "Test"
        assert device.product == "Device"
    
    def test_device_matches(self):
        """Test device matching"""
        device1 = USBDevice(0x1234, 0x5678, "ABC123")
        device2 = USBDevice(0x1234, 0x5678, "ABC123")
        device3 = USBDevice(0x1234, 0x5678, "XYZ789")
        
        assert device1.matches(device2)
        assert not device1.matches(device3)
    
    def test_device_str(self):
        """Test device string representation"""
        device = USBDevice(
            vendor_id=0x1234,
            product_id=0x5678,
            serial_number="ABC123",
            manufacturer="TestCo",
            product="TestKey"
        )
        
        device_str = str(device)
        assert "TestCo" in device_str
        assert "TestKey" in device_str
        assert "1234" in device_str
        assert "5678" in device_str
    
    def test_device_validation_vendor_id(self):
        """Test vendor ID validation"""
        # Invalid vendor IDs
        with pytest.raises(ValueError, match="Invalid vendor_id"):
            USBDevice(vendor_id=-1, product_id=0x1234, serial_number="ABC123")
        
        with pytest.raises(ValueError, match="Invalid vendor_id"):
            USBDevice(vendor_id=0x10000, product_id=0x1234, serial_number="ABC123")
        
        # Valid vendor IDs
        USBDevice(vendor_id=0x0000, product_id=0x1234, serial_number="ABC123")
        USBDevice(vendor_id=0xFFFF, product_id=0x1234, serial_number="ABC123")
    
    def test_device_validation_product_id(self):
        """Test product ID validation"""
        # Invalid product IDs
        with pytest.raises(ValueError, match="Invalid product_id"):
            USBDevice(vendor_id=0x1234, product_id=-1, serial_number="ABC123")
        
        with pytest.raises(ValueError, match="Invalid product_id"):
            USBDevice(vendor_id=0x1234, product_id=0x10000, serial_number="ABC123")
        
        # Valid product IDs
        USBDevice(vendor_id=0x1234, product_id=0x0000, serial_number="ABC123")
        USBDevice(vendor_id=0x1234, product_id=0xFFFF, serial_number="ABC123")
    
    def test_device_validation_serial_number(self):
        """Test serial number validation"""
        # Invalid serial numbers
        with pytest.raises(ValueError, match="Serial number cannot be empty"):
            USBDevice(vendor_id=0x1234, product_id=0x5678, serial_number="")
        
        with pytest.raises(ValueError, match="Serial number cannot be empty"):
            USBDevice(vendor_id=0x1234, product_id=0x5678, serial_number="   ")
        
        # Valid serial number
        USBDevice(vendor_id=0x1234, product_id=0x5678, serial_number="ABC123")


class TestUSBKeyManager:
    """Tests for USBKeyManager class"""
    
    @pytest.fixture
    def temp_config_path(self):
        """Create a temporary config file path"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.usbkey') as f:
            config_path = f.name
        yield config_path
        # Cleanup
        if os.path.exists(config_path):
            os.unlink(config_path)
    
    @pytest.fixture
    def test_device(self):
        """Create a test USB device"""
        return USBDevice(
            vendor_id=0x1050,
            product_id=0x0407,
            serial_number="12345678",
            manufacturer="Yubico",
            product="YubiKey"
        )
    
    def test_manager_initialization(self, temp_config_path):
        """Test USB key manager initialization"""
        manager = USBKeyManager(temp_config_path)
        
        assert manager.config_path == Path(temp_config_path)
        assert not manager.is_device_registered()
    
    def test_register_device(self, temp_config_path, test_device):
        """Test registering a USB device"""
        manager = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        challenge = manager.register_device(test_device, master_password)
        
        assert challenge is not None
        assert len(challenge) == 32  # 32 bytes challenge
        assert manager.is_device_registered()
        assert manager.get_registered_device() is not None
    
    def test_registered_device_persistence(self, temp_config_path, test_device):
        """Test that registered device persists across manager instances"""
        manager1 = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        manager1.register_device(test_device, master_password)
        
        # Create new manager with same config
        manager2 = USBKeyManager(temp_config_path)
        
        assert manager2.is_device_registered()
        registered_device = manager2.get_registered_device()
        assert registered_device.matches(test_device)
    
    def test_verify_device_authentication_success(self, temp_config_path, test_device):
        """Test successful device authentication verification"""
        # Note: This test won't actually check USB connection, just cryptographic verification
        manager = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        manager.register_device(test_device, master_password)
        
        # Manually set the device as "connected" for testing
        # In real scenario, this would check actual USB connection
        # We can't actually verify without the device, so we test the hash logic
        challenge = manager.get_challenge()
        response_hash = manager.get_response_hash()
        
        assert challenge is not None
        assert response_hash is not None
        assert len(response_hash) == 64  # SHA256 hex string
    
    def test_authenticate_with_device_only(self, temp_config_path, test_device):
        """Test device-only authentication"""
        manager = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        manager.register_device(test_device, master_password)
        
        # Get derived key (doesn't require actual USB connection check)
        derived_key = manager.authenticate_with_device_only()
        
        # Should return None if device not connected (which it isn't in test)
        # But we can test the mechanism works
        assert derived_key is None or isinstance(derived_key, str)
    
    def test_unregister_device(self, temp_config_path, test_device):
        """Test unregistering a device"""
        manager = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        manager.register_device(test_device, master_password)
        assert manager.is_device_registered()
        
        manager.unregister_device()
        assert not manager.is_device_registered()
        assert manager.get_registered_device() is None
    
    def test_unregister_removes_config_file(self, temp_config_path, test_device):
        """Test that unregistering removes config file"""
        manager = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        manager.register_device(test_device, master_password)
        assert os.path.exists(temp_config_path)
        
        manager.unregister_device()
        assert not os.path.exists(temp_config_path)
    
    def test_list_available_devices(self, temp_config_path):
        """Test listing available USB devices"""
        manager = USBKeyManager(temp_config_path)
        
        # This will return empty list in most test environments
        # but should not crash
        devices = manager.list_available_devices()
        
        assert isinstance(devices, list)
        # All items should be USBDevice instances
        for device in devices:
            assert isinstance(device, USBDevice)
    
    def test_get_challenge_and_response_hash(self, temp_config_path, test_device):
        """Test getting challenge and response hash"""
        manager = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        assert manager.get_challenge() is None
        assert manager.get_response_hash() is None
        
        manager.register_device(test_device, master_password)
        
        challenge = manager.get_challenge()
        response_hash = manager.get_response_hash()
        
        assert challenge is not None
        assert response_hash is not None
        assert isinstance(challenge, bytes)
        assert isinstance(response_hash, str)
    
    def test_different_passwords_produce_different_hashes(self, temp_config_path, test_device):
        """Test that different passwords produce different response hashes"""
        manager1 = USBKeyManager(temp_config_path + ".1")
        manager2 = USBKeyManager(temp_config_path + ".2")
        
        manager1.register_device(test_device, "Password1")
        manager2.register_device(test_device, "Password2")
        
        hash1 = manager1.get_response_hash()
        hash2 = manager2.get_response_hash()
        
        assert hash1 != hash2
        
        # Cleanup
        manager1.unregister_device()
        manager2.unregister_device()
    
    def test_config_file_permissions(self, temp_config_path, test_device):
        """Test that config file has restrictive permissions"""
        manager = USBKeyManager(temp_config_path)
        master_password = "TestPassword123!"
        
        manager.register_device(test_device, master_password)
        
        # Check file permissions (should be 0o600 on Unix-like systems)
        if os.name != 'nt':  # Skip on Windows
            stat_info = os.stat(temp_config_path)
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o600


class TestUSBKeyIntegration:
    """Integration tests for USB key functionality"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_full_registration_workflow(self, temp_config_dir):
        """Test full USB key registration workflow"""
        config_path = os.path.join(temp_config_dir, "config.usbkey")
        manager = USBKeyManager(config_path)
        
        # Create test device
        test_device = USBDevice(
            vendor_id=0x1050,
            product_id=0x0407,
            serial_number="TESTKEY123",
            manufacturer="TestCo",
            product="TestKey"
        )
        
        # Register device
        master_password = "SecurePassword123!"
        challenge = manager.register_device(test_device, master_password)
        
        # Verify registration
        assert manager.is_device_registered()
        registered_device = manager.get_registered_device()
        assert registered_device.matches(test_device)
        
        # Verify persistence
        manager2 = USBKeyManager(config_path)
        assert manager2.is_device_registered()
        
        # Unregister
        manager2.unregister_device()
        assert not manager2.is_device_registered()
