# AGENTS.md

**Source of Truth** for coding agents working on the knowledge-tuning test suite.

This file contains the authoritative requirements, guidelines, and instructions for the knowledge-tuning test suite. All test requirements, mocking standards, execution policies, and project scope are defined here.

## Setup Commands

- Install test dependencies:

  ```bash
  cd tests/knowledge-tuning
  pip install -e .
  ```

- Run all tests:

  ```bash
  python tests/knowledge-tuning/run_push_tests.py
  ```

- Run tests with pytest directly:

  ```bash
  pytest tests/knowledge-tuning/ -v
  ```

- Run specific test files:

  ```bash
  pytest tests/knowledge-tuning/test_notebook_structure.py
  pytest tests/knowledge-tuning/test_notebook_imports.py
  pytest tests/knowledge-tuning/test_utils.py
  pytest tests/knowledge-tuning/test_environment.py
  pytest tests/knowledge-tuning/test_venv_build.py
  ```

## Testing Instructions

### What Tests Validate

The test suite validates the following for `examples/knowledge-tuning/`:

- **Notebook Structure**: Metadata compliance, no execution counts, no stored outputs, consistent kernelspec/language_info
- **Import Validation**: Syntax checking of import statements without execution
- **Utility Functions**: Correctness of utility functions with mocked dependencies
- **Environment Configuration**: Validation of pyproject.toml files
- **Virtual Environment Build**: Dependency resolution and venv build validation

### Test Execution Requirements

- Tests must run in **seconds** (target: ~18 seconds with parallel workers)
- **No notebook cell execution** during push checks - only static analysis
- **No GPU operations** - all GPU-related calls must be mocked
- **No external API calls** - all LLM API calls must be mocked
- **No heavy dependency execution** - use `pip install --dry-run` for dependency validation
- All external services, GPU calls, ML training, and LLM APIs must be mocked
- Tests must be deterministic, reproducible, and fast

### Running Tests Locally

Before committing, always run:

```bash
python tests/knowledge-tuning/run_push_tests.py
```

This will:

- Run all tests in parallel (using pytest-xdist)
- Generate JUnit XML report: `tests/knowledge-tuning/test-results/junit.xml`
- Generate HTML report: `tests/knowledge-tuning/test-results/report.html`

Fix any test failures before committing. The commit should pass all tests before merging.

## Notebook Testing Requirements

### Metadata Enforcement

When working with notebooks in `examples/knowledge-tuning/`, ensure:

- All notebooks have **no execution counts** (`execution_count` must be null)
- Notebooks contain **no stored outputs** of any kind (all `outputs` arrays must be empty)
- `kernelspec.name` must match the project's approved kernel (consistent across all notebooks)
- `language_info.version` must remain consistent across all notebooks
- Notebook metadata must not include environment-specific values (no vscode, colab, kaggle, etc.)
- All notebooks must follow a **single standardized metadata schema**
- Any deviation will cause test failure

### Structure Checks

Notebooks should have:

- Required sections: imports, data prep, model setup, training, inference
- Logical ordering of Markdown and code cells
- No missing, empty, or duplicated sections
- First cell should typically be markdown (title/overview)

## Mocking Standards

### What Must Be Mocked

- **All external service calls** - No real API calls
- **All GPU-related calls** - Mock torch.cuda, GPU operations
- **ML training operations** - Mock OSFT operations and heavy compute routines
- **LLM API calls** - All LLM API calls must be mocked
- **Heavy dependency execution** - Use mocks instead of real model downloads

### Mocking Frameworks

- Use **pytest-mock** or **unittest.mock** only
- Mocks must be lightweight, deterministic, and safe for PR execution
- See `tests/knowledge-tuning/mocks/` for example mock implementations

### Example: Mocking Tokenizers

```python
from unittest.mock import MagicMock
from tests.knowledge-tuning.mocks.transformers_mock import MockTokenizer

# Use MockTokenizer instead of real tokenizers
tokenizer = MockTokenizer()
result = count_len_in_tokens(df, tokenizer)
```

## Import Validation

When validating imports in notebooks:

- All imports must be parseable (syntax validation without execution)
- Imports must conform to project style (grouped, sorted, unique)
- Detect missing, unused, or out-of-order imports
- Skip shell commands (`!` or `%`) in code cells during validation
- Note: We validate syntax only, not actual resolution (to avoid execution)

## Environment Testing

### Virtual Environment Build Validation

Tests validate that:

- Each step's `pyproject.toml` can be used to build a clean virtual environment
- Dependencies resolve without conflicts (using `pip install --dry-run`)
- GPU-specific dependencies are gracefully skipped on non-GPU systems
- No GPU-specific packages in required dependencies
- Dependency graph structure is valid

### pyproject.toml Requirements

- All `pyproject.toml` files must be valid TOML and parseable
- Dependencies must be parseable (no syntax errors)
- Python version requirements must be consistent (>=3.12)
- No obviously deprecated package patterns

## Project Scope

### Files You Can Modify

- **Only files inside `examples/knowledge-tuning/`** can be modified
- Test files in `tests/knowledge-tuning/` can be modified for test improvements
- The model must not modify files outside these directories

### Protected Paths (Do Not Modify)

Do not modify or create files in:

- `.github/` (unless explicitly approved)
- `.gitlab/`
- `.vscode/`
- `.idea/`
- `.devcontainer/`
- `scripts/`
- `configs/`
- `requirements.txt`
- `environment.yml`
- Root-level `pyproject.toml`
- `setup.py`
- `setup.cfg`
- `Dockerfile` (any location)
- Any CI/CD pipeline files

### Critical Rules

- **CRITICAL**: Never modify program code to make a test pass
- Never alter repo-wide configuration or scaffolding
- Never touch workflow files, packaging files, or infra definitions
- If changes are needed outside the allowed folder, ask for explicit confirmation

## CI/CD Integration

### Automatic Execution

- Tests run **automatically on push** to the main branch
- GitHub Actions workflow: `.github/workflows/knowledge-tuning-push-tests.yml`
- Tests run on `ubuntu-latest` with Python 3.12

### Consistency Requirements

- Tests must behave **identically** in local development and in CI
- **No CI-specific conditionals, flags, or behavior branches** are allowed
- Tests must not rely on machine-specific paths, environment variables, GPUs, or network access
- Any test that passes locally but fails in CI—or vice versa—is considered invalid
- All mocks, imports, file paths, and data references must function the same in both environments

### Design for CI

- Design tests assuming they run in a **non-interactive CI environment** with limited resources
- Tests must not require manual steps, user input, or execution within an active notebook session
- All PR validations must be deterministic, reproducible, and fast

## Working Guidelines

### Focus

- Stay on the user's current task only
- No speculative assumptions—ask clarifying questions if unsure

### Safety

- No hallucinated code, commands, or file structures
- No destructive actions or restructuring unless explicitly authorized

### Communication

- Propose changes as diffs and wait for user approval
- Every modification, deletion, or refactor requires explicit user consent
- Provide reasoning, risks, and alternatives with every change request

### Editing

- Create or modify files only when requested
- Use minimal diffs
- Preserve all existing context unless directed otherwise
- No unrequested file generation
- No silent or implicit refactor
- No changes to repository architecture without approval

## QA Principles

- Validate correctness before returning results
- No partial solutions—deliver complete, professional outputs
- Review the original plan after completion; if the implementation diverges from the plan, notify the user instead of rewriting the plan
