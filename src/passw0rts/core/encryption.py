"""
Encryption module using AES-256-GCM for secure password storage
"""

import base64
import secrets
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class EncryptionManager:
    """
    Manages encryption and decryption of password data using AES-256-GCM.
    Uses PBKDF2 for key derivation from master password.
    """
    
    # Constants for key derivation
    PBKDF2_ITERATIONS = 600000  # OWASP recommended minimum
    SALT_SIZE = 32  # 256 bits
    KEY_SIZE = 32   # 256 bits for AES-256
    NONCE_SIZE = 12  # 96 bits, recommended for GCM
    
    def __init__(self):
        """Initialize the encryption manager"""
        self._key = None
        self._salt = None
    
    def derive_key(self, master_password: str, salt: bytes = None) -> bytes:
        """
        Derive an encryption key from the master password using PBKDF2.
        
        Args:
            master_password: The master password string
            salt: Optional salt bytes (generated if not provided)
            
        Returns:
            The derived key bytes and salt used
        """
        if salt is None:
            salt = secrets.token_bytes(self.SALT_SIZE)
        
        self._salt = salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        
        self._key = kdf.derive(master_password.encode('utf-8'))
        return self._key
    
    def get_salt(self) -> bytes:
        """Get the current salt"""
        return self._salt
    
    def set_key(self, key: bytes):
        """Set the encryption key directly"""
        if len(key) != self.KEY_SIZE:
            raise ValueError(f"Key must be {self.KEY_SIZE} bytes")
        self._key = key
    
    def encrypt(self, plaintext: str) -> Tuple[bytes, bytes]:
        """
        Encrypt plaintext using AES-256-GCM.
        
        Args:
            plaintext: The plaintext string to encrypt
            
        Returns:
            Tuple of (ciphertext, nonce)
            
        Raises:
            ValueError: If key is not set
        """
        if self._key is None:
            raise ValueError("Encryption key not set. Call derive_key first.")
        
        # Generate a random nonce
        nonce = secrets.token_bytes(self.NONCE_SIZE)
        
        # Create cipher and encrypt
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        return ciphertext, nonce
    
    def decrypt(self, ciphertext: bytes, nonce: bytes) -> str:
        """
        Decrypt ciphertext using AES-256-GCM.
        
        Args:
            ciphertext: The encrypted data
            nonce: The nonce used during encryption
            
        Returns:
            The decrypted plaintext string
            
        Raises:
            ValueError: If key is not set
            cryptography.exceptions.InvalidTag: If authentication fails
        """
        if self._key is None:
            raise ValueError("Encryption key not set. Call derive_key first.")
        
        # Create cipher and decrypt
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode('utf-8')
    
    def encrypt_to_base64(self, plaintext: str) -> str:
        """
        Encrypt and encode to base64 for storage.
        
        Args:
            plaintext: The plaintext string to encrypt
            
        Returns:
            Base64 encoded string containing nonce and ciphertext
        """
        ciphertext, nonce = self.encrypt(plaintext)
        # Combine nonce and ciphertext
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode('ascii')
    
    def decrypt_from_base64(self, encoded_data: str) -> str:
        """
        Decrypt from base64 encoded string.
        
        Args:
            encoded_data: Base64 encoded string containing nonce and ciphertext
            
        Returns:
            The decrypted plaintext string
        """
        combined = base64.b64decode(encoded_data)
        # Split nonce and ciphertext
        nonce = combined[:self.NONCE_SIZE]
        ciphertext = combined[self.NONCE_SIZE:]
        return self.decrypt(ciphertext, nonce)
    
    def clear(self):
        """Clear sensitive data from memory"""
        if self._key:
            # Note: Python's memory management makes true secure wiping difficult
            # This is a best-effort approach
            key_len = len(self._key)
            self._key = None  # Release reference
            # Force garbage collection (not guaranteed to be immediate)
            import gc
            gc.collect()
        self._key = None
        self._salt = None
