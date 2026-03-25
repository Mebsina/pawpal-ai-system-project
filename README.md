# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

Four logic improvements were added to `pawpal_system.py` to make the scheduler more useful for a real pet owner.

### Sort tasks by time

`Scheduler.sort_by_time(tasks)` returns any list of tasks ordered chronologically by their `scheduled_time` field (`"HH:MM"` string). Because times are zero-padded, Python's built-in `sorted()` with a plain string lambda is enough — no datetime parsing needed.

```python
sorted_tasks = scheduler.sort_by_time(all_tasks)
```

Each `Task` now has a `scheduled_time` field (default `"00:00"`). In the app, this is set via a time picker with 15-minute increments.

### Filter tasks by pet or status

`Scheduler.filter_tasks(pet_name=None, status=None)` returns a flat list of tasks matching any combination of filters:

```python
scheduler.filter_tasks(pet_name="Mochi", status=False)  # Mochi's incomplete tasks only
scheduler.filter_tasks(status=True)                      # all completed tasks across all pets
```

`generate_plan()` accepts an optional `tasks` argument so a filtered list can be passed directly into the scheduler, letting you generate a plan scoped to one pet or one status.

### Recurring task handling

`Scheduler.reschedule_if_recurring(task, pet)` marks a task complete and, if its `frequency` is `"daily"` or `"weekly"`, automatically creates the next occurrence with the correct due date using Python's `timedelta`:

```python
# daily:  next due = today + 1 day
# weekly: next due = today + 7 days
next_task = scheduler.reschedule_if_recurring(task, pet)
```

Each `Task` stores a `due_date` field (`"YYYY-MM-DD"`) that defaults to today. One-off tasks (`"once"`) return `None` — no new task is created.

### Conflict detection

`Scheduler.detect_time_conflicts(tasks=None)` checks whether any two tasks share the same `scheduled_time` slot across all pets. It never raises — it returns a list of plain-text warning strings (empty list means no conflicts):

```python
conflicts = scheduler.detect_time_conflicts()
# ["CONFLICT at 09:00 — Litter box (Luna), Meds (Mochi)"]
```

In the app, this check runs before a new task is saved. If a conflict is found, the task is rejected with a warning and the owner is prompted to choose a different time.

---

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
