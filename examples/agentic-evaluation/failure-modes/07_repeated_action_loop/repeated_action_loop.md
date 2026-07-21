# Failure Mode: Repeated Action Loop

## What it is

The agent gets stuck repeating actions without making progress toward completing the task.

**Sub-cases:**

- **Error retry loop** — the same tool call with the same inputs and same failure repeats.
- **Cyclical alternation** — two or more tools repeat in a loop without advancing.
- **Semantic loop** — different tools pursue the same failed goal without a meaningful strategy change.

## Why it matters

Loops waste tokens, increase latency, and can drive up tool or model cost while still failing to help the user.

## Scenario used

A travel agent attempts to book a flight. Three failing traces demonstrate retry, cycle, and semantic-loop behavior. One passing trace demonstrates normal progression through search, detail lookup, and booking.

## Scorers

### Custom `@scorer` (MLflow native)

- **Import:** `from mlflow.genai.scorers import scorer`
- **Needs expectations:** No
- **Type:** Deterministic

### Custom `make_judge()` (MLflow native)

- **Import:** `from mlflow.genai.judges import make_judge`
- **Needs expectations:** No
- **Type:** LLM judge

## Scorer comparison

| Scorer | Type | Looks at | Catches semantic loops? | Needs expectations? |
|---|---|---|---|---|
| Custom `@scorer` | Deterministic | Tool names, inputs, outputs, sequence patterns | No | No |
| Custom `make_judge()` | LLM judge | Full trace | Yes | No |

## Notebook

See [07_repeated_action_loop.ipynb](07_repeated_action_loop.ipynb) to run the evaluation on synthetic traces.
