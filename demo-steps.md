# PawPal+ Fresh-Start Demo Script (All AI Features + Guardrails)

This is a click-by-click demo flow that matches the current implementation (Streamlit UI + local Ollama) and explicitly covers **every feature listed under `## AI Features`** in `README.md`, with a guardrail highlight for each.

## Pre-demo setup (fresh start)

1. (Optional) Reset data:
   - Delete `data/pawpal_data.json` if you want a clean demo database.
2. Start Ollama:
   - `ollama pull llama3.2:3b`
   - `ollama serve`
3. Start the app:
   - `streamlit run app.py`
4. Confirm the pages exist: **Dashboard**, **Tasks**, **Planner**, **AI Metrics**.

---

## Step 1 - Add a Pet (AI Feature: CRUD Pets)

1. Open **Dashboard** and confirm owner info is saved.
2. Click **💬 Ask AI**.
3. Send: `i want to add a cat name Luna`
4. Send: `10 years old`
5. Click **✅ Confirm**.

> **Guardrail:** Human-in-the-loop confirmation. No pet is written until confirmed.

---

## Step 2 - Schedule a Feeding Task (AI Feature: Schedule a Task)

1. In AI chat, send: `schedule a feeding task at 8am for 10 min daily`
2. Send: `high prior`
3. Click **✅ Confirm**.

> **Guardrails:**
> - **Strict JSON extraction** - missing fields prompt a follow-up, never a guess.
> - **Validation** - HH:MM format and `>0` duration enforced before saving.

---

## Step 3 - Schedule a Play Task (AI Feature: Schedule a Task + Conflict Detection)

1. In AI chat, send: `i want to add a task for playing with Luna at 8am daily`
2. Send: `let's make it at 8:30am`
3. Send: `medium prior`
4. Click **✅ Confirm**.

> **Guardrail:** Conflict detection. The 8:00 AM overlap is caught before saving and the system requests a new time.

---

## Step 4 - View Tasks Page

1. Open **Tasks**.
2. Verify both tasks appear:
   - **Feeding** · 08:00 · 10 min · high · daily
   - **Playing** · 08:30 · medium · daily

---

## Step 5 - Check Current Plan (AI Feature: Check Plans)

1. In AI chat, send: `what is my current plan`
2. Show the schedule table (Scheduled / Could not fit).

> **Guardrail:** Null-safe fallback. An empty schedule returns a clean message, not a crash.

---

## Step 6 - Smart Planner (AI Feature: Smart Planner)

1. Open **Planner**.
2. In AI chat, send: `what should i schedule for my pet today`
3. Show the plan grouped by pet with times.
4. Click **✅ Confirm Plan** to batch-add tasks.

> **Guardrails:**
> - **Agentic multi-turn refinement** - retries internally when conflicts or budget overruns are detected.
> - **Budget enforcement** - will not propose tasks that exceed daily minutes or overlap existing slots.

---

## Step 7 - Complete Tasks

1. Open **Tasks**.
2. Check **Feeding** as complete ✅.
3. Check **Playing** as complete ✅.

---

## Step 8 - Check Status (AI Feature: Check Status)

1. In AI chat, send: `How am I doing with my pets this week?`
2. Show the response as one natural paragraph with no bullet lists.

> **Guardrails:**
> - **Multiple data sources** - merges completion history with anomaly detection.
> - **Style constraint** - markdown lists/headers are prohibited to force a conversational tone.

---

## Step 9 - AI Metrics (AI Feature: Automated Testing / Reliability)

1. Open **AI Metrics**.
2. Show confidence scores and turn counts tracked per tool.

> **Guardrail:** ReliabilityAuditor logs tool-level success/confidence for regression detection.

---

## Step 10 - Remove Pet (AI Feature: CRUD Pets, destructive action)

1. In AI chat, send: `i want to remove a pet`
2. Send: `Luna`
3. Show the confirmation step.
4. Click **✅ Confirm** to delete.

> **Guardrails:**
> - **Destructive action gate** - no data is deleted until confirmed.
> - **Escape keywords** (`cancel`, `stop`, `start over`) break intent locks safely.

---

## Step 11 - Verify Removal on Tasks Page

1. Open **Tasks**.
2. Confirm Luna's tasks no longer appear. The pet and all associated tasks have been removed.

---

## Honest demo notes (avoid overclaiming)

- Restricted keyword checks are **detection/logging + scoping** (non-medical), not a hard content block.
- Don't quote specific test counts/coverage unless you re-ran them in your environment.
