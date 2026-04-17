from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import date, timedelta
from core.models import Task, Pet, Owner
from config import PRIORITY_ORDER

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
        slots: dict[str, list[str]] = defaultdict(list)

        if tasks is not None:
            task_to_pet: dict[str, str] = {}
            for pet in self.owner.pets:
                for t in pet.tasks:
                    task_to_pet[t.id] = pet.name
            for t in tasks:
                pet_name = task_to_pet.get(t.id, "Unknown")
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
        task.created_next_task_id = next_task.id
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
