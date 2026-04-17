from datetime import datetime, timedelta
from core import Owner, Pet, Task, CompletionRecord, AnalyticsEngine

# ---------------------------------------------------------------------------
# Analytics Engine
# Test: recent history within day range
# Test: unusual patterns for overdue tasks
# ---------------------------------------------------------------------------

def test_analytics_get_recent_history():
    """get_recent_history() should return records within the requested day range."""
    owner = Owner(name="Alex", available_minutes=60)
    now = datetime.now()
    r1 = CompletionRecord(task_id="1", pet_name="M", task_title="T1", category="C", timestamp=(now - timedelta(days=2)).isoformat())
    r2 = CompletionRecord(task_id="2", pet_name="M", task_title="T2", category="C", timestamp=(now - timedelta(days=10)).isoformat())
    owner.history = [r1, r2]

    engine = AnalyticsEngine(owner=owner)
    recent = engine.get_recent_history(days=7)

    assert len(recent) == 1
    assert recent[0].task_id == "1"


def test_analytics_detect_unusual_patterns_overdue():
    """get_unusual_patterns() should flag tasks whose due_date is in the past."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])

    # Task due yesterday
    yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
    pet.add_task(Task(title="Overdue Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", due_date=yesterday))

    engine = AnalyticsEngine(owner=owner)
    anomalies = engine.get_unusual_patterns()

    assert len(anomalies) == 1
    assert "missing" in anomalies[0]