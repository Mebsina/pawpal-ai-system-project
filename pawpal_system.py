"""
Full implementation of backend logics for the PawPal pet care scheduling system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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

    def generate_plan(self) -> Schedule:
        """Retrieve all tasks from owner's pets and build a schedule.

        Returns
        -------
        Schedule
            A Schedule whose .tasks list contains every task that fit,
            and whose .unscheduled list contains every task that did not.
        """
        all_tasks = [task for pet in self.owner.pets for task in pet.tasks]

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

    def explain_plan(self, schedule: Schedule) -> str:
        """Return an explanation of the generated plan.

        Parameters
        ----------
        schedule:
            A Schedule previously returned by generate_plan().

        Returns
        -------
        str
            Explanation of why each task was scheduled or skipped.
        """
        lines = [
            f"Daily plan for {self.owner.name} "
            f"({self.owner.available_minutes} minutes available):\n"
        ]

        for task in schedule.tasks:
            lines.append(
                f"  [scheduled]  {task.title} "
                f"({task.duration_minutes} min, {task.priority} priority)"
            )

        for task in schedule.unscheduled:
            lines.append(
                f"  [skipped]    {task.title} "
                f"({task.duration_minutes} min, {task.priority} priority) "
                f"— did not fit within the time budget"
            )

        lines.append(f"\nTotal scheduled time: {schedule.total_duration} minutes.")
        return "\n".join(lines)
