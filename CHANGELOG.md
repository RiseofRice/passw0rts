# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-03

### Added
- Initial release of passw0rts password manager
- AES-256-GCM encryption for password storage
- PBKDF2 key derivation with 600,000 iterations
- USB security key support (YubiKey, Nitrokey, etc.)
- TOTP 2FA authentication
- CLI interface with rich terminal support
- Web UI with Flask backend
- Password generator with customizable options
- Password strength estimation
- Auto-lock after inactivity
- Clipboard timeout for security
- Search functionality across all fields
- Categories and tags for organization
- Import/Export functionality (JSON format)
- Cross-platform support (macOS, Windows, Linux)

### Security
- Military-grade AES-256-GCM encryption
- OWASP-recommended key derivation settings
- Hardware-based authentication support
- Secure session management
- Automatic clipboard clearing

[0.1.0]: https://github.com/RiseofRice/passw0rts/releases/tag/v0.1.0
