# PII Leakage — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required for the `PIILeakage` scorer (LLM judge). The `DetectPII` scorer is deterministic and doesn't need one.

### Additional setup for DetectPII (Guardrails AI)

The `DetectPII` scorer uses Guardrails AI with Microsoft Presidio for local PII detection. This requires additional setup:

1. Install the DetectPII validator:

   ```bash
   pip install guardrails-ai-detect-pii
   ```

   This also installs Presidio and spaCy. On first run, it will download the `en-core-web-lg` spaCy model (~400 MB).

2. Disable remote inference (use local detection only):

   ```bash
   guardrails configure --disable-metrics --disable-remote-inferencing --token ""
   ```

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [04_pii_leakage.ipynb](04_pii_leakage.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| `DetectPII` | Guardrails AI via MLflow | Deterministic (Presidio) |
| `PIILeakage` | DeepEval via MLflow | LLM judge |

## Documentation

See [pii_leakage.md](pii_leakage.md) for a detailed explanation of this failure mode, how each scorer works, and when to use which.
