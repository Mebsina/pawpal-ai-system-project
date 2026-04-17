import logging
import ollama
from config import MODEL_NAME, STRICT_TEMPERATURE
from core import load_data, AnalyticsEngine

logger = logging.getLogger(__name__)

def get_insights_tool(user_input: str, chat_history: list = None):
    """
    Evaluates historical data dynamically feeding natural language summaries over Analytics Arrays organically.
    """
    owner = load_data()
    engine = AnalyticsEngine(owner=owner)
    
    recent_records = engine.get_recent_history(days=7)
    
    if not recent_records:
        return "I scoped your analytics history, but I haven't recorded any completed tasks in the last 7 days! Mark some tasks complete on your dashboard so I can track your behavior insights!"
        
    # Compress history arrays conceptually physically mapping data constraints
    history_strings = []
    for r in recent_records:
        history_strings.append(f"{r.pet_name} completed '{r.task_title}' ({r.category}) on {r.timestamp}")
        
    system_prompt = f"""You are PawPal, a helpful AI analyzing a user's pet care history.
The user wants insights dynamically based on the exact historical records provided rigidly below.
CRITICAL INSTRUCTION: Base your analysis STRICTLY on these physical data constraints. Do NOT invent completions.

COMPLETIONS (Last 7 Days):
{chr(10).join(history_strings)}

Answer the user's specific analytic question warmly and conversationally directly addressing the temporal data patterns. Do NOT generate visual bar charts or markdown tables.
CRITICAL RULE: NEVER ask the user a follow up question. End your message with a conclusive, finite statement framing the analytics explicitly."""

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        messages.extend(chat_history[-4:])
    messages.append({"role": "user", "content": user_input})
        
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            options={"temperature": STRICT_TEMPERATURE}
        )
        llm_greeting = response.message.content.strip()
    except Exception as e:
        logger.error(f"[get_insights] LLM summarization pipeline failed organically: {e}")
        llm_greeting = "I reliably mapped your analytics arrays, but am having trouble dynamically summarizing them right now via the underlying inference engine."
        
    return llm_greeting
