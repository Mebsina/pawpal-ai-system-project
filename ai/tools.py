"""
tools.py
Backend execution functions dynamically triggered by the intent routing engine.
"""

import logging
import ollama

from config import MODEL_NAME, STRICT_TEMPERATURE
from pawpal_system import load_data, save_data, Task
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def add_task_tool(user_input: str) -> str:
    """
    Parses user input to extract required task parameters, enforces the conversational 
    anti-guessing protocol for missing parameters, and applies the physical creation in the DB.
    """
    owner = load_data()
    pet_names = [p.name for p in owner.pets]
    
    # If no pets exist, halt the workflow natively.
    if not pet_names:
        return "It looks like no pets are registered assigned to the profile. Please add a pet before creating tasks."
    
    pet_context = f"Valid registered pets are: {', '.join(pet_names)}."
    if len(pet_names) == 1:
        pet_context += " Since there is only one pet, default to this pet if none is explicitly mentioned."
        
    system_prompt = f"""You are a data extraction module for a pet care scheduling system.
Extract the task details from the provided input string.
{pet_context}

Return strictly a JSON dictionary featuring the following keys. Do not guess values if omitted; utilize null.
- "title": (string) Brief task name, e.g. "Walk", "Meds"
- "pet_name": (string) The intended pet, or null if unspecified.
- "duration_minutes": (integer) Time duration in minutes. Default 15.
- "priority": (string) "low", "medium", or "high". Default "medium".
- "category": (string) "walk", "feeding", "meds", "grooming", "enrichment". Default "walk".
- "frequency": (string) "once", "daily", "weekly". Default "once".
- "scheduled_time": (string) "HH:MM" format (24-hour), or null if strictly unspecified.
"""
    
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
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
    
    # Single-Pet Automatic Assignment (The Anti-Guessing Single-Pet Exception)
    if len(pet_names) == 1 and not pet_name:
        pet_name = pet_names[0]
        
    # Conversational Follow-Up Trigger Check
    if not pet_name:
        return f"Which pet is this schedule adjustment intended for ({', '.join(pet_names)})?"
        
    if not scheduled_time:
        tentative_title = extracted_data.get("title", "task")
        return f"I can certainly organize that {tentative_title} for {pet_name}. What specific time should the schedule reflect?"
        
    # Verify exact pet linkage matching
    matching_pet = next((p for p in owner.pets if p.name.lower() == pet_name.lower()), None)
    
    if not matching_pet:
        return f"The profile '{pet_name}' is not currently registered. Valid options are: {', '.join(pet_names)}."
        
    # Standard DB Object Generation
    new_task = Task(
        title=extracted_data.get("title", "Task"),
        duration_minutes=extracted_data.get("duration_minutes", 15),
        priority=extracted_data.get("priority", "medium"),
        category=extracted_data.get("category", "walk"),
        frequency=extracted_data.get("frequency", "once"),
        scheduled_time=scheduled_time,
        notes="Generated seamlessly via Conversational UI Hub"
    )
    
    matching_pet.add_task(new_task)
    
    try:
        save_data(owner)
    except Exception as e:
        logger.error(f"[ai/tools] Database commit failed on task generation: {e}")
        return "An internal database conflict occurred while saving the schedule."
        
    return f"Successfully locked in: {new_task.title} for {matching_pet.name} at {new_task.scheduled_time}."
