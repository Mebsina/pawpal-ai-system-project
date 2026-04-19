import streamlit as st
from datetime import time as dtime
from datetime import date as ddate
from itertools import groupby
from core import Task, Scheduler, save_data, CompletionRecord
from config import PRIORITY_ORDER, PRIORITY_EMOJI, CATEGORY_EMOJI, SPECIES_EMOJI

def render_task_manager(owner):
    """Renders the comprehensive Task Manager and Dashboard."""
    st.subheader("Task Manager")

    if not owner.pets:
        st.info("Add a pet above to get started.")
        st.divider()
        return

    pet_names = [p.name for p in owner.pets]
    st.session_state.active_pet_index = st.selectbox(
        "Select pet",
        range(len(owner.pets)),
        format_func=lambda i: f"{SPECIES_EMOJI.get(owner.pets[i].species, '🐾')} {owner.pets[i].name}",
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
        # Frequency determines how recurring tasks are rescheduled upon completion.
        frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
    with col6:
        # Increment time input by 15-minute steps (900 seconds) to facilitate common scheduling blocks.
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
        # Check for time conflicts across all pets before committing to persistence
        all_existing = [t for pet in owner.pets for t in pet.tasks]
        conflicts = Scheduler(owner=owner).detect_time_conflicts(tasks=all_existing + [new_task])
        if conflicts:
            for warning in conflicts:
                st.warning(f"⚠ {warning}. Please adjust the time or resolve the conflict first.")
        else:
            active_pet.add_task(new_task)
            save_data(owner)
            st.success(f"'{task_title}' added at {scheduled_time}.")

    # Real-time data sanitization loop to surgically repair any corrupted saved states during runtime
    for pet in owner.pets:
        for t in pet.tasks:
            t.priority = (t.priority.lower() if t.priority else "medium")
            # Ensure duration is a positive integer; default to 15m for missing or invalid data
            if not t.duration_minutes or t.duration_minutes < 1:
                t.duration_minutes = 15
            t.category = t.category or "walk"
            t.title = t.title or "Task"
            if len(t.scheduled_time) > 5:
                t.scheduled_time = t.scheduled_time[-5:]

    # Capture all active tasks across every pet for unified dashboard indexing
    all_tasks_with_pet = [(pet, t) for pet in owner.pets for t in pet.tasks]
    st.divider()
    if all_tasks_with_pet:
        st.markdown(f"**Task Dashboard** ({len(all_tasks_with_pet)} tasks across {len(owner.pets)} pets)")

        col_sort, col_filter, col_toggle = st.columns([2, 2, 1.5])
        with col_sort:
            sort_by = st.selectbox(
                "Sort by",
                ["Time", "Priority (high first)", "Duration (shortest first)"],
                key="task_sort",
            )
        with col_filter:
            all_priorities = ["All"] + sorted({t.priority for _, t in all_tasks_with_pet})
            filter_priority = st.selectbox("Filter by priority", all_priorities, key="task_filter")
        with col_toggle:
            hide_completed = st.checkbox("Hide Done", value=False)

        tab_today, tab_upcoming, tab_all = st.tabs(["Today", "Upcoming", "All Tasks"])
        today_iso = ddate.today().isoformat()
        
        def render_pet_grouped_tasks(task_list, key_prefix="all"):
            if not task_list:
                st.info("Clear! No tasks found.")
                return

            filtered = [
                (p, t) for p, t in task_list 
                if (filter_priority == "All" or t.priority == filter_priority)
                and (not hide_completed or not t.completion_status)
            ]
            
            if not filtered:
                st.info("No tasks match your filters.")
                return

            if sort_by == "Time":
                filtered = sorted(filtered, key=lambda pt: pt[1].scheduled_time)
            elif sort_by == "Priority (high first)":
                filtered = sorted(filtered, key=lambda pt: -PRIORITY_ORDER[pt[1].priority.lower()])
            else:
                filtered = sorted(filtered, key=lambda pt: pt[1].duration_minutes)

            # Conditional container for the task list: use fixed height for scrolling when items exceed count
            container_args = {"height": 400} if len(filtered) > 5 else {}
            with st.container(**container_args):
                # Group tasks by pet to remove redundant columns and improve visual hierarchy
                filtered.sort(key=lambda pt: pt[0].name)
                for pet_name, group in groupby(filtered, key=lambda pt: pt[0].name):
                    st.markdown(f"**{SPECIES_EMOJI.get(next(iter(group))[0].species, '🐾')} {pet_name}**")
                    # Re-extracting group because the groupby iterator is exhausted upon first access
                    pet_tasks = [ (p,t) for p,t in filtered if p.name == pet_name ]
                    
                    # Build data for the editor to leverage st.data_editor's premium formatting
                    editor_data = []
                    for p, t in pet_tasks:
                        editor_data.append({
                            "Done": t.completion_status,
                            "Task": t.title,
                            "Time": t.scheduled_time,
                            "Due Date": t.due_date,
                            "Duration": f"{t.duration_minutes}m",
                            "Priority": PRIORITY_EMOJI.get(t.priority.lower(), t.priority),
                            "Category": f"{CATEGORY_EMOJI.get(t.category.lower(), '')} {t.category}".strip(),
                            "Frequency": t.frequency
                        })
                    
                    # Configure columns: interactive "Done" checkbox, all others read-only
                    column_config = {
                        "Done": st.column_config.CheckboxColumn("Done", help="Toggle completion status", default=False),
                        "Task": st.column_config.TextColumn("Task", disabled=True),
                        "Time": st.column_config.TextColumn("Time", disabled=True),
                        "Due Date": st.column_config.TextColumn("Due Date", disabled=True),
                        "Duration": st.column_config.TextColumn("Duration", disabled=True),
                        "Priority": st.column_config.TextColumn("Priority", disabled=True),
                        "Category": st.column_config.TextColumn("Category", disabled=True),
                        "Frequency": st.column_config.TextColumn("Frequency", disabled=True),
                    }

                    # Render the interactive table
                    edited_list = st.data_editor(
                        editor_data,
                        key=f"editor_{key_prefix}_{pet_name}",
                        column_config=column_config,
                        width="stretch",
                        hide_index=True,
                    )

                    # Detect and process changes in completion status
                    for i, row in enumerate(edited_list):
                        p, t = pet_tasks[i]
                        new_status = row["Done"]
                        
                        if t.completion_status != new_status:
                            if t.completion_status:  # Un-completing (True -> False)
                                t.completion_status = False
                                if t.created_next_task_id:
                                    p.tasks = [task for task in p.tasks if task.id != t.created_next_task_id]
                                    t.created_next_task_id = None
                                owner.history = [r for r in owner.history if r.task_id != t.id]
                            else:  # Completing (False -> True)
                                t.completion_status = True
                                record = CompletionRecord(
                                    task_id=t.id,
                                    pet_name=p.name,
                                    task_title=t.title,
                                    category=t.category,
                                    timestamp=f"{t.due_date}T{t.scheduled_time}"
                                )
                                owner.history.append(record)
                                Scheduler(owner=owner).reschedule_if_recurring(task=t, pet=p)
                            
                            save_data(owner)
                            st.rerun()
                    st.divider()

        with tab_today:
            today_tasks = [(p, t) for p, t in all_tasks_with_pet if t.due_date == today_iso]
            render_pet_grouped_tasks(today_tasks, key_prefix="today")
            
        with tab_upcoming:
            upcoming_tasks = [(p, t) for p, t in all_tasks_with_pet if t.due_date > today_iso]
            render_pet_grouped_tasks(upcoming_tasks, key_prefix="upcoming")
            
        with tab_all:
            render_pet_grouped_tasks(all_tasks_with_pet, key_prefix="all")

        st.markdown("**Pet Special Needs**")
        for pet in owner.pets:
            needs = ", ".join(pet.special_needs) if pet.special_needs else "none"
            st.caption(f"{pet.name}: {needs}")
    else:
        st.info("No tasks yet. Add one above.")

    st.divider()
