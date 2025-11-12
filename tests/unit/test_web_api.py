"""
Unit tests for web API endpoints
"""

import tempfile
import shutil
from pathlib import Path
from passw0rts.web.app import create_app


class TestWebAPIVaultInit:
    """Test vault initialization endpoints"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "test_vault.enc"
        self.app = create_app(storage_path=str(self.storage_path))
        self.client = self.app.test_client()

    def teardown_method(self):
        """Clean up test environment"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_vault_status_not_exists(self):
        """Test vault status when vault doesn't exist"""
        response = self.client.get('/api/vault/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['exists'] is False

    def test_vault_status_exists(self):
        """Test vault status when vault exists"""
        # Initialize vault first
        response = self.client.post('/api/vault/init', json={
            'master_password': 'test_password_123',
            'enable_totp': False
        })
        assert response.status_code == 200

        # Check status
        response = self.client.get('/api/vault/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['exists'] is True

    def test_init_vault_basic(self):
        """Test basic vault initialization"""
        response = self.client.post('/api/vault/init', json={
            'master_password': 'test_password_123',
            'enable_totp': False
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['totp_secret'] is None

    def test_init_vault_with_totp(self):
        """Test vault initialization with TOTP enabled"""
        response = self.client.post('/api/vault/init', json={
            'master_password': 'test_password_123',
            'enable_totp': True
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['totp_secret'] is not None
        assert len(data['totp_secret']) > 0

    def test_init_vault_already_exists(self):
        """Test vault initialization when vault already exists"""
        # Initialize vault first
        response = self.client.post('/api/vault/init', json={
            'master_password': 'test_password_123',
            'enable_totp': False
        })
        assert response.status_code == 200

        # Try to initialize again
        response = self.client.post('/api/vault/init', json={
            'master_password': 'another_password',
            'enable_totp': False
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_init_vault_no_password(self):
        """Test vault initialization without password"""
        response = self.client.post('/api/vault/init', json={
            'enable_totp': False
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestWebAPITOTP:
    """Test TOTP endpoints"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "test_vault.enc"
        self.app = create_app(storage_path=str(self.storage_path))
        self.client = self.app.test_client()

        # Initialize vault and login
        self.client.post('/api/vault/init', json={
            'master_password': 'test_password_123',
            'enable_totp': False
        })
        self.client.post('/api/auth/login', json={
            'master_password': 'test_password_123'
        })

    def teardown_method(self):
        """Clean up test environment"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_setup_totp(self):
        """Test TOTP setup"""
        response = self.client.post('/api/vault/totp/setup')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'secret' in data
        assert len(data['secret']) > 0

    def test_totp_status_disabled(self):
        """Test TOTP status when not enabled"""
        response = self.client.get('/api/vault/totp/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['enabled'] is False

    def test_totp_status_enabled(self):
        """Test TOTP status when enabled"""
        # Setup TOTP first
        self.client.post('/api/vault/totp/setup')

        response = self.client.get('/api/vault/totp/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['enabled'] is True

    def test_get_totp_qrcode(self):
        """Test TOTP QR code generation"""
        response = self.client.post('/api/vault/totp/qrcode', json={
            'secret': 'JBSWY3DPEHPK3PXP'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'qr_code' in data
        assert 'uri' in data
        assert data['qr_code'].startswith('data:image/png;base64,')

    def test_get_totp_qrcode_no_secret(self):
        """Test TOTP QR code generation without secret"""
        response = self.client.post('/api/vault/totp/qrcode', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_remove_totp(self):
        """Test TOTP removal"""
        # Setup TOTP first
        self.client.post('/api/vault/totp/setup')

        # Remove it
        response = self.client.post('/api/vault/totp/remove')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_totp_not_authenticated(self):
        """Test TOTP endpoints without authentication"""
        # Logout
        self.client.post('/api/auth/logout')

        # Try to setup TOTP
        response = self.client.post('/api/vault/totp/setup')
        assert response.status_code == 401


class TestWebAPIUSBKey:
    """Test USB key endpoints"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "test_vault.enc"
        self.app = create_app(storage_path=str(self.storage_path))
        self.client = self.app.test_client()

        # Initialize vault and login
        self.client.post('/api/vault/init', json={
            'master_password': 'test_password_123',
            'enable_totp': False
        })
        self.client.post('/api/auth/login', json={
            'master_password': 'test_password_123'
        })

    def teardown_method(self):
        """Clean up test environment"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_list_usb_devices(self):
        """Test listing USB devices"""
        response = self.client.get('/api/vault/usbkey/devices')

        assert response.status_code == 200
        data = response.get_json()
        assert 'devices' in data
        assert 'count' in data
        assert isinstance(data['devices'], list)

    def test_usb_key_status_not_registered(self):
        """Test USB key status when not registered"""
        response = self.client.get('/api/vault/usbkey/status')

        assert response.status_code == 200
        data = response.get_json()
        assert 'registered' in data
        assert 'connected' in data
        assert data['registered'] is False

    def test_remove_usb_key(self):
        """Test USB key removal"""
        response = self.client.post('/api/vault/usbkey/remove')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_register_usb_key_not_authenticated(self):
        """Test USB key registration without authentication"""
        # Logout
        self.client.post('/api/auth/logout')

        # Try to register USB key
        response = self.client.post('/api/vault/usbkey/register', json={
            'device_index': 0,
            'master_password': 'test_password_123'
        })
        assert response.status_code == 401

    def test_register_usb_key_no_device_index(self):
        """Test USB key registration without device index"""
        response = self.client.post('/api/vault/usbkey/register', json={
            'master_password': 'test_password_123'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_register_usb_key_no_password(self):
        """Test USB key registration without password"""
        response = self.client.post('/api/vault/usbkey/register', json={
            'device_index': 0
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
