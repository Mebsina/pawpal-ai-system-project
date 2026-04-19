"""
router.py
Intercepts natural language from the Unified Chat Hub, classifies the intent,
and delegates standard actions to the requisite backend tools.
"""

import logging
import ollama
import streamlit as st

from config import MODEL_NAME, STRICT_TEMPERATURE, CHAT_TEMPERATURE
from .tools import (
    add_task_tool,
    schedule_tool,
    status_report_tool,
    planner_tool,
    list_pets_tool,
    add_pet_tool,
    remove_pet_tool
)
from .utils import extract_json, ReliabilityAuditor, validate_schema, check_restricted_keywords

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
- ADD_TASK: The user wants to schedule a specific NEW care event, routine, or activity (e.g., 'Schedule a task for my pet', 'walk Mochi at 2pm', 'add a feeding task'). Keywords: schedule, task, activity, routine, walk, feed, meds.
- ADD_PET: The user wants to register a brand NEW pet profile (e.g., 'add a 2 year old cat', 'register a new dog', 'new pet named Bella'). Keywords: new pet, register, add pet, profile.
- REMOVE_PET: The user wants to delete, remove, say goodbye to, or rehome an existing pet profile. Keywords: remove, delete, rehome, say goodbye.
- CHECK_SCHEDULE: The user wants to VIEW their existing scheduled tasks for today (e.g., 'what is my plan?', 'show my schedule', 'today task'). Keywords: plan, schedule, today, view.
- SUGGEST_SCHEDULE: The user wants the AI to ANALYZE data and PROPOSE new things to do. Keywords: suggest, analyze, what should I, recommend.
- LIST_PETS: The user explicitly wants to see a list of their current pets. Keywords: list pets, what pets, show animals.
- PET_INSIGHTS: The user is asking for analytics or history data.
- CHECK_ALERTS: The user asks for warnings or missed tasks.
- HELP_MENU: The user wants help or options.
- GENERAL_CHAT: The user is saying hello or asking conversational questions.

CRITICAL DISAMBIGUATION:
1. 'Schedule a task' or 'Add a task' MUST always be ADD_TASK, never ADD_PET.
2. 'Add a pet' is for registration only. If they mention an action (walk/feed), it is ADD_TASK.

CRITICAL RULE: You MUST classify the intent of the VERY LAST MESSAGE in the sequence. Previous messages are ONLY context. 

Return strictly a JSON dictionary:
- "intent": (string) One of the categories above.
- "confidence": (float) A score between 0.0 and 1.0 representing your certainty.

ABSOLUTELY NO CONVERSATIONAL TEXT. Return ONLY raw valid JSON."""

        from ai.utils import extract_json
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        else:
            messages.append({"role": "user", "content": user_input})

        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                options={"temperature": STRICT_TEMPERATURE, "format": "json"}
            )
            # Use the extraction utility to handle potential boilerplate
            classification = extract_json(response.message.content)
            
            # Automated Validation of Intent Payload
            is_valid = validate_schema(classification, ["intent", "confidence"])
            if is_valid:
                # Content Guardrail check
                check_restricted_keywords(response.message.content)
                
                intent = str(classification.get("intent", "GENERAL_CHAT")).strip().upper()
                confidence = classification.get("confidence", 0.0)
                ReliabilityAuditor.record_metric("Intent_Classification", confidence=confidence)
                logger.info(f"[ai/router] Intent: {intent}, Confidence: {confidence}")
            else:
                intent = "GENERAL_CHAT"
                ReliabilityAuditor.record_metric("Intent_Classification", confidence=0.0, success=False)
                logger.warning(f"[ai/router] Validation failure for classification JSON.")
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
        return schedule_tool(user_input, chat_history)
    elif "SUGGEST_SCHEDULE" in intent:
        st.session_state.active_intent = None
        return planner_tool(user_input, chat_history)
    elif "PET_INSIGHTS" in intent:
        st.session_state.active_intent = None
        return status_report_tool(user_input, chat_history)
    elif "CHECK_ALERTS" in intent:
        st.session_state.active_intent = None
        return status_report_tool(user_input, chat_history)
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
