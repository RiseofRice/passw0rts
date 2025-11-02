"""
USB Security Key Manager for hardware-based authentication.

Supports USB security keys (including YubiKey) for authentication.
Uses USB device identification (Vendor ID, Product ID, Serial Number)
combined with challenge-response for secure authentication.
"""

import json
import hashlib
import secrets
from typing import Optional, Dict, List, Tuple
from pathlib import Path


class USBDevice:
    """Represents a USB device"""
    
    def __init__(self, vendor_id: int, product_id: int, serial_number: str, manufacturer: str = "", product: str = ""):
        # Validate USB identifiers
        if not (0x0000 <= vendor_id <= 0xFFFF):
            raise ValueError(f"Invalid vendor_id: {vendor_id}. Must be 0x0000-0xFFFF")
        if not (0x0000 <= product_id <= 0xFFFF):
            raise ValueError(f"Invalid product_id: {product_id}. Must be 0x0000-0xFFFF")
        if not serial_number or not serial_number.strip():
            raise ValueError("Serial number cannot be empty")
        
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.serial_number = serial_number
        self.manufacturer = manufacturer
        self.product = product
    
    def __str__(self):
        return f"{self.manufacturer} {self.product} (VID:{self.vendor_id:04x} PID:{self.product_id:04x} SN:{self.serial_number})"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'vendor_id': self.vendor_id,
            'product_id': self.product_id,
            'serial_number': self.serial_number,
            'manufacturer': self.manufacturer,
            'product': self.product
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'USBDevice':
        """Create from dictionary"""
        return cls(
            vendor_id=data['vendor_id'],
            product_id=data['product_id'],
            serial_number=data['serial_number'],
            manufacturer=data.get('manufacturer', ''),
            product=data.get('product', '')
        )
    
    def matches(self, other: 'USBDevice') -> bool:
        """Check if this device matches another"""
        return (
            self.vendor_id == other.vendor_id and
            self.product_id == other.product_id and
            self.serial_number == other.serial_number
        )


class USBKeyManager:
    """
    Manages USB security key authentication.
    
    Uses USB device identification combined with challenge-response
    for secure authentication without requiring the master password
    when the USB key is connected.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize USB key manager.
        
        Args:
            config_path: Path to USB key config file (default: ~/.passw0rts/config.usbkey)
        """
        if config_path is None:
            home = Path.home()
            config_dir = home / ".passw0rts"
            config_dir.mkdir(exist_ok=True, mode=0o700)
            config_path = str(config_dir / "config.usbkey")
        
        self.config_path = Path(config_path)
        self._registered_device: Optional[USBDevice] = None
        self._challenge: Optional[bytes] = None
        self._response_hash: Optional[str] = None
        self._load_config()
    
    def _load_config(self):
        """Load USB key configuration from file"""
        if not self.config_path.exists():
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            if 'device' in data:
                self._registered_device = USBDevice.from_dict(data['device'])
            
            if 'challenge' in data:
                import base64
                self._challenge = base64.b64decode(data['challenge'])
            
            if 'response_hash' in data:
                self._response_hash = data['response_hash']
                
        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
            # If config is missing or corrupted, start fresh
            # In production, this could be logged for debugging
            pass
    
    def _save_config(self):
        """Save USB key configuration to file"""
        import base64
        import os
        
        data = {}
        
        if self._registered_device:
            data['device'] = self._registered_device.to_dict()
        
        if self._challenge:
            data['challenge'] = base64.b64encode(self._challenge).decode('ascii')
        
        if self._response_hash:
            data['response_hash'] = self._response_hash
        
        # Write atomically
        temp_path = self.config_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        temp_path.replace(self.config_path)
        
        # Set restrictive permissions
        os.chmod(self.config_path, 0o600)
    
    def list_available_devices(self) -> List[USBDevice]:
        """
        List all available USB devices that could be used as security keys.
        
        Returns:
            List of USB devices
        """
        devices = []
        
        try:
            import usb.core
            import usb.util
            
            # Find all USB devices
            usb_devices = usb.core.find(find_all=True)
            
            for dev in usb_devices:
                try:
                    # Skip devices without serial numbers
                    if not dev.serial_number:
                        continue
                    
                    # Get device info
                    manufacturer = ""
                    product = ""
                    
                    try:
                        manufacturer = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else ""
                    except:
                        pass
                    
                    try:
                        product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else ""
                    except:
                        pass
                    
                    device = USBDevice(
                        vendor_id=dev.idVendor,
                        product_id=dev.idProduct,
                        serial_number=dev.serial_number,
                        manufacturer=manufacturer,
                        product=product
                    )
                    devices.append(device)
                    
                except (ValueError, Exception) as e:
                    # Skip devices we can't access (permissions, etc.)
                    # Using Exception to catch usb.core.USBError and other USB-related errors
                    continue
                    
        except ImportError:
            # pyusb not installed or libusb not available
            pass
        except Exception:
            # Other USB access errors
            pass
        
        return devices
    
    def register_device(self, device: USBDevice, master_password: str) -> bytes:
        """
        Register a USB device as a security key.
        
        Args:
            device: The USB device to register
            master_password: The master password to derive key material
            
        Returns:
            Challenge bytes that should be stored securely
        """
        # Generate a random challenge
        self._challenge = secrets.token_bytes(32)
        
        # Derive a response from master password + device info + challenge
        # Use delimiters to prevent device ID collision
        device_id = f"{device.vendor_id:04x}:{device.product_id:04x}:{device.serial_number}"
        response_data = f"{master_password}:{device_id}:{self._challenge.hex()}"
        
        # Hash the response for verification
        self._response_hash = hashlib.sha256(response_data.encode('utf-8')).hexdigest()
        
        # Store device info
        self._registered_device = device
        
        # Save configuration
        self._save_config()
        
        return self._challenge
    
    def is_device_registered(self) -> bool:
        """Check if a USB key is registered"""
        return self._registered_device is not None
    
    def get_registered_device(self) -> Optional[USBDevice]:
        """Get the registered USB device"""
        return self._registered_device
    
    def is_registered_device_connected(self) -> bool:
        """
        Check if the registered USB device is currently connected.
        
        Returns:
            True if registered device is connected
        """
        if not self._registered_device:
            return False
        
        available_devices = self.list_available_devices()
        
        for device in available_devices:
            if self._registered_device.matches(device):
                return True
        
        return False
    
    def verify_device_authentication(self, master_password: str) -> bool:
        """
        Verify authentication using the connected USB device.
        
        Args:
            master_password: The master password
            
        Returns:
            True if authentication succeeds
        """
        if not self._registered_device or not self._challenge or not self._response_hash:
            return False
        
        # Check if device is connected
        if not self.is_registered_device_connected():
            return False
        
        # Derive response from master password + device info + challenge
        # Use delimiters to prevent device ID collision
        device_id = f"{self._registered_device.vendor_id:04x}:{self._registered_device.product_id:04x}:{self._registered_device.serial_number}"
        response_data = f"{master_password}:{device_id}:{self._challenge.hex()}"
        
        # Verify response hash
        computed_hash = hashlib.sha256(response_data.encode('utf-8')).hexdigest()
        
        return computed_hash == self._response_hash
    
    def authenticate_with_device_only(self) -> Optional[str]:
        """
        Attempt to authenticate using only the USB device (no password required).
        This derives a key from the USB device information.
        
        Returns:
            Derived key string if device is connected, None otherwise
        """
        if not self._registered_device or not self._challenge:
            return None
        
        # Check if device is connected
        if not self.is_registered_device_connected():
            return None
        
        # Derive a key from device info + challenge
        # This allows unlocking without password when USB key is present
        # Use delimiters to prevent device ID collision
        device_id = f"{self._registered_device.vendor_id:04x}:{self._registered_device.product_id:04x}:{self._registered_device.serial_number}"
        key_material = f"usbkey:{device_id}:{self._challenge.hex()}"
        
        # Return a deterministic key derived from device
        return hashlib.sha256(key_material.encode('utf-8')).hexdigest()
    
    def unregister_device(self):
        """Unregister the USB security key"""
        self._registered_device = None
        self._challenge = None
        self._response_hash = None
        
        if self.config_path.exists():
            self.config_path.unlink()
    
    def get_challenge(self) -> Optional[bytes]:
        """Get the challenge for this USB key"""
        return self._challenge
    
    def get_response_hash(self) -> Optional[str]:
        """Get the response hash for verification"""
        return self._response_hash
