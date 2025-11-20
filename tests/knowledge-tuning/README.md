# Knowledge-Tuning Tests

This directory houses the knowledge-tuning specific tests that exercise the mocked utility functions and supporting infrastructure under `examples/knowledge-tuning/`. Repo-wide notebook and configuration checks now live in `tests/format_checks/`.

> **Source of Truth:** Follow `tests/AGENTS.md` for the complete requirements, mocking standards, and CI expectations.

## Setup

Install the shared dependencies once:

```bash
cd tests
pip install -e .
```

## Running the Knowledge-Tuning Suite

```bash
# Recommended runner (parallel execution + reports)
python tests/knowledge-tuning/run_knowledge_tuning_tests.py

# Direct pytest invocation
pytest tests/knowledge-tuning/ -v
```

## Test Structure

- `test_utils.py` – Mock-driven coverage of `knowledge_utils.py`
- `conftest.py` – Fixtures that resolve `examples/knowledge-tuning/` assets
- `mocks/` – Deterministic mocks for transformers/tokenizers/GPU calls
- `run_knowledge_tuning_tests.py` – Runner that produces HTML + JUnit reports

## Reports

Runner output is written to `tests/test-results/knowledge-tuning/`:

- `junit.xml` – CI-friendly report
- `report.html` – Human-readable summary

These files are ignored by git automatically.
