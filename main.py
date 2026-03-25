"""Phase 2: Core Implementation - temporary testing ground.

Run this script to verify scheduling logic works in the terminal:
    python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler

# --- Set up pets and tasks ---

mochi = Pet(name="Mochi", species="dog", age=3)
mochi.tasks = [
    Task(title="Morning walk",  duration_minutes=30, priority="high",   category="walk",     frequency="daily"),
    Task(title="Feeding",       duration_minutes=10, priority="high",   category="feeding",  frequency="daily"),
    Task(title="Grooming",      duration_minutes=45, priority="low",    category="grooming", frequency="weekly"),
]

luna = Pet(name="Luna", species="cat", age=5)
luna.tasks = [
    Task(title="Litter box",    duration_minutes=10, priority="high",   category="cleaning", frequency="daily"),
    Task(title="Play time",     duration_minutes=20, priority="medium", category="enrichment", frequency="daily"),
]

# --- Set up owner ---

jordan = Owner(name="Jordan", available_minutes=60, pets=[mochi, luna])

# --- Run scheduler ---

scheduler = Scheduler(owner=jordan)
schedule = scheduler.generate_plan()

# --- Print results ---

print("=" * 40)
print("       TODAY'S SCHEDULE")
print("=" * 40)
print(scheduler.explain_plan(schedule))
