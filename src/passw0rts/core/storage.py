"""
Storage manager for encrypted password data
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict
from .encryption import EncryptionManager
from .password_entry import PasswordEntry


class StorageManager:
    """
    Manages storage and retrieval of encrypted password entries.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize storage manager.
        
        Args:
            storage_path: Path to storage file (default: ~/.passw0rts/vault.enc)
        """
        if storage_path is None:
            home = Path.home()
            storage_dir = home / ".passw0rts"
            storage_dir.mkdir(exist_ok=True, mode=0o700)
            storage_path = str(storage_dir / "vault.enc")
        
        self.storage_path = Path(storage_path)
        self.encryption_manager: Optional[EncryptionManager] = None
        self._entries: Dict[str, PasswordEntry] = {}
        self._salt: Optional[bytes] = None
    
    def initialize(self, master_password: str) -> bool:
        """
        Initialize or load the vault with the master password.
        
        Args:
            master_password: The master password
            
        Returns:
            True if successful
        """
        self.encryption_manager = EncryptionManager()
        
        if self.storage_path.exists():
            # Load existing vault
            return self._load_vault(master_password)
        else:
            # Create new vault
            return self._create_vault(master_password)
    
    def _create_vault(self, master_password: str) -> bool:
        """Create a new vault"""
        # Derive key from master password
        self.encryption_manager.derive_key(master_password)
        self._salt = self.encryption_manager.get_salt()
        self._entries = {}
        
        # Save empty vault
        self._save_vault()
        return True
    
    def _load_vault(self, master_password: str) -> bool:
        """Load and decrypt existing vault"""
        try:
            with open(self.storage_path, 'r') as f:
                vault_data = json.load(f)
            
            # Get salt from vault
            import base64
            self._salt = base64.b64decode(vault_data['salt'])
            
            # Derive key from master password and salt
            self.encryption_manager.derive_key(master_password, self._salt)
            
            # Decrypt entries
            encrypted_data = vault_data['data']
            decrypted_json = self.encryption_manager.decrypt_from_base64(encrypted_data)
            entries_data = json.loads(decrypted_json)
            
            # Load entries
            self._entries = {
                entry_id: PasswordEntry.from_dict(entry_dict)
                for entry_id, entry_dict in entries_data.items()
            }
            
            return True
        except Exception as e:
            # Could be wrong password or corrupted data
            raise ValueError(f"Failed to load vault: {str(e)}")
    
    def _save_vault(self):
        """Save and encrypt vault to disk"""
        if self.encryption_manager is None:
            raise ValueError("Storage not initialized")
        
        # Serialize entries
        entries_data = {
            entry_id: entry.to_dict()
            for entry_id, entry in self._entries.items()
        }
        entries_json = json.dumps(entries_data)
        
        # Encrypt
        encrypted_data = self.encryption_manager.encrypt_to_base64(entries_json)
        
        # Save to file
        import base64
        vault_data = {
            'version': '1.0',
            'salt': base64.b64encode(self._salt).decode('ascii'),
            'data': encrypted_data
        }
        
        # Write atomically
        temp_path = self.storage_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(vault_data, f, indent=2)
        
        temp_path.replace(self.storage_path)
        
        # Set restrictive permissions
        os.chmod(self.storage_path, 0o600)
    
    def add_entry(self, entry: PasswordEntry) -> str:
        """
        Add a new password entry.
        
        Args:
            entry: The password entry to add
            
        Returns:
            The ID of the added entry
        """
        self._entries[entry.id] = entry
        self._save_vault()
        return entry.id
    
    def get_entry(self, entry_id: str) -> Optional[PasswordEntry]:
        """
        Get a password entry by ID.
        
        Args:
            entry_id: The entry ID
            
        Returns:
            The password entry or None if not found
        """
        return self._entries.get(entry_id)
    
    def update_entry(self, entry_id: str, entry: PasswordEntry):
        """
        Update an existing password entry.
        
        Args:
            entry_id: The entry ID
            entry: The updated entry
        """
        if entry_id not in self._entries:
            raise ValueError(f"Entry {entry_id} not found")
        
        entry.update_timestamp()
        self._entries[entry_id] = entry
        self._save_vault()
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete a password entry.
        
        Args:
            entry_id: The entry ID
            
        Returns:
            True if entry was deleted
        """
        if entry_id in self._entries:
            del self._entries[entry_id]
            self._save_vault()
            return True
        return False
    
    def list_entries(self) -> List[PasswordEntry]:
        """
        Get all password entries.
        
        Returns:
            List of all password entries
        """
        return list(self._entries.values())
    
    def search_entries(self, query: str) -> List[PasswordEntry]:
        """
        Search for password entries.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching password entries
        """
        return [
            entry for entry in self._entries.values()
            if entry.matches_search(query)
        ]
    
    def export_data(self) -> str:
        """
        Export all entries as JSON (unencrypted - use with caution).
        
        Returns:
            JSON string of all entries
        """
        entries_data = [entry.to_dict() for entry in self._entries.values()]
        return json.dumps(entries_data, indent=2)
    
    def import_data(self, json_data: str):
        """
        Import entries from JSON.
        
        Args:
            json_data: JSON string containing entries
        """
        entries_data = json.loads(json_data)
        for entry_dict in entries_data:
            entry = PasswordEntry.from_dict(entry_dict)
            self._entries[entry.id] = entry
        
        self._save_vault()
    
    def clear(self):
        """Clear sensitive data from memory"""
        self._entries.clear()
        if self.encryption_manager:
            self.encryption_manager.clear()
