import logging
import ollama
import config
from core import load_data, AnalyticsEngine
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def get_insights_tool(user_input: str, chat_history: list = None):
    """
    Evaluates historical data and provides natural language summaries formatted as JSON with confidence scoring.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    recent_records = engine.get_recent_history(days=7)
    
    if not recent_records:
        return "I scoped your analytics history, but I haven't recorded any completed tasks in the last 7 days! Mark some tasks complete on your dashboard so I can track your behavior insights!"
        
    history_strings = []
    for r in recent_records:
        history_strings.append(f"{r.pet_name} completed '{r.task_title}' ({r.category}) on {r.timestamp}")
        
    system_prompt = f"""You are PawPal, a helpful AI analyzing a user's pet care history.

COMPLETIONS (Last 7 Days):
{chr(10).join(history_strings)}

Answer the user's specific analytic question warmly and conversationally based strictly on the data above.
Do NOT generate charts or tables. End with a conclusive statement.

Return strictly a JSON dictionary:
- "message": (string) Your conversational analytic summary.
- "confidence": (float) A score between 0.0 and 1.0 representing your certainty.

ABSOLUTELY NO CONVERSATIONAL TEXT outside the JSON. Return ONLY raw valid JSON."""

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-4:])
    messages.append({"role": "user", "content": user_input})
        
    try:
        response = ollama.chat(
            model=config.MODEL_NAME,
            messages=messages,
            options={"temperature": config.STRICT_TEMPERATURE, "format": "json"}
        )
        extracted_data = extract_json(response.message.content)
        if extracted_data:
            confidence = extracted_data.get("confidence", 0.0)
            logger.info(f"[ai/tools/get_insights] Insights Confidence: {confidence}")
            message = extracted_data.get("message", "I've analyzed your pet care patterns.")
        else:
            message = response.message.content.strip()
    except Exception as e:
        logger.error(f"[get_insights] LLM failed: {e}")
        message = "I reliably mapped your analytics, but am having trouble summarizing them right now."
        
    return message
