from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import date

@dataclass
class Task:
    """Represents a single care task assigned to a pet.

    Attributes
    ----------
    title:
        Name for the task.
    duration_minutes:
        How long the task takes to complete.
    priority:
        One of "low", "medium", or "high" (see PRIORITY_ORDER).
    category:
        Broad grouping such as "walk", "feeding", "meds",
        "grooming", or "enrichment".
    frequency:
        How often the task recurs, e.g. "daily", "weekly", "once".
    completion_status:
        Whether the task has been completed today.
    notes:
        Optional free-text notes about the task.
    """
    title: str
    duration_minutes: int
    priority: str
    category: str
    frequency: str
    completion_status: bool = False
    notes: str = ""
    scheduled_time: str = "00:00"
    due_date: str = field(default_factory=lambda: date.today().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_next_task_id: str | None = None

    def __post_init__(self) -> None:
        """Normalize fields after initialization."""
        if isinstance(self.priority, str):
            self.priority = self.priority.lower().strip()

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completion_status = True

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Create a Task instance from a dictionary."""
        return cls(**data)

@dataclass
class Pet:
    """Represents a pet and its associated care tasks.

    Attributes
    ----------
    name:
        The pet's name.
    species:
        The pet's species (e.g. "dog", "cat").
    age:
        The pet's age in years.
    special_needs:
        List of special needs or conditions (e.g. ["diabetic", "senior"]).
    tasks:
        List of care tasks assigned to this pet.
    """
    name: str
    species: str
    age: int
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        self.tasks.append(task)

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Create a Pet instance from a dictionary, including nested tasks."""
        tasks_data = data.pop("tasks", [])
        tasks = [Task.from_dict(t) for t in tasks_data]
        return cls(**data, tasks=tasks)

@dataclass
class CompletionRecord:
    """Represents a fixed historical record of a task physically completed."""
    task_id: str
    pet_name: str
    task_title: str
    category: str
    timestamp: str

    @classmethod
    def from_dict(cls, data: dict) -> CompletionRecord:
        """Create a CompletionRecord instance from a dictionary."""
        return cls(**data)

@dataclass
class Owner:
    """Represents the pet owner and their daily time budget.

    Attributes
    ----------
    name:
        The owner's name.
    available_minutes:
        Total minutes per day available for pet care.
    preferences:
        Optional key/value preferences (e.g. {"morning_tasks": ["walk"]}).
    pets:
        List of pets the owner manages. Remove with :meth:`remove_pet` or
        :func:`remove_pet_for_owner` (shared with the Streamlit UI).
    """
    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)
    history: list[CompletionRecord] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's list."""
        self.pets.append(pet)

    def get_pet_by_name(self, name: str) -> Pet | None:
        """Find a pet by name in the owner's managed list."""
        return next((p for p in self.pets if p.name == name), None)

    def remove_pet(self, name: str) -> bool:
        """Remove a pet by exact name and drop their completion history records."""
        return remove_pet_for_owner(self, name)

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Create an Owner instance from a dictionary, including nested pets and history."""
        pets_data = data.pop("pets", [])
        history_data = data.pop("history", [])
        pets = [Pet.from_dict(p) for p in pets_data]
        history = [CompletionRecord.from_dict(h) for h in history_data]
        return cls(**data, pets=pets, history=history)


def remove_pet_for_owner(owner: Owner, name: str) -> bool:
    """Remove a pet by exact name and drop matching completion history.

    Module-level helper so UI layers can call it directly (same behavior as
    :meth:`Owner.remove_pet`) without relying on a possibly stale method binding
    under Streamlit reloads.
    """
    if not name or not str(name).strip():
        return False
    name = str(name).strip()
    before = len(owner.pets)
    owner.pets = [p for p in owner.pets if p.name != name]
    if len(owner.pets) == before:
        return False
    owner.history = [h for h in owner.history if h.pet_name != name]
    return True
