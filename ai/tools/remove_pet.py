import logging
import ollama
from config import MODEL_NAME, STRICT_TEMPERATURE
from core import load_data

logger = logging.getLogger(__name__)

def remove_pet_tool(user_input: str, chat_history: list = None):
    """
    Identifies which pet the user wants to remove and returns a confirmation payload.

    The database write runs only after the user confirms in the chat UI, which calls
    :func:`core.models.remove_pet_for_owner` (same helper as the Dashboard).
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
1. If the user DID NOT specify a name from the list above, you MUST return 'null' for pet_name.
2. Return strictly a JSON dictionary:
   - "pet_name": (string or null)
   - "confidence": (float) A score between 0.0 and 1.0 representing your certainty.

ABSOLUTELY NO CONVERSATIONAL TEXT. Return ONLY raw valid JSON."""

        try:
            from ai.utils import extract_json
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"The user says: {user_input}"}
                ],
                options={"temperature": STRICT_TEMPERATURE, "format": "json"}
            )
            extracted_data = extract_json(response.message.content)
            if extracted_data:
                extracted_name = extracted_data.get("pet_name")
                confidence = extracted_data.get("confidence", 0.0)
                logger.info(f"[ai/tools/remove_pet] Extraction Confidence: {confidence}")
                target_name = next((p for p in pet_names if p.lower() == str(extracted_name).lower()), "null")
            else:
                target_name = "null"
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
