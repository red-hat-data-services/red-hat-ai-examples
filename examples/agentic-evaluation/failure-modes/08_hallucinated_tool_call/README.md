# Hallucinated Tool Call — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

No LLM API key needed — this scorer is fully deterministic.

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [08_hallucinated_tool_call.ipynb](08_hallucinated_tool_call.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| `tool_existence_check` | Custom (`@scorer`) | Deterministic (set membership check) |

This notebook demonstrates the first pure deterministic `@scorer` — no LLM involved. The `@scorer` decorator was introduced in [FM06 (Hallucinated Completion)](../06_hallucinated_completion/06_hallucinated_completion.ipynb), where it wraps an LLM judge; here it's used for a simple set membership check.

## Documentation

See [hallucinated_tool_call.md](hallucinated_tool_call.md) for a detailed explanation of this failure mode, how the scorer works, and why no existing scorer fits.
