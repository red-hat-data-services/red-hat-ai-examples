# Failure Mode: Goal Achievement

## What it is

The agent finishes but doesn't actually satisfy what the user asked for. This is the most fundamental evaluation — did the agent do what it was supposed to do?

**Sub-cases:**

- **Partial answer** — agent addresses some parts of the request but not all (e.g., reports temperature but omits humidity)
- **Wrong answer** — agent completes confidently but the answer is factually incorrect
- **Refusal/failure to engage** — agent refuses or fails to engage with a reasonable request

## Why it matters

All other failure modes check *how* the agent worked. This one checks *whether* it worked. An agent that gives partial or wrong answers erodes user trust, even if it uses the right tools and completes without errors.

Partial answers are especially hard to catch because they look correct at first glance — the response contains some accurate information, but the user doesn't realize they're missing part of what they asked for.

## Scenario used

A user asks "What's the weather and humidity in Paris?" The agent calls `get_weather("Paris")` and the tool returns `{temperature_celsius: 22, condition: "partly cloudy", humidity: 65}`.

**Failing trace:** The agent responds "It's 22°C in Paris." — omits condition and humidity, only partially answers the question.

**Passing trace:** The agent responds "It's 22°C and partly cloudy in Paris, with 65% humidity." — fully answers the question.

Both traces use the same tool and get the same data back. The failure is in how the agent formulates its response, not in how it uses tools.

## Scorers

### Correctness (MLflow native)

Checks whether specific expected facts are present in the agent's response. Only reads the response text — does not see tool calls or trace structure.

**Import:** `from mlflow.genai.scorers import Correctness`

**Needs expectations:** Yes — `expected_facts` (list of strings) or `expected_response` (string)

**Type:** LLM judge

**How it works:** The scorer builds a prompt with three components:

- **Question** — the user's original request
- **Claim** — the expected facts you provide, formatted as a bulleted list
- **Document** — the user's question and the agent's response combined

The prompt instructs: *"You must determine whether the claim is supported by the document in the context of the question. Do not focus on the correctness or completeness of the claim. Do not make assumptions, approximations, or bring in external knowledge."*

All expected facts are checked together as a single claim. The LLM returns `yes` (all facts supported) or `no` (some unsupported).

**What it sees:** Input + response only. Does NOT read tool spans or trace structure.

**Best practice:** Use `expected_facts` over `expected_response` — more flexible, doesn't require word-for-word matching.

### AgentGoalAccuracyWithReference (RAGAS via MLflow)

Checks if the workflow outcome matches a reference answer you provide. Unlike `Correctness`, this scorer reads the **full conversation** (messages + tool calls), not just the response text.

**Import:** `from mlflow.genai.scorers.ragas import AgentGoalAccuracyWithReference`

**Needs expectations:** Yes — `expected_output` (string)

**Type:** LLM judge (two-step chain)

**How it works (two-step LLM chain):**

1. **Infer end state:** Reads the full conversation (user messages, AI responses, tool outputs). Instructs: *"Identify the end_state (the final outcome or result of the workflow)."*

2. **Compare end state vs reference:** *"Given desired outcome and achieved outcome, compare them and identify if they are the same (1) or different (0)."* Binary: 1.0 or 0.0.

> *Prompt text from RAGAS 0.4.3*

**Correctness vs AgentGoalAccuracyWithReference:** Both need expectations and both catch partial answers, but they differ in what they evaluate:

- **Correctness** only reads the **response text**. If the agent doesn't repeat all the details in its response, Correctness fails — even if the agent did the right work behind the scenes. For example, an agent that books a flight and responds "Done!" would fail Correctness because the response doesn't contain the expected facts about the booking.

- **AgentGoalAccuracyWithReference** reads the **full conversation** — messages, tool calls, and tool outputs. It knows the booking happened because it saw the `book_flight` tool call succeed, even if the response is just "Done!" This makes it more appropriate for action-oriented agents where the result is in the workflow, not the response text.

### TaskCompletion (DeepEval via MLflow)

Assesses whether the agent accomplished the task based on its workflow — input, response, and tool calls.

**Import:** `from mlflow.genai.scorers.deepeval import TaskCompletion`

**Needs expectations:** No

**Type:** LLM judge (two-step chain)

**How it works (two-step LLM chain):**

1. **Extract task and outcome:** Receives three separate fields — user input, agent response, and tool calls. Instructs: *"Given an agentic workflow comprised of a human input, AI response, and tools used by the AI, identify the task and the task_outcome. The task outcome should be solely factual, derived strictly from the workflow."*

2. **Generate verdict:** Compares task vs outcome: *"Compare how well the actual outcome aligns with the desired task."* Returns `yes` or `no` (mapped to 1.0 or 0.0 in metrics).

> *Prompt text from DeepEval 3.9.9*

**What it sees:** Input + response + tool calls (names, inputs, outputs extracted from TOOL spans).

**Important limitation:** Although the scorer receives the response and tool outputs as separate fields, its prompt treats them collectively as "the workflow." The LLM judge may conflate "data the agent retrieved" with "data the agent communicated to the user."

This means TaskCompletion may score a partial answer as fully completed if the tool returned the correct data — even when the agent omitted it from its response. The rationale may claim the data was "provided" because it appeared in the tool output, not because the user received it. **Retrieving the data ≠ communicating it to the user.** See the [notebook](02_goal_achievement.ipynb) for a concrete demonstration of this behavior.

### AgentGoalAccuracyWithoutReference (RAGAS via MLflow)

Same mechanism as `AgentGoalAccuracyWithReference` — same two-step chain, same prompts. The only difference is where the "desired outcome" comes from. No expectations needed.

**Import:** `from mlflow.genai.scorers.ragas import AgentGoalAccuracyWithoutReference`

**Needs expectations:** No

**Type:** LLM judge (two-step chain)

- **WithReference:** you provide the desired outcome as a reference string
- **WithoutReference:** the scorer infers the desired outcome from the user's request in the conversation

Both read the full conversation, both infer the end state the same way, both use the same comparison step. Choose WithReference when you have ground truth, WithoutReference when you don't.

**Why this catches partial answers:** Unlike TaskCompletion, the end state is inferred from what the agent actually told the user — not from what the tools returned. If the tool returned humidity but the agent didn't mention it, the end state won't include humidity, and the comparison against the user's goal (which asked for humidity) will fail.

## Scorer comparison

| Scorer | Type | Looks at | Catches partial answers? | Needs expectations? |
|---|---|---|---|---|
| `Correctness` | LLM judge | Input + response | Yes — missing facts = `no` | Yes |
| `AgentGoalAccuracyWithReference` | LLM judge | Full conversation (outcome vs reference) | Yes — compares outcome to reference | Yes |
| `TaskCompletion` | LLM judge | Input + response + tools | No — tool returned the data, so "completed" | No |
| `AgentGoalAccuracyWithoutReference` | LLM judge | Full conversation (goal vs end state) | Yes — end state derived from response, not tool output | No |

**Two pairs, different perspectives:**

The four scorers split into two pairs — with and without expectations — but each pair works differently:

**With expectations:**

- `Correctness` checks if facts appear in the **response text**. It doesn't see tool calls or workflow — just "did the response contain these facts?"
- `AgentGoalAccuracyWithReference` reads the **full conversation** (messages + tool calls) and compares the outcome to your reference. It's workflow-aware — "did the agent's actions and response together achieve the expected outcome?"

**Without expectations:**

- `TaskCompletion` reads input, response, and tool calls but treats them as one "workflow." It checks "did the agent do the work?" — and may pass partial answers if the tool returned the right data, even if the response omitted it.
- `AgentGoalAccuracyWithoutReference` infers the goal from the user's request and the end state from the agent's response. It checks "did the user get what they asked for?" — and catches partial answers because the end state comes from the response, not the tool output.

**When to use which:**

- **Correctness:** When you have ground truth facts and want to check the response text. Most precise — explicitly checks each fact.
- **AgentGoalAccuracyWithReference:** When you have a reference answer and want a workflow-aware check. Better than Correctness for agents that produce results through actions.
- **TaskCompletion:** When you want to check if the agent engaged with and worked toward the goal. Good for catching complete failures, not subtle partial answers.
- **AgentGoalAccuracyWithoutReference:** When you want a holistic check without ground truth — did the user get what they asked for? Best balance of workflow awareness and response checking.

## Logging expectations

Approaches 1 and 2 require expectations. We attach them to traces using `mlflow.log_expectation()` — this logs expectations directly on the trace objects in the MLflow server. Each scorer uses a different key:

- `Correctness`: `expected_facts` — a list of fact strings the response should contain
- `AgentGoalAccuracyWithReference`: `expected_output` — a reference string describing the desired outcome

Expectations are logged **within** the evaluation cell for each approach, and do not affect Approaches 3 and 4 (which ignore them).

## Notebook

See [02_goal_achievement.ipynb](02_goal_achievement.ipynb) to run the evaluation on synthetic traces.
