"""
Unit tests for the edit functionality at the storage level
"""
import tempfile
import shutil
from pathlib import Path
from passw0rts.core import StorageManager, PasswordEntry


class TestEditStorage:
    """Test cases for editing password entries"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp(prefix="passw0rts_test_")
        self.vault_path = str(Path(self.test_dir) / "vault.enc")
        self.master_password = "TestMaster123!"
        self.storage = StorageManager(self.vault_path)
        self.storage.initialize(self.master_password)

    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_update_entry_title(self):
        """Test updating an entry's title"""
        # Create entry
        entry = PasswordEntry(
            title="Original Title",
            username="test@example.com",
            password="password123",
            url="https://example.com",
            category="test",
            notes="Test notes"
        )
        entry_id = self.storage.add_entry(entry)

        # Update title
        updated_entry = PasswordEntry(
            id=entry_id,
            title="Updated Title",
            username=entry.username,
            password=entry.password,
            url=entry.url,
            category=entry.category,
            notes=entry.notes,
            created_at=entry.created_at
        )
        self.storage.update_entry(entry_id, updated_entry)

        # Verify
        retrieved = self.storage.get_entry(entry_id)
        assert retrieved.title == "Updated Title"
        assert retrieved.username == entry.username
        assert retrieved.created_at == entry.created_at
        assert retrieved.updated_at > entry.updated_at

    def test_update_entry_password(self):
        """Test updating an entry's password"""
        entry = PasswordEntry(
            title="Test Entry",
            username="test@example.com",
            password="oldpassword",
            category="test"
        )
        entry_id = self.storage.add_entry(entry)

        # Update password
        updated_entry = PasswordEntry(
            id=entry_id,
            title=entry.title,
            username=entry.username,
            password="newpassword123",
            category=entry.category,
            created_at=entry.created_at
        )
        self.storage.update_entry(entry_id, updated_entry)

        # Verify
        retrieved = self.storage.get_entry(entry_id)
        assert retrieved.password == "newpassword123"

    def test_update_entry_preserves_id(self):
        """Test that updating preserves the entry ID"""
        entry = PasswordEntry(
            title="Test Entry",
            password="password123"
        )
        entry_id = self.storage.add_entry(entry)

        # Update multiple fields
        updated_entry = PasswordEntry(
            id=entry_id,
            title="Completely Different",
            username="new@example.com",
            password="newpass",
            url="https://new.com",
            category="new",
            notes="New notes",
            created_at=entry.created_at
        )
        self.storage.update_entry(entry_id, updated_entry)

        # Verify ID is preserved
        retrieved = self.storage.get_entry(entry_id)
        assert retrieved.id == entry_id
        assert retrieved.title == "Completely Different"

    def test_update_entry_preserves_created_at(self):
        """Test that updating preserves the created_at timestamp"""
        import time

        entry = PasswordEntry(
            title="Test Entry",
            password="password123"
        )
        entry_id = self.storage.add_entry(entry)
        original_created_at = entry.created_at

        # Wait a moment to ensure timestamps would differ
        time.sleep(0.01)

        # Update entry
        updated_entry = PasswordEntry(
            id=entry_id,
            title="Updated Entry",
            password="newpass",
            created_at=original_created_at
        )
        self.storage.update_entry(entry_id, updated_entry)

        # Verify created_at is preserved but updated_at changed
        retrieved = self.storage.get_entry(entry_id)
        assert retrieved.created_at == original_created_at
        assert retrieved.updated_at > original_created_at

    def test_update_nonexistent_entry_fails(self):
        """Test that updating a non-existent entry raises an error"""
        import pytest

        entry = PasswordEntry(
            title="Test Entry",
            password="password123"
        )

        with pytest.raises(ValueError, match="not found"):
            self.storage.update_entry("nonexistent-id", entry)

    def test_update_entry_persists_across_reload(self):
        """Test that updates persist when vault is reloaded"""
        # Create entry
        entry = PasswordEntry(
            title="Original",
            password="password123"
        )
        entry_id = self.storage.add_entry(entry)

        # Update entry
        updated_entry = PasswordEntry(
            id=entry_id,
            title="Updated",
            password="newpassword",
            created_at=entry.created_at
        )
        self.storage.update_entry(entry_id, updated_entry)

        # Reload storage from disk
        storage2 = StorageManager(self.vault_path)
        storage2.initialize(self.master_password)

        # Verify update persisted
        retrieved = storage2.get_entry(entry_id)
        assert retrieved.title == "Updated"
        assert retrieved.password == "newpassword"

    def test_update_entry_all_fields(self):
        """Test updating all fields of an entry"""
        entry = PasswordEntry(
            title="Original Title",
            username="old@example.com",
            password="oldpass",
            url="https://old.com",
            category="old",
            notes="Old notes",
            tags=["old", "test"]
        )
        entry_id = self.storage.add_entry(entry)

        # Update all fields
        updated_entry = PasswordEntry(
            id=entry_id,
            title="New Title",
            username="new@example.com",
            password="newpass",
            url="https://new.com",
            category="new",
            notes="New notes",
            tags=["new", "updated"],
            created_at=entry.created_at
        )
        self.storage.update_entry(entry_id, updated_entry)

        # Verify all fields updated
        retrieved = self.storage.get_entry(entry_id)
        assert retrieved.title == "New Title"
        assert retrieved.username == "new@example.com"
        assert retrieved.password == "newpass"
        assert retrieved.url == "https://new.com"
        assert retrieved.category == "new"
        assert retrieved.notes == "New notes"
        assert retrieved.tags == ["new", "updated"]

    def test_update_entry_optional_fields_to_none(self):
        """Test updating optional fields to None"""
        entry = PasswordEntry(
            title="Test Entry",
            username="test@example.com",
            password="password123",
            url="https://example.com",
            notes="Some notes"
        )
        entry_id = self.storage.add_entry(entry)

        # Update with None values
        updated_entry = PasswordEntry(
            id=entry_id,
            title="Test Entry",
            username=None,
            password="password123",
            url=None,
            notes=None,
            created_at=entry.created_at
        )
        self.storage.update_entry(entry_id, updated_entry)

        # Verify fields are None
        retrieved = self.storage.get_entry(entry_id)
        assert retrieved.username is None
        assert retrieved.url is None
        assert retrieved.notes is None
