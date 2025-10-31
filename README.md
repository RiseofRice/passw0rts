# 🔐 Passw0rts

A secure, cross-platform password manager with CLI and web UI capabilities. Built with strong encryption (AES-256-GCM), TOTP 2FA support, and modern security practices.

## Features

### Security
- **AES-256-GCM Encryption**: Military-grade encryption for your passwords
- **PBKDF2 Key Derivation**: 600,000 iterations (OWASP recommended)
- **TOTP 2FA**: Optional two-factor authentication support
- **Auto-lock**: Automatic session locking after inactivity
- **Clipboard Timeout**: Passwords automatically cleared from clipboard
- **Secure Storage**: Encrypted vault with restrictive file permissions

### Functionality
- **CLI Interface**: Rich terminal interface with color support
- **Web UI**: Modern, responsive dashboard with dark/light themes
- **Password Generator**: Generate strong passwords with customizable options
- **Password Strength Estimation**: Real-time strength analysis
- **Search**: Fast search across all fields
- **Categories & Tags**: Organize passwords efficiently
- **Import/Export**: JSON-based backup and restore
- **Cross-Platform**: Works on macOS, Windows, and Linux

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/RiseofRice/passw0rts.git
cd passw0rts

# Install dependencies
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Requirements
- Python 3.8+
- pip

## Quick Start

### Initialize Vault

```bash
# Initialize a new password vault
passw0rts init

# You'll be prompted for a master password and TOTP setup (optional)
```

### CLI Usage

```bash
# Unlock vault (required before other operations)
passw0rts unlock

# Add a new password entry
passw0rts add

# List all entries
passw0rts list

# Search for entries
passw0rts list gmail

# Show entry details
passw0rts show <entry-id>

# Delete an entry
passw0rts delete <entry-id>

# Generate passwords
passw0rts generate --length 20 --count 5

# Export to JSON (unencrypted!)
passw0rts export --output backup.json

# Import from JSON
passw0rts import backup.json
```

### Web UI

```bash
# Start the web server
passw0rts web

# Custom host and port
passw0rts web --host 0.0.0.0 --port 8080

# Access at http://127.0.0.1:5000
```

The web UI provides:
- Modern, responsive dashboard
- Dark/light theme toggle
- Password management (add/edit/delete/search)
- Password generator
- Secure session management

## Architecture

```
passw0rts/
├── src/passw0rts/
│   ├── core/                  # Core functionality
│   │   ├── encryption.py      # AES-256-GCM encryption
│   │   ├── password_entry.py  # Password entry model
│   │   └── storage.py         # Encrypted storage manager
│   ├── utils/                 # Utilities
│   │   ├── password_generator.py  # Password generation
│   │   ├── totp_manager.py        # TOTP 2FA
│   │   └── session_manager.py     # Auto-lock sessions
│   ├── cli/                   # CLI interface
│   │   ├── main.py            # Click-based CLI
│   │   └── clipboard_handler.py   # Clipboard operations
│   └── web/                   # Web UI
│       ├── app.py             # Flask application
│       └── templates/         # HTML templates
└── tests/                     # Test suite
    └── unit/                  # Unit tests
```

## Security Features

### Encryption
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 600,000 iterations
- **Salt**: 256-bit random salt per vault
- **Nonce**: 96-bit random nonce per encryption
- **Authentication**: Built-in authentication tag prevents tampering

### Password Storage
- Master password never stored
- All passwords encrypted at rest
- Vault file has restrictive permissions (0600)
- Sensitive data cleared from memory on logout

### Session Security
- Auto-lock after configurable timeout (default: 5 minutes)
- Clipboard automatically cleared after 30 seconds
- TOTP 2FA for additional security layer

## Configuration

### Storage Location
Default: `~/.passw0rts/vault.enc`

Custom location:
```bash
passw0rts init --storage-path /custom/path/vault.enc
passw0rts unlock --storage-path /custom/path/vault.enc
```

### Auto-lock Timeout
```bash
passw0rts unlock --auto-lock 600  # 10 minutes
```

## Password Generator

The password generator supports:
- Customizable length (minimum 8 characters)
- Character types: lowercase, uppercase, digits, symbols
- Ambiguous character exclusion
- Passphrase generation
- Strength estimation

Example:
```bash
# Generate 20-character password
passw0rts generate --length 20

# Generate without symbols
passw0rts generate --no-symbols

# Generate 5 passwords
passw0rts generate --count 5
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=passw0rts tests/

# Run specific test file
pytest tests/unit/test_encryption.py -v
```

### Project Structure
- `src/passw0rts/`: Main package
- `tests/`: Test suite
- `requirements.txt`: Production dependencies
- `setup.py`: Package configuration

## Security Considerations

### Best Practices
1. **Strong Master Password**: Use a long, unique master password
2. **Enable TOTP**: Add extra security layer with 2FA
3. **Regular Backups**: Export and securely store backups
4. **Keep Updated**: Stay on latest version for security patches
5. **Secure Storage**: Keep vault file in secure location

### Threat Model
- Protects against: Offline attacks, data breaches, unauthorized access
- Requires: Strong master password, secure device
- Does not protect against: Keyloggers, compromised device, shoulder surfing

### Known Limitations
- Master password stored in memory during session
- Export creates unencrypted file (use with caution)
- Web UI requires local network trust

## Roadmap

Future enhancements may include:
- [ ] Cloud sync support
- [ ] Breach database checking (HaveIBeenPwned integration)
- [ ] Browser extension
- [ ] Mobile apps
- [ ] Password sharing
- [ ] Biometric unlock
- [ ] Hardware key support (YubiKey)

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

RiseofRice

## Acknowledgments

- Built with Python, Flask, Click, and Rich
- Cryptography by the [cryptography](https://cryptography.io/) library
- TOTP support via [PyOTP](https://github.com/pyauth/pyotp)

---

**⚠️ Security Notice**: This is a local password manager. Keep your master password secure and back up your vault regularly. The security of your passwords depends on the security of your master password and your device.
