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
from passw0rts.utils import PasswordGenerator, TOTPManager
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
    """Unlock and access the password vault"""
    try:
        ctx.storage = StorageManager(storage_path)
        
        if not ctx.storage.storage_path.exists():
            console.print("[red]Vault not found. Run 'passw0rts init' first.[/red]")
            sys.exit(1)
        
        # Get master password
        master_password = Prompt.ask("[bold]Master password[/bold]", password=True)
        
        try:
            ctx.storage.initialize(master_password)
            # Don't store master password - it's no longer needed after initialization
        except ValueError as e:
            console.print(f"[red]Failed to unlock vault: {e}[/red]")
            sys.exit(1)
        
        # Check for TOTP
        config_dir = ctx.storage.storage_path.parent
        config_file = config_dir / "config.totp"
        
        if config_file.exists():
            secret = config_file.read_text().strip()
            ctx.totp = TOTPManager(secret)
            
            totp_code = Prompt.ask("[bold]TOTP code[/bold]")
            if not ctx.totp.verify_code(totp_code):
                console.print("[red]Invalid TOTP code![/red]")
                sys.exit(1)
        
        ctx.authenticated = True
        ctx.session = SessionManager(timeout_seconds=auto_lock)
        ctx.session.unlock()
        
        console.print("[bold green]✓ Vault unlocked successfully![/bold green]")
        console.print(f"Entries: {len(ctx.storage.list_entries())}")
        console.print(f"Auto-lock: {auto_lock} seconds\n")
        
        # Show help
        console.print("[dim]Use 'passw0rts list' to see all entries[/dim]")
        console.print("[dim]Use 'passw0rts add' to add a new entry[/dim]")
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
        
        console.print("\n[bold green]✓ Vault destroyed successfully![/bold green]")
        console.print("[dim]Run 'passw0rts init' to create a new vault.[/dim]")
        
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
    """Automatically authenticate by prompting for master password"""
    try:
        ctx.storage = StorageManager(storage_path)
        
        if not ctx.storage.storage_path.exists():
            console.print("[red]Vault not found. Run 'passw0rts init' first.[/red]")
            return False
        
        # Get master password
        master_password = Prompt.ask("[bold]Master password[/bold]", password=True)
        
        try:
            ctx.storage.initialize(master_password)
            # Don't store master password - it's no longer needed after initialization
        except ValueError as e:
            console.print(f"[red]Failed to unlock vault: {e}[/red]")
            return False
        
        # Check for TOTP
        config_dir = ctx.storage.storage_path.parent
        config_file = config_dir / "config.totp"
        
        if config_file.exists():
            secret = config_file.read_text().strip()
            ctx.totp = TOTPManager(secret)
            
            totp_code = Prompt.ask("[bold]TOTP code[/bold]")
            if not ctx.totp.verify_code(totp_code):
                console.print("[red]Invalid TOTP code![/red]")
                return False
        
        ctx.authenticated = True
        ctx.session = SessionManager(timeout_seconds=300)
        ctx.session.unlock()
        
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
