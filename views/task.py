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
            t.priority = t.priority or "medium"
            t.duration_minutes = t.duration_minutes or 15
            t.category = t.category or "walk"
            t.title = t.title or "Task"
            if len(t.scheduled_time) > 5:
                t.scheduled_time = t.scheduled_time[-5:]

    # Capture all active tasks across every pet for unified dashboard indexing
    all_tasks_with_pet = [(pet, t) for pet in owner.pets for t in pet.tasks]

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
            st.write("") # spacer
            hide_completed = st.checkbox("Hide Done", value=False)

        tab_today, tab_upcoming, tab_all = st.tabs(["📅 Today", "🔜 Upcoming", "📜 All Tasks"])
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
                filtered = sorted(filtered, key=lambda pt: -PRIORITY_ORDER[pt[1].priority])
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
                    
                    header = st.columns([1.5, 1, 1.5, 1, 1, 1.2, 1, 1])
                    labels = ["Task", "Time", "Due Date", "Duration", "Priority", "Category", "Frequency", "Done"]
                    for col, label in zip(header, labels):
                        col.caption(f"**{label}**")
                    
                    for pt_pet, t in pet_tasks:
                        row = st.columns([1.5, 1, 1.5, 1, 1, 1.2, 1, 1])
                        row[0].write(("~~" + t.title + "~~") if t.completion_status else t.title)
                        row[1].write(t.scheduled_time)
                        row[2].write(t.due_date)
                        row[3].write(f"{t.duration_minutes}m")
                        row[4].write(PRIORITY_EMOJI.get(t.priority, t.priority))
                        cat_label = f"{CATEGORY_EMOJI.get(t.category.lower(), '')} {t.category}".strip()
                        row[5].write(cat_label)
                        row[6].write(t.frequency)
                        
                        btn_label = "No" if t.completion_status else "Yes"
                        btn_type = "primary" if t.completion_status else "secondary"
                        if row[7].button(btn_label, type=btn_type, key=f"{key_prefix}_btn_{t.id}", use_container_width=True):
                            if t.completion_status:
                                t.completion_status = False
                                if t.created_next_task_id:
                                    pt_pet.tasks = [task for task in pt_pet.tasks if task.id != t.created_next_task_id]
                                    t.created_next_task_id = None
                                owner.history = [r for r in owner.history if r.task_id != t.id]
                            else:
                                record = CompletionRecord(
                                    task_id=t.id,
                                    pet_name=pt_pet.name,
                                    task_title=t.title,
                                    category=t.category,
                                    timestamp=f"{t.due_date}T{t.scheduled_time}"
                                )
                                owner.history.append(record)
                                Scheduler(owner=owner).reschedule_if_recurring(task=t, pet=pt_pet)
                            
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
