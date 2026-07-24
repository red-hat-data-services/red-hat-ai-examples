# Verification Skipped — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required for the custom `make_judge()` scorer (LLM judge).

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [09_verification_skipped.ipynb](09_verification_skipped.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| `verification_skipped` | Custom (`make_judge()`) | LLM judge |

## Documentation

See [verification_skipped.md](verification_skipped.md) for a detailed explanation of this failure mode, when verification is and isn't needed, and how the custom judge works.
