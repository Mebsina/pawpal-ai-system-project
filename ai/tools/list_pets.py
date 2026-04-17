import logging
import ollama
from config import MODEL_NAME, CHAT_TEMPERATURE
from pawpal_system import load_data

logger = logging.getLogger(__name__)

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
