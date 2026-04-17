import logging
import ollama
import streamlit as st
from config import MODEL_NAME
from core import load_data, AnalyticsEngine

logger = logging.getLogger(__name__)

def predictive_alerts_tool(user_input: str, chat_history: list = None):
    """
    Scans the system for behavioral anomalies and missed tasks, then humanizes them via LLM.
    Strictly grounded in system data to prevent hallucinations.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    anomalies = engine.get_unusual_patterns()
    registered_pets = [p.name for p in owner.pets]
    
    if not anomalies:
        return "Everything looks on track! I haven't detected any missed routines or unusual patterns for your pets."
        
    system_prompt = f"""You are PawPal, a precise pet care assistant.
Your goal is to summarize the following detected anomalies.

REAL PETS REGISTERED: {', '.join(registered_pets)}
DETECTED ANOMALIES:
{chr(10).join(['- ' + a for a in anomalies])}

CRITICAL INSTRUCTIONS:
1. INTERNAL LABELS: Never mention the internal labels like 'REAL PETS REGISTERED' or 'DETECTED ANOMALIES' in your output. Just use the information naturally.
2. SCOPE: ONLY mention pets and issues found in the lists above.
3. NO HALLUCINATIONS: If a pet or task is not in the lists above, IT DOES NOT EXIST. DO NOT make up names or events.
4. STYLE: Be warm, professional, and stay strictly 100% grounded in the facts provided.
5. RECOMMENDATION: If you mention a missed task, ask if the user wants to schedule a catch-up session now."""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Please summarize these alerts for me."}
            ],
            options={"temperature": 0.0}  # Use 0.0 for maximum grounding
        )
        message = response.message.content.strip()
        
        # Lock intent to SUGGEST_SCHEDULE so a follow-up ("sure", "yes") triggers the real planner
        st.session_state.active_intent = "SUGGEST_SCHEDULE"
        
    except Exception as e:
        logger.error(f"[predictive_alerts] LLM failed: {e}")
        message = "I noticed some items might need your attention: " + ", ".join(anomalies)
        
    return message
