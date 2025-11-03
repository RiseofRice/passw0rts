# PyPI Publishing Guide

This document explains how to publish the `passw0rts` package to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at [pypi.org](https://pypi.org/)
2. **Test PyPI Account** (optional): Create an account at [test.pypi.org](https://test.pypi.org/)
3. **API Token**: Generate an API token from your PyPI account settings

## Local Testing

Before publishing, always test the package locally:

```bash
# Clean previous builds
rm -rf dist/ build/ src/*.egg-info

# Build the package
python -m build

# Check the package
twine check dist/*

# Test installation locally
pip install dist/passw0rts-0.1.0-py3-none-any.whl

# Run the CLI to verify
passw0rts --help
```

## Publishing to Test PyPI (Recommended First)

Test your package on Test PyPI before publishing to the main PyPI:

```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    passw0rts
```

Note: `--extra-index-url` is needed because dependencies are on the main PyPI.

## Publishing to PyPI

Once you've verified everything works on Test PyPI:

```bash
# Upload to PyPI
twine upload dist/*
```

You'll be prompted for your PyPI username and API token.

## Publishing via GitHub Actions (Recommended)

The repository includes a GitHub Actions workflow (`.github/workflows/publish.yaml`) that automates publishing.

### Automatic Publishing on Release

1. **Set up PyPI API Token**:
   - Go to PyPI and create an API token for the `passw0rts` project
   - In GitHub, go to Settings → Secrets and variables → Actions
   - Add the token (not needed if using trusted publishing)

2. **Configure Trusted Publishing** (Recommended):
   - Go to PyPI → Account Settings → Publishing
   - Add GitHub as a trusted publisher
   - Repository: `RiseofRice/passw0rts`
   - Workflow: `publish.yaml`
   - Environment: `pypi`

3. **Create a Release**:
   ```bash
   # Create and push a tag
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

4. **Create GitHub Release**:
   - Go to GitHub → Releases → Create a new release
   - Choose the tag you just created
   - Write release notes (use CHANGELOG.md as reference)
   - Publish the release

The workflow will automatically:
- Build the package
- Run checks
- Publish to PyPI

### Manual Trigger for Test PyPI

To test publishing without creating a release:

1. Go to GitHub → Actions → Publish to PyPI workflow
2. Click "Run workflow"
3. Check "Publish to Test PyPI instead of PyPI"
4. Click "Run workflow"

## Version Management

Before each release:

1. **Update Version**:
   - Update version in `pyproject.toml`
   - Update version in `src/passw0rts/__init__.py`
   - Update version in `setup.py`

2. **Update CHANGELOG.md**:
   - Add release date
   - Document all changes
   - Follow [Keep a Changelog](https://keepachangelog.com/) format

3. **Run Tests**:
   ```bash
   pytest
   ```

4. **Build and Check**:
   ```bash
   python -m build
   twine check dist/*
   ```

## Post-Publication Checklist

After publishing:

- [ ] Verify package appears on [pypi.org/project/passw0rts](https://pypi.org/project/passw0rts)
- [ ] Test installation: `pip install passw0rts`
- [ ] Verify CLI works: `passw0rts --help`
- [ ] Check PyPI page displays correctly
- [ ] Update README.md with PyPI installation instructions
- [ ] Announce the release

## Common Issues

### Build Fails

```bash
# Clean everything and rebuild
rm -rf dist/ build/ src/*.egg-info
python -m build --no-isolation
```

### Upload Fails with "File already exists"

PyPI doesn't allow re-uploading the same version. You must:
1. Increment the version number
2. Rebuild the package
3. Upload again

### Dependencies Not Found

Make sure all dependencies in `pyproject.toml` match those in `setup.py` and are available on PyPI.

## Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [GitHub Actions for PyPI](https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
