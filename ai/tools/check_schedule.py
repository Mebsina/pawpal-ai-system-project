import logging
import ollama
from datetime import date
from config import MODEL_NAME
from pawpal_system import load_data, Scheduler

logger = logging.getLogger(__name__)

def check_schedule_tool(user_input: str, chat_history: list = None):
    """
    Analyzes mathematical scheduling bounds logically and passes the unified variable tracking natively to an LLM 
    instruction structurally strictly limited to a single output sentence serving as a humanized visual wrapper for the pandas dataframe loop.
    """
    
    owner = load_data()
    scheduler = Scheduler(owner=owner)
    today_str = date.today().isoformat()
    
    # Isolate uncompleted metrics functionally for exclusively the current date
    incomplete = scheduler.filter_tasks(status=False, target_date=today_str)
    
    if not incomplete:
        return {
            "type": "show_schedule_table",
            "message": "It looks like your schedule is completely clear for today! Is there anything you'd like to dynamically add?"
        }
        
    schedule = scheduler.generate_plan(tasks=incomplete)
    
    # Extract structural metrics cleanly
    tasks_count = len(schedule.tasks)
    used_mins = schedule.total_duration
    rem_mins = owner.available_minutes - used_mins
    unscheduled = len(schedule.unscheduled)
    
    # Construct an explicitly constrained zero-shot prompt forcing exactly 1 conversation wrapper over the vars
    system_prompt = f"""You are PawPal, a warm and helpful pet care assistant.
The user is checking their daily schedule. 
Strictly write ONLY ONE warm, conversational sentence introducing their plan. 
Incorporate these exact metrics seamlessly into the sentence: 
- {tasks_count} tasks scheduled 
- {used_mins} minutes utilized
- {rem_mins} minutes remaining in their daily time budget
{'Warn them gently that ' + str(unscheduled) + ' tasks could not fit today.' if unscheduled > 0 else 'All tasks fit perfectly!'}
CRITICAL RULE: DO NOT generate a list or a table. DO NOT output the tasks themselves. Write EXACTLY one friendly greeting sentence!"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            options={"temperature": 0.5}
        )
        llm_greeting = response.message.content.strip()
    except Exception as e:
        logger.error(f"[check_schedule] LLM summarization pipeline failed organically: {e}")
        llm_greeting = "Here is your completely optimized plan for today:"
        
    return {
        "type": "show_schedule_table",
        "message": llm_greeting
    }
