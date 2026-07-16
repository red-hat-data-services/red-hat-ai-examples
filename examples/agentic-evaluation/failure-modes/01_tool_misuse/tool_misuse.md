# Failure Mode: Tool Misuse

## What it is

The agent selects the wrong tool for the task, or passes incorrect arguments to the right tool. The agent has access to the correct tool but chooses a different one — or calls the right tool with wrong parameters.

**Sub-cases:**

- **Wrong tool** — agent calls `web_search` when it should call `get_weather`
- **Wrong arguments** — agent calls `get_weather("London")` when the user asked about Paris

## Why it matters

Tool misuse can produce irrelevant or misleading results even though the agent appears to have completed the task. The response looks normal — it doesn't crash or error out — but the answer is wrong because it came from the wrong source. This is hard to catch without evaluation because the output looks plausible.

It also wastes resources: calling an expensive tool unnecessarily, or making multiple tool calls when one correct call would suffice.

## Scenario used

A user asks "What's the weather like in Paris right now?" The agent has two tools available:

- `get_weather(location)` — returns current weather data
- `web_search(query)` — general web search

**Failing trace (wrong tool):** The agent calls `web_search("weather in Paris")` and gets travel guide results. It responds with travel advice instead of weather data.

**Failing trace (wrong arguments):** The agent calls `get_weather("London")` — the right tool, but with the wrong location. It responds with accurate weather data for London, which doesn't answer the question about Paris.

**Passing trace:** The agent calls `get_weather("Paris")` and gets temperature, condition, and humidity. It responds with accurate weather data.

## Scorers

### ToolCallCorrectness (MLflow native)

Evaluates whether the agent's tool selection was appropriate. Supports three modes: ground-truth-free (LLM judge, no expectations), fuzzy match (LLM judge, with expectations), and exact match (deterministic, no LLM).

**Import:** `from mlflow.genai.scorers import ToolCallCorrectness`

**Needs expectations:** Optional — works without (ground-truth-free) or with (fuzzy/exact match)

**Type:** LLM judge (ground-truth-free and fuzzy match) / Deterministic (exact match)

**1. Ground-truth-free (default)** — no expectations needed. The scorer reads:

- The user's request
- The available tools and their descriptions (from `mlflow.chat.tools` in the trace)
- The actual tool calls the agent made

It evaluates four criteria:

- Was using a tool necessary for this request?
- Is each tool a good match for the subtask?
- Do the arguments match the tool's schema?
- Is the tool call sequence logical?

The prompt explicitly asks: *"For each step, is the chosen tool a good match for the subtask?"* and *"Do the arguments match the tool's schema?"*

**2. Fuzzy match** — with expectations. Compares actual tool calls against expected ones using semantic similarity. The LLM assesses whether the actual calls "semantically match" the expected ones, allowing for minor variations.

**3. Exact match** (`should_exact_match=True`) — deterministic, no LLM needed. Direct set/sequence comparison of tool names and (optionally) arguments. Returns `yes`/`no` based on whether the actual calls match the expected calls exactly.

To check that tools were called in a specific order, enable `should_consider_ordering=True`. Uses strict position-by-position comparison — every position must match exactly, or the whole check fails.

### ToolCorrectness (DeepEval via MLflow)

A third-party scorer that compares called tools against expected tools using deterministic matching. Optionally adds an LLM layer for tool selection quality scoring.

**Import:** `from mlflow.genai.scorers.deepeval import ToolCorrectness`

**Needs expectations:** Yes

**Type:** Deterministic by default. An optional LLM layer activates only when `available_tools` is passed to the constructor — it scores tool selection quality (Correct Selection, Over-selection, Under-selection, Mis-selection). The final score is `min(deterministic, LLM)`. Without `available_tools`, only the deterministic comparison runs.

**Argument checking:** Off by default (name-only matching). To enable, pass `evaluation_params=[ToolCallParams.INPUT_PARAMETERS]` (imported from `deepeval.test_case`).

**Ordered matching:** Off by default. Enable with `should_consider_ordering=True`. Uses LCS (Longest Common Subsequence) — finds the longest matching subsequence, so partial ordering still gets credit. More forgiving than ToolCallCorrectness's strict position-by-position comparison.

**Expectations format:** ToolCorrectness uses `input_parameters` as the key for expected arguments, while MLflow's native `ToolCallCorrectness` uses `arguments`. When logging expectations with `mlflow.log_expectation()`, use the key that matches the scorer you're running.

## Scorer comparison

| Scorer | Type | Needs expectations? | Catches wrong tool? | Catches wrong args? | Ordered matching |
|---|---|---|---|---|---|
| `ToolCallCorrectness` (ground-truth-free) | LLM judge | No | Yes | Yes | N/A |
| `ToolCallCorrectness` (exact match) | Deterministic | Yes | Yes | Yes | Strict position-by-position |
| `ToolCorrectness` | Deterministic | Yes | Yes | Only with `evaluation_params` | LCS-based (partial credit) |

**When to use which:**

- **ToolCallCorrectness (ground-truth-free):** Exploratory evaluation — catches both wrong tools and wrong arguments without expectations.
- **ToolCallCorrectness (exact match):** CI/CD pipelines — deterministic, catches both, no LLM cost.
- **ToolCorrectness:** When you need LCS-based ordered matching, or want a DeepEval-specific evaluation alongside MLflow native scorers for comparison.

## Logging expectations

Approaches 2 and 3 both require expected tool calls. We attach them to traces using `mlflow.log_expectation()` — this logs expectations directly on the trace objects in the MLflow server. Each scorer uses a different key:

- `ToolCallCorrectness`: `{"name": "get_weather", "arguments": {"location": "Paris"}}`
- `ToolCorrectness`: `{"name": "get_weather", "input_parameters": {"location": "Paris"}}`

Expectations are logged **after** Approach 1 runs to avoid affecting the ground-truth-free LLM judge mode.

## Notebook

See [01_tool_misuse.ipynb](01_tool_misuse.ipynb) to run the evaluation on synthetic traces.
