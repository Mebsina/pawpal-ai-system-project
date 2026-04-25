import os
import json
from core import Owner, Pet, Task, save_data, load_data, remove_pet_for_owner
import core.persistence

# ---------------------------------------------------------------------------
# Data Persistence
# Test: save/load round-trip preserves full state integrity
# Test: missing file returns default owner (first-run logic)
# Test: corrupted JSON recovery (resilience to malformed files)
# Test: parent-child relationship linkage persistence
# Test: remove_pet_for_owner drops pet, nested tasks, and matching history rows
# ---------------------------------------------------------------------------

def test_save_load_round_trip():
    """Saving and loading data should preserve all Owner, Pet, and Task attributes."""
    test_file = "data/test_pawpal_data_roundtrip.json"
    import core.persistence
    original_data_file = core.persistence.DATA_FILE
    core.persistence.DATA_FILE = test_file

    try:
        from core.models import CompletionRecord
        owner = Owner(name="Alex", available_minutes=45, preferences={"theme": "dark"})
        pet = Pet(name="Mochi", species="dog", age=3, special_needs=["allergy"])
        task = Task(title="Meds", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="08:00")
        task.id = "specific-uuid-123"
        pet.add_task(task)
        owner.add_pet(pet)
        
        # Test history persistence
        record = CompletionRecord(task_id="specific-uuid-123", pet_name="Mochi", task_title="Meds", category="meds", timestamp="2026-04-17T08:00:00")
        owner.history.append(record)

        save_data(owner)
        loaded_owner = load_data()

        assert loaded_owner.name == "Alex"
        assert loaded_owner.available_minutes == 45
        assert loaded_owner.preferences == {"theme": "dark"}
        assert len(loaded_owner.pets) == 1
        assert loaded_owner.pets[0].tasks[0].id == "specific-uuid-123"
        assert len(loaded_owner.history) == 1
        assert loaded_owner.history[0].task_id == "specific-uuid-123"

    finally:
        core.persistence.DATA_FILE = original_data_file
        if os.path.exists(test_file):
            os.remove(test_file)

def test_load_data_missing_file_returns_default_owner():
    """Behavior when data file doesn't exist yet."""
    test_file = "data/non_existent_file.json"
    import core.persistence
    original_data_file = core.persistence.DATA_FILE
    core.persistence.DATA_FILE = test_file

    try:
        if os.path.exists(test_file):
            os.remove(test_file)
        
        loaded_owner = load_data()
        assert isinstance(loaded_owner, Owner)
        assert loaded_owner.name == "" # Default value from load_data
    finally:
        core.persistence.DATA_FILE = original_data_file

def test_load_data_corrupted_json_handles_gracefully():
    """Behavior when data file contains invalid JSON."""
    test_file = "data/corrupted_data.json"
    import core.persistence
    original_data_file = core.persistence.DATA_FILE
    core.persistence.DATA_FILE = test_file

    try:
        os.makedirs("data", exist_ok=True)
        with open(test_file, "w") as f:
            f.write("{ invalid json [")
        
        loaded_owner = load_data()
        assert isinstance(loaded_owner, Owner)
        assert loaded_owner.name == ""
    finally:
        core.persistence.DATA_FILE = original_data_file
        if os.path.exists(test_file):
            os.remove(test_file)

def test_save_load_preserves_created_next_task_id():
    """Verify that the parent-child linkage survives round-trip serialization."""
    test_file = "data/test_pawpal_linkage.json"
    import core.persistence
    original_data_file = core.persistence.DATA_FILE
    core.persistence.DATA_FILE = test_file

    try:
        owner = Owner(name="Alex", available_minutes=1440)
        pet = Pet(name="Mochi", species="dog", age=3)
        task = Task(title="Walk", duration_minutes=30, priority="medium", category="exercise", frequency="daily", scheduled_time="08:00")
        task.created_next_task_id = "next-uuid-456" # The load-bearing linkage field
        pet.add_task(task)
        owner.add_pet(pet)

        save_data(owner)
        loaded_owner = load_data()

        assert loaded_owner.pets[0].tasks[0].created_next_task_id == "next-uuid-456"

    finally:
        core.persistence.DATA_FILE = original_data_file
        if os.path.exists(test_file):
            os.remove(test_file)


def test_remove_pet_for_owner_prunes_pets_and_history():
    """remove_pet_for_owner: same contract as Owner.remove_pet (UI and AI entry point)."""
    from core.models import CompletionRecord

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
    assert remove_pet_for_owner(owner, "Mochi") is True
    assert len(owner.pets) == 1
    assert owner.pets[0].name == "Luna"
    assert len(owner.history) == 1
    assert owner.history[0].pet_name == "Luna"
    assert remove_pet_for_owner(owner, "Nope") is False
