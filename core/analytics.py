from __future__ import annotations
from datetime import datetime, timedelta
from core.models import Owner, CompletionRecord

class AnalyticsEngine:
    """Computes operational logic mapping longitudinal insights directly over legacy historical constraints."""
    def __init__(self, owner: Owner):
        self.owner = owner
        
    def get_recent_history(self, days: int = 7) -> list[CompletionRecord]:
        """Return historical record of task completions within the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        for r in self.owner.history:
            try:
                if datetime.fromisoformat(r.timestamp) >= cutoff:
                    recent.append(r)
            except ValueError:
                pass
        return recent

    def get_unusual_patterns(self) -> list[str]:
        """Detects if recurring tasks have been missed based on history and current status."""
        anomalies = []
        now = datetime.now()
        today_iso = now.date().isoformat()
        current_time_str = now.strftime("%H:%M")
        
        for pet in self.owner.pets:
            for task in pet.tasks:
                if not task.completion_status:
                    # Case 1: Past Due Date
                    if task.due_date < today_iso:
                        anomalies.append(f"{pet.name} is missing their {task.frequency} {task.title} (Due: {task.due_date})")
                    # Case 2: Due Today but Scheduled Time has passed
                    elif task.due_date == today_iso:
                        if task.scheduled_time and task.scheduled_time < current_time_str:
                            anomalies.append(f"{pet.name}'s {task.title} was scheduled for {task.scheduled_time} today, but isn't marked done yet.")
        return anomalies
