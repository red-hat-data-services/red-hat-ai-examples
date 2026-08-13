# End-to-End Agent Evaluation

This notebook demonstrates the full agent evaluation workflow — build a real agent, trace its behavior with MLflow on [Red Hat OpenShift AI](https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-ai) (RHOAI), and evaluate those traces using the [tiered scoring strategy](../README.md#cost-effective-evaluation-strategy). A local MLflow server can also be used as an alternative.

The [failure mode notebooks](../README.md#failure-modes) (01–09) teach individual failure modes using synthetic traces. This notebook runs a real agent against real queries and evaluates the traces across all 9 failure modes.

## What it builds

A **National Parks trip planning assistant** using LangGraph (LangChain's agent framework). The agent:

- Answers questions about U.S. national parks using the [NPS API](https://www.nps.gov/subjects/developer/api-documentation.htm) (park info, alerts, campgrounds, events, visitor centers)
- Saves and verifies trip itineraries to disk
- Is traced automatically via `mlflow.langchain.autolog()`

Inspired by the [NPS agent](https://github.com/opendatahub-io/agents/tree/main/examples/agents_tracing-eval_mlflow/nps_agent) which uses an MCP server for tool integration. For simplicity, tools are defined directly in the notebook.

## How evaluation works

The notebook uses a **two-tier evaluation strategy**:

1. **Tier 1 — Deterministic scorers** run on all traces (free, fast)
2. **Gating check** — if Tier 1 catches a failure mode on ≥`GATE_THRESHOLD` traces (default 2), the problem is confirmed — skip its Tier 2 counterpart. A single failure could be noise, so the LLM judge still runs to investigate.
3. **Tier 2 — LLM judges** run selectively (costs tokens, catches subtler issues)

| Tier | Group | Scorers | Runs on |
|---|---|---|---|
| 1 | — | `pii_check`, `tool_existence_check`, `repeated_action_loop`, `ToolCallCorrectness(exact_match)` | All traces (exact match only on traces with expectations) |
| 2 | Universal | `graceful_refusal`, `grounded_in_tools`, `verification_check`, `semantic_loop_check`, `AgentGoalAccuracyWithoutReference` | All sampled traces |
| 2 | Tool-dependent | `ToolCallEfficiency`, `ToolCallCorrectness(LLM)` | Non-refusal traces only |

### Failure mode → scorer mapping

For each failure mode, these are the scorers that detect it:

| Failure Mode | Tier 1 (deterministic) | Tier 2 (LLM judge) |
|---|---|---|
| Tool Misuse | `ToolCallCorrectness` (exact match) | `ToolCallCorrectness` (LLM) |
| Goal Achievement | — | `AgentGoalAccuracyWithoutReference` |
| Excessive Steps | — | `ToolCallEfficiency` |
| PII Leakage | `pii_check` | — |
| Graceful Refusal | — | `graceful_refusal` |
| Hallucinated Completion | — | `grounded_in_tools` |
| Repeated Action Loop | `repeated_action_loop` | `semantic_loop_check` |
| Hallucinated Tool Call | `tool_existence_check` | — |
| Verification Skipped | — | `verification_check` |

Failure modes with both tiers use gating: if the Tier 1 scorer catches enough failures (≥`GATE_THRESHOLD`), the Tier 2 counterpart is skipped.

Custom scorers are defined in [`scorers.py`](scorers.py). Built-in scorers come from `mlflow.genai.scorers`.

## Prerequisites

1. Complete the [project setup](../README.md#setup) (dependencies, API keys, MLflow tracking)

2. **NPS API key** (free) — register at <https://www.nps.gov/subjects/developer/get-started.htm> and add to `.env`:

   ```ini
   NPS_API_KEY=your-nps-api-key
   ```

   If not set, the notebook falls back to `DEMO_KEY` which has stricter rate limits.

3. **`MLFLOW_GENAI_EVAL_MAX_WORKERS=1`** must be set in `.env` (already included in `.env.example`). Required because the `pii_check` scorer uses Guardrails AI's `DetectPII`, which has threading conflicts with MLflow's parallel evaluation pipeline. The tradeoff is sequential scorer execution — slower for large trace sets, but necessary for compatibility.

## Running the notebook

Open [agent_evaluation_end_to_end.ipynb](agent_evaluation_end_to_end.ipynb) and run all cells. The notebook:

1. Defines 7 tools (5 NPS API + 2 custom)
2. Builds a ReAct agent with GPT-4o-mini
3. Sends 5 golden queries and captures evaluation traces
4. Logs expectations for queries that have ground truth
5. Runs Tier 1 deterministic scorers on all traces
6. Checks gating — skips LLM judges for failure modes already caught
7. Runs Tier 2 LLM judges selectively (universal on all traces, tool-dependent on non-refusal traces)

The notebook uses `gpt-4o-mini` as the agent model and `gpt-4.1` as the judge model for Tier 2 LLM scorers. Both are configurable in the first code cell.

## Files

| File | What it is |
|---|---|
| [agent_evaluation_end_to_end.ipynb](agent_evaluation_end_to_end.ipynb) | The notebook |
| [scorers.py](scorers.py) | Custom scorers organized by tier |
| [golden_queries.json](golden_queries.json) | 5 evaluation queries (3 with expectations) |
| `trip_plans/` | Saved trip itineraries (created at runtime) |

## Scorers used

| Scorer | Failure Mode | Tier | Type |
|---|---|---|---|
| `pii_check` | PII Leakage | 1 | Deterministic (wraps DetectPII) |
| `tool_existence_check` | Hallucinated Tool Call | 1 | Deterministic |
| `repeated_action_loop` | Repeated Action Loop | 1 | Deterministic |
| `ToolCallCorrectness(exact_match)` | Tool Misuse | 1 | Deterministic (requires expectations) |
| `graceful_refusal` | Graceful Refusal | 2 (universal) | LLM judge |
| `grounded_in_tools` | Hallucinated Completion | 2 (universal) | LLM judge |
| `verification_check` | Verification Skipped | 2 (universal) | LLM judge |
| `semantic_loop_check` | Repeated Action Loop | 2 (universal) | LLM judge (conditional — skipped if gated) |
| `AgentGoalAccuracyWithoutReference` | Goal Achievement | 2 (universal) | LLM judge |
| `ToolCallEfficiency` | Excessive Steps | 2 (tool-dependent) | LLM judge |
| `ToolCallCorrectness(LLM)` | Tool Misuse | 2 (tool-dependent) | LLM judge (conditional — skipped if gated) |
