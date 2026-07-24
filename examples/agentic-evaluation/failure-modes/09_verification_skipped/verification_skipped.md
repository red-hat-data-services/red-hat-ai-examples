# Failure Mode: Verification Skipped

## What it is

The agent completes an action but doesn't use available tools to verify the result. It reports success to the user without confirming the action actually went through.

## Why it matters

An unverified action is a silent assumption. If the agent books a flight and tells the user "you're all set" without checking, the booking could have failed, been waitlisted, or encountered an error — and the user wouldn't know until they show up at the airport. When a verification tool is available and the action's response doesn't confirm success on its own, the agent should use it.

This is distinct from other failure modes. Tool Misuse (FM1) checks whether the agent called the right tool with the right arguments. Goal Achievement (FM2) checks whether the agent's response matches the expected outcome. Verification Skipped checks whether the agent confirmed the outcome of its own action before reporting it as done.

## When verification is and isn't needed

Not every action requires a separate verification step:

- **Verification needed:** The action tool returns a minimal response — just a booking ID with no confirmation status. The agent doesn't know if the action succeeded and should call the verification tool.
- **Verification not needed:** The action tool returns a comprehensive response including confirmation status, full details, and price. The tool itself already confirmed success — calling a verification tool on top of that is redundant.
- **Verification not needed:** The agent performed a read-only action (like a search). Nothing changed, nothing to verify.
- **Verification not possible:** No verification tool is available in the agent's toolset. The agent can't verify what it has no tool to check.

This nuance is why a deterministic check ("was `verify_booking` called?") would be too rigid. An LLM judge can reason about whether verification was warranted given the action tool's response.

## Scenario used

A travel booking agent with `TRAVEL_AGENT_TOOLS` including `verify_booking`. The notebook creates three traces:

- **Unverified booking (fail):** User asks "Book me a flight from NYC to London on August 15." Agent calls `search_flights` to find a flight, then `book_flight` which returns a minimal response: `{"booking_id": "BK-901"}`. The agent tells the user "Your flight is booked!" without calling `verify_booking`. This is wrong because the minimal response doesn't confirm success — the agent should have verified before reporting.
- **Verified booking (pass):** Same request. Agent calls `search_flights`, then `book_flight` which returns the same minimal `{"booking_id": "BK-902"}`. The agent then calls `verify_booking` which returns `{"booking_id": "BK-902", "status": "confirmed", "flight_id": "FL-301"}`. Only after confirmation does the agent tell the user the flight is booked.
- **Self-confirming action (pass):** Same request. Agent calls `search_and_book` which returns a comprehensive response: `{"booking_id": "BK-903", "flight_id": "FL-302", "airline": "BA", "price": 450, "departure": "08:00", "arrival": "20:00", "status": "confirmed"}`. The action tool already confirmed success — skipping `verify_booking` is reasonable.

## Scorers

### Custom `make_judge()` (MLflow native)

Assesses whether the agent verified its action when verification was warranted, based on the request, response, available tools, and tool call results.

**Import:** `from mlflow.genai.judges import make_judge`

**Needs expectations:** No

**Type:** LLM judge (custom)

**How it works:** `make_judge()` takes an `instructions` string that defines the evaluation criteria. The instructions reference template variables:

- `{{ inputs }}` — the user's request (substituted inline as JSON in the prompt)
- `{{ outputs }}` — the agent's response (substituted inline as JSON in the prompt)
- `{{ trace }}` — the agent's execution trace. Rather than substituting trace data inline, MLflow switches the judge into **agentic mode** — the judge LLM receives tools (`get_root_span`, `list_spans`, `get_span`, etc.) to inspect the trace step by step.

**The instructions evaluate four rules:**

1. Identify whether the agent took a state-changing action (booking, cancellation, etc.).
2. Check whether a verification tool was available in the agent's toolset.
3. Examine the action tool's response — if it already includes comprehensive confirmation details, separate verification is not necessary.
4. If the action tool's response was minimal, the agent should have called the verification tool before reporting success.

Returns `yes` (verified or verification not needed) or `no` (skipped verification when it was warranted) with a rationale.

## Scorer comparison

| Scorer | Type | What it checks | Catches unverified actions? | Handles self-confirming tools? | Needs expectations? |
|---|---|---|---|---|---|
| Custom `make_judge()` | LLM judge | Whether verification was warranted and performed | Yes | Yes — passes when action tool already confirmed | No |

## Limitations

- **LLM judge:** Requires an LLM API key, is slower and costlier than a deterministic scorer, and is non-deterministic — verdicts may vary slightly between runs or judge models. Borderline cases (e.g., a response that includes partial confirmation) may be judged differently across runs.
- **Context-dependent:** What counts as "comprehensive confirmation" is a judgment call. The instructions define guidelines, but the LLM applies them — different judge models may draw the line differently.

## Notebook

See [09_verification_skipped.ipynb](09_verification_skipped.ipynb) to run the evaluation on synthetic traces.
