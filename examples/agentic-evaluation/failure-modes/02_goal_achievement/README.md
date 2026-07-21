# Goal Achievement — Setup & Usage

## Prerequisites

Make sure you have completed the setup steps in the [project README](../../README.md) (install dependencies, configure API key, start MLflow server).

An LLM API key is required for all four scorers in this notebook (all are LLM judges).

## Running the notebook

The notebook is self-contained — it creates its own synthetic traces, evaluates them, and cleans up old traces on each run. Open [02_goal_achievement.ipynb](02_goal_achievement.ipynb) and run all cells.

## Scorers used

| Scorer | Source | Type |
|---|---|---|
| `Correctness` | MLflow native | LLM judge |
| `AgentGoalAccuracyWithReference` | RAGAS via MLflow | LLM judge |
| `TaskCompletion` | DeepEval via MLflow | LLM judge |
| `AgentGoalAccuracyWithoutReference` | RAGAS via MLflow | LLM judge |

## Documentation

See [goal_achievement.md](goal_achievement.md) for a detailed explanation of this failure mode, how each scorer works, and when to use which.
