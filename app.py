import streamlit as st
from datetime import time as dtime
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# --- Session state initialization ---
# Streamlit reruns the entire script on every interaction.
# Only create these objects once. After that, read from session_state.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="", available_minutes=60, pets=[])

if "owner_editing" not in st.session_state:
    st.session_state.owner_editing = False

if "active_pet_index" not in st.session_state:
    st.session_state.active_pet_index = 0

owner = st.session_state.owner

# --- Owner Info ---
st.subheader("Owner Info")
owner_locked = bool(owner.name) and not st.session_state.owner_editing
col1, col2, col3 = st.columns([3, 3, 1])
with col1:
    owner.name = st.text_input("Owner name", value=owner.name, disabled=owner_locked)
with col2:
    owner.available_minutes = st.number_input(
        "Available minutes per day", min_value=1, max_value=480, value=owner.available_minutes,
        disabled=owner_locked
    )
with col3:
    st.write("")  # vertical alignment spacer
    if owner_locked:
        if st.button("Edit"):
            st.session_state.owner_editing = True
            st.rerun()
    elif owner.name:
        if st.button("Save"):
            st.session_state.owner_editing = False
            st.rerun()

st.divider()

# --- Add a Pet ---
st.subheader("Add a Pet")
col1, col2, col3 = st.columns(3)
with col1:
    new_pet_name = st.text_input("Pet name")
with col2:
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])
with col3:
    new_pet_age = st.number_input("Age", min_value=0, max_value=30, value=1)

if st.button("Adding a Pet"):
    if new_pet_name.strip():
        new_pet = Pet(name=new_pet_name.strip(), species=new_pet_species, age=new_pet_age)
        owner.add_pet(new_pet)
        st.session_state.active_pet_index = len(owner.pets) - 1
        st.success(f"{new_pet_name} added!")
    else:
        st.warning("Enter a pet name first.")

st.divider()

# --- Task Manager ---
st.subheader("Task Manager")

if not owner.pets:
    st.info("Add a pet above to get started.")
else:
    pet_names = [p.name for p in owner.pets]
    st.session_state.active_pet_index = st.selectbox(
        "Select pet",
        range(len(pet_names)),
        format_func=lambda i: pet_names[i],
        index=st.session_state.active_pet_index,
    )
    active_pet = owner.pets[st.session_state.active_pet_index]

    st.caption(f"Adding tasks for: **{active_pet.name}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col4, col5, col6 = st.columns(3)
    with col4:
        category = st.text_input("Category", value="walk")
    with col5:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
    with col6:
        # Increment time input by 15-minute steps (900 seconds) to make it easier to select common times.
        scheduled_time = st.time_input("Scheduled Time", value=dtime(0, 0), step=900).strftime("%H:%M")

    if st.button("Scheduling a Task"):
        new_task = Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=priority,
            category=category,
            frequency=frequency,
            scheduled_time=scheduled_time,
        )
        # Check for a time conflict before committing the task
        all_existing = [t for pet in owner.pets for t in pet.tasks]
        conflicts = Scheduler(owner=owner).detect_time_conflicts(tasks=all_existing + [new_task])
        if conflicts:
            for warning in conflicts:
                st.warning(f"⚠ {warning} — adjust the time or resolve the conflict first.")
        else:
            active_pet.add_task(new_task)
            st.success(f"'{task_title}' added at {scheduled_time}.")

    if active_pet.tasks:
        st.write(f"Tasks for {active_pet.name}:")
        st.table([
            {
                "Pet": active_pet.name,
                "Task Title": t.title,
                "Time": t.scheduled_time,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority,
                "Category": t.category,
                "Frequency": t.frequency,
            }
            for t in active_pet.tasks
        ])
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

# --- Generate Plan ---
st.subheader("Generate Plan")

col1, col2 = st.columns(2)
with col1:
    pet_filter_options = ["All Pets"] + [p.name for p in owner.pets]
    selected_pet_filter = st.selectbox("Filter by pet", pet_filter_options)
with col2:
    status_filter_options = {"Incomplete only": False, "Complete only": True, "All tasks": None}
    selected_status_label = st.selectbox("Filter by status", list(status_filter_options.keys()))
    selected_status_filter = status_filter_options[selected_status_label]

if st.button("Current Plan"):
    if not owner.pets:
        st.warning("Add at least one pet first.")
    elif not any(p.tasks for p in owner.pets):
        st.warning("Add at least one task before generating a schedule.")
    elif not owner.name:
        st.warning("Enter an owner name first.")
    else:
        scheduler = Scheduler(owner=owner)
        pet_name_filter = None if selected_pet_filter == "All Pets" else selected_pet_filter
        filtered = scheduler.filter_tasks(pet_name=pet_name_filter, status=selected_status_filter)

        if not filtered:
            st.warning("No tasks match the selected filters.")
        else:
            schedule = scheduler.generate_plan(tasks=filtered)

            # Build a task-id -> pet name lookup for display
            task_pet = {id(t): pet.name for pet in owner.pets for t in pet.tasks}

            def task_row(t):
                return {
                    "Pet": task_pet.get(id(t), "-"),
                    "Task Title": t.title,
                    "Time": t.scheduled_time,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority,
                }

            st.success(f"Scheduled {len(schedule.tasks)} task(s), {schedule.total_duration} minutes total.")

            if schedule.tasks:
                st.markdown("**Scheduled tasks:**")
                st.table([task_row(t) for t in schedule.tasks])

            if schedule.unscheduled:
                st.markdown("**Could not fit:**")
                st.table([task_row(t) for t in schedule.unscheduled])

