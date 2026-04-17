from core import Task, Pet

# ---------------------------------------------------------------------------
# Data model integrity
# Test: mark task complete changes status
# Test: adding task increases pet task count
# ---------------------------------------------------------------------------

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
