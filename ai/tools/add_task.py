import logging
import ollama
from datetime import datetime
from config import MODEL_NAME, STRICT_TEMPERATURE
from core import Task, save_data, load_data, Scheduler
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
- "confidence": (float) A score between 0.0 and 1.0 representing your certainty about the extraction.

EXAMPLE W/ VAGUE INPUT:
Input: "Schedule a task for my pet"
Output: {{"title": null, "pet_name": null, "duration_minutes": null, "priority": null, "category": null, "frequency": null, "scheduled_time": null, "due_date": null, "confidence": 0.5}}
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
        
    confidence = extracted_data.get("confidence", 0.0)
    logger.info(f"[ai/tools/add_task] Extraction Confidence: {confidence}")
        
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
