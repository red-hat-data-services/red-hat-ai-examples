# Agentic Evaluation with MLflow

## Background

### What is an agent?

An agent is a system built around an LLM that can use tools, make decisions, and take actions across multiple steps to accomplish a task. The LLM is the brain, but the agent adds the ability to interact with external systems — calling APIs, querying databases, reading files, booking flights. A travel booking agent, for example, might search for flights, compare prices, book a ticket, and confirm the reservation — all autonomously.

But if the agent is doing all of this on its own, how do you know it's doing it correctly?

### Why agent evaluation is different

Evaluating an LLM on its own is about measuring response quality — metrics like perplexity, BLEU, ROUGE, or human preference scores tell you how good the output text is. But once that LLM is wrapped in an agent, the response is only one piece of the puzzle. The agent also selects tools, passes arguments, interprets results, and decides what to do next. A correct final response doesn't mean the agent took the right path to get there — and a plausible-looking response can hide serious mistakes made along the way.

To evaluate what happened along the way, you need to see it. This is where MLflow tracing comes in.

### Traces — capturing the workflow

MLflow's tracing layer captures the agent's full workflow as a structured trace — the user's request, each tool call (name, arguments, outputs), and the agent's final response. These traces give you visibility into every decision the agent made, and they're what the evaluation runs against.

Once you can see the workflow, the question becomes: what should you check for? This depends on the kinds of mistakes agents make — their failure modes.

### Failure modes — what can go wrong

Agents fail in ways that are specific to their tool-using, decision-making nature. These failure patterns are called failure modes. For example, some of the failure modes could be:

- Calling the wrong tool for the task (tool misuse)
- Giving a partial answer that omits key information (goal achievement)
- Making redundant or unnecessary tool calls (excessive steps)
- Exposing sensitive data like names or SSNs in its response (PII leakage)
- Saying "your flight is booked!" when the booking tool actually failed (hallucinated completion)
- Attempting a task it has no tools for, or refusing one it can handle (graceful refusal)

Some failure modes are universal — any agent can leak PII or hallucinate a response regardless of its domain. Others are domain-specific — a medical agent giving a partial diagnosis is a critical failure, while a weather agent omitting humidity is a minor inconvenience. Same failure mode, different severity depending on the use case.

Detecting these failure modes manually by reading traces doesn't scale. You need automated checks — this is what MLflow scorers provide.

### Scorers — detecting failure modes

MLflow provides scorers — automated checks that take a trace as input and return a verdict: did this trace exhibit the failure mode or not? There are two types:

- **Deterministic scorers** — rule-based checks. Fast, cheap, and reproducible. Example: checking if a called tool actually exists in the agent's tool set.
- **LLM judge scorers** — use an LLM to assess the trace. More flexible and able to handle nuanced judgments, but slower and costlier. Example: judging whether an agent's refusal was appropriate.

MLflow provides built-in scorers and integrations with DeepEval, RAGAS, and Guardrails AI. When no existing scorer fits, you can build custom ones using MLflow's `@scorer` decorator or `make_judge()` function.

Some scorers can judge a trace on their own. Others need to be told what "correct" looks like — this is where expectations come in.

### Expectations — ground truth for scorers

Expectations are ground truth you provide to help a scorer judge more accurately — for example, the expected tool calls, the expected facts in the response, or a reference answer. Without expectations, the scorer has to infer correctness on its own.

There's a tradeoff:

- **With expectations** — scorers are more accurate, especially for subtle failures that require domain expertise to recognize. If judging correctness is difficult even for a human without context, the scorer needs expectations too.
- **Without expectations** — scorers can run against much larger datasets because you don't need to manually create ground truth for every test case. Getting expectations at scale is often infeasible.

In practice, use expectation-free scorers for broad coverage across large datasets, and expectation-based scorers for critical subsets where accuracy matters most.

Each notebook in this repo demonstrates scorers — some with expectations, some without — so you can see the tradeoff in action. The traces these scorers run against are synthetic.

### Why synthetic traces?

These notebooks use synthetic traces to demonstrate how each scorer works — hardcoded mock functions that produce the same trace structure a real agent would, with predetermined tool calls and responses. No LLM or API keys are needed to create them.

With a real agent, you would skip trace creation entirely — MLflow's autolog captures traces automatically, and you'd run the same scorers against those real traces.

### How to use these notebooks

**Read this README first** — it provides the background context that the notebooks assume. Each notebook focuses on demonstrating scorers, not re-explaining the concepts above.

Every notebook follows the same structure:

1. **Setup** — connects to the MLflow server and cleans up old traces
2. **Create traces** — builds synthetic traces that demonstrate the failure mode (passing and failing cases)
3. **Load traces** — fetches the traces from the server
4. **Evaluate** — runs one or more scorers against the traces and prints results
5. **Interpret** — explains what the scores mean and when to use each scorer

The notebooks can be run in any order, but there's a natural learning path: notebooks 1–4 use existing MLflow scorers (built-in and third-party integrations), then notebooks 5+ introduce custom scorers built with `@scorer` and `make_judge()`. If you're new to agent evaluation, start with notebook 1 (Tool Misuse) and work through them in order.

## Setup

### 1. Navigate to the project directory

All commands below assume you are in the `examples/agentic-evaluation/` directory:

```bash
cd examples/agentic-evaluation
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Copy the example file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and set the API key environment variable according to your model provider. The notebooks use OpenAI by default, but you can use any provider MLflow supports by changing the `model=` parameter in the scorer constructors:

| Provider | API key env var | Model parameter example |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `model="openai:/gpt-4o"` |
| Anthropic | `ANTHROPIC_API_KEY` | `model="anthropic:/claude-sonnet-5"` |
| Google | `GOOGLE_API_KEY` | `model="google:/gemini-2.0-flash"` |

### 4. Start an MLflow server

```bash
mlflow server --host 127.0.0.1 --port 5000
```

The notebooks create synthetic traces on this server and evaluate them. After running a notebook, you can view the traces and evaluation results in the MLflow UI at `http://localhost:5000`.

## Failure Modes

Each failure mode has its own self-contained notebook that creates traces, evaluates them, and cleans up after itself. Run them in any order.

| # | Failure Mode | Scorers | Notebook |
|---|---|---|---|
| 1 | [Tool Misuse](failure-modes/01_tool_misuse/) | `ToolCallCorrectness` (MLflow), `ToolCorrectness` (DeepEval) | [01_tool_misuse.ipynb](failure-modes/01_tool_misuse/01_tool_misuse.ipynb) |
| 2 | [Goal Achievement](failure-modes/02_goal_achievement/) | `Correctness` (MLflow), `AgentGoalAccuracyWithReference` (RAGAS), `TaskCompletion` (DeepEval), `AgentGoalAccuracyWithoutReference` (RAGAS) | [02_goal_achievement.ipynb](failure-modes/02_goal_achievement/02_goal_achievement.ipynb) |
| 3 | [Excessive Steps](failure-modes/03_excessive_steps/) | `ToolCallEfficiency` (MLflow) | [03_excessive_steps.ipynb](failure-modes/03_excessive_steps/03_excessive_steps.ipynb) |
| 4 | [PII Leakage](failure-modes/04_pii_leakage/) | `DetectPII` (Guardrails AI), `PIILeakage` (DeepEval) | [04_pii_leakage.ipynb](failure-modes/04_pii_leakage/04_pii_leakage.ipynb) |
| 5 | [Graceful Refusal](failure-modes/05_graceful_refusal/) | Custom `make_judge()` | [05_graceful_refusal.ipynb](failure-modes/05_graceful_refusal/05_graceful_refusal.ipynb) |
| 7 | [Repeated Action Loop](failure-modes/07_repeated_action_loop/) | Custom `@scorer` (MLflow), custom `make_judge()` (MLflow) | [07_repeated_action_loop.ipynb](failure-modes/07_repeated_action_loop/07_repeated_action_loop.ipynb) |

## Project Structure

```text
agentic-evaluation/
  .env.example          — environment variable template
  requirements.txt      — pinned dependencies
  tools.py              — shared tool definitions
  utils.py              — shared evaluation helper
  failure-modes/
    01_tool_misuse/      — notebook + docs + README
    02_goal_achievement/ — notebook + docs + README
    03_excessive_steps/  — notebook + docs + README
    04_pii_leakage/      — notebook + docs + README
    05_graceful_refusal/ — notebook + docs + README
    07_repeated_action_loop/ — notebook + docs + README
```

`tools.py` contains the tool definitions (function name, description, parameters) used by the simulated agents in the notebooks. Each failure mode imports the tools it needs. You don't need to modify this file unless you're adding new failure modes.
