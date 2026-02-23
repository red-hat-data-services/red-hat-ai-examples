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

## Working with Jupyter Notebooks

This repository uses `nbstripout` (via pre-commit) to automatically strip outputs and some metadata from Jupyter notebooks before they are committed. This keeps diffs small and avoids committing large or transient outputs.

### Preserving Specific Cell Outputs

In some cases, you may need to keep the output of a particular cell (for example, a reference plot or a summary table that is important for readers). To **exclude a cell's output from being stripped by `nbstripout`**, mark the cell with special metadata:

- **Using a cell tag (recommended)**
  - Select the cell
  - In the right sidebar, open the **Tags** panel
  - Add the tag `keep_output`

- **Using cell metadata directly**
  - Open the cell metadata editor and add:

    ```json
    {
      "keep_output": true
    }
    ```

Cells tagged with `keep_output` (or with metadata `"keep_output": true`) will keep their outputs even when the `nbstripout` pre-commit hook runs. All other cells will have their outputs stripped as usual.

## Code Quality Standards

All contributions must pass the automated code quality checks before being merged. This includes:

- Python code must be formatted with Ruff
- Python code must pass Ruff linting checks
- Markdown files must follow markdownlint rules
- No secrets or sensitive information should be committed
- No trailing whitespace or other common file issues

## Contributing Examples

When contributing new examples or modifying existing ones, please follow these standards:

### Required Documentation

All examples MUST include:

1. **Metadata file (`example.yaml`)** - Structured metadata describing the example
   - See [docs/METADATA_SCHEMA.md](docs/METADATA_SCHEMA.md) for complete schema documentation
   - Includes hardware requirements, duration estimates, tags, and more

2. **README file** - Clear documentation following our structure
   - See [docs/EXAMPLE_STYLE_GUIDE.md](docs/EXAMPLE_STYLE_GUIDE.md) for README requirements

3. **Dependencies** - `pyproject.toml`
   - Pin major versions: `package>=4.57.0,<5.0`
   - See style guide for structure and best practices

4. **Environment variables** - `.env.example` if your example uses env vars
   - Document all required variables with comments
   - Never commit actual `.env` files

### Style Guide

Follow the comprehensive style guide for:

- File naming conventions
- Directory structure patterns
- README structure and required sections
- Jupyter notebook organization
- Dependency management
- Code quality standards

**Read the full guide:** [docs/EXAMPLE_STYLE_GUIDE.md](docs/EXAMPLE_STYLE_GUIDE.md)

### Metadata Schema

All examples require an `example.yaml` metadata file with:

- Title and description
- Hardware requirements (GPU, CPU, memory, storage)
- Duration estimates
- Tags and use case classification
- Components required
- Structure information

**Read the full schema:** [docs/METADATA_SCHEMA.md](docs/METADATA_SCHEMA.md)

### Validation

Your contribution will be automatically validated for:

- Metadata schema compliance
- Required files present
- Naming conventions followed
- README structure
- YAML syntax validity

Run validation locally before submitting:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run metadata validation
pytest tests/validation/test_example_metadata.py -v

# Run structure validation
pytest tests/validation/test_example_structure.py -v

# Run all validation tests
pytest tests/validation/ -v
```

### Example Contribution Checklist

Before submitting a pull request with a new example:

- [ ] Created `example.yaml` with all required metadata fields
- [ ] Wrote comprehensive README.md following the style guide
- [ ] Included `pyproject.toml` with pinned versions
- [ ] Created `.env.example` if example uses environment variables
- [ ] Followed naming conventions for directories and files
- [ ] Tested the example end-to-end
- [ ] Ran validation tests locally and all pass
- [ ] No secrets or credentials committed
- [ ] Pre-commit hooks pass

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all pre-commit hooks pass
5. Run validation tests locally
6. Submit a pull request
