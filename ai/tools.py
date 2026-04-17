"""
tools.py
Backend execution functions dynamically triggered by the intent routing engine.
"""

import logging
import json
import ollama
from dataclasses import asdict
from datetime import datetime, date

import streamlit as st
from config import MODEL_NAME, STRICT_TEMPERATURE, STANDARD_CARE_GUIDELINES
from pawpal_system import load_data, save_data, Task, Scheduler, AnalyticsEngine
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def add_task_tool(user_input: str, chat_history: list = None):
    """
    Parses user input to extract required task parameters, enforces the conversational 
    anti-guessing protocol for missing parameters, and packages the physical Draft natively for UI validation.
    """
    owner = load_data()
    pet_names = [p.name for p in owner.pets]
    
    # If no pets exist, halt the workflow natively.
    if not pet_names:
        return "It looks like no pets are registered assigned to the profile. Please add a pet before creating tasks."
    
    pet_context = f"Valid registered pets are: {', '.join(pet_names)}."
    if len(pet_names) == 1:
        pet_context += " Since there is only one pet, default to this pet if none is explicitly mentioned."
        
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%Y-%m-%d")
        
    system_prompt = f"""You are a data extraction module for a pet care scheduling system.
The current time is {current_time} on {current_date}. You MUST functionally resolve relative times (e.g., "in 5 minutes") and dates (e.g., "tmr" = tomorrow) into absolute mathematical formats.
Extract the task details from the provided input string.
{pet_context}

CRITICAL RULES:
1. Do NEVER invent, assume, or hallucinate ANY values.
2. If the user does not explicitly specify a time, you MUST set "scheduled_time" to null. (Do NOT default predictably).
3. If a variable is completely missing from the user prompt, explicitly return it as null.
4. ABSOLUTELY NO CONVERSATIONAL TEXT. You must return ONLY raw valid JSON starting with {{ and ending with }}.

Return strictly a JSON dictionary featuring the following format:
- "title": (string or null) The exact task activity declared by the user (e.g., "play", "feeding", "walk").
- "pet_name": (string or null) The intended pet. You must deduce this from recent chat history if the user already selected one. If completely unmentioned, return null.
- "duration_minutes": (integer or null) Strictly the length of the task. Do NOT confuse clock times (e.g., "5 pm") with duration. If length is missing, return null.
- "priority": (string or null) 
- "category": (string or null) 
- "frequency": (string or null) 
- "scheduled_time": (string or null) "HH:MM" format (24-hour).
- "due_date": (string or null) "YYYY-MM-DD" format.

EXAMPLE W/ VAGUE INPUT:
Input: "Schedule a task for my pet"
Output: {{"title": null, "pet_name": null, "duration_minutes": null, "priority": null, "category": null, "frequency": null, "scheduled_time": null, "due_date": null}}
"""
    
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-8:])  # deeply preserve history for accumulated context state
    else:
        messages.append({"role": "user", "content": user_input})
    
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options={"temperature": STRICT_TEMPERATURE, "format": "json"}
        )
    except Exception as e:
        logger.error(f"Local AI failed extraction: {e}")
        return "I'm having trouble connecting to the local AI. Please try again."
        
    extracted_data = extract_json(response.message.content)
    
    if not extracted_data:
        return "The natural language extractor failed to assemble a valid task. Could you rephrase the request?"
        
    pet_name = extracted_data.get("pet_name")
    scheduled_time = extracted_data.get("scheduled_time")
    title = extracted_data.get("title")
    due_date = extracted_data.get("due_date") or current_date
    
    if not title or title.lower() in ["task", "null", "none"]:
        title = extracted_data.get("category")
    
    # Single-Pet Automatic Assignment (The Anti-Guessing Single-Pet Exception)
    if len(pet_names) == 1 and not pet_name:
        pet_name = pet_names[0]
        
    if not pet_name or pet_name not in pet_names:
        return {
            "type": "selection_menu",
            "message": "Which pet is this schedule adjustment intended for?",
            "options": pet_names
        }
        
    if not title or title.lower() in ["task", "null"]:
        return f"I can definitely set that up for {pet_name}. What specific activity or task are we scheduling? (e.g., '15 minute walk at 14:00' or 'feeding in 5 minutes')"
        
    if not scheduled_time:
        tentative_title = title or "task"
        day_str = " tomorrow" if due_date != current_date else ""
        return f"I can certainly organize that {tentative_title} for {pet_name}{day_str}. What specific time should the schedule reflect?"
        
    # Verify exact pet linkage matching
    matching_pet = next((p for p in owner.pets if p.name.lower() == pet_name.lower()), None)
    
    if not matching_pet:
        return f"The profile '{pet_name}' is not currently registered. Valid options are: {', '.join(pet_names)}."

    # Ensure time extracts natively isolated from calendar metadata
    if scheduled_time and len(scheduled_time) > 5:
        scheduled_time = scheduled_time[-5:]
        
    # Validation Complete - Execute Task Framework
    try:
        # Natively translate structural LLM output securely into our Dataclass
        task_preview = Task(
            title=title,
            duration_minutes=extracted_data.get("duration_minutes") or 15,
            priority=extracted_data.get("priority") or "medium",
            category=extracted_data.get("category") or title,
            scheduled_time=scheduled_time,
            due_date=due_date,
            frequency=extracted_data.get("frequency") or "once",
            notes="Generated seamlessly via Conversational UI Hub"
        )
        
        # Actively map the proposal natively onto the pet instance structurally so Conflict Tracker detects the pet!
        matching_pet.tasks.append(task_preview)
        
        # Cross-reference the integrated calendar array mathematically
        all_existing = [t for p in owner.pets for t in p.tasks]
        conflicts = Scheduler(owner=owner).detect_time_conflicts(tasks=all_existing)
        
        # Detach immediately avoiding silent data injection
        matching_pet.tasks.remove(task_preview)
        
        if conflicts:
            conflict_str = " and ".join(conflicts)
            return f"I can't lock that in just yet! ⚠ I noticed {conflict_str}.\n\nWhat alternative time would work better?"
            
    except Exception as e:
        logger.error(f"Task object creation failed: {e}")
        return "There was an error processing the task details. Please try again."
    
    # Return purely an isolated validation dictionary structure to enforce front-end intercept logic
    return {
        "type": "task_confirmation",
        "message": f"Please verify this schedule: **{task_preview.title}** for **{matching_pet.name}** at {task_preview.scheduled_time} on {task_preview.due_date}. It will take {task_preview.duration_minutes} minutes, recurring '{task_preview.frequency}', with {task_preview.priority} priority.\n\nDoes this look accurate?",
        "task_preview": task_preview,
        "pet_name": matching_pet.name
    }


def check_schedule_tool(user_input: str, chat_history: list = None):
    """
    Analyzes mathematical scheduling bounds logically and passes the unified variable tracking natively to an LLM 
    instruction structurally strictly limited to a single output sentence serving as a humanized visual wrapper for the pandas dataframe loop.
    """
    
    owner = load_data()
    scheduler = Scheduler(owner=owner)
    today_str = date.today().isoformat()
    
    # Isolate uncompleted metrics functionally for exclusively the current date
    incomplete = scheduler.filter_tasks(status=False, target_date=today_str)
    
    if not incomplete:
        return {
            "type": "show_schedule_table",
            "message": "It looks like your schedule is completely clear for today! Is there anything you'd like to dynamically add?"
        }
        
    schedule = scheduler.generate_plan(tasks=incomplete)
    
    # Extract structural metrics cleanly
    tasks_count = len(schedule.tasks)
    used_mins = schedule.total_duration
    rem_mins = owner.available_minutes - used_mins
    unscheduled = len(schedule.unscheduled)
    
    # Construct an explicitly constrained zero-shot prompt forcing exactly 1 conversation wrapper over the vars
    system_prompt = f"""You are PawPal, a warm and helpful pet care assistant.
The user is checking their daily schedule. 
Strictly write ONLY ONE warm, conversational sentence introducing their plan. 
Incorporate these exact metrics seamlessly into the sentence: 
- {tasks_count} tasks scheduled 
- {used_mins} minutes utilized
- {rem_mins} minutes remaining in their daily time budget
{'Warn them gently that ' + str(unscheduled) + ' tasks could not fit today.' if unscheduled > 0 else 'All tasks fit perfectly!'}
CRITICAL RULE: DO NOT generate a list or a table. DO NOT output the tasks themselves. Write EXACTLY one friendly greeting sentence!"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            options={"temperature": 0.5}
        )
        llm_greeting = response.message.content.strip()
    except Exception as e:
        logger.error(f"[check_schedule] LLM summarization pipeline failed organically: {e}")
        llm_greeting = "Here is your completely optimized plan for today:"
        
    return {
        "type": "show_schedule_table",
        "message": llm_greeting
    }


def get_insights_tool(user_input: str, chat_history: list = None):
    """
    Evaluates historical data dynamically feeding natural language summaries over Analytics Arrays organically.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    recent_records = engine.get_recent_history(days=7)
    
    if not recent_records:
        return "I scoped your analytics history, but I haven't recorded any completed tasks in the last 7 days! Mark some tasks complete on your dashboard so I can track your behavior insights!"
        
    # Compress history arrays conceptually physically mapping data constraints
    history_strings = []
    for r in recent_records:
        history_strings.append(f"{r.pet_name} completed '{r.task_title}' ({r.category}) on {r.timestamp}")
        
    system_prompt = f"""You are PawPal, a helpful AI analyzing a user's pet care history.
The user wants insights dynamically based on the exact historical records provided rigidly below.
CRITICAL INSTRUCTION: Base your analysis STRICTLY on these physical data constraints. Do NOT invent completions.

COMPLETIONS (Last 7 Days):
{chr(10).join(history_strings)}

Answer the user's specific analytic question warmly and conversationally directly addressing the temporal data patterns. Do NOT generate visual bar charts or markdown tables.
CRITICAL RULE: NEVER ask the user a follow up question. End your message with a conclusive, finite statement framing the analytics explicitly."""

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-4:])
    messages.append({"role": "user", "content": user_input})
        
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options={"temperature": STRICT_TEMPERATURE}
        )
        llm_greeting = response.message.content.strip()
    except Exception as e:
        logger.error(f"[get_insights] LLM summarization pipeline failed organically: {e}")
        llm_greeting = "I reliably mapped your analytics arrays, but am having trouble dynamically summarizing them right now via the underlying inference engine."
        
    return llm_greeting


def predictive_alerts_tool(user_input: str, chat_history: list = None):
    """
    Scans the system for behavioral anomalies and missed tasks, then humanizes them via LLM.
    Strictly grounded in system data to prevent hallucinations.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    anomalies = engine.get_unusual_patterns()
    registered_pets = [p.name for p in owner.pets]
    
    if not anomalies:
        return {
            "type": "show_quick_menu",
            "message": "Everything looks on track! I haven't detected any missed routines or unusual patterns for your pets."
        }
        
    system_prompt = f"""You are PawPal, a precise pet care assistant.
Your goal is to summarize the following detected anomalies.

REAL PETS REGISTERED: {', '.join(registered_pets)}
DETECTED ANOMALIES:
{chr(10).join(['- ' + a for a in anomalies])}

CRITICAL INSTRUCTIONS:
1. INTERNAL LABELS: Never mention the internal labels like 'REAL PETS REGISTERED' or 'DETECTED ANOMALIES' in your output. Just use the information naturally.
2. SCOPE: ONLY mention pets and issues found in the lists above.
3. NO HALLUCINATIONS: If a pet or task is not in the lists above, IT DOES NOT EXIST. DO NOT make up names or events.
4. STYLE: Be warm, professional, and stay strictly 100% grounded in the facts provided.
5. RECOMMENDATION: If you mention a missed task, ask if the user wants to schedule a catch-up session now."""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Please summarize these alerts for me."}
            ],
            options={"temperature": 0.0}  # Use 0.0 for maximum grounding
        )
        message = response.message.content.strip()
        
        # Lock intent to SUGGEST_SCHEDULE so a follow-up ("sure", "yes") triggers the real planner
        st.session_state.active_intent = "SUGGEST_SCHEDULE"
        
    except Exception as e:
        logger.error(f"[predictive_alerts] LLM failed: {e}")
        message = "I noticed some items might need your attention: " + ", ".join(anomalies)
        
    return message


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
1. ACTIONABLE OUTPUT: Your primary goal is to fill the "suggestions" array with specific, valid JSON task objects.
2. ROUTINE RECOVERY: If history shows a daily pattern (e.g., walk at 2 PM) but NO task is scheduled for today ({current_date}), you MUST suggest it.
3. ANOMALY FIXING: If there are anomalies (late tasks from previous days), suggest a new time TODAY to catch up.
4. NO DUPLICATES: Check "existing_tasks" for each pet. If a task with a similar title/category is ALREADY scheduled for today ({current_date}), do NOT suggest it again.
5. SPECIAL NEEDS: Senior pets or pets with special needs (like arthritis) should have tailored suggestions (meds, gentle play).

JSON FORMAT:
{{
  "summary": "Short explanation of the plan.",
  "suggestions": [
    {{
      "pet_name": "PetName",
      "title": "Task",
      "duration_minutes": 15,
      "priority": "medium",
      "category": "walk/feeding/etc",
      "frequency": "daily",
      "scheduled_time": "HH:MM",
      "due_date": "{current_date}"
    }}
  ]
}}
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
            options={"temperature": STRICT_TEMPERATURE, "format": "json"}
        )
        logger.info(f"[suggest_schedule] Raw LLM Response: {response.message.content}")
        extracted_data = extract_json(response.message.content)
    except Exception as e:
        logger.error(f"[suggest_schedule] LLM failed: {e}")
        return "I'm having trouble analyzing your pets' needs right now. Please try again later."

    if not extracted_data:
        return "I scoured your pet data but couldn't come up with a valid JSON plan. The AI engine might be struggling with the current data volume."

    suggestions = extracted_data.get("suggestions", [])
    
    # Validate and package for UI
    valid_suggestions = []
    registered_pet_names = [p.name.lower().strip() for p in owner.pets]
    
    for s in suggestions:
        p_name = str(s.get("pet_name", "")).lower().strip()
        if p_name in registered_pet_names:
            # Re-map to the exact case-sensitive name from the owner object
            actual_pet = next(p for p in owner.pets if p.name.lower().strip() == p_name)
            s["pet_name"] = actual_pet.name
            valid_suggestions.append(s)
            
    if not valid_suggestions:
        return extracted_data.get("summary", "I scoured your pet data but couldn't identify any valid tasks for your registered pets! Try adding more details to their profiles.")

    return {
        "type": "plan_suggestion",
        "message": extracted_data.get("summary", "Here is a proactive plan I've put together for your pets:"),
        "suggestions": valid_suggestions
    }


def list_pets_tool(user_input: str, chat_history: list = None):
    """
    Retrieves the full list of pets and summarizes them naturally using an LLM,
    incorporating species emojis and detailed attributes in a clean list format.
    """
    owner = load_data()
    
    if not owner.pets:
        return "You haven't registered any pets yet! You can add one using the 'Add a Pet' form on the main dashboard."
        
    pet_data = []
    for pet in owner.pets:
        # Define species emoji mapping for the LLM to reference
        emoji = "🐶" if pet.species == "dog" else "🐱" if pet.species == "cat" else "🐾"
        needs_str = ", ".join(pet.special_needs) if pet.special_needs else "None"
        pet_data.append(f"- {emoji} **{pet.name}**: {pet.age}-year-old {pet.species}. (Special needs: {needs_str})")
        
    system_prompt = f"""You are PawPal, a warm and helpful pet care assistant.
The user is asking about their pets. 
Based strictly on the data below, provide a friendly summary of all their registered pets.

REGISTERED PETS:
{chr(10).join(pet_data)}

CRITICAL RULES:
1. Use a clean, bulleted list for the pets.
2. Use the EXACT emojis provided in the data list below for each pet (🐶 for dogs, 🐱 for cats, 🐾 for others).
3. Explicitly mention their age and any special needs they have.
4. Be warm and professional.
5. End your message by asking if they would like to schedule a specific task for any of them."""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            options={"temperature": CHAT_TEMPERATURE}
        )
        return response.message.content.strip()
    except Exception as e:
        logger.error(f"[list_pets_tool] LLM failed: {e}")
        # Fallback with bullet points, emojis and details
        fallback = "I found your pets in the system:\n" + "\n".join(pet_data)
        return fallback
