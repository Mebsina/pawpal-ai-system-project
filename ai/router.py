"""
router.py
Intercepts natural language from the Unified Chat Hub, classifies the intent,
and delegates standard actions to the requisite backend tools.
"""

import logging
import ollama

from config import MODEL_NAME, STRICT_TEMPERATURE, CHAT_TEMPERATURE
from ai.tools import add_task_tool

logger = logging.getLogger(__name__)

def classify_and_route(user_input: str, chat_history: list = None):
    """
    Classifies the unified intention and delegates payload processing to specific modular tools.
    """
    system_prompt = """Classify the following user input into strictly ONE of the categories below:
- ADD_TASK: The user wants to schedule a new care event (e.g. walk, feed).
- CHECK_SCHEDULE: The user is asking to view or generate their daily plan.
- GENERAL_CHAT: The user is saying hello or asking conversational questions.

Return absolutely nothing but the exact category string."""

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
        logger.warning(f"[ai/router] Local Ollama classification failed: {e}")
        return "I am currently unable to interpret requests. Please verify the local AI engine is running."

    intent = response.message.content.strip().upper()
    logger.info(f"[ai/router] Interpreted Context Classification: {intent}")

    if "ADD_TASK" in intent:
        return add_task_tool(user_input, chat_history)
    elif "CHECK_SCHEDULE" in intent:
        return "I am ready to interpret calendar metrics, but the schedule visualization tool is currently finalizing."
    else:
        # Fallback to pure conversational routing
        return conversational_bypass(user_input, chat_history)
        

def conversational_bypass(user_input: str, chat_history: list = None) -> str:
    """
    Provides standard conversational feedback streams when formal tool commands are not invoked.
    """
    system_prompt = "Act as a helpful pet care assistant. Provide brief conversational responses to general chat inquiries."
    
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history)
    else:
        messages.append({"role": "user", "content": user_input})
        
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options={"temperature": CHAT_TEMPERATURE}
        )
        return response.message.content
    except Exception as e:
        logger.warning(f"[ai/router] Conversational bypass failed: {e}")
        return "I'm having trouble maintaining conversation right now."
