import json
import os
from dataclasses import asdict
from config import DATA_FILE
from core.models import Owner

def save_data(owner: Owner) -> None:
    """Serialize the entire owner data tree to JSON using automated dataclass mapping."""
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
            data = json.load(f)
        return Owner.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Fallback to empty state if JSON is corrupted or structural schema has drifted
        return Owner(name="", available_minutes=60)
