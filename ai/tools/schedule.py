import logging
import ollama
from datetime import date
import config
from core import load_data, Scheduler
from ai.utils import extract_json

logger = logging.getLogger(__name__)

def schedule_tool(user_input: str, chat_history: list = None):
    """
    Analyzes mathematical scheduling bounds and provides a humanized visual wrapper 
    formatted as JSON with confidence scoring.
    """
    
    owner = load_data()
    scheduler = Scheduler(owner=owner)
    today_str = date.today().isoformat()
    
    incomplete = scheduler.filter_tasks(status=False, target_date=today_str)
    
    if not incomplete:
        return {
            "type": "show_schedule_table",
            "message": "It looks like your schedule is completely clear for today! Is there anything you'd like to dynamically add?"
        }
        
    schedule = scheduler.generate_plan(tasks=incomplete)
    
    tasks_count = len(schedule.tasks)
    used_mins = schedule.total_duration
    rem_mins = owner.available_minutes - used_mins
    unscheduled = len(schedule.unscheduled)
    
    system_prompt = f"""You are PawPal, a warm and helpful pet care assistant.
The user is checking their daily schedule. 
Strictly write ONLY ONE warm, conversational sentence introducing their plan. 
Incorporate these exact metrics: {tasks_count} tasks, {used_mins} mins used, {rem_mins} mins remaining.
{'Warn them that ' + str(unscheduled) + ' tasks could not fit.' if unscheduled > 0 else 'All tasks fit!'}

Return strictly a JSON dictionary:
- "message": (string) Your ONE friendly greeting sentence.
- "confidence": (float) A score between 0.0 and 1.0 representing your certainty.

ABSOLUTELY NO CONVERSATIONAL TEXT outside the JSON. Return ONLY raw valid JSON."""

    try:
        response = ollama.chat(
            model=config.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            options={"temperature": config.CHAT_TEMPERATURE, "format": "json"}
        )
        extracted_data = extract_json(response.message.content)
        if extracted_data:
            confidence = extracted_data.get("confidence", 0.0)
            logger.info(f"[ai/tools/schedule] Summary Confidence: {confidence}")
            llm_greeting = extracted_data.get("message", "Here is your plan for today:")
        else:
            llm_greeting = response.message.content.strip()
    except Exception as e:
        logger.error(f"[schedule] LLM summarization pipeline failed: {e}")
        llm_greeting = "Here is your completely optimized plan for today:"
        
    return {
        "type": "show_schedule_table",
        "message": llm_greeting
    }
