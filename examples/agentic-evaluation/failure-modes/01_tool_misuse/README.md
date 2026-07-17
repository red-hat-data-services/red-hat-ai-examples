# Tool Misuse — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required for the `ToolCallCorrectness` scorer (LLM judge mode). The other two approaches are deterministic and don't need one.

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [01_tool_misuse.ipynb](01_tool_misuse.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| `ToolCallCorrectness` (ground-truth-free) | MLflow native | LLM judge |
| `ToolCallCorrectness` (exact match) | MLflow native | Deterministic |
| `ToolCorrectness` | DeepEval via MLflow | Deterministic |

## Documentation

See [tool_misuse.md](tool_misuse.md) for a detailed explanation of this failure mode, how each scorer works, and when to use which.
