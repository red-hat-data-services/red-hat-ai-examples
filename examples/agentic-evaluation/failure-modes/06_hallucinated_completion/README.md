# Hallucinated Completion — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required — the `grounded_in_tools` scorer wraps MLflow's `is_grounded()` judge with `gpt-4o` explicitly specified (the MLflow default is `gpt-4.1-mini`).

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [06_hallucinated_completion.ipynb](06_hallucinated_completion.ipynb) and run all cells.

## Scorer used

| Scorer | Source | Type |
|---|---|---|
| `grounded_in_tools` | Custom `@scorer` wrapping MLflow's `is_grounded()` | LLM judge |

## Documentation

See [hallucinated_completion.md](hallucinated_completion.md) for a detailed explanation of this failure mode, how the scorer works, and why existing groundedness scorers don't work for TOOL spans.
