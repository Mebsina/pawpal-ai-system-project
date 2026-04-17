import logging
import json
import ollama
from dataclasses import asdict
from datetime import datetime
from config import MODEL_NAME, STRICT_TEMPERATURE, CHAT_TEMPERATURE, STANDARD_CARE_GUIDELINES
from core import load_data, AnalyticsEngine
from ai.utils import extract_json, ReliabilityAuditor, validate_schema, check_restricted_keywords

logger = logging.getLogger(__name__)

def suggest_schedule_tool(user_input: str, chat_history: list = None):
    """
    Analyzes all pets, history, and current tasks to propose a comprehensive 'Smart Plan'.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    pet_data = []
    # Provide the FULL pet data structure and owner preferences for maximum context
    pet_data = [asdict(pet) for pet in owner.pets]
    preferences = owner.preferences
    
    recent_history = engine.get_recent_history(days=3)
    history_strs = [f"{r.pet_name} completed {r.task_title} on {r.timestamp}" for r in recent_history]
    
    anomalies = engine.get_unusual_patterns()
    
    # Format global guidelines for the prompt context
    guidelines_str = "\n".join([f"- {k.capitalize()}: {', '.join(v)}" for k, v in STANDARD_CARE_GUIDELINES.items()])
    
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%Y-%m-%d")

    system_prompt = f"""You are a Proactive Pet Care Planner.
The current time is {current_time} on {current_date}.
Your mission is to generate a 'Smart Plan' for today by analyzing pet needs, history, and missing routines. 

PET CARE GUIDELINES (Standard Industry Baselines):
{guidelines_str}

OWNER PREFERENCES:
{json.dumps(preferences, indent=2)}

PETS (Full Database):
{json.dumps(pet_data, indent=2)}

RECENT HISTORY (Last 3 Days):
{chr(10).join(history_strs)}

ANOMALIES/MISSED TASKS:
{json.dumps(anomalies, indent=2)}

CRITICAL GOALS:
1. ACTIONABLE OUTPUT: Fill the "suggestions" array with specific, valid JSON task objects.
2. ROUTINE RECOVERY: If history shows a daily pattern (e.g., walk at 2 PM) but NO task is scheduled for today ({current_date}), suggest it.
3. BASELINE CARE: Any pet with zero tasks scheduled for today MUST receive at least two suggestions: one feeding session and one activity session (walk/play).
4. SMART STAGGERING: If multiple pets have similar needs (e.g., feeding), stagger their times by 1-5 minutes (e.g., 08:00, 08:05) to avoid overlap.
5. NO DUPLICATES: Check "existing_tasks" for each pet. Do NOT suggest a task if a similar one is already scheduled.
6. SPECIAL NEEDS: Senior/Arthritic pets like Luna require gentle play and meds.

Return strictly a JSON dictionary:
- "summary": (string) A warm welcome for the plan.
- "suggestions": (list of objects) [{{"pet_name": str, "title": str, "scheduled_time": "HH:MM", "duration_minutes": int, "priority": str, "category": str, "frequency": str}}]
- "confidence": (float) 0.0-1.0 score matching your self-assessment of the plan's quality.

ABSOLUTELY NO CONVERSATIONAL TEXT outside the JSON."""

    # --- Agentic Multi-Turn Loop ---
    MAX_TURNS = 5
    current_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    final_result = None
    
    for turn in range(MAX_TURNS):
        logger.info(f"[suggest_schedule] Agentic Turn {turn+1} starting...")
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=current_messages,
                options={
                    "temperature": STRICT_TEMPERATURE if turn == 0 else CHAT_TEMPERATURE,
                    "format": "json"
                }
            )
            extracted_data = extract_json(response.message.content)
            
            # Automated Validation of Agentic Proposals
            required = ["summary", "suggestions", "confidence"]
            if not validate_schema(extracted_data, required):
                logger.warning(f"[suggest_schedule] Turn {turn+1} failed schema validation.")
                continue
            
            # Content Guardrail check
            check_restricted_keywords(response.message.content)
            
            suggestions = extracted_data.get("suggestions", [])
            valid_suggestions = []
            issues = []
            taken_slots = set() # (pet_name_lower, time)
            
            # Pre-populate with existing tasks for accurate conflict avoidance (RAG-style check)
            for pet in owner.pets:
                for t in pet.tasks:
                    if t.due_date == current_date:
                        try:
                            h, m = t.scheduled_time.split(":")
                            norm_time = f"{int(h):02d}:{int(m):02d}"
                        except:
                            norm_time = t.scheduled_time
                        taken_slots.add((pet.name.lower(), norm_time))
            
            pet_names_map = {p.name.lower(): p.name for p in owner.pets}
            
            for s in suggestions:
                p_name_lower = str(s.get("pet_name", "")).lower().strip()
                time_raw = s.get("scheduled_time")
                
                if p_name_lower in pet_names_map and time_raw:
                    try:
                        h, m = str(time_raw).split(":")
                        h_int, m_int = int(h), int(m)
                        if not (0 <= h_int <= 23 and 0 <= m_int <= 59):
                            raise ValueError("out of range")
                        time = f"{h_int:02d}:{m_int:02d}"
                    except Exception:
                        issues.append(f"INVALID_TIME: '{time_raw}' for {s.get('title')} ({s.get('pet_name')}) is not valid HH:MM. Use 24-hour format like 08:00 or 18:30.")
                        continue

                    slot_key = (p_name_lower, time)
                    if slot_key not in taken_slots:
                        s["pet_name"] = pet_names_map[p_name_lower]
                        s["scheduled_time"] = time
                        if not s.get("due_date"):
                            s["due_date"] = current_date
                        valid_suggestions.append(s)
                        taken_slots.add(slot_key)
                    else:
                        issues.append(f"CONFLICT: {s.get('title')} for {s.get('pet_name')} at {time} overlaps with an existing task or previous suggestion.")
            
            # Check for Baseline Care Gaps (per-pet category and count enforcement)
            FEEDING_KEYWORDS = {"feeding", "feed", "food", "breakfast", "dinner", "lunch"}
            MIN_TASKS_PER_PET = 2
            MIN_SAME_CAT_GAP = 120  # min gap between same-category tasks for one pet

            def _classify(cat_str, title_str):
                """Normalize task into a broad type for proximity checks."""
                combined = f"{cat_str} {title_str}".lower()
                if any(kw in combined for kw in FEEDING_KEYWORDS):
                    return "feeding"
                if any(kw in combined for kw in ("walk", "stroll")):
                    return "walk"
                if any(kw in combined for kw in ("play", "enrichment", "toy")):
                    return "play"
                if any(kw in combined for kw in ("groom", "brush", "bath")):
                    return "grooming"
                return cat_str.lower()

            for pet in owner.pets:
                pn_lower = pet.name.lower()

                has_feeding = False
                existing_count = 0
                cat_times = {}  # {type: [minutes, ...]}
                for t in pet.tasks:
                    if t.due_date == current_date:
                        existing_count += 1
                        task_type = _classify(t.category, t.title)
                        if task_type == "feeding":
                            has_feeding = True
                        try:
                            h, m = t.scheduled_time.split(":")
                            cat_times.setdefault(task_type, []).append(int(h) * 60 + int(m))
                        except Exception:
                            pass

                suggested_count = 0
                for s in valid_suggestions:
                    if s["pet_name"].lower() == pn_lower:
                        suggested_count += 1
                        task_type = _classify(s.get("category", ""), s.get("title", ""))
                        if task_type == "feeding":
                            has_feeding = True
                        try:
                            h, m = s["scheduled_time"].split(":")
                            cat_times.setdefault(task_type, []).append(int(h) * 60 + int(m))
                        except Exception:
                            pass

                if not has_feeding:
                    issues.append(f"GAP: {pet.name} has no feeding task. Add a feeding suggestion (use category 'feeding').")

                total = existing_count + suggested_count
                if total < MIN_TASKS_PER_PET:
                    issues.append(f"GAP: {pet.name} only has {total} task(s). Add at least {MIN_TASKS_PER_PET - total} more suggestion(s).")

                # Check for same-category tasks too close together
                for task_type, times in cat_times.items():
                    times.sort()
                    for i in range(1, len(times)):
                        gap = times[i] - times[i - 1]
                        if 0 < gap < MIN_SAME_CAT_GAP:
                            issues.append(f"TOO_CLOSE: {pet.name} has two '{task_type}' tasks only {gap}m apart. Space same-type tasks at least {MIN_SAME_CAT_GAP}m apart.")

            # Check daily time budget
            existing_minutes = sum(t.duration_minutes for pet in owner.pets for t in pet.tasks if t.due_date == current_date)
            suggested_minutes = sum(s.get("duration_minutes", 0) for s in valid_suggestions)
            total_minutes = existing_minutes + suggested_minutes
            budget = owner.available_minutes
            if total_minutes > budget:
                issues.append(f"OVER_BUDGET: Total is {total_minutes}m but owner only has {budget}m available. Remove or shorten some tasks.")

            confidence = extracted_data.get("confidence", 0.0)
            logger.info(f"[suggest_schedule] Turn {turn+1}: {len(valid_suggestions)} suggestions, {len(issues)} issues, confidence={confidence}")

            if not issues and confidence >= 0.9:
                pet_count = len({s["pet_name"] for s in valid_suggestions})
                task_count = len(valid_suggestions)
                logger.info(f"[suggest_schedule] Done. Final: {task_count} task(s) for {pet_count} pet(s), confidence={confidence}")
                final_result = {
                    "type": "plan_suggestion",
                    "message": f"Here is your smart plan: {task_count} task(s) for {pet_count} pet(s).",
                    "suggestions": valid_suggestions
                }
                ReliabilityAuditor.record_metric("Agentic_Planning", confidence=confidence, turns=turn+1, success=True)
                break

            if turn == MAX_TURNS - 1:
                pet_count = len({s["pet_name"] for s in valid_suggestions})
                task_count = len(valid_suggestions)
                warnings = "\n".join(f"- {i}" for i in issues)
                logger.warning(f"[suggest_schedule] Max turns reached with {len(issues)} unresolved issue(s). confidence={confidence}")
                final_result = {
                    "type": "plan_suggestion",
                    "message": f"Here is your smart plan: {task_count} task(s) for {pet_count} pet(s).\n\n**Note:** Some issues remain:\n{warnings}",
                    "suggestions": valid_suggestions
                }
                ReliabilityAuditor.record_metric("Agentic_Planning", confidence=confidence, turns=MAX_TURNS, success=False)
                break
            else:
                # Feedback loop to improve the next turn
                feedback = "I reviewed your draft and found these issues. Please adjust the plan to be 100% compliant:\n" + "\n".join(issues)
                current_messages.append({"role": "assistant", "content": response.message.content})
                current_messages.append({"role": "user", "content": feedback})
                logger.warning(f"[suggest_schedule] Turn {turn+1} found {len(issues)} issues (confidence={confidence}). Re-prompting for improvement...")

        except Exception as e:
            logger.error(f"[suggest_schedule] Agentic Turn {turn+1} crashed: {e}")
            if turn == MAX_TURNS - 1:
                return "The AI planner encountered an error while refining your schedule."

    if not final_result or not final_result["suggestions"]:
        return "I scoured your pet data but couldn't identify any new tasks that don't conflict with your current schedule."

    return final_result
