# Testing Infrastructure

This repository includes comprehensive testing infrastructure for validating Jupyter notebooks.

## Overview

The tests are organized into two main categories:

1. **Validation Tests** (`tests/validation/`): Repository-wide tests that validate **all** notebooks automatically
2. **Smoke Tests** (`tests/examples/`): Example-specific tests that verify specific example workflows

## Quick Start

### Install Test Dependencies

```bash
# Install the package with test dependencies
pip install -e ".[test]"
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run tests in parallel (faster)
pytest -n auto
```

### Run Specific Test Suites

```bash
# Run only validation tests (structure, content, syntax)
pytest tests/validation/

# Run only smoke tests (example-specific)
pytest tests/examples/
```

### Get Test Coverage

```bash
# Run tests with coverage report
pytest --cov=tests --cov-report=term

# Generate HTML coverage report
pytest --cov=tests --cov-report=html

# Generate both terminal and HTML reports
pytest --cov=tests --cov-report=term --cov-report=html
```

## Directory Structure

```text
tests/
├── conftest.py                              # Shared fixtures and configuration
├── validation/                              # Repository-wide validation tests
│   ├── test_notebook_structure.py          # Basic structure validation
│   ├── test_notebook_content.py            # Content cleanliness validation
│   ├── test_notebook_syntax.py             # Python syntax validation
│   └── test_pyproject_toml.py              # Configuration file validation
│
└── examples/                                # Example-specific smoke tests
    └── knowledge_tuning/
        ├── conftest.py                      # Knowledge-tuning fixtures
        ├── test_smoke.py                    # Structure and consistency tests
        ├── test_knowledge_utils.py          # Utility function tests
        └── mocks/
            └── transformers_mock.py         # Mock transformers for testing
```

## Test Types Explained

### Validation Tests

Repository-wide tests in `tests/validation/` that run on **all notebooks** automatically:

#### Structure Tests (`test_notebook_structure.py`)

- ✅ **JSON Validity**: Ensures notebooks are valid JSON
- ✅ **Structure Validation**: Validates nbformat schema
- ✅ **Cell Validation**: Checks cells have valid types
- ✅ **Metadata Validation**: Ensures proper metadata exists
- ✅ **Error Detection**: Identifies execution errors in outputs
- ✅ **Type Checking**: Validates cell types (code, markdown, raw)

#### Content Tests (`test_notebook_content.py`)

- ✅ **No Execution Counts**: Ensures notebooks have cleared execution counts
- ✅ **No Stored Outputs**: Ensures notebooks have cleared outputs
- ✅ **No Empty Code Cells**: Prevents empty code cells

#### Syntax Tests (`test_notebook_syntax.py`)

- ✅ **Import Parseability**: Ensures all import statements are parseable
- ✅ **Well-formed Imports**: Validates import statements have correct structure
- ✅ **Code Validation**: All code cells have valid Python syntax
- ✅ **Shell Commands**: Skips shell commands and magic commands appropriately

#### Metadata Tests (`test_notebook_metadata.py`)

- ✅ **Kernelspec Consistency**: Ensures all notebooks use the same kernel
- ✅ **No Environment Metadata**: Prevents environment-specific metadata (vscode, colab, etc.)
- ✅ **Standardized Schema**: Validates consistent metadata structure across notebooks
- ✅ **Required Sections**: Ensures notebooks have setup/import documentation
- ✅ **Cell Ordering**: Validates logical cell type ordering

#### PyProject Tests (`test_pyproject_toml.py`)

- ✅ **Valid TOML**: Ensures pyproject.toml files are valid TOML
- ✅ **Required Sections**: Validates [project] or [tool] sections exist
- ✅ **Dependencies**: Checks dependencies are well-formed
- ✅ **Python Version**: Validates requires-python field
- ✅ **No GPU Packages**: Ensures GPU-specific packages aren't in required dependencies
- ✅ **Version Consistency**: Validates Python version consistency across projects
- ✅ **Venv Build Validation**: Uses `pip install --dry-run` to verify dependencies can be resolved
- ✅ **Conflict Detection**: Checks for dependency conflicts without installing packages

### Smoke Tests (Knowledge-Tuning)

Example-specific tests in `tests/examples/knowledge_tuning/` that verify the knowledge-tuning workflow:

#### Structure Tests (`test_smoke.py`)

- ✅ Directory structure validation
- ✅ Required files present (README, .env.example, pyproject.toml)
- ✅ All step directories exist (00_Setup through 06_Evaluation)
- ✅ Notebook structure validation
- ✅ Import validation (transformers, torch, etc.)
- ✅ Environment variable usage
- ✅ Documentation completeness (overview sections)
- ✅ Consistency across notebooks (Python version)

#### Utility Function Tests (`test_knowledge_utils.py`)

- ✅ **get_avg_summaries_per_raw_doc**: Tests average summary calculation logic
- ✅ **sample_doc_qa**: Tests Q&A pair sampling with proper column validation
- ✅ **generate_knowledge_qa_dataset**: Tests dataset generation in chat format
- ✅ **count_len_in_tokens**: Tests token counting with mocked tokenizers
- ✅ **Data Contract Validation**: Ensures all functions validate required columns
- ✅ **JSON Schema Validation**: Verifies output follows expected structure
- ✅ **Reasoning Support**: Tests functions with and without reasoning columns
- ✅ **Pre-training Flags**: Validates unmask column generation

## Shared Fixtures

The [tests/conftest.py](tests/conftest.py) file provides shared fixtures for all tests:

- `repo_root`: Repository root path
- `all_notebooks`: List of all notebooks in examples/
- `all_pyproject_files`: List of all pyproject.toml files
- `knowledge_tuning_path`: Path to knowledge-tuning example
- `toml_parser`: TOML parser (tomllib or tomli)

## Continuous Integration

Tests run automatically in GitHub Actions:

- **Trigger**: On push to main, pull requests, or manual dispatch
- **Workflow**: [.github/workflows/notebook-tests.yml](.github/workflows/notebook-tests.yml)
- **Jobs**:
  - **validation-tests**: Runs validation tests (structure, content, syntax, metadata, pyproject)
  - **smoke-tests**: Runs example-specific smoke tests
  - **test-coverage**: Generates coverage report (PRs only)

## Running Tests Locally

### Basic Usage

```bash
# Run all tests
pytest

# Run all tests with verbose output
pytest -v

# Run specific test file
pytest tests/validation/test_notebook_structure.py

# Run specific test function
pytest tests/validation/test_notebook_structure.py::test_all_notebooks_found

# Run tests matching a pattern
pytest -k "validation"
pytest -k "structure"
pytest -k "knowledge_tuning"
```

### Selective Test Execution

```bash
# Run only validation tests
pytest tests/validation/

# Run only smoke tests
pytest tests/examples/

# Run tests for specific example
pytest tests/examples/knowledge_tuning/

# Run specific validation category
pytest tests/validation/test_notebook_content.py
```

### Get Coverage Locally

```bash
# Run tests with coverage (terminal output)
pytest --cov=tests --cov-report=term

# Run with HTML coverage report
pytest --cov=tests --cov-report=html

# Run with both terminal and HTML reports
pytest --cov=tests --cov-report=term --cov-report=html

# Show which lines are missing coverage
pytest --cov=tests --cov-report=term-missing
```

## Test Markers

Mark tests with categories for selective execution:

```python
@pytest.mark.smoke
def test_quick_check():
    pass

@pytest.mark.slow
def test_comprehensive():
    pass
```

Run specific markers:

```bash
pytest -m smoke        # Run only smoke tests
pytest -m "not slow"   # Skip slow tests
```

## Testing Requirements for New Examples

When adding new examples to the repository, they must pass all validation tests automatically. Additionally, consider adding example-specific smoke tests for comprehensive validation.

### Automatic Validation (Required)

All examples automatically undergo validation testing without any additional setup:

- **Notebook Structure Validation**
- **Notebook Content Validation**
- **Notebook Syntax Validation**
- **PyProject.toml Validation**

### Example-Specific Smoke Tests (Recommended)

For complex examples with multiple steps or critical workflows, add smoke tests in `tests/examples/your-example-name/`:

**Example Structure:**

```text
tests/examples/your-example-name/
├── __init__.py
├── conftest.py              # Fixtures for your example
├── test_smoke.py            # Structure and consistency tests
├── test_utils.py            # Utility function tests (if applicable)
└── mocks/                   # Mock heavy dependencies
    └── __init__.py
```

**Reference Implementation:**

See [tests/examples/knowledge_tuning/](tests/examples/knowledge_tuning/) for a complete example of smoke tests including:

- File structure validation
- Notebook import verification
- Documentation completeness checks
- Utility function testing with mocked transformers/torch
- Configuration consistency validation

### Running Tests for New Examples

Verify your example passes all tests:

```bash
# Run all validation tests
pytest tests/validation/ -v

# Run validation tests for specific notebooks
pytest tests/validation/ -v -k "your_notebook_name"

# Verify PyProject.toml
pytest tests/validation/test_pyproject_toml.py -v

# Run your smoke tests (if added)
pytest tests/examples/your-example-name/ -v

# Run all tests together
pytest -v
```
