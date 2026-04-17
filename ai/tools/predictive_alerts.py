import logging
import ollama
import streamlit as st
import config
from core import load_data, AnalyticsEngine
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def predictive_alerts_tool(user_input: str, chat_history: list = None):
    """
    Scans for behavioral anomalies and humanizes them via LLM packaged in JSON with confidence scoring.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    anomalies = engine.get_unusual_patterns()
    registered_pets = [p.name for p in owner.pets]
    
    if not anomalies:
        return "Everything looks on track! I haven't detected any missed routines or unusual patterns for your pets."
        
    system_prompt = f"""You are PawPal, a precise pet care assistant analyzing anomalies.

REAL PETS REGISTERED: {', '.join(registered_pets)}
DETECTED ANOMALIES:
{chr(10).join(['- ' + a for a in anomalies])}

CRITICAL INSTRUCTIONS:
1. ONLY mention pets and issues found in the lists above.
2. STYLE: Be warm, professional, and stay strictly 100% grounded in the facts.
3. RECOMMENDATION: Ask if the user wants to schedule a catch-up session now.
4. Return strictly a JSON dictionary:
   - "message": (string) Your conversational alert summary.
   - "confidence": (float) A score between 0.0 and 1.0 representing your certainty.

ABSOLUTELY NO CONVERSATIONAL TEXT outside the JSON. Return ONLY raw valid JSON."""

    try:
        response = ollama.chat(
            model=config.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Please summarize these alerts for me."}
            ],
            options={"temperature": config.STRICT_TEMPERATURE, "format": "json"}
        )
        extracted_data = extract_json(response.message.content)
        if extracted_data:
            confidence = extracted_data.get("confidence", 0.0)
            logger.info(f"[ai/tools/predictive_alerts] Alert Confidence: {confidence}")
            message = extracted_data.get("message", "I noticed some items might need your attention.")
        else:
            message = response.message.content.strip()
            
        st.session_state.active_intent = "SUGGEST_SCHEDULE"
        
    except Exception as e:
        logger.error(f"[predictive_alerts] LLM failed: {e}")
        message = "I noticed some items might need your attention: " + ", ".join(anomalies)
        
    return message
