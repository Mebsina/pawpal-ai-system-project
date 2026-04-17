"""
router.py
Intercepts natural language from the Unified Chat Hub, classifies the intent,
and delegates standard actions to the requisite backend tools.
"""

import logging
import ollama
import streamlit as st

from config import MODEL_NAME, STRICT_TEMPERATURE, CHAT_TEMPERATURE
from ai.tools import add_task_tool, check_schedule_tool, get_insights_tool, predictive_alerts_tool, suggest_schedule_tool, list_pets_tool, add_pet_tool, remove_pet_tool

logger = logging.getLogger(__name__)

def classify_and_route(user_input: str, chat_history: list = None):
    """
    Classifies the unified intention and delegates payload processing to specific modular tools.
    Utilizes active session intent locks to enforce linear multi-turn pipeline sequences mathematically.
    """
    
    # 1. Physical User Override: Provide clean organic escape routes from active loops unconditionally
    hard_input = user_input.lower().strip()
    # Broaden the escape list to include common 'get me out of here' phrases
    escape_keywords = [
        "menu", "help", "options", "cancel", "nevermind", "stop", 
        "abort", "exit", "quit", "start over", "restart", "back"
    ]
    if hard_input in escape_keywords or hard_input.startswith("exit "):
        st.session_state.active_intent = None
        logger.info(f"[ai/router] Intent lock manually released via keyword: {hard_input}")

    # 2. Sequential Intent Lock: Force strict continuity bypassing LLM variance if already trapped in an active tool loop
    locked_intent = st.session_state.get("active_intent")
    
    # Hardcoded keyword shortcuts to ensure system reliability for critical menus
    clean_input = user_input.strip().lower()
    if clean_input in ["menu", "help", "options"]:
        logger.info(f"[ai/router] System intercepted keyword shortcut: HELP_MENU")
        return {
            "type": "show_quick_menu",
            "message": "I'm your PawPal assistant! You can use these buttons to quickly manage your pets, or just type what you need below:"
        }

    if locked_intent:
        intent = locked_intent
        logger.info(f"[ai/router] System structurally intercepted via Active Context State Lock: {intent}")
    else:
        system_prompt = """Classify the following user input into strictly ONE of the categories below:
- ADD_TASK: The user wants to schedule a specific NEW care event (e.g. 'walk Mochi at 2pm').
- ADD_PET: The user wants to register a brand NEW pet (e.g. 'add a 2 year old cat').
- REMOVE_PET: The user wants to delete, remove, say goodbye to, or rehome an existing pet (e.g. 'remove Mochi', 'delete Kiki').
- CHECK_SCHEDULE: The user wants to VIEW their CURRENTLY scheduled tasks for today. (e.g. 'what is my plan?', 'show my schedule', 'today task', 'what are my tasks?').
- SUGGEST_SCHEDULE: The user wants the AI to ANALYZE data and PROPOSE new things to do. (e.g. 'what should I schedule?', 'what do my pets need?', 'give me a plan base on history').
- LIST_PETS: The user explicitly wants to see a list of their pets. (e.g., 'what pets do I have?', 'show my animals', 'list pets').
- PET_INSIGHTS: The user is asking for analytics, history, or how often they completed tasks.
- CHECK_ALERTS: The user asks for alerts, warnings, or if they missed anything.
- HELP_MENU: The user explicitly types 'menu', requests help, asks what you can do, or asks for options.
- GENERAL_CHAT: The user is saying hello or asking conversational questions.

CRITICAL RULE: You MUST classify the intent of the VERY LAST MESSAGE in the sequence. Previous messages are ONLY context. 
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
            intent = response.message.content.strip().upper()
            logger.info(f"[ai/router] Interpreted Context Classification: {intent}")
        except Exception as e:
            logger.warning(f"[ai/router] Local Ollama classification failed: {e}")
            return "I am currently unable to interpret requests. Please verify the local AI engine is running."

    # 3. Intent Delegation & Persistence Updates
    
    if "ADD_TASK" in intent:
        st.session_state.active_intent = "ADD_TASK"
        return add_task_tool(user_input, chat_history)
    elif "ADD_PET" in intent:
        st.session_state.active_intent = "ADD_PET"
        return add_pet_tool(user_input, chat_history)
    elif "REMOVE_PET" in intent:
        st.session_state.active_intent = "REMOVE_PET"
        return remove_pet_tool(user_input, chat_history)
    elif "CHECK_SCHEDULE" in intent:
        st.session_state.active_intent = None
        return check_schedule_tool(user_input, chat_history)
    elif "SUGGEST_SCHEDULE" in intent:
        st.session_state.active_intent = None
        return suggest_schedule_tool(user_input, chat_history)
    elif "PET_INSIGHTS" in intent:
        st.session_state.active_intent = None
        return get_insights_tool(user_input, chat_history)
    elif "CHECK_ALERTS" in intent:
        st.session_state.active_intent = None
        return predictive_alerts_tool(user_input, chat_history)
    elif "LIST_PETS" in intent:
        st.session_state.active_intent = None
        return list_pets_tool(user_input, chat_history)
    elif "HELP_MENU" in intent:
        return {
            "type": "show_quick_menu",
            "message": "I'm your PawPal assistant! I can help you manage your pet's schedule, track tasks, and answer pet care questions. Here is my core menu:"
        }
    else:
        # Fallback to pure conversational routing
        return conversational_bypass(user_input, chat_history)
        

def conversational_bypass(user_input: str, chat_history: list = None) -> str:
    """
    Provides standard conversational feedback streams when formal tool commands are not invoked.
    """
    system_prompt = f"Act as a helpful pet care assistant. Provide brief conversational responses to general chat inquiries. IMPORTANT: If the user is trying to add, remove, or list pets, or schedule tasks, tell them you can help with that and use the menu below."
    
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
