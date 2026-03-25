"""Phase 2: Core Implementation - temporary testing ground.

Run this script to verify scheduling logic works in the terminal:
    python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler

# --- Set up pets and tasks (intentionally out of time order) ---

mochi = Pet(name="Mochi", species="dog", age=3)
mochi.tasks = [
    Task(title="Grooming",      duration_minutes=45, priority="low",    category="grooming",   frequency="weekly", scheduled_time="14:00"),
    Task(title="Morning walk",  duration_minutes=30, priority="high",   category="walk",       frequency="daily",  scheduled_time="07:00"),
    Task(title="Feeding",       duration_minutes=10, priority="high",   category="feeding",    frequency="daily",  scheduled_time="08:30"),
]

luna = Pet(name="Luna", species="cat", age=5)
luna.tasks = [
    Task(title="Play time",     duration_minutes=20, priority="medium", category="enrichment", frequency="daily",  scheduled_time="17:00"),
    Task(title="Litter box",    duration_minutes=10, priority="high",   category="cleaning",   frequency="daily",  scheduled_time="09:00"),
]

# Mark one task complete so we can test status filtering
mochi.tasks[1].mark_complete()  # Morning walk is done

# --- Set up owner ---

jordan = Owner(name="Jordan", available_minutes=60, pets=[mochi, luna])

# --- Run scheduler ---

scheduler = Scheduler(owner=jordan)

# ----- TEST 1: sort_by_time -----
print("=" * 40)
print("  TEST 1: sort_by_time()")
print("  All tasks sorted chronologically")
print("=" * 40)
all_tasks = [task for pet in jordan.pets for task in pet.tasks]
for t in scheduler.sort_by_time(all_tasks):
    done = "[done]" if t.completion_status else "      "
    print(f"  {t.scheduled_time}  {done}  {t.title}")

# ----- TEST 2: filter_tasks by status -----
print()
print("=" * 40)
print("  TEST 2: filter_tasks(status=False)")
print("  Only incomplete tasks")
print("=" * 40)
incomplete = scheduler.filter_tasks(status=False)
for t in incomplete:
    print(f"  {t.title} ({t.frequency})")

# ----- TEST 3: filter_tasks by pet -----
print()
print("=" * 40)
print("  TEST 3: filter_tasks(pet_name='Mochi')")
print("  Only Mochi's tasks")
print("=" * 40)
mochi_tasks = scheduler.filter_tasks(pet_name="Mochi")
for t in mochi_tasks:
    done = "[done]" if t.completion_status else "[    ]"
    print(f"  {done}  {t.title}")

# ----- TEST 4: generate plan from incomplete tasks only -----
print()
print("=" * 40)
print("  TEST 4: generate_plan(incomplete tasks)")
print("=" * 40)
schedule = scheduler.generate_plan(tasks=incomplete)
print(scheduler.explain_plan(schedule))
