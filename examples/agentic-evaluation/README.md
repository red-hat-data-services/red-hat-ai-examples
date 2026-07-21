# Agentic Evaluation with MLflow

Traditional LLM evaluation checks whether a model's response is correct. Agentic evaluation goes further — it checks the entire workflow: did the agent pick the right tools, pass the correct arguments, complete the user's goal, and avoid leaking sensitive data?

Agents fail in ways that are hard to catch — calling the wrong tool, giving partial answers, leaking PII, or refusing tasks they can handle. Knowing **what to evaluate** and **how to evaluate it** is critical.

This repo covers both:

- **What to evaluate** — common agent failure modes (tool misuse, goal achievement, excessive steps, PII leakage, and more). Each failure mode is defined, explained, and demonstrated with synthetic traces.
- **How to evaluate** — MLflow scorers that detect these failure modes. This includes existing scorers from MLflow and its third-party integrations (DeepEval, RAGAS, Guardrails AI), as well as custom scorers built with MLflow's `make_judge()` and `@scorer` APIs.

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

The notebooks create synthetic traces on this server and evaluate them.

## Failure Modes

Each failure mode has its own self-contained notebook that creates traces, evaluates them, and cleans up after itself. Run them in any order.

| # | Failure Mode | Scorers | Notebook |
|---|---|---|---|
| 1 | [Tool Misuse](failure-modes/01_tool_misuse/) | `ToolCallCorrectness` (MLflow), `ToolCorrectness` (DeepEval) | [01_tool_misuse.ipynb](failure-modes/01_tool_misuse/01_tool_misuse.ipynb) |
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
    07_repeated_action_loop/ — notebook + docs + README
```

`tools.py` contains the tool definitions (function name, description, parameters) used by the simulated agents in the notebooks. Each failure mode imports the tools it needs. You don't need to modify this file unless you're adding new failure modes.
