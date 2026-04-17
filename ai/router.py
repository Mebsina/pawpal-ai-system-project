"""
router.py
Intercepts natural language from the Unified Chat Hub, classifies the intent,
and delegates standard actions to the requisite backend tools.
"""

import logging
import ollama
import streamlit as st

from config import MODEL_NAME, STRICT_TEMPERATURE, CHAT_TEMPERATURE
from ai.tools import add_task_tool

logger = logging.getLogger(__name__)

def classify_and_route(user_input: str, chat_history: list = None):
    """
    Classifies the unified intention and delegates payload processing to specific modular tools.
    Utilizes active session intent locks to enforce linear multi-turn pipeline sequences mathematically.
    """
    
    # 1. Physical User Override: Provide clean organic escape routes from active loops unconditionally
    hard_input = user_input.lower().strip()
    if hard_input in ["menu", "help", "cancel", "nevermind", "stop", "abort"]:
        st.session_state.active_intent = None

    # 2. Sequential Intent Lock: Force strict continuity bypassing LLM variance if already trapped in an active tool loop
    locked_intent = st.session_state.get("active_intent")
    
    if locked_intent:
        intent = locked_intent
        logger.info(f"[ai/router] System structurally intercepted via Active Context State Lock: {intent}")
    else:
        system_prompt = """Classify the following user input into strictly ONE of the categories below:
- ADD_TASK: The user wants to schedule a new care event (e.g. walk, feed).
- CHECK_SCHEDULE: The user is asking to view or generate their daily plan.
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
    elif "CHECK_SCHEDULE" in intent:
        st.session_state.active_intent = None
        return "I am ready to interpret calendar metrics, but the schedule visualization tool is currently finalizing."
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
