# Model Card — PawPal+ Applied AI System

## Summary

PawPal+ is an AI-extended pet care task scheduler built in Python with a Streamlit UI. It adds a conversational assistant powered by a local Ollama model that can classify user intent, extract structured task and pet actions, and propose validated daily care plans with guardrails and reliability logging.

## System + Model

- **LLM runtime**: local Ollama with `llama3.2:3b`
- **AI entry point**: `ai/router.py` for intent classification and routing
- **AI Tool execution**: `ai/tools/*` for structured extraction and confirmation payloads
- **Guardrails + evaluation**: `ai/utils.py` for JSON sanitization, schema validation, restricted keyword checks, and `ReliabilityAuditor`
- **Metrics storage**: `data/reliability_metrics.json`

## Intended use

- Help a pet owner translate natural language into **structured tasks**, **pet CRUD actions**, and **daily schedules**.
- Provide **non-medical** reminders and pattern-based care nudges grounded in the user’s stored data and care guidelines.

## Out of scope / not intended

- Veterinary diagnosis or medical advice.
- Safety-critical scheduling. This is a productivity assistant, and the user remains responsible for verifying schedules.

## 1. Design

### A. Core system design

#### Initial

- The core data model centers on `Owner`, `Pet`, and `Task`. A `Scheduler` aggregates tasks across pets, fits them into the owner time budget, and returns a `Schedule`.
- Responsibilities
  - `Owner` stores user constraints, preferences, pets, and the completion history ledger
  - `Pet` stores profile fields and owns its tasks
  - `Task` stores a single care activity and its scheduling fields
  - `Scheduler` handles deterministic planning, conflict detection, and recurrence behavior

#### Changes

- Added a `PRIORITY_ORDER` mapping so string priorities, low, medium, and high, can be sorted deterministically.

### B. AI system design

#### Initial

- The first AI integration attempt was form-driven. The UI relied on manual form submission for most actions, and AI was not the primary interface for executing changes.

#### Changes

- Moved configuration into `config.py` instead of using `.env`. The original plan considered a hosted AI API that would require secrets, but the final system uses a local Ollama model on localhost, so setup is simpler and no API key is needed.
- Pivoted to a unified natural language chat interface so most AI interactions start from one conversational entry point.
- Added `ai/router.py` to classify intent and route requests through a single conversational entry point.
- Added `ai/tools/*` as granular tool modules that extract structured JSON for specific actions.
- **Retrieval-Augmented Generation (RAG) Architecture**: Upgraded the backend to actively fetch dynamic historical anomalies via the `AnalyticsEngine` and merge them with static care guidelines before querying the LLM, grounding the AI's responses in reality.
- Added guardrails and evaluation utilities in `ai/utils.py`, including JSON extraction, schema validation, restricted keyword checks, and reliability logging.
- Added human confirmation steps for destructive actions in both chat and dashboard flows.

## 2. Scheduling Logic and Tradeoffs

### a. Constraints and priorities

- **Hard constraint**: owner daily time budget, `available_minutes`.
- **Soft constraint/order**: task priority, then duration as a tiebreaker for tasks with equal priority.

### b. One tradeoff

- Uses a greedy approach that schedules priority first. This favors predictability and user comprehension over global optimal packing.

## 3. Collaboration with AI during development

During development, I used AI as a collaborative partner in three main ways: **prompting**, **debugging**, and **design iteration**. I treated the model like a fast “pair programmer” for generating drafts and identifying gaps, but I did not treat it as an authority. Any AI-generated suggestion only “counted” after I verified it in the actual running app and against the test suite.

- **Prompting / tool shaping**: I used AI to turn ambiguous user messages into **strict JSON contracts** for tool execution, without guessing missing fields. When early prompts were too permissive, I tightened them to require explicit `null` values, enforce schema-required keys, and return JSON only.

- **Debugging**: I used AI to brainstorm failure modes when outputs didn’t match expectations, such as malformed JSON, invalid times, conflicts, or budget overruns. Then I validated the fix by reproducing the issue, updating validation logic in the tool layer, and locking the behavior with unit tests and mocks.

- **Design**: I used AI to explore architecture options and tradeoffs, then implemented the safer approach: one conversational entry point, tool-specific extractors, guardrails, and confirmation steps for writes. The planner is also designed to self-correct when deterministic Python checks detect constraint violations.

**Helpful Suggestion by AI**: When refactoring to a unified conversational hub, the AI suggested passing the `st.session_state` chat history array directly into the Router and Extractor LLMs. This provided the system with full multi-turn conversational memory, resolving the "AI amnesia" issue effectively without the overhead of an external database.

**Flawed Suggestion by AI**: When attempting to fix a deprecation warning for `st.components.v1.html`, the AI repeatedly suggested using `st.iframe()` to render the floating chat box script. This completely broke the floating UI because `st.iframe()` is sandboxed and restricts DOM-modifying scripts. Despite the UI being broken, the AI confidently claimed the issue was fixed over multiple turns. The actual solution was shifting the DOM logic to modern `st.html("""...""", unsafe_allow_javascript=True)` structures.

**Lesson Learned**: The lesson learned from collaborating with AI during development is that AI tools do what you ask, not what you mean. Good results require precise prompts, verifying suggestions against the running system, and rejecting changes that are technically valid but architecturally wrong.

## 4. Reliability, Guardrails, and Evaluation

### Guardrails implemented

- **Agentic Multi-Turn Loop**: The Smart Planner executes an observable, 5-turn self-correction loop. If an AI proposal fails strict Python logic checks (e.g., time overlaps or budget overruns), the system actively feeds the error message back to the LLM to force a correction. If it fails to resolve after 5 turns, a dynamic 6th LLM call synthesizes a conversational fallback message to positively explain the compromises.
- **Dynamic Temperature Control**: Actively toggles between `0.0` (zero-temperature) for strict JSON tool extraction and `0.7` for natural conversational routing, heavily specializing the baseline model.
- **Strict JSON extraction**: sanitizes model output into machine-parseable JSON and rejects or repairs markdown-wrapped responses.
- **Schema validation**: checks required keys and non-null requirements before any data mutation.
- **Restricted keyword checks**: blocks unsafe categories such as medical diagnosis and forces non-medical wording.
- **Human-in-the-loop confirmation**: destructive actions such as removing a pet require explicit confirmation.
- **Reliability logging**: `ReliabilityAuditor` records confidence, success, and turns to `data/reliability_metrics.json`.
- **Intent Break/Escape Keywords**: Users can get stuck in infinite conversation loops if the AI refuses to extract `null` values or is missing data. Adding keywords like "cancel" or "stop" to manually break intent locks acts as a crucial guardrail.

### Example behaviors, guardrails in action

- **Missing fields**: if the model cannot confidently extract a required value such as a time, the tool returns nulls and follow-up prompts instead of guessing.
- **Destructive actions**: “remove a pet” produces a selection + confirmation step; no data is changed until confirmed.

## 5. Testing Results

- **Test command**:
  - `python -m pytest tests`
  - `python -m pytest --cov=ai --cov=core --cov-report=term-missing tests`
- **Current results**: **139 / 139 tests passing**, **98% coverage** for `ai` + `core`.

- **Standalone Evaluation Harness** (`eval_ai.py`): A separate mocked regression harness that replays five fixed prompts end-to-end through the real router and tool modules without requiring a live Ollama instance. Each case asserts both the structural output type (e.g., `dict(type=task_confirmation)`) and a minimum-length substantive response guard. The harness is fully case-isolated: `chat_history` resets and `Owner` state is deep-copied before every case so mutations from one case cannot bleed into the next.

  | Run | Cases | Passed | Failed | Pass Rate | Avg Confidence |
  |-----|-------|--------|--------|-----------|----------------|
  | Latest | 5 | 5 | 0 | **100%** | **0.95** |

  Feature breakdown: CRUD Pets 1/1 · Check Plans 1/1 · Schedule a Task 1/1 · Smart Planner 1/1 (agentic 2-turn refinement verified) · Check Status 1/1

**Confidence**: these results make the system stable against regressions in core logic and guardrail behavior. However, the system still relies on an LLM that can make mistakes or hallucinate, especially on unusual phrasing. The design goal is to reduce the impact of those mistakes by using deterministic extraction, validation, and confirmation steps instead of trusting free-form model output.

## 6. Limitations, Biases, and Future Improvements

### Limitations / biases

- Natural language parsing depends on prompt quality and the user’s phrasing. Ambiguous times can still require follow-ups.
- Pattern-based alerts are statistical and can produce false positives due to seasonal changes or atypical routines.
- The system is not a medical expert; it must avoid medical claims and should defer to professionals.

### Misuse risks and mitigations

- **Risk: over-reliance on AI advice**, treating alerts as medical guidance.  
  **Mitigation**: the system is explicitly scoped as **non-medical** and uses restricted keyword detection to flag medical language; the UI flow encourages user verification before applying changes.
- **Risk: destructive actions**, accidentally deleting a pet and their tasks and history.  
  **Mitigation**: pet removal requires a **human confirmation step** in chat and on the Dashboard before any write is applied.
- **Risk: silent data corruption from hallucinated fields**, such as wrong pet name, time, or duration.  
  **Mitigation**: tools are prompted to return **explicit `null`** for missing/uncertain fields, schema validation prevents executing incomplete payloads, and follow-up questions are used instead of guessing.

### What surprised you while testing reliability

- **Sequential JSON Generation**: LLMs generate JSON arrays sequentially top-to-bottom. When enforcing strict budgets, I had to explicitly prompt the AI to generate high-priority tasks (like feeding) at the very top of the JSON list, otherwise it would run out of budget on low-priority items (like playtime) and fail the validation loop.
- **Live Inference in Tests**: Missing a single `mock_ollama` fixture in a parametrized test caused massive test suite slowdowns because it accidentally executed real live local LLM inference! Always ensure mocks are tightly bound.
- Small prompt differences, or user phrasing like “in 5” vs “at 5,” can shift extraction behavior. Requiring strict JSON and allowing `null` follow-ups was much more reliable than trying to guess defaults.
- UI/agent loops can get “stuck” without an escape hatch; adding explicit cancel/menu keywords to break intent locks significantly improved usability and prevented frustration.

### Future improvements

- Make the assistant more human and creative without sacrificing correctness. When temperature was increased to sound more natural, the smaller model hallucinated more often. A future iteration would separate creative chat from tool extraction more strictly, keeping extraction deterministic while allowing a more expressive voice only in safe responses.
- Improve smart scheduling creativity without inventing nonsense tasks. The current planner is grounded by strict care guidelines, but higher creativity settings tended to generate unrealistic or irrelevant suggestions. A future iteration would keep guideline grounding mandatory and add tighter suggestion validation, allowing creativity only in phrasing and ordering, not in task invention.
- Add task completion, undo, and task editing through chat. For example, mark a task complete, undo a completion, move a task time, or adjust duration and priority, with the same confirmation pattern used for destructive actions.
- Add stronger guardrails. For example, block writes below a confidence threshold, require agreement across multiple extractions for key fields, and provide a clearer preview diff for every mutation before saving.
- ~~Add a small evaluation script that replays a fixed set of inputs and summarizes pass/fail + confidence deltas for regression testing of prompts.~~ **Shipped** — `eval_ai.py` now covers all five AI features with structural and substantive output assertions, per-case state isolation, and a verbose confidence breakdown.
