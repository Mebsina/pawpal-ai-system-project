import logging
import ollama
import config
from core import load_data
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def list_pets_tool(user_input: str, chat_history: list = None):
    """
    Retrieves the full list of pets and summarizes them naturally using an LLM 
    packaged in a structured JSON response with confidence scoring.
    """
    owner = load_data()
    
    if not owner.pets:
        return "You haven't registered any pets yet! You can add one using the 'Add a Pet' form on the main dashboard."
        
    pet_data = []
    for pet in owner.pets:
        emoji = "🐶" if pet.species == "dog" else "🐱" if pet.species == "cat" else "🐾"
        needs_str = ", ".join(pet.special_needs) if pet.special_needs else "None"
        pet_data.append(f"- {emoji} **{pet.name}**: {pet.age}-year-old {pet.species}. (Special needs: {needs_str})")
        
    system_prompt = f"""You are PawPal, a warm and helpful pet care assistant.
The user is asking about their pets. 
Based strictly on the data below, provide a friendly summary of all their registered pets.

REGISTERED PETS:
{chr(10).join(pet_data)}

CRITICAL RULES:
1. Use a clean, bulleted list for the pets using the provided emojis.
2. End your message by asking if they would like to schedule a specific task.
3. Return strictly a JSON dictionary:
   - "message": (string) Your conversational summary.
   - "confidence": (float) A score between 0.0 and 1.0 representing your certainty.

ABSOLUTELY NO CONVERSATIONAL TEXT outside the JSON. Return ONLY raw valid JSON."""

    try:
        response = ollama.chat(
            model=config.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            options={"temperature": config.CHAT_TEMPERATURE, "format": "json"}
        )
        extracted_data = extract_json(response.message.content)
        if extracted_data:
            confidence = extracted_data.get("confidence", 0.0)
            logger.info(f"[ai/tools/list_pets] Summary Confidence: {confidence}")
            return extracted_data.get("message", "Here are your pets!")
        return response.message.content.strip()
    except Exception as e:
        logger.error(f"[list_pets_tool] LLM failed: {e}")
        fallback = "I found your pets in the system:\n" + "\n".join(pet_data)
        return fallback
