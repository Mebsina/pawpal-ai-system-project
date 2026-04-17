import logging
import ollama
from config import MODEL_NAME, STRICT_TEMPERATURE
from core import load_data

logger = logging.getLogger(__name__)

def remove_pet_tool(user_input: str, chat_history: list = None):
    """
    Identifies which pet the user wants to remove and returns a confirmation payload.
    """
    owner = load_data()
    pet_names = [p.name for p in owner.pets]
    
    if not pet_names:
        return "You don't have any pets to remove!"

    # 1. Detect generic "I want to remove a pet" requests to bypass LLM hallucinations
    generic_triggers = ["remove a pet", "remove pet", "i need to remove a pet", "delete a pet", "remove one of my pets"]
    clean_input = user_input.strip().lower()
    if clean_input in generic_triggers:
        return {
            "type": "selection_menu",
            "message": "I can help with that. Which pet would you like to remove?",
            "options": pet_names
        }

    # 2. Direct match check (to handle button clicks precisely)
    match = next((p for p in pet_names if p.lower() == clean_input), None)
    
    if match:
        target_name = match
    else:
        # 3. LLM Extraction fallback for natural language
        system_prompt = f"""Identify the EXACT name of the pet the user wants to remove from this list: {', '.join(pet_names)}.

CRITICAL INSTRUCTIONS:
1. If the user DID NOT specify a name from the list above, you MUST return 'null'.
2. Do NOT guess, default, or pick a pet if the user is being general (e.g., "remove a pet").
3. Return ONLY the name or 'null'. No other text."""

        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"The user says: {user_input}"}
                ],
                options={"temperature": STRICT_TEMPERATURE}
            )
            extracted = response.message.content.strip().replace("'", "").replace('"', "").replace(".", "")
            target_name = next((p for p in pet_names if p.lower() == extracted.lower()), "null")
        except Exception as e:
            logger.error(f"Remove pet extraction failed: {e}")
            target_name = "null"

    if target_name == "null":
        return {
            "type": "selection_menu",
            "message": "I'm not sure which pet you'd like to remove. Please select one from your list:",
            "options": pet_names
        }

    return {
        "type": "pet_remove_confirmation",
        "message": f"Are you absolutely sure you want to remove **{target_name}**? This will delete all their scheduled tasks and history as well.",
        "pet_name": target_name
    }
