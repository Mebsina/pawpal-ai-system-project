import logging
import ollama
import streamlit as st
import config
from core import load_data, AnalyticsEngine
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def status_report_tool(user_input: str, chat_history: list = None):
    """
    Unified tool that scans for both completed history and missed routines,
    providing a warm conversational status report.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    # Data source 1: Anomalies (Missed tasks)
    anomalies = engine.get_unusual_patterns()
    # Data source 2: History (Completions)
    recent_records = engine.get_recent_history(days=7)
    
    history_strings = [f"{r.pet_name} completed '{r.task_title}'" for r in recent_records]
    
    system_prompt = f"""You are PawPal, a warm and professional pet care assistant.
    
COMPLETED TASKS (Last 7 Days):
{chr(10).join(list(set(history_strings))) if history_strings else "No tasks completed yet this week."}

MISSED OR OVERDUE TASKS:
{chr(10).join(['- ' + a for a in anomalies]) if anomalies else "No missed tasks detected!"}

GOAL: Provide a unified, warm, and conversational status report. 

CONVERSATIONAL RULES:
1. Write in a single, friendly paragraph (3-5 sentences).
2. Start with positive reinforcement based on the COMPLETED TASKS.
3. Transition naturally to any MISSED OR OVERDUE TASKS.
4. If everything is complete, celebrate the user's progress!
5. ABSOLUTELY NO markdown headers, bullets, or lists. Use natural flowy sentences only.
6. End with a supportive suggestion on how to get back on track or maintain the good work.

CONSTRAINTS:
1. Return strictly a JSON dictionary:
   - "message": (string) Your conversational status report.
   - "confidence": (float) A score between 0.0 and 1.0.

STRICTLY JSON ONLY."""

    try:
        response = ollama.chat(
            model=config.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "How am I doing with my pets this week?"}
            ],
            options={"temperature": config.STRICT_TEMPERATURE, "format": "json"}
        )
        extracted_data = extract_json(response.message.content)
        if extracted_data:
            confidence = extracted_data.get("confidence", 0.0)
            logger.info(f"[ai/tools/status_report] Status Confidence: {confidence}")
            message = extracted_data.get("message", "I noticed some items might need your attention.")
        else:
            message = response.message.content.strip()
            
        st.session_state.active_intent = "SUGGEST_SCHEDULE"
        
    except Exception as e:
        logger.error(f"[status_report] Unified status failed: {e}")
        message = _format_fallback_message(anomalies, recent_records)
        
    return message

def _format_fallback_message(anomalies: list[str], recent_records: list) -> str:
    """Simple narrative fallback for unified status reporting."""
    if not anomalies and not recent_records:
        return "Everything looks on track! I haven't detected any missed routines or history yet."

    msg = "You've been busy with your pets! "
    if recent_records:
        msg += f"I see you've completed {len(recent_records)} tasks recently, which is great progress. "

    if anomalies:
        # Include anomaly details so individual pet names appear in the output.
        anomaly_detail = "; ".join(anomalies[:3])
        msg += f"However, some items might need your attention: {anomaly_detail}."
    else:
        msg += "Everything else seems to be running smoothly!"

    return msg + " Would you like to schedule a catch-up session now?"
