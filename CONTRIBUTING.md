# Contributing to Red Hat AI Examples

This guide will help you set up your development environment and understand the code quality standards.

## Development Setup

This repository uses automated code quality and security scanning tools. To contribute, you'll need to install the
following development tools:

### Required Tools

**Python Tools:**

```bash
pip install pre-commit ruff detect-secrets
```

- **pre-commit** - Manages git hooks for automated code quality checks
- **ruff** - Fast Python linter and formatter
- **detect-secrets** - Prevents secrets from being committed to the repository

- **markdownlint-cli** (requires Node.js):

  ```bash
  npm install -g markdownlint-cli
  ```

- **gitleaks** (for local secret scanning):
  - macOS: `brew install gitleaks`
  - Linux: See [Gitleaks installation guide](https://github.com/gitleaks/gitleaks#installation)

### Setting Up Pre-commit Hooks

After installing the tools, set up the pre-commit hooks:

```bash
# Install git hooks
pre-commit install
pre-commit install --hook-type commit-msg

# To Run hooks on all files
pre-commit run --all-files
```

The pre-commit hooks will automatically run on every commit to check:

- Python code quality and formatting (Ruff)
- Markdown linting
- Secret scanning (Gitleaks, Talisman, and detect-secrets)
- General file quality (trailing whitespace, YAML syntax, etc.)

See [.pre-commit-config.yaml](.pre-commit-config.yaml) for the complete configuration.

### Working with Secret Scanning

**If detect-secrets fails during commit**, it means potential secrets were detected in your changes.

If detect-secrets flags something that is not actually a secret (false positive), you have to:

**Update the baseline** (recommended for legitimate false positives):

```bash
# Scan and update the baseline
detect-secrets scan > .secrets.baseline

# Audit the baseline to mark false positives
detect-secrets audit .secrets.baseline

# Commit the updated baseline
git add .secrets.baseline
git commit -m "Update detect-secrets baseline"
```

### Manual Code Quality Checks

You can also run these tools manually:

```bash
# Python linting
ruff check .

# Fix Python linting
ruff check --fix .

# Python formatting
ruff format .

# Markdown linting
markdownlint .

# Fix Markdown lint
markdownlint --fix .

# Run all pre-commit hooks
pre-commit run --all-files
```

## Code Quality Standards

All contributions must pass the automated code quality checks before being merged. This includes:

- Python code must be formatted with Ruff
- Python code must pass Ruff linting checks
- Markdown files must follow markdownlint rules
- No secrets or sensitive information should be committed
- No trailing whitespace or other common file issues

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all pre-commit hooks pass
5. Submit a pull request
