import streamlit as st
from datetime import date as ddate
from core import Scheduler
from config import PRIORITY_EMOJI

def render_plan_generator(owner):
    """Renders the schedule plan generation section and results."""
    st.subheader("Generate Plan")

    col1, col2 = st.columns(2)
    with col1:
        pet_filter_options = ["All Pets"] + [p.name for p in owner.pets]
        selected_pet_filter = st.selectbox("Filter by pet", pet_filter_options)
    with col2:
        status_filter_options = {"Incomplete only": False, "Complete only": True, "All tasks": None}
        selected_status_label = st.selectbox("Filter by status", list(status_filter_options.keys()))
        selected_status_filter = status_filter_options[selected_status_label]

    if not owner.pets:
        st.warning("Add at least one pet first.")
    elif not any(p.tasks for p in owner.pets):
        st.warning("Add at least one task before generating a schedule.")
    elif not owner.name:
        st.warning("Enter an owner name first.")
    else:
        scheduler = Scheduler(owner=owner)
        pet_name_filter = None if selected_pet_filter == "All Pets" else selected_pet_filter
        today_date = ddate.today().isoformat()
        
        all_filtered = scheduler.filter_tasks(pet_name=pet_name_filter, status=selected_status_filter, target_date=today_date)
        incomplete = [t for t in all_filtered if not t.completion_status]
        completed = [t for t in all_filtered if t.completion_status]

        if not all_filtered:
            st.warning("No tasks match the selected filters.")
        else:
            schedule = scheduler.generate_plan(tasks=incomplete)

            # Build a task-id lookup dictionary to identify the parent pet name during plan display
            task_pet = {t.id: pet.name for pet in owner.pets for t in pet.tasks}

            def task_row(t):
                return {
                    "Pet": task_pet.get(t.id, "-"),
                    "Task Title": t.title,
                    "Time": t.scheduled_time,
                    "Due Date": t.due_date,
                    "Duration (min)": t.duration_minutes,
                    "Priority": PRIORITY_EMOJI.get(t.priority.lower(), t.priority),
                }

            m1, m2, m3 = st.columns(3)
            m1.metric("Tasks Scheduled", len(schedule.tasks))
            m2.metric("Minutes Used", schedule.total_duration)
            m3.metric("Minutes Remaining", owner.available_minutes - schedule.total_duration)

            if schedule.unscheduled:
                st.warning(f"{len(schedule.unscheduled)} task(s) could not fit in your time budget.")
            else:
                st.success(f"All {len(schedule.tasks)} task(s) fit within your {owner.available_minutes}-minute budget.")

            if schedule.tasks:
                st.markdown("**Scheduled:**")
                sorted_scheduled = scheduler.sort_by_time(schedule.tasks)
                st.table([task_row(t) for t in sorted_scheduled])

            if schedule.unscheduled:
                st.markdown("**Could not fit:**")
                st.table([task_row(t) for t in schedule.unscheduled])

            if completed:
                st.markdown("**Complete:**")
                st.table([task_row(t) for t in completed])
    
    st.divider()
