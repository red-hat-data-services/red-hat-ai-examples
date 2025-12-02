# Notebook Format Checks

This directory contains repo-wide format checks that statically validate every notebook and `pyproject.toml` file in the repository. The suite enforces the metadata, import, environment, and dependency rules defined in `tests/AGENTS.md`.

## Overview

The format checks run quickly (<30s), never execute notebook cells, and validate:

- Notebook metadata and structure (no execution counts/outputs, consistent kernelspec & language info, required sections, ordering)
- Import syntax and tokenization safety for every notebook code cell
- TOML validity, dependency shape, and Python version declarations for every `pyproject.toml`
- Dependency resolution safety using `pip install --dry-run` with GPU-aware skips

## Setup

Install the shared test dependencies once:

```bash
cd tests
pip install -e .
```

> All runners share the same dependency set via `tests/pyproject.toml`.

## Running Format Checks

```bash
# Recommended (parallel execution + reports)
python tests/format_checks/format_checks.py

# Direct pytest invocation
pytest tests/format_checks/ -v
```

### Individual Files

```bash
pytest tests/format_checks/test_notebook_structure.py
pytest tests/format_checks/test_notebook_imports.py
pytest tests/format_checks/test_environment.py
pytest tests/format_checks/test_venv_build.py
```

## Test Structure

- `conftest.py` – Repo-wide fixtures that discover notebooks and `pyproject.toml` files
- `test_notebook_structure.py` – Metadata, sections, ordering, schema checks
- `test_notebook_imports.py` – Import syntax/tokenization validation
- `test_environment.py` – TOML validity, dependency parsing, Python version checks
- `test_venv_build.py` – Dry-run dependency resolution & GPU-aware validation
- `format_checks.py` – Runner with parallel execution and HTML/JUnit reports

## Reports

`format_checks.py` creates artifacts under `tests/test-results/format_checks/`:

- `junit.xml` – CI-friendly report
- `report.html` – Human-readable summary (self-contained)

The directory is git-ignored by default.

## CI Integration

`python tests/format_checks/format_checks.py` runs automatically in `.github/workflows/notebook-tests.yml` alongside the knowledge-tuning-specific suite, ensuring every push validates notebooks repo-wide.
