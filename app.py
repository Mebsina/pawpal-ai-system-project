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

if "active_pet_index" not in st.session_state:
    st.session_state.active_pet_index = 0

owner = st.session_state.owner

# --- Owner Info ---
st.subheader("Owner Info")
col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.available_minutes = st.number_input(
        "Available minutes per day", min_value=1, max_value=480, value=owner.available_minutes
    )

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
        active_pet.add_task(Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=priority,
            category=category,
            frequency=frequency,
            scheduled_time=scheduled_time,
        ))

    if active_pet.tasks:
        st.write(f"Tasks for {active_pet.name}:")
        st.table([
            {
                "Title": t.title,
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

if st.button("Current Plan"):
    if not owner.pets:
        st.warning("Add at least one pet first.")
    elif not any(p.tasks for p in owner.pets):
        st.warning("Add at least one task before generating a schedule.")
    elif not owner.name:
        st.warning("Enter an owner name first.")
    else:
        scheduler = Scheduler(owner=owner)
        schedule = scheduler.generate_plan()

        st.success(f"Scheduled {len(schedule.tasks)} task(s), {schedule.total_duration} minutes total.")

        if schedule.tasks:
            st.markdown("**Scheduled tasks:**")
            st.table([
                {"title": t.title, "duration_minutes": t.duration_minutes, "priority": t.priority}
                for t in schedule.tasks
            ])

        if schedule.unscheduled:
            st.markdown("**Could not fit:**")
            st.table([
                {"title": t.title, "duration_minutes": t.duration_minutes, "priority": t.priority}
                for t in schedule.unscheduled
            ])

        st.markdown("**Explanation:**")
        st.text(scheduler.explain_plan(schedule))
