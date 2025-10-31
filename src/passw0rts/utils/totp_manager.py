"""
TOTP (Time-based One-Time Password) manager for 2FA
"""

import pyotp
import qrcode
from io import BytesIO
from typing import Optional


class TOTPManager:
    """
    Manages TOTP for two-factor authentication.
    """
    
    def __init__(self, secret: Optional[str] = None):
        """
        Initialize TOTP manager.
        
        Args:
            secret: Base32 encoded secret (generated if not provided)
        """
        if secret is None:
            secret = pyotp.random_base32()
        
        self.secret = secret
        self.totp = pyotp.TOTP(secret)
    
    def get_secret(self) -> str:
        """Get the TOTP secret"""
        return self.secret
    
    def get_provisioning_uri(self, name: str, issuer: str = "Passw0rts") -> str:
        """
        Get the provisioning URI for QR code generation.
        
        Args:
            name: Account name (e.g., user email)
            issuer: Issuer name
            
        Returns:
            The provisioning URI
        """
        return self.totp.provisioning_uri(name=name, issuer_name=issuer)
    
    def generate_qr_code(self, name: str, issuer: str = "Passw0rts") -> bytes:
        """
        Generate a QR code for TOTP setup.
        
        Args:
            name: Account name
            issuer: Issuer name
            
        Returns:
            QR code image as PNG bytes
        """
        uri = self.get_provisioning_uri(name, issuer)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def generate_code(self) -> str:
        """
        Generate current TOTP code.
        
        Returns:
            6-digit TOTP code
        """
        return self.totp.now()
    
    def verify_code(self, code: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            code: The TOTP code to verify
            valid_window: Number of time windows to check (before/after current)
            
        Returns:
            True if code is valid
        """
        return self.totp.verify(code, valid_window=valid_window)
    
    def get_remaining_time(self) -> int:
        """
        Get remaining seconds until current code expires.
        
        Returns:
            Seconds remaining
        """
        import time
        return 30 - (int(time.time()) % 30)
