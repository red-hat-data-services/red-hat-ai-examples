# Graceful Refusal — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required for the custom `make_judge()` scorer (LLM judge).

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [05_graceful_refusal.ipynb](05_graceful_refusal.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| `graceful_refusal` | Custom (`make_judge()`) | LLM judge |

This is the first notebook that builds a custom scorer. It introduces `make_judge()` — MLflow's function for creating LLM judges with custom evaluation instructions.

## Documentation

See [graceful_refusal.md](graceful_refusal.md) for a detailed explanation of this failure mode, why no existing scorer fits, and how the custom judge works.
