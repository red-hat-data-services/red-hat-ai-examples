# Excessive Steps — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required for the `ToolCallEfficiency` scorer (LLM judge).

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [03_excessive_steps.ipynb](03_excessive_steps.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| `ToolCallEfficiency` | MLflow native | LLM judge |

## Documentation

See [excessive_steps.md](excessive_steps.md) for a detailed explanation of this failure mode and how the scorer works.
