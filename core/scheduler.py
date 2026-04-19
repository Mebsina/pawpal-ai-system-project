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
            key=lambda t: (-PRIORITY_ORDER[t.priority.lower()], t.duration_minutes),
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
        """Check for temporal overlaps between tasks, accounting for durations.

        Compares tasks across all pets (or a supplied list) and returns 
        plain-text warnings for overlapping intervals.

        Parameters
        ----------
        tasks:
            Optional pre-filtered task list to check. If None, all
            tasks from all pets are used.

        Returns
        -------
        list[str]
            One warning string per conflict cluster.
        """
        # 1. Gather all tasks and map them to pet names
        if tasks is not None:
            all_relevant = tasks
            task_to_pet = {}
            for pet in self.owner.pets:
                for t in pet.tasks:
                    task_to_pet[t.id] = pet.name
        else:
            all_relevant = [t for pet in self.owner.pets for t in pet.tasks]
            task_to_pet = {t.id: pet.name for pet in self.owner.pets for t in pet.tasks}

        # 2. Convert to intervals [start, end) in minutes
        intervals = []
        for t in all_relevant:
            start = self._to_minutes(t.scheduled_time)
            intervals.append({
                "start": start,
                "end": start + t.duration_minutes,
                "entry": f"{t.title} for {task_to_pet.get(t.id, 'Unknown')}",
                "original_time": t.scheduled_time
            })
            
        # 3. Group overlapping tasks into clusters
        # Sort by start time to process linearly
        intervals.sort(key=lambda x: x["start"])
        
        clusters: list[list[dict]] = []
        for interval in intervals:
            added = False
            for cluster in clusters:
                # If this interval overlaps ANY member of the cluster, add it
                if any(max(interval["start"], m["start"]) < min(interval["end"], m["end"]) for m in cluster):
                    cluster.append(interval)
                    added = True
                    break
            if not added:
                clusters.append([interval])
                
        # 4. Format clusters with >1 task into warnings
        warnings = []
        for cluster in sorted(clusters, key=lambda c: sorted([m["original_time"] for m in c])[0]):
            if len(cluster) > 1:
                # Deterministic sort for entry strings (by title/pet)
                entries = sorted([m["entry"] for m in cluster])
                
                if len(entries) == 2:
                    joined_entries = f"'{entries[0]}' and '{entries[1]}'"
                else:
                    joined_entries = ", ".join([f"'{e}'" for e in entries[:-1]]) + f", and '{entries[-1]}'"
                
                # Determine earliest time in cluster
                earliest_time = sorted([m["original_time"] for m in cluster])[0]
                
                # Format: Use "exactly at" for exact matches to preserve test compatibility
                if all(m["original_time"] == earliest_time for m in cluster):
                    warnings.append(f"a scheduling overlap exactly at {earliest_time} between {joined_entries}")
                else:
                    warnings.append(f"a scheduling overlap around {earliest_time} between {joined_entries}")

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

        # Skip if this specific instance already spawned its next occurrence
        if task.created_next_task_id:
            return None

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

    def _to_minutes(self, hhmm: str) -> int:
        """Helper to convert HH:MM string to absolute minutes from midnight."""
        try:
            h, m = map(int, hhmm.split(":"))
            return h * 60 + m
        except Exception:
            # Fallback for invalid formats during migration or malformed input
            return 0
