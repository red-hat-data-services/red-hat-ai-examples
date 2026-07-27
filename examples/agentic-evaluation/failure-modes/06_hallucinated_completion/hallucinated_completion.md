# Failure Mode: Hallucinated Completion

## What it is

The agent's final response is not grounded in evidence from its trace. The agent says something that contradicts or has no support in what the tools actually returned.

**Sub-cases:**

- **Ungrounded response** — the response contradicts what tools actually returned (e.g., tool returns price "$450", agent says "$299")
- **Fabricated action** — the agent claims it performed actions that don't appear in the trace (e.g., "your booking is confirmed!" when the booking tool was never called or returned an error)

## Why it matters

Hallucinated completions erode user trust and can cause real harm. A travel agent that reports the wrong price leads to unexpected charges. A coding agent that says "tests pass!" when no tests ran gives false confidence before a deploy. A medical agent that fabricates a diagnosis from thin air is dangerous. Unlike other failure modes that affect efficiency or scope, hallucinated completions deliver confidently wrong information — the most dangerous kind of failure because users have no reason to doubt it.

## Scenario used

A user asks a travel booking agent to "Book me a flight from NYC to London on July 20." Four traces test different hallucination patterns:

**Failing traces:**

1. **Ungrounded response (wrong price):** The agent calls `search_and_book` which returns `{"booking_id": "BK-456", "flight_id": "FL-123", "price": 450, "status": "confirmed"}`. The agent responds: *"Your flight is booked! The total cost was $299."* — contradicts the $450 price from the tool.

2. **Fabricated action — tool failed:** The agent calls `search_and_book` which returns `{"status": "failed", "reason": "no flights available"}`. The agent responds: *"Your flight is booked! Booking reference: BK-789."* — fabricates a successful booking when the tool returned a failure.

3. **Fabricated action — no tool called:** The agent makes no tool calls at all. The agent responds: *"Your flight is booked! Booking reference: BK-101."* — claims to have completed the task without ever calling a tool. The trace has zero tool spans.

**Passing trace:**

1. **Grounded response:** The agent calls `search_and_book` which returns `{"booking_id": "BK-456", "flight_id": "FL-123", "price": 450, "status": "confirmed"}`. The agent responds: *"Your flight is booked! NYC to London, July 20, flight FL-123. Total: $450. Booking reference: BK-456."* — accurately reflects the tool output.

## Scorers

This is the first failure mode scorer to use `@scorer` — MLflow's decorator for writing custom evaluation logic in Python. The [Graceful Refusal](../05_graceful_refusal/05_graceful_refusal.ipynb) notebook introduced `make_judge()` for custom LLM judges; `@scorer` is the second pattern, used here to wrap an existing MLflow judge with custom context extraction.

### `grounded_in_tools` (custom `@scorer` wrapping MLflow's `is_grounded()`)

**Import:** `from mlflow.genai.judges import is_grounded` and `from mlflow.genai.scorers import scorer`

**Needs expectations:** No — context comes from tool outputs in the trace

**Type:** LLM judge (existing MLflow judge, custom wrapper)

**Why not use `RetrievalGroundedness` directly?**

MLflow has `RetrievalGroundedness` and several third-party groundedness/faithfulness scorers, but they all extract context from RETRIEVER spans only. For agentic traces with TOOL spans (not RETRIEVER spans), these scorers find no context to check against.

However, MLflow exposes `is_grounded()` — the lower-level judge function that `RetrievalGroundedness` uses internally. It accepts a `context` parameter directly, so we can pass tool outputs as context directly.

**How `is_grounded()` works:**

The groundedness prompt receives:

- `<claim>` — the user's question + the agent's response
- `<document>` — the context we provide (tool outputs)

The instruction: *"You must determine whether the claim is supported by the document. Do not focus on the correctness or completeness of the claim. Do not make assumptions, approximations, or bring in external knowledge."*

This covers both sub-cases:

- **Ungrounded response:** The response says "$299" — the judge sees `search_and_book` returned `"price": 450` → contradiction → "not supported"
- **Fabricated action (tool failed):** The response says "booking confirmed" — the judge sees the tool returned `"status": "failed"` → contradiction → "not supported"

Returns `yes` (grounded) or `no` (not grounded) with a rationale.

> *Prompt text from `mlflow/genai/judges/prompts/groundedness.py`*

**The `@scorer` wrapper:**

We wrap `is_grounded()` in an `@scorer`-decorated function so it can run inside `mlflow.genai.evaluate()`:

1. Extracts tool outputs from the trace (name, inputs, outputs for each TOOL span)
2. If no tool spans exist, short-circuits with `no` — nothing to ground against
3. Extracts the request and response from the root span
4. Passes everything to `is_grounded()` and returns the result

```python
@scorer
def grounded_in_tools(*, trace: Trace) -> Feedback:
    tool_spans = trace.search_spans(span_type=SpanType.TOOL)

    if not tool_spans:
        return Feedback(
            value="no",
            rationale=(
                "No tool calls found in the trace. "
                "The agent's response has no evidence to be grounded in."
            ),
        )

    context = [
        {"content": f"{ts.name}({ts.inputs}) → {ts.outputs}"}
        for ts in tool_spans
    ]

    root = trace.data.spans[0]
    request = str(root.inputs)
    response = str(root.outputs)

    return is_grounded(
        request=request,
        response=response,
        context=context,
        name="grounded_in_tools",
        model="openai:/gpt-4o",
    )
```

**What it sees:** The full trace — specifically all TOOL span names, inputs, and outputs, plus the root span's inputs (request) and outputs (response). This is different from most existing scorers which only see the response text.

**What it catches:** Both hallucination sub-cases — contradictions against tool output (ungrounded) and claims with no supporting evidence (fabricated). The prompt's instruction to "not make assumptions or bring in external knowledge" ensures that claims about actions not present in the context are flagged as unsupported.

**Limitations:** Relies on an LLM judge, so results may vary slightly between runs. The quality of detection depends on how clearly tool outputs map to the agent's claims — highly paraphrased or indirect references may occasionally pass.

## Scorer comparison

| Scorer | Type | Looks at | Catches ungrounded? | Catches fabricated? | Needs expectations? |
|---|---|---|---|---|---|
| `grounded_in_tools` | LLM judge (`is_grounded()` wrapper) | Tool outputs from trace | Yes | Yes | No |
| `RetrievalGroundedness` (MLflow) | LLM judge | RETRIEVER spans only | No (no context for TOOL spans) | No | No |

**When to use `grounded_in_tools`:** Whenever your agent uses TOOL spans and you need to verify that the final response accurately reflects what tools returned. This is the primary use case for agentic evaluation — most agents call tools, not retrievers.

**When to use `RetrievalGroundedness`:** When your application is a RAG pipeline with RETRIEVER spans and you want to check whether the response is grounded in retrieved documents.

## Notebook

See [06_hallucinated_completion.ipynb](06_hallucinated_completion.ipynb) to run the evaluation on synthetic traces.
