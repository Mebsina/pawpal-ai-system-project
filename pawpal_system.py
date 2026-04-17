"""
Full implementation of backend logics for the PawPal pet care scheduling system.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, timedelta

DATA_FILE = "data/pawpal_data.json"

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

PRIORITY_ORDER: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


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
    scheduled_time: str = "00:00"  # "HH:MM" format, e.g. "08:30"
    due_date: str = field(default_factory=lambda: date.today().isoformat())  # "YYYY-MM-DD"

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completion_status = True


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
        List of pets the owner manages.
    """

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's list."""
        self.pets.append(pet)


@dataclass
class Schedule:
    """The result produced by Scheduler.generate_plan().

    Attributes
    ----------
    tasks:
        Ordered list of tasks that fit within the owner's time budget.
    total_duration:
        Sum of duration_minutes for all scheduled tasks.
    unscheduled:
        Tasks that could not fit within the available time.
    """

    tasks: list[Task] = field(default_factory=list)
    total_duration: int = 0
    unscheduled: list[Task] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


@dataclass
class Scheduler:
    """Generates a daily care schedule across all of an owner's pets.

    Retrieves tasks from every pet in owner.pets, sorts them by priority
    (with duration as a tiebreaker), and fits them within the owner's
    available_minutes budget.
    """

    owner: Owner

    def generate_plan(self, tasks: list[Task] | None = None) -> Schedule:
        """Retrieve all tasks from owner's pets and build a schedule.

        Parameters
        ----------
        tasks:
            Optional pre-filtered list of tasks to schedule. If None,
            all tasks from all pets are used (default behaviour).

        Returns
        -------
        Schedule
            A Schedule whose .tasks list contains every task that fit,
            and whose .unscheduled list contains every task that did not.
        """
        all_tasks = tasks if tasks is not None else [task for pet in self.owner.pets for task in pet.tasks]

        sorted_tasks = sorted(
            all_tasks,
            key=lambda t: (-PRIORITY_ORDER[t.priority], t.duration_minutes),
        )

        schedule = Schedule()
        remaining = self.owner.available_minutes

        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                schedule.tasks.append(task)
                schedule.total_duration += task.duration_minutes
                remaining -= task.duration_minutes
            else:
                schedule.unscheduled.append(task)

        return schedule

    def detect_time_conflicts(self, tasks: list[Task] | None = None) -> list[str]:
        """Check for tasks that share the same scheduled_time slot.

        Compares every task across all pets (or a supplied list) and
        returns a plain-text warning for each time slot where two or
        more tasks overlap. Never raises — always returns a list that
        is empty when there are no conflicts.

        Parameters
        ----------
        tasks:
            Optional pre-filtered task list to check. If None, all
            tasks from all pets are used.

        Returns
        -------
        list[str]
            One warning string per conflicting time slot, e.g.:
            ["CONFLICT at 09:00 — Litter box (Luna), Feeding (Mochi)"]
            Empty list means no conflicts were found.
        """
        from collections import defaultdict

        # Build a dict: time_slot -> [(pet_name, task_title), ...]
        slots: dict[str, list[str]] = defaultdict(list)

        if tasks is not None:
            # Map task object -> pet name for the supplied list
            task_to_pet: dict[int, str] = {}
            for pet in self.owner.pets:
                for t in pet.tasks:
                    task_to_pet[id(t)] = pet.name
            for t in tasks:
                pet_name = task_to_pet.get(id(t), "Unknown")
                slots[t.scheduled_time].append(f"{t.title} for {pet_name}")
        else:
            for pet in self.owner.pets:
                for t in pet.tasks:
                    slots[t.scheduled_time].append(f"{t.title} for {pet.name}")

        warnings = []
        for time_slot, entries in sorted(slots.items()):
            if len(entries) > 1:
                if len(entries) == 2:
                    joined_entries = f"'{entries[0]}' and '{entries[1]}'"
                else:
                    joined_entries = ", ".join([f"'{e}'" for e in entries[:-1]]) + f", and '{entries[-1]}'"
                
                warnings.append(
                    f"a scheduling overlap exactly at {time_slot} between {joined_entries}"
                )
        return warnings

    def reschedule_if_recurring(self, task: Task, pet: Pet) -> Task | None:
        """Mark a task complete and create the next occurrence if it recurs.

        Uses timedelta to calculate the next due date:
          - "daily"  -> due_date + 1 day
          - "weekly" -> due_date + 7 days
          - anything else ("once", "as_needed") -> no new task created

        Parameters
        ----------
        task:
            The task being completed. Must already belong to pet.tasks.
        pet:
            The pet this task belongs to. The new occurrence is added here.

        Returns
        -------
        Task | None
            The newly created next-occurrence Task, or None if non-recurring.
        """
        task.mark_complete()

        RECURRENCE_DELTA: dict[str, timedelta] = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }

        delta = RECURRENCE_DELTA.get(task.frequency)
        if delta is None:
            return None

        next_due = date.fromisoformat(task.due_date) + delta

        next_task = Task(
            title=task.title,
            duration_minutes=task.duration_minutes,
            priority=task.priority,
            category=task.category,
            frequency=task.frequency,
            notes=task.notes,
            scheduled_time=task.scheduled_time,
            due_date=next_due.isoformat(),
        )
        pet.add_task(next_task)
        return next_task

    def filter_tasks(
        self,
        pet_name: str | None = None,
        status: bool | None = None,
        target_date: str | None = None,
    ) -> list[Task]:
        """Return tasks filtered by pet name and/or completion status.

        Parameters
        ----------
        pet_name:
            If provided, only include tasks belonging to this pet.
            Pass None to include all pets.
        status:
            If provided, only include tasks whose completion_status
            matches this value (False = incomplete, True = complete).
            Pass None to include both.
        target_date:
            If provided, strict matching against the task's due_date standard.

        Returns
        -------
        list[Task]
            Flat list of Task objects matching all supplied filters.
        """
        return [
            task
            for pet in self.owner.pets
            for task in pet.tasks
            if (pet_name is None or pet.name == pet_name)
            and (status is None or task.completion_status == status)
            and (target_date is None or task.due_date == target_date)
        ]

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted chronologically by scheduled_time.

        Parameters
        ----------
        tasks:
            List of Task objects to sort.

        Returns
        -------
        list[Task]
            New list sorted by scheduled_time in ascending order.
            "HH:MM" strings sort correctly with a plain lexicographic key
            because hours and minutes are zero-padded.
        """
        return sorted(tasks, key=lambda t: t.scheduled_time)


# ---------------------------------------------------------------------------
# Challenge 2: Data Persistence with Agent Mode
# ---------------------------------------------------------------------------

def save_data(owner: Owner) -> None:
    """Serialize owner, pets, and tasks to DATA_FILE as JSON."""
    os.makedirs("data", exist_ok=True)
    data = {
        "name": owner.name,
        "available_minutes": owner.available_minutes,
        "preferences": owner.preferences,
        "pets": [
            {
                "name": pet.name,
                "species": pet.species,
                "age": pet.age,
                "special_needs": pet.special_needs,
                "tasks": [
                    {
                        "title": t.title,
                        "duration_minutes": t.duration_minutes,
                        "priority": t.priority,
                        "category": t.category,
                        "frequency": t.frequency,
                        "completion_status": t.completion_status,
                        "notes": t.notes,
                        "scheduled_time": t.scheduled_time,
                        "due_date": t.due_date,
                    }
                    for t in pet.tasks
                ],
            }
            for pet in owner.pets
        ],
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_data() -> Owner:
    """Load owner, pets, and tasks from DATA_FILE. Returns empty Owner if file missing."""
    if not os.path.exists(DATA_FILE):
        return Owner(name="", available_minutes=60, pets=[])
    with open(DATA_FILE) as f:
        data = json.load(f)
    pets = []
    for p in data.get("pets", []):
        tasks = [Task(**t) for t in p.get("tasks", [])]
        pet = Pet(
            name=p["name"],
            species=p["species"],
            age=p["age"],
            special_needs=p.get("special_needs", []),
            tasks=tasks,
        )
        pets.append(pet)
    return Owner(
        name=data.get("name", ""),
        available_minutes=data.get("available_minutes", 60),
        preferences=data.get("preferences", {}),
        pets=pets,
    )
