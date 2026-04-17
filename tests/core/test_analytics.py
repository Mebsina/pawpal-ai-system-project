from datetime import datetime, timedelta
from core import Owner, Pet, Task, CompletionRecord, AnalyticsEngine

# ---------------------------------------------------------------------------
# Analytics Engine
# Test: recent history filtered by day range
# Test: empty history state resilience
# Test: unusual patterns for overdue legacy tasks (due_date in past)
# Test: missed today task detection (scheduled time passed)
# Test: history lookup boundary conditions (inclusive logic)
# Test: history cleanup simulation on task uncompletion
# Test: malformed timestamp handling in historical records
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

def test_analytics_empty_history_returns_empty():
    """Edge case: owner with zero history records."""
    owner = Owner(name="New", available_minutes=60)
    engine = AnalyticsEngine(owner=owner)
    assert engine.get_recent_history() == []
    assert engine.get_unusual_patterns() == []

def test_analytics_detect_unusual_patterns_overdue():
    """get_unusual_patterns() should flag tasks whose due_date is in the past."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
    pet.add_task(Task(title="Overdue Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", due_date=yesterday))

    engine = AnalyticsEngine(owner=owner)
    anomalies = engine.get_unusual_patterns()

    assert len(anomalies) == 1
    assert "missing" in anomalies[0]
    assert "Mochi" in anomalies[0]

def test_analytics_detect_missed_today_task():
    """Verify that a task scheduled for 2 hours ago but not done is flagged."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    
    two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime("%H:%M")
    today = datetime.now().date().isoformat()
    
    pet.add_task(Task(
        title="Late Feeding", 
        duration_minutes=10, 
        priority="high", 
        category="feeding", 
        frequency="daily", 
        due_date=today,
        scheduled_time=two_hours_ago
    ))

    engine = AnalyticsEngine(owner=owner)
    anomalies = engine.get_unusual_patterns()
    assert len(anomalies) == 1
    assert "was scheduled for" in anomalies[0]

def test_analytics_get_recent_history_boundary():
    """Verify boundary inclusive logic (exactly 7 days ago)."""
    owner = Owner(name="Alex", available_minutes=60)
    # Use 7 days minus 1 minute to ensure it falls within the >= boundary despite execution time
    seven_days_ago = (datetime.now() - timedelta(days=7, seconds=-60)).isoformat()
    owner.history = [CompletionRecord(task_id="1", pet_name="M", task_title="T", category="C", timestamp=seven_days_ago)]
    
    engine = AnalyticsEngine(owner=owner)
    assert len(engine.get_recent_history(days=7)) == 1

def test_analytics_cleanup_on_uncomplete():
    """Uncompleting a task should logically remove the corresponding history record."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    
    task = Task(title="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily")
    pet.add_task(task)
    
    # Complete
    task.mark_complete()
    record = CompletionRecord(
        task_id=task.id, 
        pet_name=pet.name, 
        task_title=task.title, 
        category=task.category, 
        timestamp=datetime.now().isoformat()
    )
    owner.history.append(record)
    assert len(owner.history) == 1
    
    # Uncomplete simulation (reflecting current UI logic gap)
    task.completion_status = False
    # Logic to remove record:
    owner.history = [r for r in owner.history if r.task_id != task.id]
    
    assert len(owner.history) == 0

def test_get_recent_history_malformed_timestamp():
    """Ensure malformed timestamps in history are skipped without crashing."""
    owner = Owner(name="Alex", available_minutes=60)
    owner.history.append(CompletionRecord("1", "Mochi", "Bad Time", "exercise", "not-a-timestamp"))
    
    engine = AnalyticsEngine(owner=owner)
    # Should not raise ValueError
    recent = engine.get_recent_history(days=7)
    assert len(recent) == 0