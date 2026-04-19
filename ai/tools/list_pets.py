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
        return {
            "type": "pet_management_menu",
            "message": "You haven't registered any pets yet! Would you like to add one now?",
            "confidence": 1.0
        }
        
    pet_data = []
    for pet in owner.pets:
        needs_str = ", ".join(pet.special_needs) if pet.special_needs else "None"
        pet_data.append(f"Pet: {pet.name}, Age: {pet.age}, Species: {pet.species}, Special Needs: {needs_str}")
        
    system_prompt = f"""You are PawPal, a warm and helpful pet care assistant.
The user is asking about their pets. 

Based strictly on the data below, provide a warm, conversational summary of the pets in a single NATURAL PARAGRAPH.

CRITICAL RULES:
1. DO NOT use bullet points or lists.
2. Group pets by species (dogs, cats, etc.) to make the response flow naturally.
3. Mention each pet's name, age, and any special needs naturally. BOLD each pet's name (e.g., **Name**).
4. ABSOLUTELY NO random emojis or symbols (like ✓, 👛, or 𞤩). 
5. Use ONLY the data provided below:

REGISTERED PETS:
{chr(10).join(pet_data)}

6. END your message by asking if they would like to add/remove a pet or schedule a task.
7. Return strictly a JSON dictionary:
   - "message": (string) Your natural paragraph response with bolded names.
   - "confidence": (float) A score between 0.0 and 1.0.

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
            return {
                "type": "pet_management_menu",
                "message": extracted_data.get("message", "Here are your pets!"),
                "confidence": confidence
            }
        return {
            "type": "pet_management_menu",
            "message": response.message.content.strip(),
            "confidence": 0.0
        }
    except Exception as e:
        logger.error(f"[list_pets_tool] LLM failed: {e}")
        fallback = "I found your pets in the system:\n" + "\n".join(pet_data)
        return {
            "type": "pet_management_menu",
            "message": fallback,
            "confidence": 0.0
        }
