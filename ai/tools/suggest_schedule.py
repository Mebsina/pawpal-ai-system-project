import logging
import json
import ollama
from dataclasses import asdict
from datetime import datetime
from config import MODEL_NAME, STRICT_TEMPERATURE, STANDARD_CARE_GUIDELINES
from pawpal_system import load_data, AnalyticsEngine
from ai.utils import extract_json

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
