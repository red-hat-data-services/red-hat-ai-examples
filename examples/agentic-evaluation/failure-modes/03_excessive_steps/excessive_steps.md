# Failure Mode: Excessive Steps

## What it is

The agent completes the task but takes more steps than necessary. The final answer may be correct, but the path to get there is wasteful.

**Sub-cases:**

- **Redundant calls** — agent makes tool calls it didn't need to. This includes duplicate calls (same tool, same arguments, repeated), unnecessary calls (a tool that adds no value because another tool already returned the data), and unconsolidated calls (multiple separate calls to the same tool that could have been combined into a single call with multiple arguments).
- **Longer path** — agent takes more steps than necessary by choosing a roundabout sequence of tools when a shorter path exists (e.g., using `search_flights` → `get_flight_details` → `book_flight` when `search_and_book` does it in one call).

## Why it matters

Excessive steps waste compute, increase latency, and can incur unnecessary API costs. In production, they may also signal that the agent is confused or stuck in a suboptimal reasoning pattern — even if it eventually arrives at the right answer.

Unlike Tool Misuse (wrong tool) or Goal Achievement (wrong answer), the agent gets the right result here. The problem is efficiency, not correctness.

## Scenario used

Two scenarios demonstrate the two sub-cases:

**Scenario 1 — Redundant calls:** A user asks "What's the weather like in Paris right now?" The agent has `get_weather` and `web_search` available. The agent calls `get_weather("Paris")` twice with identical arguments (duplicate), then calls `web_search("current weather in Paris")` even though `get_weather` already returned the data (unnecessary). Three tool calls where one would suffice.

**Scenario 2 — Longer path:** A user asks "Book me a flight from NYC to London on July 20." The agent has `search_flights`, `get_flight_details`, `book_flight`, and `search_and_book` available. The agent calls `search_flights` → `get_flight_details` → `book_flight` (3 steps) when `search_and_book` would do it in 1 step. Each call is individually valid — the agent just chose a roundabout path.

**Passing traces:** Each agent completes its task in a single tool call.

## Scorers

### ToolCallEfficiency (MLflow native)

Evaluates whether the agent's tool usage is efficient — catching both redundant calls and longer-than-necessary paths.

**Import:** `from mlflow.genai.scorers import ToolCallEfficiency`

**Needs expectations:** No

**Type:** LLM judge

**How it works:** The scorer builds a prompt with three components:

- **Request** — the user's original question
- **Available tools** — the tool definitions from the trace (via `mlflow.chat.tools`)
- **Tools called** — the sequence of tool calls the agent made (names, arguments, and outputs)

The main instruction is broad: *"Consider the agent's tool usage for redundancy and inefficiency. Given the user's request, the available tools, and the sequence of tools called by the agent, determine whether any tool calls were unnecessary or could have been made more efficient."*

The prompt then highlights three patterns to consider in particular:

1. *"Calls to the same tool with identical or very similar arguments"*
2. *"Repeated calls to the same tool with the same parameters"*
3. *"Multiple calls that could reasonably have been consolidated into a single call"*

Returns `yes` (efficient) or `no` (inefficient calls found), with a rationale explaining which specific calls are inefficient and why.

**Error retries are treated as efficient:** The prompt explicitly instructs: *"Treat retries caused by temporary tool failures (e.g., timeouts, transient errors) as efficient and not redundant."* This means an agent that retries a failed call is not penalized — only genuinely unnecessary or suboptimal calls are flagged.

> *Prompt text from MLflow 3.14.0*

**What it sees:** The user's request, available tool definitions, and the sequence of tool calls (names, arguments, and outputs).

## Scorer comparison

| Scorer | Type | Catches redundant calls? | Catches longer path? | Needs expectations? |
|---|---|---|---|---|
| `ToolCallEfficiency` | LLM judge | Yes | Yes | No |

## Notebook

See [03_excessive_steps.ipynb](03_excessive_steps.ipynb) to run the evaluation on synthetic traces.
