# Publishing to PyPI

This document describes how to publish lsspy to PyPI using GitHub's Trusted Publisher feature (OIDC).

## Prerequisites

Before you can publish, you need to:

1. Have maintainer access to the [lsspy PyPI project](https://pypi.org/project/lsspy/)
2. Configure Trusted Publisher on PyPI (one-time setup)

## Configuring Trusted Publisher on PyPI

Trusted Publishers allow GitHub Actions to publish packages to PyPI without requiring API tokens.

### First-Time Setup

1. **Go to PyPI**
   - Visit https://pypi.org/manage/account/publishing/
   - Or navigate to: Your Account → Publishing → Add a new pending publisher

2. **Fill in the Trusted Publisher Configuration**

   Use these exact values:

   - **PyPI Project Name**: `lsspy`
   - **Owner**: `lodestar-cli`
   - **Repository name**: `lsspy`
   - **Workflow name**: `publish.yml`
   - **Environment name**: (leave blank)

3. **Save Configuration**
   
   Click "Add" to save the pending publisher configuration.

### Important Notes

- The pending publisher becomes active once the first release is published successfully
- No API tokens or secrets are needed in GitHub
- The workflow automatically gets permission through OIDC authentication
- You can configure this before the first release (as a "pending publisher")

## Publishing a Release

Once Trusted Publisher is configured, publishing is automated:

1. **Create a Git Tag**

   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

2. **Create a GitHub Release**

   - Go to https://github.com/lodestar-cli/lsspy/releases/new
   - Select the tag you just created
   - Add release notes (use CHANGELOG.md as reference)
   - Click "Publish release"

3. **Automatic Publishing**

   - The `publish.yml` workflow automatically triggers
   - GitHub Actions builds the package (wheel + sdist)
   - The package is published to PyPI using Trusted Publisher authentication
   - Check the Actions tab for progress: https://github.com/lodestar-cli/lsspy/actions

## Verifying the Release

After publishing:

1. Check PyPI: https://pypi.org/project/lsspy/
2. Test installation:

   ```bash
   pip install --upgrade lsspy
   lsspy --version
   ```

## Troubleshooting

### "Trusted publisher configuration invalid"

- Verify all configuration values match exactly
- Check that the workflow file is named `publish.yml`
- Ensure the workflow has `id-token: write` permission

### "Permission denied"

- Ensure you have maintainer access on PyPI
- Verify you're creating a GitHub Release (not just pushing a tag)

### "Package already exists"

- You're trying to publish a version that already exists
- Increment the version in `pyproject.toml` and try again

## References

- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions OpenID Connect](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
