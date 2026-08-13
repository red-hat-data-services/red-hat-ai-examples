# Failure Mode: Hallucinated Tool Call

## What it is

The agent calls a tool that doesn't exist in its available tools list. The agent "hallucinates" a tool name — invoking something that was never defined in its tool set.

This is different from Tool Misuse (calling the *wrong* existing tool). Here the tool doesn't exist at all.

## Why it matters

A hallucinated tool call means the agent is operating outside its defined capabilities. In a real system, this would cause a runtime error — the tool doesn't exist, so the call fails.

## Scenario used

A travel booking agent with flight-related tools (`search_flights`, `search_alternative_routes`, `get_flight_details`, `book_flight`, `search_and_book`, `verify_booking`, `cancel_booking`).

**Failing trace (single):** User asks to book a flight. Agent calls `check_passport("USR-12345")` — a tool that doesn't exist in its tool set — before calling `search_and_book` (which does exist). The agent hallucinated a passport-checking tool. The agent should have skipped the passport check entirely and proceeded directly with `search_and_book`.

**Failing trace (multiple):** User asks to book a flight and arrange airport transfer. Agent calls `search_and_book` (exists), then `book_transfer` and `arrange_pickup` — neither exists in its tool set. The scorer catches both hallucinated tools in one pass. The agent should have completed only the flight booking using its available tools and informed the user that airport transfer is outside its capabilities.

**Passing trace:** User asks to book a flight. Agent calls only `search_and_book` — a tool that exists in its set.

## Scorers

No existing MLflow scorer is designed to check whether called tools exist in the agent's available set. `ToolCallCorrectness` might catch this incidentally (its prompt sees the available tools list), but it evaluates tool selection *quality*, not *existence* — a deterministic check is more reliable and has no LLM cost. We build a custom scorer using `@scorer` — MLflow's decorator for writing evaluation logic in Python. We call this scorer `tool_existence_check`.

### `tool_existence_check`

A deterministic set membership check — verifies that every tool the agent called exists in its available tools set.

**Import:** `from mlflow.genai.scorers import scorer`

**Needs expectations:** No — available tools come from the trace

**Type:** Deterministic (no LLM)

**How it works:**

1. Reads the available tool definitions from the agent span's `mlflow.chat.tools` attribute
2. Extracts the names of all TOOL spans from the trace
3. Checks if every called tool name exists in the available tools set: `called_tools ⊆ available_tools`
4. Returns `yes` if all tools exist, `no` if any are hallucinated
5. The rationale lists exactly which tools were hallucinated and what tools are actually available

## `@scorer` vs `make_judge()`

MLflow provides two patterns for custom scorers:

- **`@scorer`** — write evaluation logic in Python. Use when the check is deterministic: set membership, threshold comparison, pattern matching. No LLM cost, instant, perfectly reproducible.
- **`make_judge()`** — delegate evaluation to an LLM. Use when the check requires reasoning or judgment that can't be reduced to a simple rule.

Tool existence is a set membership check — `@scorer` is the right choice. Compare this to Graceful Refusal, where judging whether a refusal was appropriate requires understanding context and intent — that needs `make_judge()`.

## Scorer comparison

| Scorer | Type | What it checks | Deterministic? | Needs expectations? |
|---|---|---|---|---|
| Custom `@scorer` | Deterministic | `called_tools ⊆ available_tools` | Yes | No |

## Limitations

- **Name-only matching:** The scorer checks tool names, not whether the agent used the tool correctly. An agent that calls a valid tool with completely wrong arguments will pass this check — use Tool Misuse (FM01) to catch that.
- **Requires `mlflow.chat.tools` attribute:** The scorer reads the available tools list from the agent span. If the agent framework doesn't populate this attribute, the scorer can't determine what tools are available.
- **No alias handling:** If the agent calls a tool by a different name or alias (e.g., `flight_search` instead of `search_flights`), the scorer treats it as hallucinated even if the intent maps to a valid tool.

## Notebook

See [08_hallucinated_tool_call.ipynb](08_hallucinated_tool_call.ipynb) to run the evaluation on synthetic traces.
