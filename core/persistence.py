import json
import os
from dataclasses import asdict
from config import DATA_FILE
from core.models import Owner

def save_data(owner: Owner) -> None:
    """Serialize the entire owner data tree to JSON using automated dataclass mapping.
    
    Prevents saving if the owner name is empty to avoid accidental data loss during 
    initialization or UI races.
    """
    if not owner.name or not str(owner.name).strip():
        return

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        # asdict() recursively converts nested dataclasses (Pets, Tasks, History)
        json.dump(asdict(owner), f, indent=2)

def load_data() -> Owner:
    """Load the owner data tree from JSON. Returns a fresh Owner if storage is missing or corrupt."""
    if not os.path.exists(DATA_FILE):
        return Owner(name="", available_minutes=60)
    
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return Owner(name="", available_minutes=60)
            data = json.loads(content)
        return Owner.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        # Fallback to empty state if JSON is corrupted or structural schema has drifted.
        # Log error for system observability.
        import logging
        logging.error(f"Persistence | Failed to load data from {DATA_FILE}: {e}")
        return Owner(name="", available_minutes=60)
