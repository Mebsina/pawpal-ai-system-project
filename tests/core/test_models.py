from core.models import Task, Pet, Owner, CompletionRecord
import uuid

# ---------------------------------------------------------------------------
# Data Model Integrity
# Test: task completion status toggling
# Test: pet task addition API (pet.add_task)
# Test: owner pet registration (owner.add_pet)
# Test: owner pet removal (owner.remove_pet; delegates to remove_pet_for_owner)
# Test: owner.remove_pet unknown name is a no-op (returns False)
# Test: completion history pruned for removed pet only (owner.remove_pet)
# Test: persistent hex UUID identity generation
# Test: parent-child relationship binding (created_next_task_id)
# Test: mutable default argument safeguards (special_needs)
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    """Task completion: mark_complete() should set completion_status to True."""
    task = Task(title="Morning walk", duration_minutes=30, priority="high", category="walk", frequency="daily")
    assert task.completion_status is False
    task.mark_complete()
    assert task.completion_status is True

def test_adding_task_increases_pet_task_count():
    """Task addition: pet.add_task() should be the standard API for adding tasks."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high", category="feeding", frequency="daily"))
    assert len(pet.tasks) == 1

def test_owner_add_pet_appends_to_list():
    """Owner registration: owner.add_pet() should append to the pets list."""
    owner = Owner(name="Alex", available_minutes=60)
    pet = Pet(name="Luna", species="Cat", age=5)
    owner.add_pet(pet)
    assert len(owner.pets) == 1
    assert owner.pets[0].name == "Luna"

def test_task_generates_unique_uuid_identity():
    """Task identity: verify that each task receives a persistent hex UUID."""
    task1 = Task(title="T1", duration_minutes=1, priority="low", category="x", frequency="once")
    task2 = Task(title="T2", duration_minutes=1, priority="low", category="x", frequency="once")
    assert task1.id != task2.id
    assert len(task1.id) >= 32 # Hex UUID string length

def test_task_created_next_task_id_binding():
    """Task linkage: verify the created_next_task_id field exists for parent-child relationship."""
    task = Task(title="Parent", duration_minutes=1, priority="low", category="x", frequency="daily")
    assert task.created_next_task_id is None
    task.created_next_task_id = "child-123"
    assert task.created_next_task_id == "child-123"

def test_pet_special_needs_defaults_to_empty_list():
    """Mutable default safeguards: verify special_needs is unique per instance."""
    p1 = Pet(name="P1", species="dog", age=1)
    p2 = Pet(name="P2", species="cat", age=2)
    p1.special_needs.append("senior")
    assert "senior" not in p2.special_needs


def test_owner_remove_pet_drops_pet_and_tasks():
    """remove_pet: removes the pet object (and nested tasks) from the owner."""
    owner = Owner(name="Alex", available_minutes=60)
    mochi = Pet(name="Mochi", species="dog", age=2)
    mochi.add_task(Task(title="Walk", duration_minutes=20, priority="high", category="walk", frequency="daily"))
    owner.add_pet(mochi)
    owner.add_pet(Pet(name="Luna", species="cat", age=1))
    assert owner.remove_pet("Mochi") is True
    assert len(owner.pets) == 1
    assert owner.pets[0].name == "Luna"


def test_owner_remove_pet_unknown_returns_false():
    """remove_pet: no-op when name does not match any pet."""
    owner = Owner(name="Alex", available_minutes=60)
    owner.add_pet(Pet(name="Mochi", species="dog", age=2))
    assert owner.remove_pet("Nope") is False
    assert len(owner.pets) == 1


def test_owner_remove_pet_prunes_history():
    """remove_pet: strips completion records for that pet_name only."""
    owner = Owner(name="Alex", available_minutes=60)
    owner.add_pet(Pet(name="Mochi", species="dog", age=2))
    owner.add_pet(Pet(name="Luna", species="cat", age=1))
    owner.history = [
        CompletionRecord(
            task_id="a",
            pet_name="Mochi",
            task_title="Walk",
            category="walk",
            timestamp="2024-01-01T10:00:00",
        ),
        CompletionRecord(
            task_id="b",
            pet_name="Luna",
            task_title="Feed",
            category="feeding",
            timestamp="2024-01-01T11:00:00",
        ),
    ]
    assert owner.remove_pet("Mochi") is True
    assert len(owner.history) == 1
    assert owner.history[0].pet_name == "Luna"
