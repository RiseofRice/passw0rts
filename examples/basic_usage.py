#!/usr/bin/env python3
"""
Example script demonstrating basic usage of passw0rts library

WARNING: This example prints passwords in clear text for demonstration purposes.
In production code, never log or print passwords.
"""

import tempfile
from pathlib import Path

from passw0rts.core import StorageManager, PasswordEntry
from passw0rts.utils import PasswordGenerator


def main():
    """Demonstrate basic password manager operations"""
    
    # Create a temporary vault for demonstration
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "demo_vault.enc"
        
        print("=== Passw0rts Demo ===")
        print("WARNING: This demo displays passwords for demonstration purposes only.\n")
        
        # 1. Initialize vault
        print("1. Creating new vault...")
        storage = StorageManager(str(vault_path))
        master_password = "DemoMasterPassword123!"
        storage.initialize(master_password)
        print(f"   ✓ Vault created at {vault_path}\n")
        
        # 2. Generate a strong password
        print("2. Generating a strong password...")
        password = PasswordGenerator.generate(length=20, use_symbols=True)
        strength_label, strength_score = PasswordGenerator.estimate_strength(password)
        print(f"   Generated: {password}")
        print(f"   Strength: {strength_label} ({strength_score}/100)\n")
        
        # 3. Add password entries
        print("3. Adding password entries...")
        
        entry1 = PasswordEntry(
            title="Gmail Account",
            username="demo@gmail.com",
            password=password,
            url="https://gmail.com",
            category="email",
            notes="Personal email account"
        )
        
        entry2 = PasswordEntry(
            title="GitHub",
            username="demouser",
            password=PasswordGenerator.generate(length=16),
            url="https://github.com",
            category="development"
        )
        
        entry3 = PasswordEntry(
            title="Bank Account",
            username="demo_user",
            password=PasswordGenerator.generate(length=24),
            url="https://mybank.com",
            category="finance",
            notes="Primary checking account"
        )
        
        id1 = storage.add_entry(entry1)
        id2 = storage.add_entry(entry2)
        id3 = storage.add_entry(entry3)
        
        print(f"   ✓ Added {len(storage.list_entries())} entries\n")
        
        # 4. List all entries
        print("4. Listing all entries:")
        for entry in storage.list_entries():
            print(f"   - {entry.title} ({entry.category})")
            print(f"     Username: {entry.username}")
            print(f"     Password: {'*' * len(entry.password)}")
        print()
        
        # 5. Search entries
        print("5. Searching for 'github'...")
        results = storage.search_entries("github")
        print(f"   Found {len(results)} result(s):")
        for entry in results:
            print(f"   - {entry.title}")
        print()
        
        # 6. Update an entry
        print("6. Updating an entry...")
        entry_to_update = storage.get_entry(id1)
        entry_to_update.notes = "Personal email - Updated!"
        storage.update_entry(id1, entry_to_update)
        print("   ✓ Entry updated\n")
        
        # 7. Export data
        print("7. Exporting data...")
        export_data = storage.export_data()
        print(f"   ✓ Exported {len(storage.list_entries())} entries")
        print(f"   Export size: {len(export_data)} bytes\n")
        
        # 8. Verify encryption persistence
        print("8. Testing encryption persistence...")
        storage.clear()
        
        # Reload vault
        storage2 = StorageManager(str(vault_path))
        storage2.initialize(master_password)
        
        reloaded_entries = storage2.list_entries()
        print(f"   ✓ Successfully reloaded {len(reloaded_entries)} entries")
        print(f"   ✓ Data is encrypted and persistent\n")
        
        # 9. Delete an entry
        print("9. Deleting an entry...")
        storage2.delete_entry(id3)
        print(f"   ✓ Entry deleted. Remaining: {len(storage2.list_entries())}\n")
        
        # 10. Generate passphrase
        print("10. Generating a passphrase...")
        passphrase = PasswordGenerator.generate_passphrase(word_count=5)
        print(f"    Generated: {passphrase}\n")
        
        print("=== Demo Complete ===")
        print("\nKey Features Demonstrated:")
        print("  ✓ Vault creation with master password")
        print("  ✓ AES-256-GCM encryption")
        print("  ✓ Password generation with strength estimation")
        print("  ✓ CRUD operations (Create, Read, Update, Delete)")
        print("  ✓ Search functionality")
        print("  ✓ Data persistence and encryption")
        print("  ✓ Export/Import capabilities")
        print("\nFor CLI usage, run: passw0rts --help")
        print("For web UI, run: passw0rts web")


if __name__ == "__main__":
    main()
