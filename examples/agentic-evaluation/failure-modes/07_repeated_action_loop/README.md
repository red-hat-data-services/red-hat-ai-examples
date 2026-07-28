# Repeated Action Loop — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required for the `make_judge()` approach. The deterministic `@scorer` approach does not need one.

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [07_repeated_action_loop.ipynb](07_repeated_action_loop.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| Custom `@scorer` | MLflow native | Deterministic |
| Custom `make_judge()` | MLflow native | LLM judge |

## Documentation

See [repeated_action_loop.md](repeated_action_loop.md) for a detailed explanation of this failure mode, both approaches, and when to use which.
