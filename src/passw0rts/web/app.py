"""
Flask web application for passw0rts password manager
"""

import secrets
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from datetime import timedelta

from passw0rts.core import StorageManager, PasswordEntry
from passw0rts.utils import PasswordGenerator, TOTPManager, USBKeyManager

# Configure logging
logger = logging.getLogger(__name__)


def create_app(storage_path=None, secret_key=None):
    """
    Create and configure the Flask application.

    Args:
        storage_path: Path to the password vault
        secret_key: Flask secret key (generated if not provided)

    Returns:
        Flask application instance
    """
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = secret_key or secrets.token_hex(32)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['STORAGE_PATH'] = storage_path

    # Enable CORS for localhost
    CORS(app)

    # Dictionary to store storage managers per session
    # Key: session ID, Value: (StorageManager, TOTPManager)
    _session_storage = {}

    def get_storage_manager():
        """Get the storage manager for the current session."""
        session_id = session.get('session_id')
        if session_id and session_id in _session_storage:
            return _session_storage[session_id][0]
        return None

    def get_totp_manager():
        """Get the TOTP manager for the current session."""
        session_id = session.get('session_id')
        if session_id and session_id in _session_storage:
            return _session_storage[session_id][1]
        return None

    def set_session_managers(storage_mgr, totp_mgr=None):
        """Set the storage and TOTP managers for the current session."""
        session_id = session.get('session_id')
        if not session_id:
            session_id = secrets.token_hex(16)
            session['session_id'] = session_id
        _session_storage[session_id] = (storage_mgr, totp_mgr)

    def clear_session_managers():
        """Clear the managers for the current session."""
        session_id = session.get('session_id')
        if session_id and session_id in _session_storage:
            storage_mgr, _ = _session_storage[session_id]
            if storage_mgr:
                storage_mgr.clear()
            del _session_storage[session_id]

    @app.route('/')
    def index():
        """Main dashboard"""
        if 'authenticated' not in session:
            return render_template('login.html')
        return render_template('dashboard.html')

    @app.route('/init')
    def init_page():
        """Vault initialization page"""
        return render_template('init.html')

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Authenticate and unlock vault"""

        data = request.json
        master_password = data.get('master_password')
        totp_code = data.get('totp_code')

        if not master_password:
            return jsonify({'error': 'Master password required'}), 400

        try:
            # Initialize storage for this session
            storage_manager = StorageManager(app.config['STORAGE_PATH'])

            if not storage_manager.storage_path.exists():
                return jsonify({'error': 'Vault not found'}), 404

            # Unlock vault
            storage_manager.initialize(master_password)

            # Check TOTP if enabled
            totp_manager = None
            config_dir = storage_manager.storage_path.parent
            config_file = config_dir / "config.totp"

            if config_file.exists():
                if not totp_code:
                    return jsonify({'error': 'TOTP code required', 'totp_required': True}), 401

                secret = config_file.read_text().strip()
                totp_manager = TOTPManager(secret)

                if not totp_manager.verify_code(totp_code):
                    return jsonify({'error': 'Invalid TOTP code'}), 401

            # Store managers for this session
            set_session_managers(storage_manager, totp_manager)

            # Set session
            session['authenticated'] = True
            session.permanent = True

            return jsonify({
                'success': True,
                'entry_count': len(storage_manager.list_entries())
            })

        except Exception as e:
            # Log the actual error for debugging and security monitoring
            logger.error(f"Authentication failed: {str(e)}", exc_info=True)
            # Don't expose internal error details to users
            return jsonify({'error': 'Authentication failed'}), 401

    @app.route('/api/auth/logout', methods=['POST'])
    def logout():
        """Logout and lock vault"""
        clear_session_managers()
        session.clear()
        return jsonify({'success': True})

    @app.route('/api/entries', methods=['GET'])
    def get_entries():
        """Get all password entries"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        query = request.args.get('q')

        if query:
            entries = storage_manager.search_entries(query)
        else:
            entries = storage_manager.list_entries()

        # Don't send passwords in list view
        entries_data = [
            {
                'id': e.id,
                'title': e.title,
                'username': e.username,
                'url': e.url,
                'category': e.category,
                'created_at': e.created_at.isoformat(),
                'updated_at': e.updated_at.isoformat()
            }
            for e in entries
        ]

        return jsonify(entries_data)

    @app.route('/api/entries/<entry_id>', methods=['GET'])
    def get_entry(entry_id):
        """Get a specific entry with password"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        entry = storage_manager.get_entry(entry_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        return jsonify(entry.to_dict())

    @app.route('/api/entries', methods=['POST'])
    def create_entry():
        """Create a new password entry"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        data = request.json

        try:
            entry = PasswordEntry(
                title=data['title'],
                username=data.get('username'),
                password=data['password'],
                url=data.get('url'),
                notes=data.get('notes'),
                category=data.get('category', 'general'),
                tags=data.get('tags', [])
            )

            entry_id = storage_manager.add_entry(entry)
            return jsonify({'id': entry_id, 'success': True})

        except Exception as e:
            # Log the actual error for debugging
            logger.error(f"Failed to create entry: {str(e)}", exc_info=True)
            # Don't expose internal error details to users
            return jsonify({'error': 'Failed to create entry'}), 400

    @app.route('/api/entries/<entry_id>', methods=['PUT'])
    def update_entry(entry_id):
        """Update an existing entry"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        entry = storage_manager.get_entry(entry_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404

        data = request.json

        # Update fields
        if 'title' in data:
            entry.title = data['title']
        if 'username' in data:
            entry.username = data['username']
        if 'password' in data:
            entry.password = data['password']
        if 'url' in data:
            entry.url = data['url']
        if 'notes' in data:
            entry.notes = data['notes']
        if 'category' in data:
            entry.category = data['category']
        if 'tags' in data:
            entry.tags = data['tags']

        storage_manager.update_entry(entry_id, entry)
        return jsonify({'success': True})

    @app.route('/api/entries/<entry_id>', methods=['DELETE'])
    def delete_entry(entry_id):
        """Delete an entry"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        if storage_manager.delete_entry(entry_id):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Entry not found'}), 404

    @app.route('/api/generate-password', methods=['POST'])
    def generate_password():
        """Generate a random password"""
        data = request.json or {}

        length = data.get('length', 16)
        use_symbols = data.get('use_symbols', True)
        exclude_ambiguous = data.get('exclude_ambiguous', False)

        password = PasswordGenerator.generate(
            length=length,
            use_symbols=use_symbols,
            exclude_ambiguous=exclude_ambiguous
        )

        label, score = PasswordGenerator.estimate_strength(password)

        return jsonify({
            'password': password,
            'strength': {'label': label, 'score': score}
        })

    @app.route('/api/vault/status', methods=['GET'])
    def vault_status():
        """
        Check if vault exists.
        
        Note: This endpoint is intentionally unauthenticated to support the
        initialization flow where users need to be redirected to /init if no
        vault exists. This is required before authentication is possible.
        """
        storage_manager = StorageManager(app.config['STORAGE_PATH'])
        return jsonify({
            'exists': storage_manager.storage_path.exists()
        })

    @app.route('/api/vault/init', methods=['POST'])
    def init_vault():
        """Initialize a new vault"""
        data = request.json
        master_password = data.get('master_password')

        if not master_password:
            return jsonify({'error': 'Master password required'}), 400

        try:
            storage_manager = StorageManager(app.config['STORAGE_PATH'])

            if storage_manager.storage_path.exists():
                return jsonify({'error': 'Vault already exists'}), 400

            # Initialize vault
            storage_manager.initialize(master_password)

            # Set up TOTP if requested
            totp_secret = None
            if data.get('enable_totp', False):
                totp_manager = TOTPManager()
                totp_secret = totp_manager.get_secret()

                # Save TOTP secret with secure permissions
                config_dir = storage_manager.storage_path.parent
                config_file = config_dir / "config.totp"
                config_file.write_text(totp_secret)
                config_file.chmod(0o600)  # Restrict to owner only

            return jsonify({
                'success': True,
                'totp_secret': totp_secret
            })

        except Exception as e:
            logger.error(f"Failed to initialize vault: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to initialize vault'}), 500

    @app.route('/api/vault/totp/qrcode', methods=['POST'])
    def get_totp_qrcode():
        """Get TOTP QR code for a secret"""
        # Note: This endpoint is used during vault initialization (before authentication)
        # and after authentication. We check if Pillow is available and provide helpful error.
        data = request.json
        secret = data.get('secret')

        if not secret:
            return jsonify({'error': 'TOTP secret required'}), 400

        try:
            import base64
            totp_manager = TOTPManager(secret)
            qr_bytes = totp_manager.generate_qr_code('passw0rts')
            qr_base64 = base64.b64encode(qr_bytes).decode('utf-8')

            return jsonify({
                'qr_code': f'data:image/png;base64,{qr_base64}',
                'uri': totp_manager.get_provisioning_uri('passw0rts')
            })

        except ImportError as e:
            # Provide helpful error message if Pillow is not installed
            logger.error(f"Pillow not installed: {str(e)}", exc_info=True)
            return jsonify({
                'error': 'QR code generation requires Pillow. Install it with: pip install pillow',
                'uri': TOTPManager(secret).get_provisioning_uri('passw0rts'),
                'secret': secret
            }), 500
        except Exception as e:
            logger.error(f"Failed to generate QR code: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to generate QR code'}), 500

    @app.route('/api/vault/totp/setup', methods=['POST'])
    def setup_totp():
        """Setup TOTP for existing vault"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        try:
            totp_manager = TOTPManager()
            secret = totp_manager.get_secret()

            # Save TOTP secret with secure permissions
            config_dir = storage_manager.storage_path.parent
            config_file = config_dir / "config.totp"
            config_file.write_text(secret)
            config_file.chmod(0o600)  # Restrict to owner only

            return jsonify({
                'success': True,
                'secret': secret
            })

        except Exception as e:
            logger.error(f"Failed to setup TOTP: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to setup TOTP'}), 500

    @app.route('/api/vault/totp/remove', methods=['POST'])
    def remove_totp():
        """Remove TOTP from vault"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        try:
            config_dir = storage_manager.storage_path.parent
            config_file = config_dir / "config.totp"

            if config_file.exists():
                config_file.unlink()

            return jsonify({'success': True})

        except Exception as e:
            logger.error(f"Failed to remove TOTP: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to remove TOTP'}), 500

    @app.route('/api/vault/totp/status', methods=['GET'])
    def totp_status():
        """Check TOTP configuration status"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        try:
            config_dir = storage_manager.storage_path.parent
            config_file = config_dir / "config.totp"

            return jsonify({
                'enabled': config_file.exists()
            })

        except Exception as e:
            logger.error(f"Failed to check TOTP status: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to check TOTP status'}), 500

    @app.route('/api/vault/usbkey/devices', methods=['GET'])
    def list_usb_devices():
        """List available USB devices"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        try:
            storage_manager = StorageManager(app.config['STORAGE_PATH'])
            config_dir = storage_manager.storage_path.parent
            usb_manager = USBKeyManager(str(config_dir / "config.usbkey"))

            devices = usb_manager.list_available_devices()
            device_list = [str(device) for device in devices]

            return jsonify({
                'devices': device_list,
                'count': len(device_list)
            })

        except Exception as e:
            logger.error(f"Failed to list USB devices: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to list USB devices'}), 500

    @app.route('/api/vault/usbkey/register', methods=['POST'])
    def register_usb_key():
        """Register a USB security key"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        data = request.json
        device_index = data.get('device_index')
        master_password = data.get('master_password')

        if device_index is None:
            return jsonify({'error': 'Device index required'}), 400

        if not master_password:
            return jsonify({'error': 'Master password required'}), 400

        try:
            config_dir = storage_manager.storage_path.parent
            usb_manager = USBKeyManager(str(config_dir / "config.usbkey"))

            devices = usb_manager.list_available_devices()
            if device_index < 0 or device_index >= len(devices):
                return jsonify({'error': 'Invalid device index'}), 400

            selected_device = devices[device_index]
            usb_manager.register_device(selected_device, master_password)

            return jsonify({
                'success': True,
                'device': str(selected_device)
            })

        except Exception as e:
            logger.error(f"Failed to register USB key: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to register USB key'}), 500

    @app.route('/api/vault/usbkey/status', methods=['GET'])
    def usb_key_status():
        """Check USB key registration status"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        try:
            storage_manager = StorageManager(app.config['STORAGE_PATH'])
            config_dir = storage_manager.storage_path.parent
            usb_manager = USBKeyManager(str(config_dir / "config.usbkey"))

            is_registered = usb_manager.is_device_registered()
            is_connected = is_registered and usb_manager.is_registered_device_connected()

            return jsonify({
                'registered': is_registered,
                'connected': is_connected
            })

        except Exception as e:
            logger.error(f"Failed to check USB key status: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to check USB key status'}), 500

    @app.route('/api/vault/usbkey/remove', methods=['POST'])
    def remove_usb_key():
        """Remove USB security key registration"""
        if 'authenticated' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        storage_manager = get_storage_manager()
        if not storage_manager:
            return jsonify({'error': 'Session expired'}), 401

        try:
            config_dir = storage_manager.storage_path.parent
            usb_manager = USBKeyManager(str(config_dir / "config.usbkey"))
            usb_manager.unregister_device()

            return jsonify({'success': True})

        except Exception as e:
            logger.error(f"Failed to remove USB key: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to remove USB key'}), 500

    return app


def run_server(host='127.0.0.1', port=5000, storage_path=None):
    """
    Run the Flask development server.

    Args:
        host: Host address
        port: Port number
        storage_path: Path to password vault
    """
    app = create_app(storage_path=storage_path)
    app.run(host=host, port=port, debug=False)
