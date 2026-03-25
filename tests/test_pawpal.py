"""Phase 5: Testing and Verification - initial test suite."""

from pawpal_system import Owner, Pet, Task, Scheduler


def test_mark_complete_changes_status():
    """Task completion: mark_complete() should set completion_status to True."""
    task = Task(
        title="Morning walk",
        duration_minutes=30,
        priority="high",
        category="walk",
        frequency="daily",
    )
    assert task.completion_status is False
    task.mark_complete()
    assert task.completion_status is True


def test_adding_task_increases_pet_task_count():
    """Task addition: adding a task to a Pet should increase its task count."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0

    pet.tasks.append(
        Task(
            title="Feeding",
            duration_minutes=10,
            priority="high",
            category="feeding",
            frequency="daily",
        )
    )
    assert len(pet.tasks) == 1


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
