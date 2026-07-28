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

A travel agent attempts to book flights using `TRAVEL_AGENT_TOOLS`. The notebook creates four traces:

- **Error retry loop (fail):** The user asks for a flight from NYC to Atlantis. The agent calls `search_flights("NYC", "Atlantis", "2026-08-15")` three times and gets the same output each time: `{"error": "no flights available"}`. This is wrong because the repeated calls reveal no new information and make no progress. Instead, the agent should tell the user no flights were found and ask them to confirm or change the destination.
- **Cyclical alternation (fail):** The user asks for a flight from Boston to San Francisco. The agent calls `search_flights("BOS", "SFO", "2026-08-15")`, then `get_flight_details("F100")`, then repeats the same pair again without ever calling `book_flight`. This is wrong because the agent already has the same flight result and details, so repeating the loop adds no value. Instead, it should either book `F100` or ask whether the user wants a different option.
- **Semantic loop (fail):** The user asks for a flight from NYC to Atlantis. The agent first calls `search_flights("NYC", "Atlantis", "2026-08-15")`, then switches to `search_alternative_routes("NYC", "Atlantis", "2026-08-15")`, then goes back to `search_flights("NYC", "Atlantis", "2026-08-15")` again. The tools differ, but the failed goal is unchanged. This is wrong because switching tools does not change the failed goal, so the agent is still stuck. Instead, it should explain the failure and ask whether the user wants to change the destination, date, or routing constraints.
- **Normal progression (pass):** The user asks for a flight from Boston to San Francisco. The agent calls `search_flights("BOS", "SFO", "2026-08-15")`, then `get_flight_details("F200")`, then `book_flight("F200")`, and the booking succeeds.

## Scorers

### Custom `@scorer` (MLflow native)

- **Import:** `from mlflow.genai.scorers import scorer`
- **Needs expectations:** No
- **Type:** Deterministic

**How it works:**

1. Normalize each tool span into a comparable signature using its name, inputs, and outputs.
2. Compare consecutive tool spans to detect an error retry loop. If the same tool call with the same inputs and outputs repeats three or more times in a row, return `no`.
3. Compare back-to-back subsequences of full tool signatures to detect cyclical alternation. If the same sequence repeats consecutively, return `no`.
4. If neither pattern is found, return `yes`.

### Custom `make_judge()` (MLflow native)

- **Import:** `from mlflow.genai.judges import make_judge`
- **Needs expectations:** No
- **Type:** LLM judge

**How it works:**

- Read the full `{{ trace }}` rather than just the final response.
- Judge whether the agent is making progress toward the user's goal or repeating the same failed objective using different tools or approaches.
- Return `yes` when the trace shows progress and `no` when it shows a semantic loop.

## Scorer comparison

| Scorer | Type | Looks at | Catches semantic loops? | Needs expectations? |
|---|---|---|---|---|
| Custom `@scorer` | Deterministic | Tool names, inputs, outputs, repeated sequence patterns | No | No |
| Custom `make_judge()` | LLM judge | Full trace | Yes | No |

**When to use which:**

- **Custom `@scorer`:** Best for CI/CD or regression testing when you want fast, reproducible checks for exact retry loops and exact repeated tool-call cycles.
- **Custom `make_judge()`:** Best when you need to catch semantic loops that do not repeat an identical tool-call structure, but still pursue the same failed goal.

## Limitations

- **Custom `@scorer`:** Only catches exact repeated structure. It misses semantic loops and may also miss loops where the same goal is retried with meaningfully different inputs or outputs each time.
- **Custom `make_judge()`:** Requires an LLM API key, is slower and costlier than the deterministic scorer, and is non-deterministic, so verdicts may vary slightly between runs or judge models.

## Notebook

See [07_repeated_action_loop.ipynb](07_repeated_action_loop.ipynb) to run the evaluation on synthetic traces.
