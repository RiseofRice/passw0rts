# GitHub Actions Workflows

## publish.yaml - PyPI Publishing Workflow

This workflow automatically publishes the `passw0rts` package to PyPI when a new release is created.

### Features

- **Automatic Publishing**: Triggers when a GitHub release is published
- **Manual Testing**: Supports manual runs with TestPyPI for testing before production
- **Secure Authentication**: Uses PyPI Trusted Publisher (OIDC) - no tokens needed
- **Modern Build Process**: Uses the `build` package for creating distributions
- **Artifact Management**: Separates build and publish steps for better control

### Setup Instructions

#### 1. Configure PyPI Trusted Publisher

Before the workflow can publish to PyPI, you need to configure Trusted Publisher authentication:

1. Go to [PyPI](https://pypi.org) and log in
2. If the package doesn't exist yet, you'll need to manually upload the first release OR pre-register the Trusted Publisher
3. Navigate to your project → Manage → Publishing
4. Add a new Trusted Publisher with these details:
   - **PyPI Project Name**: `passw0rts`
   - **Owner**: `RiseofRice`
   - **Repository name**: `passw0rts`
   - **Workflow name**: `publish.yaml`
   - **Environment name**: `pypi`

For TestPyPI (optional, for testing):
1. Go to [TestPyPI](https://test.pypi.org) and repeat the above steps
2. Use environment name: `testpypi`

#### 2. Configure GitHub Environments

Create environments in your GitHub repository for additional protection:

1. Go to repository Settings → Environments
2. Create a new environment named `pypi`
3. (Optional) Add protection rules:
   - Required reviewers
   - Wait timer
   - Deployment branches (e.g., only `main` or release branches)
4. (Optional) Create `testpypi` environment for testing

### Usage

#### Automatic Publishing (Recommended)

The workflow automatically runs when you create a new release:

1. Update the version in `setup.py`
2. Commit and push the changes
3. Create a new release on GitHub:
   - Go to Releases → Draft a new release
   - Create a new tag (e.g., `v0.1.0`)
   - Fill in the release title and description
   - Click "Publish release"
4. The workflow will automatically:
   - Build the package
   - Publish to PyPI
   - Package will be available at `https://pypi.org/project/passw0rts/`

#### Manual Testing with TestPyPI

Before publishing to production PyPI, you can test with TestPyPI:

1. Go to Actions → Publish to PyPI
2. Click "Run workflow"
3. Check "Publish to Test PyPI instead of PyPI"
4. Click "Run workflow"
5. Once published, test installation:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ passw0rts
   ```

### Workflow Jobs

#### 1. Build Job
- Checks out the code
- Sets up Python 3.x
- Installs the `build` package
- Builds source distribution (`.tar.gz`) and wheel (`.whl`)
- Uploads artifacts for the publish jobs

#### 2. Publish to PyPI Job
- Downloads build artifacts
- Publishes to production PyPI using Trusted Publisher authentication
- Only runs when a release is published
- Requires `pypi` environment

#### 3. Publish to TestPyPI Job
- Downloads build artifacts
- Publishes to TestPyPI for testing
- Only runs when manually triggered with `test_pypi` option
- Requires `testpypi` environment

### Troubleshooting

#### "Trusted publisher configured but no JWT claims provided"
- Ensure the environment name in the workflow matches the one configured on PyPI
- Check that the `id-token: write` permission is set

#### "Forbidden: User not allowed to upload to project"
- Verify Trusted Publisher configuration on PyPI matches your repository details
- Ensure the workflow is running from the correct repository and branch

#### Build fails
- Check that `setup.py` is properly configured
- Ensure all dependencies are specified correctly
- Verify that the package can be built locally with `python -m build`

#### Package not appearing on PyPI
- Check the Actions tab for workflow execution logs
- Verify the release was properly published (not a draft)
- Check PyPI for any pending actions or verification requirements

### Security Notes

- This workflow uses **Trusted Publisher (OIDC)** authentication, which is more secure than API tokens
- No secrets need to be stored in the repository
- The `id-token: write` permission is scoped only to the publish jobs
- Build and publish are separated for better security isolation

### Additional Resources

- [PyPI Trusted Publisher Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions for PyPI Publishing](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [Python Packaging User Guide](https://packaging.python.org/)
