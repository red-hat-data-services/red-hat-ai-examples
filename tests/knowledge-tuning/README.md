# Knowledge Tuning Push Tests

This directory contains push tests for the `examples/knowledge-tuning/` directory. These tests validate notebook structure, imports, utility functions, and environment configuration.

> **Source of Truth**: `AGENTS.md` in this directory is the authoritative source for all test requirements, guidelines, and agent instructions. See `AGENTS.md` for complete details.

## Overview

The tests are designed to run quickly without executing notebook cells, GPU operations, or external API calls. They validate:

- Notebook structure and metadata (no execution counts, no outputs, consistent kernelspec/language_info)
- Import statement validity (syntax checking without execution)
- Utility function correctness (with mocked dependencies)
- Environment and dependency configuration (pyproject.toml validation)
- Virtual environment build validation

## Running Tests Locally

### Prerequisites

Install test dependencies:

```bash
cd tests/knowledge-tuning
pip install -e .
```

Or install directly:

```bash
pip install pytest pytest-mock pytest-xdist pytest-html nbformat polars jsonschema
```

### Run All Tests

```bash
# From repository root
pytest tests/knowledge-tuning/

# Or use the runner script (recommended - includes parallel execution and test reports)
python tests/knowledge-tuning/run_push_tests.py
```

The runner script automatically:
- Runs tests in parallel using pytest-xdist (faster execution, ~18 seconds)
- Generates test result files in `test-results/` directory
- Creates JUnit XML report for CI integration
- Creates HTML report for human review

### Run Specific Test Files

```bash
# Test notebook structure
pytest tests/knowledge-tuning/test_notebook_structure.py

# Test imports
pytest tests/knowledge-tuning/test_notebook_imports.py

# Test utilities
pytest tests/knowledge-tuning/test_utils.py

# Test environment
pytest tests/knowledge-tuning/test_environment.py

# Test venv build
pytest tests/knowledge-tuning/test_venv_build.py
```

## Test Structure

- `test_notebook_structure.py` - Validates notebook metadata, structure, and compliance
- `test_notebook_imports.py` - Validates import statements are parseable and well-formed
- `test_utils.py` - Tests utility functions with mocked dependencies
- `test_environment.py` - Validates pyproject.toml files
- `test_venv_build.py` - Validates virtual environment build configuration
- `mocks/` - Mock utilities for transformers, GPU operations, etc.

## Key Requirements

- Tests must run in seconds (fast execution policy - target: ~18 seconds with parallel workers)
- No notebook cell execution during push checks
- All external services, GPU calls, ML training, and LLM APIs must be mocked
- Tests must behave identically in local development and CI
- No CI-specific conditionals, flags, or behavior branches

## Test Results

When running tests via the runner script (`run_push_tests.py`), test results are automatically generated in the `test-results/` directory:

- **JUnit XML**: `test-results/junit.xml` - Standard format for CI/CD integration
- **HTML Report**: `test-results/report.html` - Human-readable visual report with test details

These files are automatically ignored by git (see `.gitignore`).

## CI/CD Integration

These tests run automatically on push to the main branch via GitHub Actions workflow (`.github/workflows/knowledge-tuning-push-tests.yml`).

