# AGENTS.md

**Source of Truth** for coding agents working on the notebook-format and knowledge-tuning test suites. This document defines all requirements, mocking standards, execution policies, and project scope for the `tests/` hierarchy.

## Testing Instructions

### Critical Rules

- **CRITICAL**: Never modify program code to make a test pass
- Never alter repo-wide configuration or scaffolding
- Never touch workflow files, packaging files, or infra definitions
- If changes are needed outside the allowed folder, ask for explicit confirmation
- Do not turn failing tests into stubs to make them pass
- Simplifying, renaming, moving or removing existing tests requires explicit user consent

### Format Checks (Repo-wide)

The format suite validates every notebook and `pyproject.toml` in the repository:

- **Notebook Structure:** No execution counts or outputs, consistent `kernelspec` + `language_info`, standardized metadata schema, logical cell ordering, required sections.
- **Import Validation:** All code cells must parse/tokenize without executing; shell/magic commands are skipped safely.
- **Environment Configuration:** Every `pyproject.toml` must contain valid TOML, dependencies, and Python version specifiers.
- **Venv Simulation:** Uses `pip install --dry-run` to validate dependency graphs with GPU-aware skips.

### Knowledge-Tuning Suite

Targets `examples/knowledge-tuning/04_Knowledge_Mixing/utils/knowledge_utils.py` and related helpers:

- Mock-driven coverage of dataset utilities and tokenizers.
- Deterministic fixtures ensure no GPU, network, or heavyweight workloads.

### Execution Requirements

- Total runtime must stay in the "seconds" range (parallel pytest workers).
- Absolutely **no notebook cell execution**.
- **No GPU operations**; all torch/accelerator APIs must be mocked.
- **No external API calls**; mock every LLM/service interaction.
- Prefer structural validation (e.g., `pip install --dry-run`, JSON schema checks) over heavyweight work.

## Running Tests Locally

Run both suites before committing:

```bash
python tests/format_checks/format_checks.py
python tests/knowledge-tuning/run_knowledge_tuning_tests.py
```

Each runner:

- Executes pytest with `-n auto` (pytest-xdist).
- Generates JUnit XML + self-contained HTML reports under `tests/test-results/<suite>/`.

## Notebook Testing Requirements

### Metadata Enforcement

When working with notebooks in `examples/`, ensure:

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

### Allowed Frameworks

- `pytest-mock` or `unittest.mock`.

### Example: Mocking Tokenizers

```python
import sys
from pathlib import Path

tests_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(tests_dir / "knowledge-tuning"))

from mocks.transformers_mock import MockTokenizer

tokenizer = MockTokenizer()
result = count_len_in_tokens(df, tokenizer)
```

## Import Validation

- Validate imports syntactically via `ast.parse`/`tokenize`.
- Skip lines beginning with `!` or `%` (shell/magic commands).
- Enforce grouped, well-formed imports—no execution allowed.

## Environment Testing

- Every `pyproject.toml` must parse under `tomllib/tomli`.
- Dependencies must be lists of strings with valid package specifiers.
- `requires-python` must be well-formed and indicate modern versions (>=3.12).
- `pip install --dry-run` reports must succeed or skip gracefully when GPU-only dependencies (e.g., `triton`, `cuda`) are unavailable on the runner.

## Project Scope

- Modify files under `examples/tests/` and only.
- Changes to `.github/workflows/notebook-tests.yml` require explicit user approval.
- Do **not** touch root-level build/test infrastructure, packaging files, container definitions, or other protected directories without approval.

## CI/CD Integration

### Automatic Execution

- `.github/workflows/notebook-tests.yml` installs shared deps (`cd tests && pip install -e .`) and runs both runners on **every push** and **pull request**.
- Tests must behave identically locally and in CI—no environment-specific flags.
- Assume `ubuntu-latest`, Python 3.12, no GPU, and no internet access in CI.

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

## Test Creation

- The test name must match the implementation. If there is a mismatch inform the user
- The test must be high quality and meaningful. Do not add junk tests.

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

- Validate correctness before sharing results.
- Deliver complete solutions—no partial implementations.
- Review the original plan after completion; if the implementation diverges from the plan, notify the user instead of rewriting the plan
