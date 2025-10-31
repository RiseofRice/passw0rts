"""
Session persistence for maintaining authentication state across CLI commands
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SessionPersistence:
    """
    Manages persistent session data for CLI authentication.
    Stores encrypted session information that persists across command invocations.
    """
    
    def __init__(self, session_dir: Optional[Path] = None):
        """
        Initialize session persistence.
        
        Args:
            session_dir: Directory to store session files (default: ~/.passw0rts)
        """
        if session_dir is None:
            session_dir = Path.home() / ".passw0rts"
        
        self.session_dir = session_dir
        self.session_file = session_dir / ".session"
        self._ensure_session_dir()
    
    def _ensure_session_dir(self):
        """Ensure session directory exists with proper permissions"""
        if not self.session_dir.exists():
            self.session_dir.mkdir(parents=True, exist_ok=True)
            # Secure permissions (owner only)
            import os
            os.chmod(self.session_dir, 0o700)
    
    def _derive_session_key(self, master_password: str, salt: bytes) -> bytes:
        """
        Derive a session encryption key from master password.
        
        Args:
            master_password: Master password
            salt: Salt for key derivation
            
        Returns:
            32-byte encryption key
        """
        return hashlib.pbkdf2_hmac(
            'sha256',
            master_password.encode('utf-8'),
            salt,
            100000,  # Iterations (lighter than vault encryption for faster CLI)
            dklen=32
        )
    
    def save_session(
        self,
        master_password: str,
        totp_verified_at: Optional[float] = None,
        auto_lock_timeout: int = 300,
        storage_path: Optional[str] = None
    ) -> bool:
        """
        Save session data.
        
        Args:
            master_password: Master password (hashed before storage)
            totp_verified_at: Timestamp when TOTP was last verified (None if not using TOTP)
            auto_lock_timeout: Auto-lock timeout in seconds
            storage_path: Custom storage path if used
            
        Returns:
            True if successful
        """
        try:
            # Generate salt for this session
            salt = secrets.token_bytes(16)
            
            # Derive session key from master password
            session_key = self._derive_session_key(master_password, salt)
            
            # Create session data
            session_data = {
                'master_password_hash': hashlib.sha256(master_password.encode()).hexdigest(),
                'totp_verified_at': totp_verified_at,
                'last_activity': time.time(),
                'auto_lock_timeout': auto_lock_timeout,
                'storage_path': storage_path,
                'created_at': time.time()
            }
            
            # Encrypt session data
            aesgcm = AESGCM(session_key)
            nonce = secrets.token_bytes(12)
            plaintext = json.dumps(session_data).encode('utf-8')
            ciphertext = aesgcm.encrypt(nonce, plaintext, None)
            
            # Save encrypted session
            session_file_data = {
                'salt': salt.hex(),
                'nonce': nonce.hex(),
                'ciphertext': ciphertext.hex()
            }
            
            self.session_file.write_text(json.dumps(session_file_data))
            
            # Secure permissions on session file
            import os
            os.chmod(self.session_file, 0o600)
            
            return True
            
        except Exception as e:
            # Silently fail - session will just require re-auth
            return False
    
    def load_session(self, master_password: str) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt session data.
        
        Args:
            master_password: Master password to decrypt session
            
        Returns:
            Session data dict or None if invalid/expired
        """
        try:
            if not self.session_file.exists():
                return None
            
            # Load encrypted session
            session_file_data = json.loads(self.session_file.read_text())
            salt = bytes.fromhex(session_file_data['salt'])
            nonce = bytes.fromhex(session_file_data['nonce'])
            ciphertext = bytes.fromhex(session_file_data['ciphertext'])
            
            # Derive session key
            session_key = self._derive_session_key(master_password, salt)
            
            # Decrypt session data
            aesgcm = AESGCM(session_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            session_data = json.loads(plaintext.decode('utf-8'))
            
            # Verify master password hash matches
            password_hash = hashlib.sha256(master_password.encode()).hexdigest()
            if session_data['master_password_hash'] != password_hash:
                self.clear_session()
                return None
            
            # Check if session has expired (auto-lock timeout)
            last_activity = session_data.get('last_activity', 0)
            auto_lock_timeout = session_data.get('auto_lock_timeout', 300)
            
            if time.time() - last_activity > auto_lock_timeout:
                # Session expired
                self.clear_session()
                return None
            
            return session_data
            
        except Exception:
            # Any error (wrong password, corrupted file, etc.) - clear session
            self.clear_session()
            return None
    
    def update_activity(self, master_password: str) -> bool:
        """
        Update last activity timestamp in session.
        
        Args:
            master_password: Master password to unlock session
            
        Returns:
            True if successful
        """
        session_data = self.load_session(master_password)
        if session_data:
            # Update and re-save
            return self.save_session(
                master_password=master_password,
                totp_verified_at=session_data.get('totp_verified_at'),
                auto_lock_timeout=session_data.get('auto_lock_timeout', 300),
                storage_path=session_data.get('storage_path')
            )
        return False
    
    def is_totp_valid(self, session_data: Dict[str, Any]) -> bool:
        """
        Check if TOTP verification is still valid (within 24 hours).
        
        Args:
            session_data: Session data dict
            
        Returns:
            True if TOTP verification is not required or still valid
        """
        totp_verified_at = session_data.get('totp_verified_at')
        
        # If TOTP was never set up, it's always valid
        if totp_verified_at is None:
            return True
        
        # Check if verification is within last 24 hours
        hours_since_verification = (time.time() - totp_verified_at) / 3600
        return hours_since_verification < 24
    
    def clear_session(self) -> bool:
        """
        Clear/delete session file.
        
        Returns:
            True if successful
        """
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            return True
        except Exception:
            return False
    
    def session_exists(self) -> bool:
        """
        Check if a session file exists.
        
        Returns:
            True if session file exists
        """
        return self.session_file.exists()
