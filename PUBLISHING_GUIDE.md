# 📦 Step-by-Step Publishing Guide for passw0rts

This guide will walk you through the complete process of publishing the `passw0rts` package to PyPI.

## ✅ Pre-Publication Checklist

### 1. Code Quality Checks

- [x] **All tests passing**: Run `pytest` - all 53 tests are passing ✅
- [x] **Package builds successfully**: Run `python -m build --no-isolation` ✅
- [x] **Package validation passes**: Run `twine check dist/*` ✅
- [x] **Templates included**: HTML templates are now properly included in the package ✅
- [x] **Local installation works**: Package can be installed and CLI works ✅

### 2. Documentation Review

- [x] **README.md**: Complete and up-to-date ✅
- [x] **CHANGELOG.md**: Version 0.1.0 documented with release date (2025-11-03) ✅
- [x] **LICENSE**: MIT License present ✅
- [x] **PYPI_PUBLISHING.md**: Detailed publishing instructions available ✅

### 3. Version Consistency

Check that version numbers match across all files:
- [x] `pyproject.toml`: version = "0.1.0" ✅
- [x] `setup.py`: version = "0.1.0" ✅
- [x] `src/passw0rts/__init__.py`: __version__ = "0.1.0" ✅

### 4. Package Configuration

- [x] **Dependencies**: All dependencies listed in both `pyproject.toml` and `setup.py` ✅
- [x] **Entry points**: CLI entry point configured (`passw0rts` command) ✅
- [x] **Package data**: HTML templates now properly included ✅
- [x] **Classifiers**: Appropriate PyPI classifiers set ✅

### 5. Repository Status

- [x] **Clean working directory**: All changes committed ✅
- [x] **GitHub Actions workflow**: `publish.yaml` configured for automated publishing ✅

---

## 🚀 Publishing Options

You have **two main options** for publishing to PyPI:

### Option A: Automated Publishing via GitHub Actions (Recommended)
### Option B: Manual Publishing via Command Line

---

## Option A: Automated Publishing via GitHub Actions (Recommended)

This is the safest and most reliable method. The repository already has a configured workflow.

### Step 1: Set Up PyPI Trusted Publishing

1. **Go to PyPI** (create account if needed):
   - Visit https://pypi.org/
   - Sign in or create an account

2. **Configure Trusted Publishing**:
   - Go to https://pypi.org/manage/account/publishing/
   - Click "Add a new pending publisher"
   - Fill in the form:
     - **PyPI Project Name**: `passw0rts`
     - **Owner**: `RiseofRice`
     - **Repository name**: `passw0rts`
     - **Workflow name**: `publish.yaml`
     - **Environment name**: `pypi`
   - Click "Add"

   > **Note**: This allows GitHub Actions to publish to PyPI without storing API tokens as secrets. It's the recommended modern approach.

### Step 2: Test on Test PyPI First (Optional but Recommended)

1. **Set up Test PyPI trusted publishing** (same as above but at https://test.pypi.org/)
   - Environment name: `testpypi`

2. **Trigger test deployment**:
   - Go to your GitHub repository
   - Click "Actions" tab
   - Select "Publish to PyPI" workflow
   - Click "Run workflow"
   - Check "Publish to Test PyPI instead of PyPI"
   - Click "Run workflow"

3. **Verify on Test PyPI**:
   - Check https://test.pypi.org/project/passw0rts/
   - Test installation:
     ```bash
     pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ passw0rts
     passw0rts --version
     ```

### Step 3: Create a Git Tag

```bash
# Make sure you're on the main branch
git checkout main
git pull origin main

# Create an annotated tag
git tag -a v0.1.0 -m "Release version 0.1.0"

# Push the tag to GitHub
git push origin v0.1.0
```

### Step 4: Create a GitHub Release

1. **Go to GitHub Releases**:
   - Navigate to https://github.com/RiseofRice/passw0rts/releases
   - Click "Create a new release"

2. **Fill in release details**:
   - **Tag**: Select `v0.1.0` (the tag you just created)
   - **Release title**: `v0.1.0 - Initial Release`
   - **Description**: Copy the relevant section from CHANGELOG.md:
     ```markdown
     ## 🎉 Initial Release of passw0rts

     A secure, cross-platform password manager with CLI and web UI capabilities.

     ### Features Added
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

     ### Installation
     ```bash
     pip install passw0rts
     ```

     See the [README](https://github.com/RiseofRice/passw0rts#readme) for full documentation.
     ```

3. **Publish the release**:
   - Click "Publish release"
   - The GitHub Actions workflow will automatically trigger
   - Monitor the progress in the Actions tab

### Step 5: Verify Publication

1. **Check GitHub Actions**:
   - Go to Actions tab
   - Watch the "Publish to PyPI" workflow
   - Ensure it completes successfully (green checkmark)

2. **Verify on PyPI**:
   - Visit https://pypi.org/project/passw0rts/
   - Confirm the package appears with version 0.1.0

3. **Test installation**:
   ```bash
   # In a fresh virtual environment
   python -m venv test_env
   source test_env/bin/activate  # On Windows: test_env\Scripts\activate
   
   pip install passw0rts
   passw0rts --version
   passw0rts --help
   
   # Test basic functionality
   passw0rts generate
   ```

---

## Option B: Manual Publishing via Command Line

Use this method if you can't use GitHub Actions or need to publish immediately.

### Prerequisites

```bash
# Install build and publishing tools
pip install build twine
```

### Step 1: Clean Previous Builds

```bash
cd /path/to/passw0rts
rm -rf dist/ build/ src/*.egg-info
```

### Step 2: Build the Package

```bash
python -m build --no-isolation
```

Expected output:
```
Successfully built passw0rts-0.1.0.tar.gz and passw0rts-0.1.0-py3-none-any.whl
```

### Step 3: Verify the Build

```bash
twine check dist/*
```

Expected output:
```
Checking dist/passw0rts-0.1.0-py3-none-any.whl: PASSED
Checking dist/passw0rts-0.1.0.tar.gz: PASSED
```

### Step 4: Test on Test PyPI (Recommended)

1. **Create Test PyPI account** at https://test.pypi.org/

2. **Generate API token**:
   - Go to https://test.pypi.org/manage/account/token/
   - Create a token with scope for the entire account
   - Save it securely (you'll only see it once)

3. **Upload to Test PyPI**:
   ```bash
   twine upload --repository testpypi dist/*
   ```
   - Username: `__token__`
   - Password: `your-test-pypi-token`

4. **Test installation from Test PyPI**:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ passw0rts
   passw0rts --version
   ```

### Step 5: Publish to PyPI

1. **Create PyPI account** at https://pypi.org/

2. **Generate API token**:
   - Go to https://pypi.org/manage/account/token/
   - Create a token with scope for the entire account (or create project-specific token after first upload)
   - Save it securely

3. **Upload to PyPI**:
   ```bash
   twine upload dist/*
   ```
   - Username: `__token__`
   - Password: `your-pypi-token`

### Step 6: Verify Publication

```bash
# Wait a minute for PyPI to process
pip install passw0rts
passw0rts --version
```

### Step 7: Create Git Tag and GitHub Release

Even with manual publishing, you should create a release on GitHub:

```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

Then create a release on GitHub (see Option A, Step 4 for details).

---

## 📝 Post-Publication Tasks

After successfully publishing:

### 1. Update README Badges (Optional)

You can add PyPI badges to README.md:

```markdown
[![PyPI version](https://badge.fury.io/py/passw0rts.svg)](https://badge.fury.io/py/passw0rts)
[![Python versions](https://img.shields.io/pypi/pyversions/passw0rts.svg)](https://pypi.org/project/passw0rts/)
[![Downloads](https://pepy.tech/badge/passw0rts)](https://pepy.tech/project/passw0rts)
```

### 2. Update Documentation

Update the README.md installation instructions to emphasize PyPI installation:

```markdown
## Installation

### From PyPI (Recommended)

```bash
pip install passw0rts
```

### From Source

```bash
git clone https://github.com/RiseofRice/passw0rts.git
cd passw0rts
pip install -e .
```
```

### 3. Announce the Release

Consider announcing on:
- GitHub Discussions (if enabled)
- Reddit (r/Python, r/opensource, r/selfhosted)
- Hacker News
- Your blog or social media
- Python Weekly newsletter submission

### 4. Monitor Issues

- Watch for installation issues
- Respond to GitHub issues
- Monitor PyPI download statistics

### 5. Plan Next Release

- Start a new section in CHANGELOG.md for [Unreleased]
- Consider setting up branch protection
- Plan for bug fixes and new features

---

## 🐛 Troubleshooting

### Build Fails

```bash
# Clean everything and rebuild
rm -rf dist/ build/ src/*.egg-info
python -m build --no-isolation
```

### Upload Fails: "File already exists"

PyPI doesn't allow re-uploading the same version. You must:
1. Increment the version number in all three locations
2. Update CHANGELOG.md
3. Rebuild and upload again

### Templates or Other Files Missing

Check:
1. `MANIFEST.in` includes the file patterns
2. `pyproject.toml` has `include-package-data = true`
3. `setup.py` has `package_data` configured
4. Rebuild and verify with `unzip -l dist/*.whl`

### Import Errors After Installation

```bash
# Verify package structure
pip show -f passw0rts

# Check if all files are present
python -c "import passw0rts; print(passw0rts.__version__)"
```

### GitHub Actions Fails

1. Check that trusted publishing is configured correctly
2. Verify the environment name matches (case-sensitive)
3. Check workflow permissions in repository settings
4. Review the Actions logs for specific errors

---

## 📚 Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [GitHub Actions for PyPI Publishing](https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [Trusted Publishers on PyPI](https://docs.pypi.org/trusted-publishers/)

---

## 🎯 Quick Reference Commands

```bash
# Build package
python -m build --no-isolation

# Check package
twine check dist/*

# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*

# Create and push tag
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0

# Test installation
pip install passw0rts
passw0rts --version
```

---

## ✅ You're Ready to Publish!

The package is in excellent shape and ready for publication. Choose Option A (GitHub Actions) for the smoothest experience, or Option B (manual) if you need more control.

**Recommended next steps:**
1. Set up PyPI trusted publishing (takes 5 minutes)
2. Test on Test PyPI first
3. Create a git tag
4. Create a GitHub release
5. Let GitHub Actions do the rest!

Good luck with your first PyPI release! 🚀
