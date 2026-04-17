import os
import json
from core import Owner, Pet, Task, save_data, load_data
import core.persistence

# ---------------------------------------------------------------------------
# Data Persistence
# ---------------------------------------------------------------------------

def test_save_load_round_trip():
    """Saving and loading data should preserve all Owner, Pet, and Task attributes."""
    test_file = "data/test_pawpal_data.json"
    
    # Monkeypatch DATA_FILE in core.persistence
    import core.persistence
    original_data_file = core.persistence.DATA_FILE
    core.persistence.DATA_FILE = test_file

    try:
        owner = Owner(name="Alex", available_minutes=45, preferences={"theme": "dark"})
        pet = Pet(name="Mochi", species="dog", age=3, special_needs=["allergy"])
        task = Task(title="Meds", duration_minutes=5, priority="high", category="meds", frequency="daily", scheduled_time="08:00")
        pet.add_task(task)
        owner.add_pet(pet)

        save_data(owner)
        loaded_owner = load_data()

        assert loaded_owner.name == "Alex"
        assert loaded_owner.available_minutes == 45
        assert loaded_owner.preferences == {"theme": "dark"}
        assert len(loaded_owner.pets) == 1
        assert loaded_owner.pets[0].name == "Mochi"
        assert loaded_owner.pets[0].special_needs == ["allergy"]
        assert len(loaded_owner.pets[0].tasks) == 1
        assert loaded_owner.pets[0].tasks[0].title == "Meds"
        assert loaded_owner.pets[0].tasks[0].scheduled_time == "08:00"

    finally:
        core.persistence.DATA_FILE = original_data_file
        if os.path.exists(test_file):
            os.remove(test_file)
