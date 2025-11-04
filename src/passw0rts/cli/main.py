"""
Main CLI interface for passw0rts password manager
"""

import click
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from passw0rts.core import StorageManager, PasswordEntry
from passw0rts.utils import PasswordGenerator, TOTPManager, SessionPersistence, USBKeyManager, USBDevice
from passw0rts.utils.session_manager import SessionManager
from .clipboard_handler import ClipboardHandler

console = Console()

# Global context for the session
class AppContext:
    def __init__(self):
        self.storage: StorageManager = None
        self.session: SessionManager = None
        self.totp: TOTPManager = None
        self.authenticated = False

ctx = AppContext()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    Passw0rts - A secure cross-platform password manager
    
    Manage your passwords securely with AES-256 encryption,
    TOTP 2FA, and auto-lock functionality.
    """
    pass


@main.command()
@click.option('--storage-path', type=click.Path(), help='Custom storage path')
@click.option('--auto-lock', type=int, default=300, help='Auto-lock timeout in seconds (default: 300)')
def init(storage_path, auto_lock):
    """Initialize a new password vault"""
    try:
        storage = StorageManager(storage_path)
        
        if storage.storage_path.exists():
            console.print("[yellow]Vault already exists. Use 'unlock' to access it.[/yellow]")
            return
        
        console.print(Panel.fit(
            "[bold cyan]Welcome to Passw0rts![/bold cyan]\n\n"
            "Let's set up your secure password vault.",
            title="🔐 Initialization"
        ))
        
        # Get master password
        master_password = Prompt.ask("\n[bold]Enter master password[/bold]", password=True)
        master_password_confirm = Prompt.ask("[bold]Confirm master password[/bold]", password=True)
        
        if master_password != master_password_confirm:
            console.print("[red]Passwords do not match![/red]")
            sys.exit(1)
        
        # Check password strength
        label, score = PasswordGenerator.estimate_strength(master_password)
        console.print(f"\nPassword strength: [bold]{label}[/bold] ({score}/100)")
        
        if score < 60:
            if not Confirm.ask("[yellow]Password is weak. Continue anyway?[/yellow]"):
                sys.exit(1)
        
        # Initialize vault
        storage.initialize(master_password)
        
        # Set up TOTP (optional)
        if Confirm.ask("\n[bold]Enable TOTP 2FA (recommended)?[/bold]", default=True):
            totp = TOTPManager()
            secret = totp.get_secret()
            
            console.print(f"\n[bold green]TOTP Secret:[/bold green] {secret}")
            console.print("\n[bold]Scan this QR code with your authenticator app:[/bold]")
            
            # Display QR code in terminal
            try:
                import qrcode
                qr = qrcode.QRCode()
                qr.add_data(totp.get_provisioning_uri('passw0rts'))
                qr.make()
                console.print()
                qr.print_ascii(invert=True)
                console.print()
            except Exception as e:
                console.print(f"[yellow]Could not display QR code: {e}[/yellow]")
                console.print(f"[dim]Manual setup URI: {totp.get_provisioning_uri('passw0rts')}[/dim]")
            
            # Save TOTP secret to a config file
            config_dir = storage.storage_path.parent
            config_file = config_dir / "config.totp"
            config_file.write_text(secret)
            console.print(f"[green]✓[/green] TOTP secret saved to {config_file}")
        
        # Set up USB security key (optional)
        if Confirm.ask("\n[bold]Register a USB security key (YubiKey or other)?[/bold]", default=False):
            config_dir = storage.storage_path.parent
            usb_manager = USBKeyManager(str(config_dir / "config.usbkey"))
            
            console.print("\n[cyan]Detecting USB devices...[/cyan]")
            devices = usb_manager.list_available_devices()
            
            if not devices:
                console.print("[yellow]No USB devices detected. Make sure your USB key is plugged in.[/yellow]")
            else:
                console.print(f"\n[bold]Found {len(devices)} USB device(s):[/bold]")
                
                for i, device in enumerate(devices, 1):
                    console.print(f"  {i}. {device}")
                
                choice = Prompt.ask(f"\n[bold]Select device (1-{len(devices)})[/bold]", default="1")
                
                try:
                    device_idx = int(choice) - 1
                    if 0 <= device_idx < len(devices):
                        selected_device = devices[device_idx]
                        usb_manager.register_device(selected_device, master_password)
                        console.print(f"\n[green]✓[/green] USB key registered: {selected_device}")
                        console.print("[dim]Note: With USB key registered, master password and TOTP become optional when the key is connected.[/dim]")
                    else:
                        console.print("[yellow]Invalid selection. USB key not registered.[/yellow]")
                except ValueError:
                    console.print("[yellow]Invalid input. USB key not registered.[/yellow]")
        
        console.print(f"\n[bold green]✓ Vault initialized successfully![/bold green]")
        console.print(f"Storage: {storage.storage_path}")
        console.print(f"Auto-lock: {auto_lock} seconds")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option('--storage-path', type=click.Path(), help='Custom storage path')
@click.option('--auto-lock', type=int, default=300, help='Auto-lock timeout in seconds')
def unlock(storage_path, auto_lock):
    """Unlock and access the password vault (optional - commands auto-authenticate)"""
    try:
        ctx.storage = StorageManager(storage_path)
        
        if not ctx.storage.storage_path.exists():
            console.print("[red]Vault not found. Run 'passw0rts init' first.[/red]")
            sys.exit(1)
        
        # Initialize session persistence
        session_persist = SessionPersistence()
        
        # Check for USB key
        config_dir = ctx.storage.storage_path.parent
        usb_key_file = config_dir / "config.usbkey"
        usb_manager = USBKeyManager(str(usb_key_file))
        has_usb_key = usb_manager.is_device_registered()
        usb_key_connected = has_usb_key and usb_manager.is_registered_device_connected()
        
        master_password = None
        
        # USB Key Authentication Flow
        if usb_key_connected:
            console.print("[green]🔑 USB security key detected![/green]")
            
            # Offer USB-only authentication (default=False for security)
            use_usb_only = Confirm.ask("[bold]Unlock with USB key only (skip password/TOTP)?[/bold]", default=False)
            
            if use_usb_only:
                # Authenticate with USB key only
                derived_key = usb_manager.authenticate_with_device_only()
                
                if derived_key:
                    try:
                        ctx.storage.initialize(derived_key)
                        master_password = derived_key
                        console.print("[green]✓ Authenticated with USB key[/green]")
                    except ValueError:
                        console.print("[yellow]USB key authentication failed. Falling back to password authentication.[/yellow]")
        
        # Get master password if not authenticated via USB
        if master_password is None:
            master_password = Prompt.ask("[bold]Master password[/bold]" + (" (optional with USB key)" if usb_key_connected else ""), password=True)
            
            try:
                ctx.storage.initialize(master_password)
            except ValueError as e:
                console.print(f"[red]Failed to unlock vault: {e}[/red]")
                sys.exit(1)
        
        # Check for TOTP (optional if USB key is connected)
        config_file = config_dir / "config.totp"
        totp_verified_at = None
        
        if config_file.exists():
            # If USB key is connected and verified, make TOTP optional
            skip_totp = False
            if usb_key_connected and usb_manager.verify_device_authentication(master_password):
                console.print("[green]✓ USB key verified. TOTP not required.[/green]")
                skip_totp = True
            
            if not skip_totp:
                secret = config_file.read_text().strip()
                ctx.totp = TOTPManager(secret)
                
                totp_code = Prompt.ask("[bold]TOTP code[/bold]")
                if not ctx.totp.verify_code(totp_code):
                    console.print("[red]Invalid TOTP code![/red]")
                    sys.exit(1)
                
                import time
                totp_verified_at = time.time()
        
        ctx.authenticated = True
        ctx.session = SessionManager(timeout_seconds=auto_lock)
        ctx.session.unlock()
        
        # Save session for future commands
        session_persist.save_session(
            master_password=master_password,
            totp_verified_at=totp_verified_at,
            auto_lock_timeout=auto_lock,
            storage_path=str(ctx.storage.storage_path) if storage_path else None
        )
        
        console.print("[bold green]✓ Vault unlocked successfully![/bold green]")
        console.print(f"Entries: {len(ctx.storage.list_entries())}")
        console.print(f"Auto-lock: {auto_lock} seconds")
        console.print(f"Session saved: Commands will not require re-authentication until lock\n")
        
        # Show help
        console.print("[dim]Use 'passw0rts list' to see all entries[/dim]")
        console.print("[dim]Use 'passw0rts add' to add a new entry[/dim]")
        console.print("[dim]Use 'passw0rts lock' to manually lock the vault[/dim]")
        console.print("[dim]Use 'passw0rts --help' for all commands[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
def add():
    """Add a new password entry"""
    if not _check_authenticated():
        return
    
    ctx.session.update_activity()
    
    console.print(Panel.fit("[bold cyan]Add New Password Entry[/bold cyan]", title="➕"))
    
    # Collect information
    title = Prompt.ask("\n[bold]Title[/bold]")
    username = Prompt.ask("[bold]Username/Email[/bold] (optional)", default="")
    
    # Password options
    if Confirm.ask("[bold]Generate password?[/bold]", default=True):
        length = int(Prompt.ask("Length", default="16"))
        use_symbols = Confirm.ask("Include symbols?", default=True)
        password = PasswordGenerator.generate(length=length, use_symbols=use_symbols)
        console.print(f"\n[bold green]Generated:[/bold green] {password}")
        label, score = PasswordGenerator.estimate_strength(password)
        console.print(f"Strength: [bold]{label}[/bold] ({score}/100)\n")
    else:
        password = Prompt.ask("[bold]Password[/bold]", password=True)
    
    url = Prompt.ask("[bold]URL[/bold] (optional)", default="")
    category = Prompt.ask("[bold]Category[/bold]", default="general")
    notes = Prompt.ask("[bold]Notes[/bold] (optional)", default="")
    
    # Create entry
    entry = PasswordEntry(
        title=title,
        username=username or None,
        password=password,
        url=url or None,
        category=category,
        notes=notes or None
    )
    
    entry_id = ctx.storage.add_entry(entry)
    console.print(f"\n[bold green]✓ Entry added successfully![/bold green]")
    console.print(f"ID: {entry_id}")


@main.command()
@click.argument('query', required=False)
def list(query):
    """List all password entries (or search with query)"""
    if not _check_authenticated():
        return
    
    ctx.session.update_activity()
    
    if query:
        entries = ctx.storage.search_entries(query)
        title = f"🔍 Search Results for '{query}'"
    else:
        entries = ctx.storage.list_entries()
        title = "📋 All Entries"
    
    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        return
    
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Title", style="cyan")
    table.add_column("Username", style="green")
    table.add_column("Category", style="magenta")
    table.add_column("URL", style="blue", overflow="fold")
    
    # Sort by title
    entries.sort(key=lambda e: e.title.lower())
    
    for entry in entries:
        table.add_row(
            entry.id[:8],
            entry.title,
            entry.username or "",
            entry.category or "",
            entry.url or ""
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(entries)} entries[/dim]")


@main.command()
@click.argument('entry_id')
def show(entry_id):
    """Show details of a password entry"""
    if not _check_authenticated():
        return
    
    ctx.session.update_activity()
    
    # Find entry by partial ID
    entry = _find_entry_by_id(entry_id)
    if not entry:
        return
    
    # Create detailed view
    console.print(Panel.fit(
        f"[bold cyan]{entry.title}[/bold cyan]\n\n"
        f"[bold]ID:[/bold] {entry.id}\n"
        f"[bold]Username:[/bold] {entry.username or 'N/A'}\n"
        f"[bold]Password:[/bold] {'*' * len(entry.password)}\n"
        f"[bold]URL:[/bold] {entry.url or 'N/A'}\n"
        f"[bold]Category:[/bold] {entry.category or 'N/A'}\n"
        f"[bold]Notes:[/bold] {entry.notes or 'N/A'}\n\n"
        f"[dim]Created: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n"
        f"[dim]Updated: {entry.updated_at.strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        title="📄 Entry Details"
    ))
    
    # Offer to copy password
    if Confirm.ask("\n[bold]Copy password to clipboard?[/bold]"):
        ClipboardHandler.copy_with_timeout(entry.password, timeout=30)
        console.print("[green]✓ Password copied (will clear in 30 seconds)[/green]")


@main.command()
@click.argument('entry_id')
def edit(entry_id):
    """Edit an existing password entry"""
    if not _check_authenticated():
        return
    
    ctx.session.update_activity()
    
    entry = _find_entry_by_id(entry_id)
    if not entry:
        return
    
    console.print(Panel.fit(
        f"[bold cyan]Edit Password Entry[/bold cyan]\n\n"
        f"[dim]Press Enter to keep current value[/dim]",
        title="✏️  Edit"
    ))
    
    # Show current entry details
    console.print(f"\n[bold]Current entry: {entry.title}[/bold]")
    
    # Collect new information (with defaults from current entry)
    title = Prompt.ask("[bold]Title[/bold]", default=entry.title)
    username = Prompt.ask("[bold]Username/Email[/bold]", default=entry.username or "")
    
    # Password options
    if Confirm.ask("[bold]Change password?[/bold]", default=False):
        if Confirm.ask("[bold]Generate new password?[/bold]", default=True):
            length = int(Prompt.ask("Length", default="16"))
            use_symbols = Confirm.ask("Include symbols?", default=True)
            password = PasswordGenerator.generate(length=length, use_symbols=use_symbols)
            console.print(f"\n[bold green]Generated:[/bold green] {password}")
            label, score = PasswordGenerator.estimate_strength(password)
            console.print(f"Strength: [bold]{label}[/bold] ({score}/100)\n")
        else:
            password = Prompt.ask("[bold]New password[/bold]", password=True)
    else:
        password = entry.password
    
    url = Prompt.ask("[bold]URL[/bold]", default=entry.url or "")
    category = Prompt.ask("[bold]Category[/bold]", default=entry.category or "general")
    notes = Prompt.ask("[bold]Notes[/bold]", default=entry.notes or "")
    
    # Create updated entry
    # Note: updated_at will be automatically set by storage.update_entry()
    updated_entry = PasswordEntry(
        id=entry.id,  # Keep the same ID
        title=title,
        username=username or None,
        password=password,
        url=url or None,
        category=category,
        notes=notes or None,
        created_at=entry.created_at  # Preserve creation time
    )
    
    ctx.storage.update_entry(entry.id, updated_entry)
    console.print(f"\n[bold green]✓ Entry updated successfully![/bold green]")


@main.command()
@click.argument('entry_id')
def delete(entry_id):
    """Delete a password entry"""
    if not _check_authenticated():
        return
    
    ctx.session.update_activity()
    
    entry = _find_entry_by_id(entry_id)
    if not entry:
        return
    
    if Confirm.ask(f"[bold red]Delete '{entry.title}'?[/bold red]"):
        ctx.storage.delete_entry(entry.id)
        console.print("[green]✓ Entry deleted[/green]")


@main.command()
@click.option('--length', type=int, default=16, help='Password length')
@click.option('--no-symbols', is_flag=True, help='Exclude symbols')
@click.option('--no-ambiguous', is_flag=True, help='Exclude ambiguous characters')
@click.option('--count', type=int, default=1, help='Number of passwords to generate')
def generate(length, no_symbols, no_ambiguous, count):
    """Generate secure random passwords"""
    console.print(Panel.fit("[bold cyan]Password Generator[/bold cyan]", title="🎲"))
    
    for i in range(count):
        password = PasswordGenerator.generate(
            length=length,
            use_symbols=not no_symbols,
            exclude_ambiguous=no_ambiguous
        )
        label, score = PasswordGenerator.estimate_strength(password)
        
        console.print(f"\n[bold green]{password}[/bold green]")
        console.print(f"Strength: [bold]{label}[/bold] ({score}/100)")


@main.command()
@click.option('--output', type=click.Path(), help='Output file path')
def export(output):
    """Export all entries to JSON"""
    if not _check_authenticated():
        return
    
    ctx.session.update_activity()
    
    if not output:
        output = f"passw0rts_export_{ctx.storage.storage_path.stem}.json"
    
    data = ctx.storage.export_data()
    Path(output).write_text(data)
    
    console.print(f"[green]✓ Exported {len(ctx.storage.list_entries())} entries to {output}[/green]")
    console.print("[yellow]⚠ Warning: Exported file is not encrypted![/yellow]")


@main.command()
@click.argument('input_file', type=click.Path(exists=True))
def import_entries(input_file):
    """Import entries from JSON file"""
    if not _check_authenticated():
        return
    
    ctx.session.update_activity()
    
    data = Path(input_file).read_text()
    ctx.storage.import_data(data)
    
    console.print(f"[green]✓ Entries imported successfully[/green]")
    console.print(f"Total entries: {len(ctx.storage.list_entries())}")


@main.command()
@click.option('--host', default='127.0.0.1', help='Host address')
@click.option('--port', type=int, default=5000, help='Port number')
@click.option('--storage-path', type=click.Path(), help='Custom storage path')
def web(host, port, storage_path):
    """Start the web UI server"""
    try:
        from passw0rts.web import create_app
        
        console.print(Panel.fit(
            f"[bold cyan]Starting Passw0rts Web UI[/bold cyan]\n\n"
            f"[bold]URL:[/bold] http://{host}:{port}\n"
            f"[bold]Storage:[/bold] {storage_path or 'default (~/.passw0rts/vault.enc)'}\n\n"
            f"[dim]Press Ctrl+C to stop the server[/dim]",
            title="🌐 Web Server"
        ))
        
        app = create_app(storage_path=storage_path)
        app.run(host=host, port=port, debug=False)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option('--storage-path', type=click.Path(), help='Custom storage path')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def destroy(storage_path, force):
    """Permanently delete the password vault"""
    try:
        storage = StorageManager(storage_path)
        
        if not storage.storage_path.exists():
            console.print("[yellow]Vault not found. Nothing to delete.[/yellow]")
            return
        
        console.print(Panel.fit(
            "[bold red]⚠️  WARNING ⚠️[/bold red]\n\n"
            "This will permanently delete your password vault and all stored passwords.\n"
            "[bold]This action cannot be undone![/bold]",
            title="🗑️  Destroy Vault"
        ))
        
        console.print(f"\n[bold]Vault location:[/bold] {storage.storage_path}")
        
        # Confirm deletion
        if not force:
            confirm_text = Prompt.ask(
                "\n[bold red]Type 'DELETE' to confirm destruction[/bold red]"
            )
            if confirm_text != "DELETE":
                console.print("[yellow]Destruction cancelled.[/yellow]")
                return
        
        # Delete vault file
        storage.storage_path.unlink()
        console.print(f"[green]✓[/green] Vault file deleted: {storage.storage_path}")
        
        # Delete TOTP config if it exists
        config_dir = storage.storage_path.parent
        config_file = config_dir / "config.totp"
        if config_file.exists():
            config_file.unlink()
            console.print(f"[green]✓[/green] TOTP config deleted: {config_file}")
        
        # Delete USB key config if it exists
        usb_key_file = config_dir / "config.usbkey"
        if usb_key_file.exists():
            usb_key_file.unlink()
            console.print(f"[green]✓[/green] USB key config deleted: {usb_key_file}")
        
        # Clear session
        session_persist = SessionPersistence()
        if session_persist.session_exists():
            session_persist.clear_session()
            console.print(f"[green]✓[/green] Session cleared")
        
        console.print("\n[bold green]✓ Vault destroyed successfully![/bold green]")
        console.print("[dim]Run 'passw0rts init' to create a new vault.[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
def lock():
    """Lock the vault and clear session"""
    try:
        session_persist = SessionPersistence()
        
        if session_persist.session_exists():
            session_persist.clear_session()
            console.print("[bold green]✓ Vault locked and session cleared![/bold green]")
            console.print("[dim]You will need to re-authenticate on the next command.[/dim]")
        else:
            console.print("[yellow]No active session found.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command(name='add-key')
@click.option('--storage-path', type=click.Path(), help='Custom storage path')
def add_key(storage_path):
    """Register a USB security key to an existing vault"""
    try:
        # Verify vault exists
        storage = StorageManager(storage_path)
        
        if not storage.storage_path.exists():
            console.print("[red]Vault not found. Run 'passw0rts init' first.[/red]")
            sys.exit(1)
        
        console.print(Panel.fit(
            "[bold cyan]Register USB Security Key[/bold cyan]\n\n"
            "This will register a USB security key (YubiKey or other) to your vault.\n"
            "Once registered, you can unlock the vault using only the USB key.",
            title="🔑 USB Key Registration"
        ))
        
        # Authenticate first
        master_password = Prompt.ask("\n[bold]Master password[/bold]", password=True)
        
        try:
            storage.initialize(master_password)
        except ValueError as e:
            console.print(f"[red]Failed to unlock vault: {e}[/red]")
            sys.exit(1)
        
        # Check for TOTP
        config_dir = storage.storage_path.parent
        config_file = config_dir / "config.totp"
        if config_file.exists():
            secret = config_file.read_text().strip()
            totp = TOTPManager(secret)
            
            totp_code = Prompt.ask("[bold]TOTP code[/bold]")
            if not totp.verify_code(totp_code):
                console.print("[red]Invalid TOTP code![/red]")
                sys.exit(1)
        
        # Set up USB key
        usb_manager = USBKeyManager(str(config_dir / "config.usbkey"))
        
        # Check if key already registered
        if usb_manager.is_device_registered():
            current_device = usb_manager.get_registered_device()
            console.print(f"\n[yellow]A USB key is already registered:[/yellow]")
            console.print(f"  {current_device}")
            
            if not Confirm.ask("\n[bold]Replace with a new key?[/bold]"):
                console.print("[yellow]Operation cancelled.[/yellow]")
                return
        
        console.print("\n[cyan]Detecting USB devices...[/cyan]")
        devices = usb_manager.list_available_devices()
        
        if not devices:
            console.print("[yellow]No USB devices detected. Make sure your USB key is plugged in.[/yellow]")
            sys.exit(1)
        
        console.print(f"\n[bold]Found {len(devices)} USB device(s):[/bold]")
        
        for i, device in enumerate(devices, 1):
            console.print(f"  {i}. {device}")
        
        choice = Prompt.ask(f"\n[bold]Select device (1-{len(devices)})[/bold]", default="1")
        
        try:
            device_idx = int(choice) - 1
            if 0 <= device_idx < len(devices):
                selected_device = devices[device_idx]
                usb_manager.register_device(selected_device, master_password)
                console.print(f"\n[bold green]✓ USB key registered successfully![/bold green]")
                console.print(f"Device: {selected_device}")
                console.print("\n[dim]Note: With USB key registered, master password and TOTP become optional when the key is connected.[/dim]")
            else:
                console.print("[red]Invalid selection.[/red]")
                sys.exit(1)
        except ValueError:
            console.print("[red]Invalid input.[/red]")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command(name='remove-key')
@click.option('--storage-path', type=click.Path(), help='Custom storage path')
def remove_key(storage_path):
    """Remove registered USB security key"""
    try:
        # Verify vault exists
        storage = StorageManager(storage_path)
        
        if not storage.storage_path.exists():
            console.print("[red]Vault not found. Run 'passw0rts init' first.[/red]")
            sys.exit(1)
        
        config_dir = storage.storage_path.parent
        usb_manager = USBKeyManager(str(config_dir / "config.usbkey"))
        
        if not usb_manager.is_device_registered():
            console.print("[yellow]No USB key is currently registered.[/yellow]")
            return
        
        current_device = usb_manager.get_registered_device()
        console.print(f"\n[bold]Currently registered USB key:[/bold]")
        console.print(f"  {current_device}")
        
        # Authenticate first
        master_password = Prompt.ask("\n[bold]Master password[/bold]", password=True)
        
        try:
            storage.initialize(master_password)
        except ValueError as e:
            console.print(f"[red]Failed to unlock vault: {e}[/red]")
            sys.exit(1)
        
        # Check for TOTP
        config_file = config_dir / "config.totp"
        if config_file.exists():
            secret = config_file.read_text().strip()
            totp = TOTPManager(secret)
            
            totp_code = Prompt.ask("[bold]TOTP code[/bold]")
            if not totp.verify_code(totp_code):
                console.print("[red]Invalid TOTP code![/red]")
                sys.exit(1)
        
        if Confirm.ask("\n[bold red]Remove this USB key?[/bold red]"):
            usb_manager.unregister_device()
            console.print("[bold green]✓ USB key removed successfully![/bold green]")
        else:
            console.print("[yellow]Operation cancelled.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def _check_authenticated():
    """Check if user is authenticated, prompt for authentication if not"""
    if not ctx.authenticated or ctx.storage is None:
        # Auto-authenticate
        if not _auto_authenticate():
            return False
    
    if ctx.session and ctx.session.is_locked:
        console.print("[red]Session locked. Re-authenticating...[/red]")
        if not _auto_authenticate():
            return False
    
    return True


def _auto_authenticate(storage_path=None):
    """Automatically authenticate using persistent session or by prompting for credentials"""
    try:
        ctx.storage = StorageManager(storage_path)
        
        if not ctx.storage.storage_path.exists():
            console.print("[red]Vault not found. Run 'passw0rts init' first.[/red]")
            return False
        
        # Initialize session persistence
        session_persist = SessionPersistence()
        
        # Check for configs
        config_dir = ctx.storage.storage_path.parent
        config_file = config_dir / "config.totp"
        has_totp = config_file.exists()
        
        # Check for USB key
        usb_key_file = config_dir / "config.usbkey"
        usb_manager = USBKeyManager(str(usb_key_file))
        has_usb_key = usb_manager.is_device_registered()
        usb_key_connected = has_usb_key and usb_manager.is_registered_device_connected()
        
        # USB Key Authentication Flow: If USB key is connected, make password/TOTP optional
        if usb_key_connected:
            console.print("[green]🔑 USB security key detected![/green]")
            
            # Offer USB-only authentication (default=False for security)
            use_usb_only = Confirm.ask("[bold]Unlock with USB key only (skip password/TOTP)?[/bold]", default=False)
            
            if use_usb_only:
                # Authenticate with USB key only
                derived_key = usb_manager.authenticate_with_device_only()
                
                if derived_key:
                    try:
                        # Use derived key as master password
                        ctx.storage.initialize(derived_key)
                        
                        ctx.authenticated = True
                        ctx.session = SessionManager(timeout_seconds=300)
                        ctx.session.unlock()
                        
                        console.print("[green]✓ Authenticated with USB key[/green]")
                        return True
                    except ValueError:
                        console.print("[yellow]USB key authentication failed. Falling back to password authentication.[/yellow]")
                else:
                    console.print("[yellow]Could not authenticate with USB key. Falling back to password authentication.[/yellow]")
        
        # Standard authentication flow (with or without USB key verification)
        # Try to load existing session
        if session_persist.session_exists():
            # Prompt for master password to unlock session
            master_password = Prompt.ask("[bold]Master password[/bold]" + (" (optional with USB key)" if usb_key_connected else ""), password=True)
            session_data = session_persist.load_session(master_password)
            
            if session_data:
                # Session is valid, check if we need TOTP
                needs_totp = has_totp and not session_persist.is_totp_valid(session_data)
                
                # If USB key is connected and registered with this password, skip TOTP
                if usb_key_connected and needs_totp:
                    if usb_manager.verify_device_authentication(master_password):
                        console.print("[green]✓ USB key verified. TOTP not required.[/green]")
                        needs_totp = False
                
                # Initialize storage with master password
                try:
                    ctx.storage.initialize(master_password)
                except ValueError as e:
                    console.print(f"[red]Failed to unlock vault: {e}[/red]")
                    session_persist.clear_session()
                    return False
                
                # Check TOTP if needed
                if needs_totp:
                    secret = config_file.read_text().strip()
                    ctx.totp = TOTPManager(secret)
                    
                    totp_code = Prompt.ask("[bold]TOTP code[/bold] (required once per day)")
                    if not ctx.totp.verify_code(totp_code):
                        console.print("[red]Invalid TOTP code![/red]")
                        return False
                    
                    # Update session with new TOTP verification time
                    import time
                    session_persist.save_session(
                        master_password=master_password,
                        totp_verified_at=time.time(),
                        auto_lock_timeout=session_data.get('auto_lock_timeout', 300),
                        storage_path=str(ctx.storage.storage_path) if storage_path else None
                    )
                elif has_totp:
                    # Load TOTP manager but don't verify (already verified today)
                    secret = config_file.read_text().strip()
                    ctx.totp = TOTPManager(secret)
                else:
                    # Update session activity
                    session_persist.update_activity(master_password)
                
                ctx.authenticated = True
                ctx.session = SessionManager(timeout_seconds=session_data.get('auto_lock_timeout', 300))
                ctx.session.unlock()
                
                return True
        
        # No valid session, do full authentication
        master_password = Prompt.ask("[bold]Master password[/bold]" + (" (optional with USB key)" if usb_key_connected else ""), password=True)
        
        try:
            ctx.storage.initialize(master_password)
        except ValueError as e:
            console.print(f"[red]Failed to unlock vault: {e}[/red]")
            return False
        
        # Check for TOTP (optional if USB key is connected)
        totp_verified_at = None
        if has_totp:
            # If USB key is connected and verified, make TOTP optional
            skip_totp = False
            if usb_key_connected:
                if usb_manager.verify_device_authentication(master_password):
                    console.print("[green]✓ USB key verified. TOTP not required.[/green]")
                    skip_totp = True
            
            if not skip_totp:
                secret = config_file.read_text().strip()
                ctx.totp = TOTPManager(secret)
                
                totp_code = Prompt.ask("[bold]TOTP code[/bold]")
                if not ctx.totp.verify_code(totp_code):
                    console.print("[red]Invalid TOTP code![/red]")
                    return False
                
                import time
                totp_verified_at = time.time()
        
        ctx.authenticated = True
        ctx.session = SessionManager(timeout_seconds=300)
        ctx.session.unlock()
        
        # Save session for future use
        session_persist.save_session(
            master_password=master_password,
            totp_verified_at=totp_verified_at,
            auto_lock_timeout=300,
            storage_path=str(ctx.storage.storage_path) if storage_path else None
        )
        
        return True
        
    except Exception as e:
        console.print(f"[red]Authentication error: {e}[/red]")
        return False


def _find_entry_by_id(entry_id: str):
    """Find entry by full or partial ID"""
    entries = ctx.storage.list_entries()
    
    # Try exact match first
    entry = ctx.storage.get_entry(entry_id)
    if entry:
        return entry
    
    # Try partial match
    matches = [e for e in entries if e.id.startswith(entry_id)]
    
    if not matches:
        console.print(f"[red]Entry not found: {entry_id}[/red]")
        return None
    
    if len(matches) > 1:
        console.print(f"[yellow]Multiple matches found. Please be more specific:[/yellow]")
        for e in matches:
            console.print(f"  {e.id[:8]} - {e.title}")
        return None
    
    return matches[0]


if __name__ == '__main__':
    main()
