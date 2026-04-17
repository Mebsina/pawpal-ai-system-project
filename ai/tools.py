"""
tools.py
Backend execution functions dynamically triggered by the intent routing engine.
"""

import logging
import ollama
from datetime import datetime

from config import MODEL_NAME, STRICT_TEMPERATURE
from pawpal_system import load_data, save_data, Task
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
        
    system_prompt = f"""You are a data extraction module for a pet care scheduling system.
The current time is {current_time}. You MUST functionally resolve relative times (e.g., "in 5 minutes") into absolute HH:MM format using this current time reference.
Extract the task details from the provided input string.
{pet_context}

CRITICAL RULES:
1. Do NEVER invent, assume, or hallucinate ANY values.
2. If the user does not explicitly name the task/activity, you MUST set "title" to null.
3. If the user does not explicitly specify a time, you MUST set "scheduled_time" to null. (Do NOT default to a random time)
4. If a variable is completely missing from the user prompt, explicitly return it as null.
5. ABSOLUTELY NO CONVERSATIONAL TEXT. You must return ONLY raw valid JSON starting with {{ and ending with }}.

Return strictly a JSON dictionary featuring the following format:
- "title": (string or null) The exact task activity declared by the user.
- "pet_name": (string or null) The exact intended pet. If not explicitly specified in the current request, you MUST return null. Do NOT assume historical pets.
- "duration_minutes": (integer or null)
- "priority": (string or null) 
- "category": (string or null) 
- "frequency": (string or null) 
- "scheduled_time": (string or null) "HH:MM" format (24-hour).

EXAMPLE W/ VAGUE INPUT:
Input: "Schedule a task for my pet"
Output: {{"title": null, "pet_name": null, "duration_minutes": null, "priority": null, "category": null, "frequency": null, "scheduled_time": null}}
"""
    
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history)
    else:
        messages.append({"role": "user", "content": user_input})
        
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options={"temperature": STRICT_TEMPERATURE}
        )
    except Exception as e:
        logger.warning(f"[ai/tools] Ollama endpoint unavailable: {e}")
        return "The local AI routing engine is currently unresponsive. Please ensure Ollama is actively running."
        
    extracted_data = extract_json(response.message.content)
    
    if not extracted_data:
        return "The natural language extractor failed to assemble a valid task. Could you rephrase the request?"
        
    pet_name = extracted_data.get("pet_name")
    scheduled_time = extracted_data.get("scheduled_time")
    title = extracted_data.get("title")
    
    if not title or title.lower() in ["task", "null"]:
        title = extracted_data.get("category")
    
    # Single-Pet Automatic Assignment (The Anti-Guessing Single-Pet Exception)
    if len(pet_names) == 1 and not pet_name:
        pet_name = pet_names[0]
        
    # Conversational Follow-Up Trigger Check dynamically integrated with structured UI payloads
    if not pet_name:
        return {
            "type": "selection_menu",
            "message": "Which pet is this schedule adjustment intended for?",
            "options": pet_names
        }
        
    if not title or title.lower() in ["task", "null"]:
        return f"I can definitely set that up for {pet_name}. What specific activity or task are we scheduling? (e.g., '15 minute walk at 14:00' or 'feeding in 5 minutes')"
        
    if not scheduled_time:
        tentative_title = title or "task"
        return f"I can certainly organize that {tentative_title} for {pet_name}. What specific time should the schedule reflect?"
        
    # Verify exact pet linkage matching
    matching_pet = next((p for p in owner.pets if p.name.lower() == pet_name.lower()), None)
    
    if not matching_pet:
        return f"The profile '{pet_name}' is not currently registered. Valid options are: {', '.join(pet_names)}."
        
    # Standard DB Object Generation securely catching explicit null injection
    new_task = Task(
        title=extracted_data.get("title") or "Task",
        duration_minutes=int(extracted_data.get("duration_minutes") or 15),
        priority=extracted_data.get("priority") or "medium",
        category=extracted_data.get("category") or "walk",
        frequency=extracted_data.get("frequency") or "once",
        scheduled_time=scheduled_time,
        notes="Generated seamlessly via Conversational UI Hub"
    )
    
    # Return purely an isolated validation dictionary structure to enforce front-end intercept logic
    return {
        "type": "task_confirmation",
        "message": f"Does this {new_task.title} for {matching_pet.name} at {new_task.scheduled_time} look accurate to schedule?",
        "task_preview": new_task,
        "pet_name": matching_pet.name
    }
