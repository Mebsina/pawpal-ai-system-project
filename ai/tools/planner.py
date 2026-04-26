import logging
import json
import ollama
from dataclasses import asdict
from datetime import datetime
from config import MODEL_NAME, STRICT_TEMPERATURE, CHAT_TEMPERATURE, STANDARD_CARE_GUIDELINES
from core import load_data, AnalyticsEngine
from ai.utils import extract_json, ReliabilityAuditor, validate_schema, check_restricted_keywords

logger = logging.getLogger(__name__)

def planner_tool(user_input: str, chat_history: list = None):
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
    
    # Format global guidelines for the prompt context using the structured labels
    guidelines_str = "\n".join([f"- {k.capitalize()}: " + ", ".join([req["label"] for req in v]) for k, v in STANDARD_CARE_GUIDELINES.items()])
    
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%Y-%m-%d")

    # --- Pre-calculate Budget and Timeline Insights ---
    total_existing_minutes = 0
    occupied_slots = []
    
    for pet in owner.pets:
        for t in pet.tasks:
            if t.due_date == current_date:
                total_existing_minutes += int(t.duration_minutes)
                try:
                    h, m = str(t.scheduled_time).split(":")
                    start_min = int(h) * 60 + int(m)
                    end_min = start_min + int(t.duration_minutes)
                    occupied_slots.append(f"{t.scheduled_time} - {(end_min//60):02d}:{(end_min%60):02d} ({pet.name}: {t.title})")
                except Exception:
                    pass

    budget = owner.available_minutes
    remaining_budget = max(0, budget - total_existing_minutes)
    
    # Smart Skip: Early exit if schedule is already full
    if total_existing_minutes >= 0.95 * budget and budget > 0:
        return f"Your schedule is already packed for today! You've used {total_existing_minutes} of your {budget} minutes budget. To add more tasks, please either mark some as 'Complete' or increase your daily time limit in the Dashboard."

    slots_str = "\n".join(f"- {s}" for s in sorted(occupied_slots)) if occupied_slots else "None (Clear schedule)"

    system_prompt = f"""You are a Proactive Pet Care Planner.
The current time is {current_time} on {current_date}.

TIME BUDGET CONSTRAINTS:
- OWNER DAILY BUDGET: {budget} minutes
- CURRENTLY SCHEDULED: {total_existing_minutes} minutes
- REMAINING BUDGET: {remaining_budget} minutes

OCCUPIED SLOTS (Do NOT overlap these):
{slots_str}

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
1. BUDGET ADHERENCE: Your total SUGGESTED duration must NOT exceed the {remaining_budget}m remaining budget. If a guideline requires a 30m task but you only have 15m left, you MUST shorten the task to fit the budget. Budget adherence is strictly more important than guideline minimums.
2. ONLY ADD NEW TASKS: This tool ONLY adds missing tasks. Never append tags like '(Rescheduled)' or '(Late)' to task titles. If a task type already exists for a pet today, do NOT suggest it again.
3. PRIORITIZE GUIDELINES FIRST: You MUST fulfill the missing PET CARE GUIDELINES before suggesting any creative or extra tasks. Only suggest extra tasks if all guidelines are met AND there is budget remaining.
4. HIGH PRIORITY FIRST: If the budget is tight, you MUST schedule 'high' priority tasks (like feedings and meds) for ALL pets before you spend budget on 'medium' or 'low' priority tasks. Place all 'high' priority tasks at the very top of your JSON 'suggestions' array!
5. SEQUENTIAL PLANNING: You are a single caregiver. New suggestions must NOT overlap with each other OR existing occupied slots.
6. SPECIAL NEEDS: Pay close attention to each pet's 'special_needs' list. For example, senior or arthritic pets require gentle play and precise medication scheduling.
7. PET MATCHING: You MUST ensure that you assign missing tasks to the EXACT 'pet_name' that needs them according to the anomalies/feedback. Do not mix up pets.

Return strictly a JSON dictionary:
- "summary": (string) A warm welcome explaining why these tasks were chosen.
- "confidence": (float) 0.0-1.0 score.
- "suggestions": A list of task objects, where each object MUST have:
    - "pet_name": (string) The exact pet name (e.g., "Luna", "Max").
    - "title": (string) The task activity (e.g., "Morning Walk", "Feeding session").
    - "scheduled_time": (string) "HH:MM" format (24-hour).
    - "duration_minutes": (integer) Length of task. Set feeding tasks strictly to 5.
    - "priority": (string) EXACTLY "high" (meds/feeding), "medium" (baseline care), or "low" (extras).
    - "category": (string) EXACTLY one of: "walk", "feeding", "meds", "grooming", "play", "training", "vet", "bath", or "general".

NOTE: duration_minutes MUST be a positive integer. Skip low-priority tasks if the budget is tight.
ABSOLUTELY NO CONVERSATIONAL TEXT outside the JSON."""

    # --- Agentic Multi-Turn Loop ---
    MAX_TURNS = 5
    current_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    final_result = None
    
    for turn in range(MAX_TURNS):
        logger.info(f"[planner] Agentic Turn {turn+1} starting...")
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
                logger.warning(f"[planner] Turn {turn+1} failed schema validation.")
                continue
            
            # Content Guardrail check
            check_restricted_keywords(response.message.content)
            
            suggestions = extracted_data.get("suggestions", [])
            valid_suggestions = []
            issues = []
            # Global timeline storing intervals: {"start": int_mins, "end": int_mins, "pet": str, "title": str}
            timeline = []
            
            # Pre-populate with existing tasks for accurate conflict avoidance
            for pet in owner.pets:
                for t in pet.tasks:
                    if t.due_date == current_date:
                        try:
                            h, m = str(t.scheduled_time).split(":")
                            start_min = int(h) * 60 + int(m)
                            end_min = start_min + int(t.duration_minutes)
                            timeline.append({
                                "start": start_min,
                                "end": end_min,
                                "pet": pet.name,
                                "title": t.title
                            })
                        except Exception:
                            pass
            
            pet_names_map = {p.name.lower(): p.name for p in owner.pets}
            
            for s in suggestions:
                p_name_lower = str(s.get("pet_name", "")).lower().strip()
                time_raw = s.get("scheduled_time")
                duration = int(s.get("duration_minutes") or 0)
                duration = max(1, duration)  # Safety enforcement
                s["duration_minutes"] = duration
                
                if p_name_lower in pet_names_map and time_raw:
                    try:
                        h, m = str(time_raw).split(":")
                        h_int, m_int = int(h), int(m)
                        if not (0 <= h_int <= 23 and 0 <= m_int <= 59):
                            raise ValueError("out of range")
                        start_min = h_int * 60 + m_int
                        end_min = start_min + duration
                        time_str = f"{h_int:02d}:{m_int:02d}"
                    except Exception:
                        issues.append(f"INVALID_TIME: '{time_raw}' for {s.get('title')} is not valid HH:MM.")
                        continue

                    # Check for overlap against the global timeline
                    overlap_found = False
                    for interval in timeline:
                        # Strictly sequential: start1 < end2 AND start2 < end1
                        if start_min < interval["end"] and interval["start"] < end_min:
                            overlap_found = True
                            issues.append(f"CONFLICT: '{s.get('title')}' for {s.get('pet_name')} ({time_str}, {duration}m) overlaps with '{interval['title']}' for {interval['pet']}.")
                            break
                    
                    if not overlap_found:
                        s["pet_name"] = pet_names_map[p_name_lower]
                        s["scheduled_time"] = time_str
                        if not s.get("due_date"):
                            s["due_date"] = current_date
                        valid_suggestions.append(s)
                        timeline.append({
                            "start": start_min,
                            "end": end_min,
                            "pet": s["pet_name"],
                            "title": s["title"]
                        })
            
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
                species = pet.name.lower() # Fallback
                # Find species requirements
                requirements = STANDARD_CARE_GUIDELINES.get(pet.species.lower(), [])
                
                # Track counts for each required type
                type_counts = {req["type"]: 0 for req in requirements}
                type_times = {req["type"]: [] for req in requirements}

                def _add_to_stats(t_list):
                    for t in t_list:
                        raw_cat = t.category if hasattr(t, "category") else t.get("category", "")
                        raw_title = t.title if hasattr(t, "title") else t.get("title", "")
                        task_type = _classify(raw_cat, raw_title)
                        
                        if task_type in type_counts:
                            type_counts[task_type] += 1
                            try:
                                scheduled_time = t.scheduled_time if hasattr(t, "scheduled_time") else t.get("scheduled_time", "")
                                h, m = scheduled_time.split(":")
                                type_times[task_type].append(int(h) * 60 + int(m))
                            except Exception:
                                pass

                # 1. Count existing tasks for today
                _add_to_stats([t for t in pet.tasks if t.due_date == current_date])
                
                # 2. Count suggested tasks
                _add_to_stats([s for s in valid_suggestions if s["pet_name"].lower() == pn_lower])

                # 3. Verify against requirements in config.py
                for req in requirements:
                    req_type = req["type"]
                    min_count = req["min_count"]
                    current_count = type_counts[req_type]
                    
                    if current_count < min_count:
                        issues.append(f"GAP: {pet.name} ({pet.species}) only has {current_count} '{req_type}' task(s). The guideline requires at least {min_count}: '{req['label']}'.")

                    # Check for same-category tasks too close together
                    times = sorted(type_times[req_type])
                    for i in range(1, len(times)):
                        gap = times[i] - times[i - 1]
                        if 0 < gap < MIN_SAME_CAT_GAP:
                            issues.append(f"TOO_CLOSE: {pet.name} has two '{req_type}' tasks only {gap}m apart. Space same-type tasks at least {MIN_SAME_CAT_GAP}m apart.")

            # Check daily time budget
            existing_minutes = sum(t.duration_minutes for pet in owner.pets for t in pet.tasks if t.due_date == current_date)
            suggested_minutes = sum(s.get("duration_minutes", 0) for s in valid_suggestions)
            total_minutes = existing_minutes + suggested_minutes
            budget = owner.available_minutes
            if total_minutes > budget:
                issues.append(f"OVER_BUDGET: Total is {total_minutes}m but owner only has {budget}m available. Remove or shorten some tasks.")

            confidence = extracted_data.get("confidence", 0.0)
            logger.info(f"[planner] Turn {turn+1}: {len(valid_suggestions)} suggestions, {len(issues)} issues, confidence={confidence}")

            if not issues and confidence >= 0.9:
                pet_count = len({s["pet_name"] for s in valid_suggestions})
                task_count = len(valid_suggestions)
                logger.info(f"[planner] Done. Final: {task_count} task(s) for {pet_count} pet(s), confidence={confidence}")
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
                logger.warning(f"[planner] Max turns reached with {len(issues)} unresolved issue(s). confidence={confidence}")
                
                # Generate a creative AI message explaining the compromises
                gap_issues = [i for i in issues if i.startswith("GAP:")]
                warnings_str = "\n".join(f"- {i}" for i in gap_issues)
                
                if gap_issues:
                    instruction = "explicitly list ALL the missing tasks from the provided constraints using the phrasing: 'we suggest you to add [Task] for [Pet]'."
                else:
                    instruction = "Do not list any specific tasks, just note that we couldn't space everything out perfectly."

                prompt = (
                    f"Write a friendly but brief 1-2 sentence note. "
                    f"Start EXACTLY with this phrase: 'This is everything for the {budget}-minute timeframe, however, '. "
                    f"Then {instruction} "
                    f"STRICT INSTRUCTION: You MUST ONLY list tasks that appear in the constraints below. DO NOT invent or hallucinate extra tasks (like swimming or grooming) that are not listed! "
                    f"Format the missing tasks naturally. If a missing task doesn't have a specific duration listed, suggest 15 minutes (but strictly suggest 5 minutes for feedings). "
                    f"Do NOT use quotation marks around the tasks. Do NOT include the pet's species (like '(dog)'). "
                    f"Do NOT use robotic phrases like 'task is incomplete' or 'manually add the reminder'. "
                    f"Do NOT use conversational fluff like 'I wanted to let you know'. "
                    f"Do NOT mention 'standard guidelines', 'baselines', or 'requirements'. "
                    f"Output ONLY the raw message text. Do not include any preambles. "
                    f"Do not use technical jargon like 'GAP' or 'OVER_BUDGET'. "
                    f"Here are the exact missing tasks to draw from (DO NOT INVENT OTHERS):\n{warnings_str if gap_issues else 'No missing tasks, just scheduling conflicts.'}"
                )
                
                try:
                    fallback_res = ollama.chat(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": prompt}],
                        options={"temperature": 0.7}
                    )
                    # Strip any leading/trailing whitespace and quotation marks
                    friendly_warning = fallback_res.message.content.strip(' "\'')
                except Exception as e:
                    logger.error(f"[planner] Fallback message generation failed: {e}")
                    friendly_warning = (
                        "I did my best to build a complete schedule, but we're running a little tight on time! "
                        "I had to leave out a few recommended activities to ensure everything fits perfectly."
                    )
                
                final_result = {
                    "type": "plan_suggestion",
                    "message": f"Here is your smart plan: {task_count} task(s) for {pet_count} pet(s).\n\n{friendly_warning}",
                    "suggestions": valid_suggestions
                }
                ReliabilityAuditor.record_metric("Agentic_Planning", confidence=confidence, turns=MAX_TURNS, success=False)
                break
            else:
                # Feedback loop to improve the next turn
                budget_info = f"\nREMAINING BUDGET: {remaining_budget}m. Current total (existing + new): {total_minutes}m."
                feedback = "I reviewed your draft and found these issues. Please adjust the plan to be 100% compliant:" + budget_info + "\n" + "\n".join(issues)
                current_messages.append({"role": "assistant", "content": response.message.content})
                current_messages.append({"role": "user", "content": feedback})
                logger.warning(f"[planner] Turn {turn+1} found {len(issues)} issues (confidence={confidence}). Re-prompting...")

        except Exception as e:
            logger.error(f"[planner] Agentic Turn {turn+1} crashed: {e}")
            if turn == MAX_TURNS - 1:
                return "The AI planner encountered an error while refining your schedule."

    if not final_result or not final_result["suggestions"]:
        return "I scoured your pet data but couldn't identify any new tasks that don't conflict with your current schedule. Try clearing some gaps or increasing your daily budget to see more options."

    return final_result
