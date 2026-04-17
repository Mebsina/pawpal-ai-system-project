"""
tools.py
Backend execution functions dynamically triggered by the intent routing engine.
"""

import logging
import ollama
from datetime import datetime, date

from config import MODEL_NAME, STRICT_TEMPERATURE
from pawpal_system import load_data, save_data, Task, Scheduler
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
    from pawpal_system import AnalyticsEngine
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
        
    return {
        "type": "show_quick_menu",
        "message": llm_greeting
    }
