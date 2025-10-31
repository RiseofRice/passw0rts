"""
Integration tests for storage manager
"""

import pytest
import tempfile
import json
from pathlib import Path
from passw0rts.core import StorageManager, PasswordEntry


class TestStorageIntegration:
    """Integration tests for StorageManager"""
    
    def test_full_workflow(self):
        """Test complete workflow: create vault, add entries, save, reload"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_vault.enc"
            master_password = "TestPassword123!"
            
            # Create new vault
            storage = StorageManager(str(storage_path))
            assert storage.initialize(master_password)
            
            # Add entries
            entry1 = PasswordEntry(
                title="Gmail",
                username="user@gmail.com",
                password="SecurePass123!",
                url="https://gmail.com",
                category="email"
            )
            
            entry2 = PasswordEntry(
                title="GitHub",
                username="developer",
                password="GitHubPass456!",
                url="https://github.com",
                category="development"
            )
            
            id1 = storage.add_entry(entry1)
            id2 = storage.add_entry(entry2)
            
            assert len(storage.list_entries()) == 2
            
            # Reload vault
            storage2 = StorageManager(str(storage_path))
            assert storage2.initialize(master_password)
            
            # Verify entries persisted
            entries = storage2.list_entries()
            assert len(entries) == 2
            
            # Verify data integrity
            loaded_entry1 = storage2.get_entry(id1)
            assert loaded_entry1.title == "Gmail"
            assert loaded_entry1.username == "user@gmail.com"
            assert loaded_entry1.password == "SecurePass123!"
            
            loaded_entry2 = storage2.get_entry(id2)
            assert loaded_entry2.title == "GitHub"
            assert loaded_entry2.password == "GitHubPass456!"
    
    def test_wrong_password_fails(self):
        """Test that wrong master password fails to unlock"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_vault.enc"
            
            # Create vault
            storage = StorageManager(str(storage_path))
            storage.initialize("CorrectPassword123!")
            
            # Add an entry
            entry = PasswordEntry(
                title="Test",
                username="test",
                password="test123"
            )
            storage.add_entry(entry)
            
            # Try to open with wrong password
            storage2 = StorageManager(str(storage_path))
            with pytest.raises(ValueError):
                storage2.initialize("WrongPassword123!")
    
    def test_update_entry(self):
        """Test updating an entry"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_vault.enc"
            storage = StorageManager(str(storage_path))
            storage.initialize("TestPassword123!")
            
            # Add entry
            entry = PasswordEntry(
                title="Test Entry",
                username="user",
                password="pass123"
            )
            entry_id = storage.add_entry(entry)
            
            # Update entry
            entry.password = "NewPassword456!"
            entry.username = "newuser"
            storage.update_entry(entry_id, entry)
            
            # Reload and verify
            storage2 = StorageManager(str(storage_path))
            storage2.initialize("TestPassword123!")
            
            updated = storage2.get_entry(entry_id)
            assert updated.password == "NewPassword456!"
            assert updated.username == "newuser"
            assert updated.title == "Test Entry"
    
    def test_delete_entry(self):
        """Test deleting an entry"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_vault.enc"
            storage = StorageManager(str(storage_path))
            storage.initialize("TestPassword123!")
            
            # Add entries
            entry1 = PasswordEntry(title="Entry 1", username="user1", password="pass1")
            entry2 = PasswordEntry(title="Entry 2", username="user2", password="pass2")
            
            id1 = storage.add_entry(entry1)
            id2 = storage.add_entry(entry2)
            
            assert len(storage.list_entries()) == 2
            
            # Delete one entry
            assert storage.delete_entry(id1)
            assert len(storage.list_entries()) == 1
            
            # Verify correct entry was deleted
            remaining = storage.list_entries()[0]
            assert remaining.title == "Entry 2"
            
            # Reload and verify
            storage2 = StorageManager(str(storage_path))
            storage2.initialize("TestPassword123!")
            assert len(storage2.list_entries()) == 1
            assert storage2.get_entry(id1) is None
            assert storage2.get_entry(id2) is not None
    
    def test_search_entries(self):
        """Test search functionality"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_vault.enc"
            storage = StorageManager(str(storage_path))
            storage.initialize("TestPassword123!")
            
            # Add various entries
            entries = [
                PasswordEntry(title="Gmail Account", username="user@gmail.com", password="pass1", category="email"),
                PasswordEntry(title="GitHub Account", username="developer", password="pass2", category="development"),
                PasswordEntry(title="Gmail Business", username="business@gmail.com", password="pass3", category="email"),
                PasswordEntry(title="Twitter", username="user", password="pass4", category="social"),
            ]
            
            for entry in entries:
                storage.add_entry(entry)
            
            # Test search
            gmail_results = storage.search_entries("gmail")
            assert len(gmail_results) == 2
            assert all("gmail" in e.title.lower() or "gmail" in (e.username or "").lower() for e in gmail_results)
            
            email_results = storage.search_entries("email")
            assert len(email_results) == 2
            
            github_results = storage.search_entries("github")
            assert len(github_results) == 1
            assert github_results[0].title == "GitHub Account"
    
    def test_export_import(self):
        """Test export and import functionality"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_vault.enc"
            export_path = Path(tmpdir) / "export.json"
            
            # Create vault with entries
            storage = StorageManager(str(storage_path))
            storage.initialize("TestPassword123!")
            
            entry1 = PasswordEntry(title="Entry 1", username="user1", password="pass1")
            entry2 = PasswordEntry(title="Entry 2", username="user2", password="pass2")
            
            storage.add_entry(entry1)
            storage.add_entry(entry2)
            
            # Export
            export_data = storage.export_data()
            export_path.write_text(export_data)
            
            # Create new vault and import
            new_storage_path = Path(tmpdir) / "new_vault.enc"
            new_storage = StorageManager(str(new_storage_path))
            new_storage.initialize("NewPassword123!")
            
            # Import
            import_data = export_path.read_text()
            new_storage.import_data(import_data)
            
            # Verify
            entries = new_storage.list_entries()
            assert len(entries) == 2
            
            titles = {e.title for e in entries}
            assert "Entry 1" in titles
            assert "Entry 2" in titles
    
    def test_multiple_sessions(self):
        """Test that multiple storage instances can't interfere"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "test_vault.enc"
            master_password = "TestPassword123!"
            
            # Create vault
            storage1 = StorageManager(str(storage_path))
            storage1.initialize(master_password)
            
            entry1 = PasswordEntry(title="Entry 1", username="user1", password="pass1")
            storage1.add_entry(entry1)
            
            # Open second instance
            storage2 = StorageManager(str(storage_path))
            storage2.initialize(master_password)
            
            # Both should see the same entry
            assert len(storage1.list_entries()) == 1
            assert len(storage2.list_entries()) == 1
            
            # Add entry in second instance
            entry2 = PasswordEntry(title="Entry 2", username="user2", password="pass2")
            storage2.add_entry(entry2)
            
            # First instance needs to reload to see changes
            storage1_new = StorageManager(str(storage_path))
            storage1_new.initialize(master_password)
            assert len(storage1_new.list_entries()) == 2
