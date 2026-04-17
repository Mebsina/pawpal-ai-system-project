import logging
import ollama
from config import MODEL_NAME, STRICT_TEMPERATURE
from pawpal_system import load_data
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def add_pet_tool(user_input: str, chat_history: list = None):
    """
    Parses user input to extract pet parameters and packages a confirmation payload.
    """
    owner = load_data()
    current_pet_names = [p.name.lower() for p in owner.pets]
    
    system_prompt = """You are a data extraction module for a pet care system.
Extract the pet details from the provided input string.

CRITICAL RULES:
1. Do NEVER invent, assume, or hallucinate ANY values.
2. Species MUST be strictly one of: "dog", "cat", "other".
3. If age is missing, return null.
4. ABSOLUTELY NO CONVERSATIONAL TEXT. Return ONLY raw valid JSON.

Return strictly a JSON dictionary:
- "name": (string or null)
- "species": (string or null)
- "age": (integer or null)
- "special_needs": (list of strings or null)
"""

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-5:])
    else:
        messages.append({"role": "user", "content": user_input})

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options={"temperature": STRICT_TEMPERATURE, "format": "json"}
        )
        extracted_data = extract_json(response.message.content)
    except Exception as e:
        logger.error(f"Add pet extraction failed: {e}")
        return "I'm having trouble connecting to the AI. Please try again."

    if not extracted_data:
        return "I couldn't parse the pet details. Could you tell me the pet's name, species, and age?"

    name = extracted_data.get("name")
    species = extracted_data.get("species")
    age = extracted_data.get("age")
    special_needs = extracted_data.get("special_needs") or []

    if not name:
        return "I'm ready to add a new pet! What is their name?"
    
    if name.lower() in current_pet_names:
        return f"A pet named **{name}** is already registered! Please use a unique name."

    if not species or species not in ["dog", "cat", "other"]:
        return f"Got it, **{name}**. Is {name} a **dog**, **cat**, or something **other**?"

    if age is None:
        return f"And how old is **{name}**?"

    # All data collected
    return {
        "type": "pet_add_confirmation",
        "message": f"I've prepared the profile for **{name}**! They are a **{age}-year-old {species}** with special needs: **{', '.join(special_needs) if special_needs else 'None'}**.\n\nShould I add them to your family?",
        "pet_data": {
            "name": name,
            "species": species,
            "age": age,
            "special_needs": special_needs
        }
    }
