# Tests Overview

This directory centralizes the automated suites that run on every push. The
requirements and guardrails for these suites live in `tests/AGENTS.md`. Two
independent packages share a single dependency set and infrastructure:

## Structure

- `format_checks/` &mdash; Repo-wide notebook and `pyproject.toml` validation
  - `conftest.py` discovers every notebook/config file in the repo
  - `test_notebook_structure.py`, `test_notebook_imports.py`,
    `test_environment.py`, `test_venv_build.py`
  - `format_checks.py` runner (parallel pytest + HTML/JUnit reports)
- `knowledge-tuning/` &mdash; Mock-driven tests for
  `examples/knowledge-tuning/04_Knowledge_Mixing/utils/knowledge_utils.py`
  - `test_utils.py`, `mocks/`, `conftest.py`
  - `run_knowledge_tuning_tests.py` runner (parallel pytest + HTML/JUnit reports)
- `test-results/` &mdash; Shared artifact root (`tests/test-results/<suite>/…`)
- `conftest.py` &mdash; Shared fixtures (e.g., `repo_root`)
- `pyproject.toml` &mdash; Shared editable install for both suites

## Setup

```bash
cd tests
pip install -e .
```

## Running the Suites

```bash
python tests/format_checks/format_checks.py
python tests/knowledge-tuning/run_knowledge_tuning_tests.py
```

Each runner:

- Executes `pytest -n auto` for fast feedback
- Emits `tests/test-results/<suite>/{junit.xml,report.html}` for CI + humans

## CI Integration

`.github/workflows/notebook-tests.yml` installs the shared dependencies once, then
executes both runners on every push and pull request targeting `main`. Keep the
runtime in the seconds range by relying on structural validation, mocks, and
`pip install --dry-run` for dependency checks.
