from core import Owner, Pet, Task, Scheduler
from config import PRIORITY_ORDER

# ---------------------------------------------------------------------------
# Sorting correctness
# Test: tasks returned in chronological order
# Test: single task list
# Test: already-sorted input unchanged
# Test: midnight (00:00) sorts before all other times
# Test: all identical times preserves all tasks
# ---------------------------------------------------------------------------

def test_sort_by_time_returns_chronological_order():
    """sort_by_time() should return tasks ordered earliest to latest."""
    owner = Owner(name="Alex", available_minutes=120)
    scheduler = Scheduler(owner=owner)

    tasks = [
        Task(title="Evening meds", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="20:00"),
        Task(title="Morning walk", duration_minutes=30, priority="high", category="walk", frequency="daily", scheduled_time="07:00"),
        Task(title="Lunch feeding", duration_minutes=10, priority="medium", category="feeding", frequency="daily", scheduled_time="12:30"),
    ]

    sorted_tasks = scheduler.sort_by_time(tasks)

    assert [t.scheduled_time for t in sorted_tasks] == ["07:00", "12:30", "20:00"]


def test_sort_by_time_single_task():
    """sort_by_time() on a one-element list should return that same task."""
    owner = Owner(name="Alex", available_minutes=60)
    scheduler = Scheduler(owner=owner)

    tasks = [Task(title="Walk", duration_minutes=20, priority="high", category="walk", frequency="daily", scheduled_time="09:00")]
    assert scheduler.sort_by_time(tasks) == tasks


def test_sort_by_time_already_sorted():
    """sort_by_time() on an already-ordered list should return the same order."""
    owner = Owner(name="Alex", available_minutes=60)
    scheduler = Scheduler(owner=owner)

    tasks = [
        Task(title="Walk", duration_minutes=20, priority="high", category="walk", frequency="daily", scheduled_time="07:00"),
        Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="12:00"),
        Task(title="Meds", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="20:00"),
    ]
    assert [t.scheduled_time for t in scheduler.sort_by_time(tasks)] == ["07:00", "12:00", "20:00"]


def test_sort_by_time_midnight_sorts_first():
    """00:00 should sort before all other times."""
    owner = Owner(name="Alex", available_minutes=60)
    scheduler = Scheduler(owner=owner)

    tasks = [
        Task(title="Late meds", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="23:59"),
        Task(title="Midnight feed", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="00:00"),
    ]
    sorted_tasks = scheduler.sort_by_time(tasks)
    assert sorted_tasks[0].scheduled_time == "00:00"
    assert sorted_tasks[-1].scheduled_time == "23:59"


def test_sort_by_time_all_same_time_preserves_length():
    """sort_by_time() with all identical times should still return all tasks."""
    owner = Owner(name="Alex", available_minutes=60)
    scheduler = Scheduler(owner=owner)

    tasks = [
        Task(title="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", scheduled_time="08:00"),
        Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="08:00"),
        Task(title="Meds", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="08:00"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert len(result) == 3
    assert all(t.scheduled_time == "08:00" for t in result)


# ---------------------------------------------------------------------------
# Recurrence logic
# Test: daily task creates next-day occurrence
# Test: once frequency returns None and adds no task
# Test: weekly frequency advances by 7 days
# Test: daily task rolls over month boundary
# Test: daily task rolls over year boundary
# ---------------------------------------------------------------------------


def test_reschedule_if_recurring_daily_creates_next_day_task():
    """Completing a daily task should create a new task due the following day."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    original_due = "2026-03-25"
    task = Task(
        title="Morning walk",
        duration_minutes=30,
        priority="high",
        category="walk",
        frequency="daily",
        scheduled_time="07:00",
        due_date=original_due,
    )
    pet.add_task(task)

    next_task = scheduler.reschedule_if_recurring(task=task, pet=pet)

    assert task.completion_status is True
    assert next_task is not None
    assert next_task.due_date == "2026-03-26"
    assert next_task.completion_status is False
    assert len(pet.tasks) == 2

def test_reschedule_is_idempotent():
    """Consecutive calls for the same task should not create multiple recurrences."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    task = Task(title="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", due_date="2026-03-25")
    pet.add_task(task)

    # First call - creates recurrence
    scheduler.reschedule_if_recurring(task, pet)
    assert len(pet.tasks) == 2
    child_id = task.created_next_task_id

    # Second call - should NOT create another one
    scheduler.reschedule_if_recurring(task, pet)
    assert len(pet.tasks) == 2
    assert task.created_next_task_id == child_id


def test_reschedule_once_frequency_returns_none():
    """A one-off task should not produce a next occurrence."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    task = Task(title="Vet visit", duration_minutes=60, priority="high", category="meds", frequency="once", due_date="2026-03-25")
    pet.add_task(task)

    next_task = scheduler.reschedule_if_recurring(task=task, pet=pet)

    assert next_task is None
    assert task.completion_status is True
    assert len(pet.tasks) == 1


def test_reschedule_weekly_adds_seven_days():
    """A weekly task should create a new task due exactly 7 days later."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    task = Task(title="Bath", duration_minutes=45, priority="medium", category="grooming", frequency="weekly", due_date="2026-03-25")
    pet.add_task(task)

    next_task = scheduler.reschedule_if_recurring(task=task, pet=pet)

    assert next_task is not None
    assert next_task.due_date == "2026-04-01"


def test_reschedule_rolls_over_month_boundary():
    """A daily task due on the last day of a month should roll to the first of the next month."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    task = Task(title="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", due_date="2026-03-31")
    pet.add_task(task)

    next_task = scheduler.reschedule_if_recurring(task=task, pet=pet)

    assert next_task is not None
    assert next_task.due_date == "2026-04-01"


def test_reschedule_rolls_over_year_boundary():
    """A daily task due on Dec 31 should roll to Jan 1 of the following year."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    task = Task(title="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", due_date="2026-12-31")
    pet.add_task(task)

    next_task = scheduler.reschedule_if_recurring(task=task, pet=pet)

    assert next_task is not None
    assert next_task.due_date == "2027-01-01"


# ---------------------------------------------------------------------------
# Conflict detection
# Test: duplicate times flagged with a warning
# Test: unique times produce no warnings
# Test: three tasks at same slot produce one warning with all titles
# Test: conflicts across different pets detected
# Test: two separate conflicting slots produce two warnings
# Test: midnight slot (00:00) not exempt from conflict detection
# ---------------------------------------------------------------------------


def test_detect_time_conflicts_flags_duplicate_times():
    """detect_time_conflicts() should return a warning when two tasks share the same time slot."""
    pet = Pet(name="Luna", species="cat", age=2)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    task_a = Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="08:00")
    task_b = Task(title="Litter box", duration_minutes=5, priority="medium", category="grooming", frequency="daily", scheduled_time="08:00")
    pet.add_task(task_a)
    pet.add_task(task_b)

    conflicts = scheduler.detect_time_conflicts()

    assert len(conflicts) == 1
    assert "08:00" in conflicts[0]


def test_detect_time_conflicts_no_warning_for_unique_times():
    """detect_time_conflicts() should return an empty list when all times are distinct."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    pet.add_task(Task(title="Morning walk", duration_minutes=30, priority="high", category="walk", frequency="daily", scheduled_time="07:00"))
    pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="12:00"))

    conflicts = scheduler.detect_time_conflicts()

    assert conflicts == []


def test_detect_conflicts_three_tasks_same_slot_produces_one_warning():
    """Three tasks at the same time should produce a single warning listing all three."""
    pet = Pet(name="Luna", species="cat", age=2)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    for title in ("Feeding", "Litter box", "Meds"):
        pet.add_task(Task(title=title, duration_minutes=5, priority="medium", category="feeding", frequency="daily", scheduled_time="09:00"))

    conflicts = scheduler.detect_time_conflicts()

    assert len(conflicts) == 1
    assert "Feeding" in conflicts[0]
    assert "Litter box" in conflicts[0]
    assert "Meds" in conflicts[0]


def test_detect_conflicts_across_different_pets():
    """Conflicts between tasks on different pets should still be detected."""
    pet_a = Pet(name="Mochi", species="dog", age=3)
    pet_b = Pet(name="Luna", species="cat", age=2)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet_a, pet_b])
    scheduler = Scheduler(owner=owner)

    pet_a.add_task(Task(title="Walk", duration_minutes=30, priority="high", category="walk", frequency="daily", scheduled_time="08:00"))
    pet_b.add_task(Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily", scheduled_time="08:00"))

    conflicts = scheduler.detect_time_conflicts()

    assert len(conflicts) == 1
    assert "08:00" in conflicts[0]


def test_detect_conflicts_two_pairs_at_different_times():
    """Two separate conflicting time slots should each produce their own warning."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    pet.add_task(Task(title="Walk A", duration_minutes=20, priority="high", category="walk", frequency="daily", scheduled_time="07:00"))
    pet.add_task(Task(title="Walk B", duration_minutes=20, priority="high", category="walk", frequency="daily", scheduled_time="07:00"))
    pet.add_task(Task(title="Meds A", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="20:00"))
    pet.add_task(Task(title="Meds B", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="20:00"))

    conflicts = scheduler.detect_time_conflicts()

    assert len(conflicts) == 2
    assert any("07:00" in c for c in conflicts)
    assert any("20:00" in c for c in conflicts)


def test_detect_conflicts_midnight_slot():
    """Tasks at 00:00 should not be exempt from conflict detection."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)

    pet.add_task(Task(title="Night meds", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="00:00"))
    pet.add_task(Task(title="Late feeding", duration_minutes=10, priority="medium", category="feeding", frequency="daily", scheduled_time="00:00"))

    conflicts = scheduler.detect_time_conflicts()

    assert len(conflicts) == 1
    assert "00:00" in conflicts[0]

def test_detect_conflicts_partial_overlap():
    """Verify that overlaps within duration windows (e.g., 08:00 for 30m vs 08:15) are detected."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])
    scheduler = Scheduler(owner=owner)
    
    # Task 1: 08:00 to 08:30
    pet.add_task(Task(title="Long Walk", duration_minutes=30, scheduled_time="08:00", priority="high", category="walk", frequency="once"))
    # Task 2: 08:15 to 08:30 (Matches the second half of Task 1)
    pet.add_task(Task(title="Quick Feed", duration_minutes=15, scheduled_time="08:15", priority="high", category="feeding", frequency="once"))
    
    conflicts = scheduler.detect_time_conflicts()
    
    # NOTE: This is a known gap. Current implementation only checks exact HH:MM strings.
    # We expect this to fail (return 0 conflicts) until logic is upgraded.
    assert len(conflicts) >= 1
    assert "08:15" in conflicts[0] or "overlap" in conflicts[0].lower()


# ---------------------------------------------------------------------------
# Scheduler: generate_plan logic
# ---------------------------------------------------------------------------


def test_generate_plan_respects_budget():
    """generate_plan() should skip tasks that exceed the available_minutes budget."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)

    # Total minutes = 70 (30 + 10 + 30)
    pet.add_task(Task(title="Long Walk", duration_minutes=30, priority="high", category="walk", frequency="daily"))
    pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily"))
    pet.add_task(Task(title="Playtime", duration_minutes=30, priority="medium", category="enrichment", frequency="daily"))

    scheduler = Scheduler(owner=owner)
    plan = scheduler.generate_plan()

    assert len(plan.tasks) == 2  # Long Walk (30) + Feeding (10) = 40. Playtime (30) would exceed 60.
    assert plan.total_duration == 40
    assert len(plan.unscheduled) == 1
    assert plan.unscheduled[0].title == "Playtime"


def test_generate_plan_sorts_by_priority():
    """generate_plan() should prioritize high-priority tasks regardless of submission order."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)

    pet.add_task(Task(title="Low priority", duration_minutes=20, priority="low", category="walk", frequency="daily"))
    pet.add_task(Task(title="High priority", duration_minutes=20, priority="high", category="walk", frequency="daily"))
    pet.add_task(Task(title="Medium priority", duration_minutes=20, priority="medium", category="walk", frequency="daily"))

    scheduler = Scheduler(owner=owner)
    plan = scheduler.generate_plan()

    assert [t.priority for t in plan.tasks] == ["high", "medium", "low"]

def test_generate_plan_empty_tasks():
    """generate_plan() should return an empty Schedule if the owner has no tasks."""
    owner = Owner(name="No Tasks", available_minutes=60)
    scheduler = Scheduler(owner=owner)
    plan = scheduler.generate_plan()
    
    assert plan.tasks == []
    assert plan.total_duration == 0
    assert plan.unscheduled == []

def test_generate_plan_all_fit():
    """generate_plan() should schedule all tasks if the total duration is within budget."""
    owner = Owner(name="Budget King", available_minutes=100)
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)
    
    pet.add_task(Task(title="T1", duration_minutes=30, priority="high", category="walk", frequency="daily"))
    pet.add_task(Task(title="T2", duration_minutes=30, priority="high", category="walk", frequency="daily"))
    
    scheduler = Scheduler(owner=owner)
    plan = scheduler.generate_plan()
    
    assert len(plan.tasks) == 2
    assert plan.total_duration == 60
    assert plan.unscheduled == []


# ---------------------------------------------------------------------------
# Scheduler: filter_tasks logic
# ---------------------------------------------------------------------------


def test_filter_tasks_by_pet():
    """filter_tasks() should only return tasks for the specified pet name."""
    pet_a = Pet(name="Mochi", species="dog", age=3)
    pet_b = Pet(name="Luna", species="cat", age=2)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet_a, pet_b])

    pet_a.add_task(Task(title="A1", duration_minutes=10, priority="high", category="walk", frequency="daily"))
    pet_b.add_task(Task(title="B1", duration_minutes=10, priority="high", category="walk", frequency="daily"))

    scheduler = Scheduler(owner=owner)
    filtered = scheduler.filter_tasks(pet_name="Mochi")

    assert len(filtered) == 1
    assert filtered[0].title == "A1"


def test_filter_tasks_by_status():
    """filter_tasks() should filter by completion_status correctly."""
    pet = Pet(name="Mochi", species="dog", age=3)
    owner = Owner(name="Alex", available_minutes=120, pets=[pet])

    t1 = Task(title="Done", duration_minutes=10, priority="high", category="walk", frequency="daily", completion_status=True)
    t2 = Task(title="Not Done", duration_minutes=10, priority="high", category="walk", frequency="daily", completion_status=False)
    pet.tasks = [t1, t2]

    scheduler = Scheduler(owner=owner)

    done_tasks = scheduler.filter_tasks(status=True)
    assert len(done_tasks) == 1
    assert done_tasks[0].title == "Done"

    pending_tasks = scheduler.filter_tasks(status=False)
    assert len(pending_tasks) == 1
    assert pending_tasks[0].title == "Not Done"
