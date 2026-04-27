"""
eval_ai.py
Standalone (mocked) evaluation harness for PawPal+ AI features.

Runs a small set of predefined prompts through the AI router + tools with
all Ollama calls mocked, then prints a custom summary (pass/fail + confidence).

Usage:
  python eval_ai.py
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable
from unittest.mock import patch

from ai.router import classify_and_route
from core.models import Owner, Pet, Task


# -----------------------------
# Lightweight mock infrastructure
# -----------------------------

class _MockMessage:
    def __init__(self, content: str):
        self.content = content


class _MockResponse:
    def __init__(self, content: str):
        self.message = _MockMessage(content)


class _SessionState(dict):
    """Minimal Streamlit-like session_state supporting attr + dict access."""

    def __getattr__(self, key: str):
        return self.get(key)

    def __setattr__(self, key: str, value: Any):
        self[key] = value


def _make_owner_fixture() -> Owner:
    """Deterministic owner fixture for evaluation."""
    owner = Owner(name="Eval Owner", available_minutes=60)
    mochi = Pet(name="Mochi", species="dog", age=3)

    # One existing incomplete task today to make CHECK_SCHEDULE meaningful.
    mochi.tasks.append(
        Task(
            title="Existing Walk",
            duration_minutes=30,
            priority="high",
            category="walk",
            frequency="once",
            scheduled_time="08:00",
            due_date=date.today().isoformat(),
        )
    )
    owner.pets = [mochi]
    return owner


def _mock_ollama_chat_factory():
    """
    Returns a stateful mock function for ollama.chat that:
    - classifies intents for ai/router.py
    - emits tool-specific JSON for ai/tools/*
    - supports a 2-turn planner refinement demo
    """

    planner_calls = 0

    def _mock_ollama_chat(*, model: str, messages: list[dict], options: dict | None = None):
        nonlocal planner_calls
        system = (messages[0].get("content") or "") if messages else ""
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = (m.get("content") or "")
                break

        # 1) Router intent classification
        if "Classify the following user input" in system:
            text = last_user.lower()
            if ("list" in text and "pet" in text) or ("what pets" in text) or ("what pet" in text):
                intent = "LIST_PETS"
            elif "remove" in text and ("pet" in text or "mochi" in text):
                intent = "REMOVE_PET"
            elif "add" in text and "pet" in text:
                intent = "ADD_PET"
            elif "what should i schedule" in text or "recommend" in text or "suggest" in text:
                intent = "SUGGEST_SCHEDULE"
            elif "status" in text or "how am i doing" in text:
                intent = "PET_INSIGHTS"
            elif "schedule" in text or "add a task" in text or "feeding" in text or "walk" in text:
                intent = "ADD_TASK"
            elif "plan" in text or "today" in text or "schedule" in text:
                intent = "CHECK_SCHEDULE"
            else:
                intent = "GENERAL_CHAT"
            return _MockResponse(json.dumps({"intent": intent, "confidence": 0.99}))

        # 2) add_task_tool extraction
        if "data extraction module for a pet care scheduling system" in system:
            text = last_user.lower()
            if "feeding" in text:
                payload = {
                    "title": "Feeding",
                    "pet_name": "Mochi",
                    "duration_minutes": 20,
                    "priority": "high",
                    "category": "feeding",
                    "frequency": "once",
                    "scheduled_time": "08:30",
                    "due_date": date.today().isoformat(),
                    "confidence": 0.93,
                }
            else:
                # Missing details → return nulls (anti-guessing)
                payload = {
                    "title": None,
                    "pet_name": "Mochi",
                    "duration_minutes": None,
                    "priority": None,
                    "category": None,
                    "frequency": None,
                    "scheduled_time": None,
                    "due_date": None,
                    "confidence": 0.6,
                }
            return _MockResponse(json.dumps(payload))

        # 3) list_pets_tool summarization
        if "REGISTERED PETS:" in system and "Return strictly a JSON dictionary" in system:
            return _MockResponse(json.dumps({"message": "You have 1 dog, **Mochi** (3). Want to add/remove a pet or schedule a task?", "confidence": 0.95}))

        # 4) schedule_tool greeting sentence
        if "Strictly write ONLY ONE warm, conversational sentence introducing their plan" in system:
            return _MockResponse(json.dumps({"message": "Here’s your plan for today: 1 tasks, 30 mins used, 30 mins remaining—let’s keep it going!", "confidence": 0.92}))

        # 5) status_report_tool paragraph
        if "Unified tool that scans for both completed history and missed routines" in system or "GOAL: Provide a unified" in system:
            return _MockResponse(json.dumps({"message": "You’ve made a solid start this week. I see a few completed items and no major missed routines. Keep the momentum by confirming today’s essentials first, then add something fun if you have time.", "confidence": 0.9}))

        # 6) planner_tool (agentic). First call returns a problematic plan, second fixes it.
        if "You are a Proactive Pet Care Planner" in system:
            planner_calls += 1
            if planner_calls == 1:
                # Intentionally cause a budget issue (over 60 mins) so planner re-prompts.
                return _MockResponse(
                    json.dumps(
                        {
                            "summary": "Draft plan",
                            "confidence": 0.7,
                            "suggestions": [
                                {"pet_name": "Mochi", "title": "Long Walk", "scheduled_time": "09:00", "duration_minutes": 90, "priority": "high", "category": "walk"}
                            ],
                        }
                    )
                )
            return _MockResponse(
                json.dumps(
                    {
                        "summary": "Fixed plan",
                        "confidence": 0.95,
                        "suggestions": [
                            {"pet_name": "Mochi", "title": "Breakfast", "scheduled_time": "08:30", "duration_minutes": 5, "priority": "high", "category": "feeding"},
                            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "09:00", "duration_minutes": 10, "priority": "medium", "category": "play"},
                            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "18:00", "duration_minutes": 5, "priority": "high", "category": "feeding"},
                        ],
                    }
                )
            )

        # Raise loudly so unexpected call paths fail visibly instead of silently.
        raise ValueError(
            f"Unexpected ollama.chat call — no mock branch matched.\n"
            f"  system[:120]={system[:120]!r}\n"
            f"  last_user[:80]={last_user[:80]!r}"
        )

    return _mock_ollama_chat


# -----------------------------
# Evaluation cases + scoring
# -----------------------------

@dataclass(frozen=True)
class EvalCase:
    name: str
    prompt: str
    check: Callable[[Any], tuple[bool, str]]
    expected_feature: str


def _truncate_preview(text: str, max_len: int = 140) -> str:
    """Truncates a string for readable inline error messages."""
    text = text.strip().replace("\n", " ")
    return (text[:max_len] + "...") if len(text) > max_len else text


def _update_feature_stats(
    by_feature: dict, feat: str, passed: bool, conf: float | None
) -> None:
    """Accumulates per-feature pass/fail and confidence stats in-place."""
    if feat not in by_feature:
        by_feature[feat] = {"passed": 0, "total": 0, "conf": []}
    by_feature[feat]["total"] += 1
    if passed:
        by_feature[feat]["passed"] += 1
    if conf is not None:
        by_feature[feat]["conf"].append(conf)


def _is_dict_type(expected_type: str) -> Callable[[Any], tuple[bool, str]]:
    def _check(output: Any) -> tuple[bool, str]:
        if not isinstance(output, dict):
            if isinstance(output, str):
                return False, f"Expected dict(type={expected_type}) but got str: {_truncate_preview(output)!r}"
            return False, f"Expected dict(type={expected_type}) but got {type(output).__name__}"
        if output.get("type") != expected_type:
            return False, f"Expected type={expected_type} but got type={output.get('type')!r}"
        return True, "ok"

    return _check


def _is_nonempty_string(min_len: int = 20) -> Callable[[Any], tuple[bool, str]]:
    """
    Checks for a substantive non-empty string response.
    Uses min_len to guard against bare error-fallback strings passing as valid output.
    """
    def _check(output: Any) -> tuple[bool, str]:
        if not isinstance(output, str) or not output.strip():
            return False, f"Expected non-empty string but got {type(output).__name__}"
        if len(output.strip()) < min_len:
            return False, f"Response too short ({len(output.strip())} chars, min={min_len}): {output.strip()!r}"
        return True, "ok"

    return _check


def _plan_suggestion_has_tasks(min_tasks: int = 1) -> Callable[[Any], tuple[bool, str]]:
    def _check(output: Any) -> tuple[bool, str]:
        if not isinstance(output, dict) or output.get("type") != "plan_suggestion":
            if isinstance(output, str):
                return False, f"Expected dict(type=plan_suggestion) but got str: {_truncate_preview(output)!r}"
            return False, f"Expected dict(type=plan_suggestion) but got {type(output).__name__}"
        suggestions = output.get("suggestions") or []
        if len(suggestions) < min_tasks:
            return False, f"Expected >= {min_tasks} suggestions but got {len(suggestions)}"
        return True, "ok"

    return _check


def main() -> int:
    owner_template = _make_owner_fixture()
    state = _SessionState()
    state.active_intent = None
    state.pending_action = None
    state.chat_history = [{"role": "assistant", "content": "Hi!"}]

    cases: list[EvalCase] = [
        EvalCase(
            name="CRUD Pets: list pets",
            prompt="What pets do I have registered?",
            check=_is_dict_type("pet_management_menu"),
            expected_feature="CRUD Pets",
        ),
        EvalCase(
            name="Check Plans: schedule table",
            prompt="What's on my plan for today?",
            check=_is_dict_type("show_schedule_table"),
            expected_feature="Check Plans",
        ),
        EvalCase(
            name="Schedule a Task: task confirmation",
            prompt="Schedule a feeding task for Mochi at 8:30 AM for 20 minutes today",
            check=_is_dict_type("task_confirmation"),
            expected_feature="Schedule a Task",
        ),
        EvalCase(
            name="Smart Planner: plan suggestion (agentic refinement)",
            prompt="What should I schedule for my pets today?",
            check=_plan_suggestion_has_tasks(1),
            expected_feature="Smart Planner",
        ),
        EvalCase(
            name="Check Status: narrative status string",
            prompt="How am I doing with my pets this week?",
            check=_is_nonempty_string(),
            expected_feature="Check Status",
        ),
    ]

    mock_chat = _mock_ollama_chat_factory()

    # Patch: all Ollama calls, session_state, and persistence I/O
    with (
        patch("ollama.chat", side_effect=mock_chat),
        # Patch module-imported bindings for extra safety
        patch("ai.router.ollama.chat", side_effect=mock_chat),
        patch("ai.tools.add_task.ollama.chat", side_effect=mock_chat),
        patch("ai.tools.list_pets.ollama.chat", side_effect=mock_chat),
        patch("ai.tools.schedule.ollama.chat", side_effect=mock_chat),
        patch("ai.tools.status.ollama.chat", side_effect=mock_chat),
        patch("ai.tools.planner.ollama.chat", side_effect=mock_chat),
        patch("streamlit.session_state", state),
        patch("core.persistence.load_data", side_effect=lambda: copy.deepcopy(owner_template)),
        patch("core.persistence.save_data"),
        patch("core.load_data", side_effect=lambda: copy.deepcopy(owner_template)),
        patch("core.save_data"),
        # Patch tool-imported load_data bindings (tools import from core at import-time).
        # side_effect returns a fresh deepcopy per call so tool mutations don't bleed across cases.
        patch("ai.tools.add_task.load_data", side_effect=lambda: copy.deepcopy(owner_template)),
        patch("ai.tools.list_pets.load_data", side_effect=lambda: copy.deepcopy(owner_template)),
        patch("ai.tools.schedule.load_data", side_effect=lambda: copy.deepcopy(owner_template)),
        patch("ai.tools.status.load_data", side_effect=lambda: copy.deepcopy(owner_template)),
        patch("ai.tools.planner.load_data", side_effect=lambda: copy.deepcopy(owner_template)),
    ):
        results = []
        confidences: list[float] = []
        by_feature: dict[str, dict[str, Any]] = {}

        for c in cases:
            # Isolate each case: fresh history + clear intent locks so no state bleeds across cases.
            state.chat_history = [{"role": "assistant", "content": "Hi!"}]
            state.pending_action = None
            state.active_intent = None

            try:
                state.chat_history.append({"role": "user", "content": c.prompt})
                out = classify_and_route(c.prompt, chat_history=state.chat_history)
                passed, note = c.check(out)

                conf = None
                if isinstance(out, dict) and isinstance(out.get("confidence"), (float, int)):
                    conf = float(out["confidence"])
                    confidences.append(conf)

                results.append((c, passed, note, conf))
                _update_feature_stats(by_feature, c.expected_feature, passed, conf)

                # Append assistant reply to history for fidelity with the real UI flow.
                assistant_msg = str(out.get("message", "")) if isinstance(out, dict) else str(out)
                state.chat_history.append({"role": "assistant", "content": assistant_msg})

            except Exception as e:
                results.append((c, False, f"Exception: {e}", None))
                _update_feature_stats(by_feature, c.expected_feature, False, None)

    total = len(results)
    passed = sum(1 for _, ok, _, _ in results if ok)
    failed = total - passed
    pass_rate = (passed / total) * 100 if total else 0.0
    avg_conf = (sum(confidences) / len(confidences)) if confidences else None

    print("PawPal+ Mocked AI Evaluation Harness")
    print("----------------------------------")
    print(f"Total cases: {total}")
    print(f"Passed:      {passed}")
    print(f"Failed:      {failed}")
    print(f"Pass rate:   {pass_rate:.1f}%")
    if avg_conf is not None:
        print(f"Avg confidence (where available): {avg_conf:.2f}")
    else:
        print("Avg confidence (where available): N/A")

    print("\nBreakdown by feature:")
    for feat, stats in by_feature.items():
        feat_pass = stats["passed"]
        feat_total = stats["total"]
        feat_rate = (feat_pass / feat_total) * 100 if feat_total else 0.0
        confs = stats["conf"]
        conf_str = f"{(sum(confs)/len(confs)):.2f}" if confs else "N/A"
        print(f"- {feat}: {feat_pass}/{feat_total} ({feat_rate:.1f}%), avg_conf={conf_str}")

    print("\nCase results:")
    for c, ok, note, conf in results:
        status = "PASS" if ok else "FAIL"
        conf_str = f"{conf:.2f}" if conf is not None else "N/A"
        print(f"- [{status}] {c.name} (feature={c.expected_feature}, conf={conf_str}) :: {note}")

    # exit code convention: 0 if all pass
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

