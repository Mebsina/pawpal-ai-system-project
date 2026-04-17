import logging
import streamlit as st
from datetime import time as dtime
from datetime import date as ddate
from core import Pet, Task, Scheduler, save_data, load_data, CompletionRecord
from config import PRIORITY_ORDER

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
from ai.router import classify_and_route
from itertools import groupby
from datetime import datetime
import streamlit.components.v1 as components

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
CATEGORY_EMOJI = {
    "walk": "🦮",
    "feeding": "🍽️",
    "feed": "🍽️",
    "meds": "💊",
    "medication": "💊",
    "grooming": "✂️",
    "groom": "✂️",
    "enrichment": "🎾",
    "play": "🎮",
    "training": "🎓",
    "vet": "🏥",
    "bath": "🛁",
}
SPECIES_EMOJI = {"dog": "🐶", "cat": "🐱", "other": "🐾"}

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# --- Session state initialization ---
# Streamlit reruns the entire script on every interaction.
# Only create these objects once. After that, read from session_state.
if "owner" not in st.session_state:
    st.session_state.owner = load_data()

if "owner_editing" not in st.session_state:
    st.session_state.owner_editing = False

if "active_pet_index" not in st.session_state:
    st.session_state.active_pet_index = 0

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Hi! How can I help you and your pets today?"}]

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "active_intent" not in st.session_state:
    st.session_state.active_intent = None

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
            save_data(owner)
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

new_pet_special_needs_raw = st.text_input("Special needs (comma-separated, optional)", placeholder="e.g. diabetic, senior")

if st.button("Adding a Pet"):
    if new_pet_name.strip():
        special_needs = [s.strip() for s in new_pet_special_needs_raw.split(",") if s.strip()]
        new_pet = Pet(name=new_pet_name.strip(), species=new_pet_species, age=new_pet_age, special_needs=special_needs)
        owner.add_pet(new_pet)
        st.session_state.active_pet_index = len(owner.pets) - 1
        save_data(owner)
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
                st.warning(f"⚠ {warning}. Please adjust the time or resolve the conflict first.")
        else:
            active_pet.add_task(new_task)
            save_data(owner)
            st.success(f"'{task_title}' added at {scheduled_time}.")

    # Real-time data sanitization loop to surgically repair any corrupted saved states
    for pet in owner.pets:
        for t in pet.tasks:
            t.priority = t.priority or "medium"
            t.duration_minutes = t.duration_minutes or 15
            t.category = t.category or "walk"
            t.title = t.title or "Task"
            if len(t.scheduled_time) > 5:
                t.scheduled_time = t.scheduled_time[-5:]

    # All tasks across every pet, with a reference to which pet owns each one
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

            # Apply global sorting/priority filter
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

            # Conditional container: use fixed height for scrolling only when tasks > 5
            container_args = {"height": 400} if len(filtered) > 5 else {}
            with st.container(**container_args):
                # We group by pet to remove the Pet column and improve hierarchy
                # Sort by pet name for groupby
                filtered.sort(key=lambda pt: pt[0].name)
                for pet_name, group in groupby(filtered, key=lambda pt: pt[0].name):
                    st.markdown(f"**{SPECIES_EMOJI.get(next(iter(group))[0].species, '🐾')} {pet_name}**")
                    # Re-extract group because groupby iterator is exhausted
                    pet_tasks = [ (p,t) for p,t in filtered if p.name == pet_name ]
                    
                    header = st.columns([1.5, 1, 1.5, 1, 1, 1.2, 1, 1])
                    labels = ["Task", "Time", "Due Date", "Dur", "Pri", "Category", "Freq", "Done"]
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
                                # Undo logic
                                t.completion_status = False
                                if t.created_next_task_id:
                                    pt_pet.tasks = [task for task in pt_pet.tasks if task.id != t.created_next_task_id]
                                    t.created_next_task_id = None
                                owner.history = [r for r in owner.history if r.task_id != t.id]
                            else:
                                # Complete logic
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

if st.button("Generate Today Plan"):
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

            # Build a task-id -> pet name lookup for display
            task_pet = {t.id: pet.name for pet in owner.pets for t in pet.tasks}

            def task_row(t):
                return {
                    "Pet": task_pet.get(t.id, "-"),
                    "Task Title": t.title,
                    "Time": t.scheduled_time,
                    "Due Date": t.due_date,
                    "Duration (min)": t.duration_minutes,
                    "Priority": PRIORITY_EMOJI.get(t.priority, t.priority),
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

# ---------------------------------------------------------------------------
# AI Chat Hub Integration (Floating Action Button)
# ---------------------------------------------------------------------------

def confirm_task_cb(owner_ref, pt):
    """Background callback locking in schedule data inherently bypassing redraw chains."""
    task_preview = pt["task_preview"]
    pet = next((p for p in owner_ref.pets if p.name == pt["pet_name"]), None)
    if pet:
        pet.add_task(task_preview)
        save_data(owner_ref)
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": f"Task confirmed! I have scheduled **{task_preview.title}** for **{pet.name}** at {task_preview.scheduled_time} on {task_preview.due_date}. It will take {task_preview.duration_minutes} minutes, recurring '{task_preview.frequency}', with {task_preview.priority} priority.\n\nIs there anything else you would like to do?"
    })

def confirm_plan_cb(owner_ref, suggestions):
    """Background callback to batch-add multiple suggested tasks from the AI."""
    count = 0
    for s in suggestions:
        pet = next((p for p in owner_ref.pets if p.name == s["pet_name"]), None)
        if pet:
            # Final Defensive Check: Ensure this exact task isn't already in the database
            is_dupe = any(
                t.title.lower() == s["title"].lower() and 
                t.scheduled_time == s["scheduled_time"] and
                t.due_date == s.get("due_date", ddate.today().isoformat())
                for t in pet.tasks
            )
            
            if not is_dupe:
                new_task = Task(
                    title=s["title"],
                    duration_minutes=s["duration_minutes"],
                    priority=s["priority"],
                    category=s["category"],
                    frequency=s["frequency"],
                    scheduled_time=s["scheduled_time"],
                    due_date=s.get("due_date", ddate.today().isoformat()),
                    notes="Proactively suggested by PawPal AI"
                )
                pet.add_task(new_task)
                count += 1
    
    save_data(owner_ref)
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": f"Confirmed! I've added {count} suggested tasks to your schedule. Anything else I can help with?"
    })

def confirm_pet_add_cb(owner_ref, pt):
    """Callback to commit a new pet to the database."""
    pet_data = pt["pet_data"]
    new_pet = Pet(
        name=pet_data["name"],
        species=pet_data["species"],
        age=pet_data["age"],
        special_needs=pet_data["special_needs"]
    )
    owner_ref.add_pet(new_pet)
    save_data(owner_ref)
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": f"Welcome to the family, **{new_pet.name}**! I've successfully registered their profile. What would you like to do next?"
    })

def confirm_pet_remove_cb(owner_ref, pet_name):
    """Callback to delete a pet from the database."""
    owner_ref.pets = [p for p in owner_ref.pets if p.name != pet_name]
    save_data(owner_ref)
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": f"Got it. **{pet_name}** has been removed from your profile along with all their records. Is there anything else I can help with?"
    })

def cancel_task_cb():
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.chat_history.append({"role": "user", "content": "Nevermind, cancel that task."})
    st.session_state.chat_history.append({"role": "assistant", "content": "No problem! Task scheduling cancelled. What would you like to do instead?"})

def sel_menu_cb(opt):
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.user_prompt_override = opt

def menu_btn_cb(opt):
    st.session_state.active_intent = None
    st.session_state.pending_action = None
    st.session_state.user_prompt_override = opt

def render_quick_menu(use_full_width=True):
    """Abstracts the core quick actions into a reusable DRY rendering container."""
    st.button("📅 Check Plan", use_container_width=use_full_width, on_click=menu_btn_cb, args=("What's on my plan for today?",))
    st.button("🐾 My Pets", use_container_width=use_full_width, on_click=menu_btn_cb, args=("What pets do I have registered?",))
    st.button("➕ Add a Pet", use_container_width=use_full_width, on_click=menu_btn_cb, args=("I'd like to add a new pet",))
    st.button("➖ Remove a Pet", use_container_width=use_full_width, on_click=menu_btn_cb, args=("I need to remove a pet",))
    st.button("🦮 Schedule Task", use_container_width=use_full_width, on_click=menu_btn_cb, args=("Schedule a task for my pet",))
    st.button("🤔 What should I schedule?", use_container_width=use_full_width, on_click=menu_btn_cb, args=("What should I schedule for my pets?",))
    st.button("🔔 Check Alerts", use_container_width=use_full_width, on_click=menu_btn_cb, args=("Do I have any alerts or missed tasks?",))
    st.button("📊 Track Analytics", use_container_width=use_full_width, on_click=menu_btn_cb, args=("How have I been doing with my pets this week?",))

@st.dialog("🐾 PawPal AI Assistant", width="small")
def ai_chat_dialog():
    # Structural isolation container enforcing an internal scrollbar algorithm without breaking screen bounds
    msg_container = st.container(height=550)
    
    # 1. Grab native callback overrides bypassing visual extraction requirements logically
    user_prompt = st.session_state.pop("user_prompt_override", None)
    
    # Merge standard typing logic seamlessly
    if prompt := st.chat_input("Ask PawPal to schedule a walk, check a plan, etc."):
        user_prompt = prompt
        st.session_state.pending_action = None

    # Unified pipeline purely operating securely via top-to-bottom matrix topology
    with msg_container:
        # Step 1: Draw absolute truth of history sequentially
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        # Step 2: Draw the Quick Menu perfectly inline identically ONLY when history empty
        if len(st.session_state.chat_history) == 1 and not user_prompt:
            render_quick_menu(use_full_width=True)
                
        # Step 3: Run the Engine organically at visual generation frame
        if user_prompt:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Responding..."):
                    raw_response = classify_and_route(user_prompt, st.session_state.chat_history)
                    
                    if isinstance(raw_response, dict) and raw_response.get("type") in ["task_confirmation", "selection_menu", "show_quick_menu", "show_schedule_table", "plan_suggestion", "pet_add_confirmation", "pet_remove_confirmation"]:
                        st.session_state.pending_action = raw_response
                        response_text = raw_response["message"]
                    else:
                        st.session_state.pending_action = None
                        response_text = raw_response
                        
                st.markdown(response_text)
                
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # Step 4: Structurally attach conditional widgets EXACTLY beneath the dynamic messages natively!
        if st.session_state.pending_action:
            action = st.session_state.pending_action
            if action["type"] == "task_confirmation":
                pt = action
                
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    st.button("✅ Confirm", use_container_width=True, on_click=confirm_task_cb, args=(st.session_state.owner, pt))
                with confirm_col2:
                    st.button("❌ Cancel", use_container_width=True, on_click=cancel_task_cb)

            elif action["type"] == "plan_suggestion":
                suggestions = action["suggestions"]
                # Group by pet, sorted by time within each group
                from itertools import groupby
                sorted_suggestions = sorted(suggestions, key=lambda s: (s["pet_name"], s.get("scheduled_time", "00:00")))
                for pet_name, group in groupby(sorted_suggestions, key=lambda s: s["pet_name"]):
                    st.markdown(f"### {pet_name}")
                    for s in group:
                        dur = s.get('duration_minutes', 0)
                        st.markdown(f"`{s['scheduled_time']}` — {s['title']}  {dur}m")
                
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    st.button("✅ Confirm Plan", use_container_width=True, on_click=confirm_plan_cb, args=(st.session_state.owner, suggestions))
                with confirm_col2:
                    st.button("❌ Nevermind", use_container_width=True, on_click=cancel_task_cb)
            
            elif action["type"] == "pet_add_confirmation":
                pt = action
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    st.button("✅ Confirm", use_container_width=True, on_click=confirm_pet_add_cb, args=(st.session_state.owner, pt))
                with confirm_col2:
                    st.button("❌ Cancel", use_container_width=True, on_click=cancel_task_cb)

            elif action["type"] == "pet_remove_confirmation":
                pet_name = action["pet_name"]
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    st.button("🗑 Confirm Removal", use_container_width=True, on_click=confirm_pet_remove_cb, args=(st.session_state.owner, pet_name))
                with confirm_col2:
                    st.button("❌ Cancel", use_container_width=True, on_click=cancel_task_cb)
                
            elif action["type"] == "selection_menu":
                for opt in action["options"]:
                    st.button(opt, use_container_width=True, on_click=sel_menu_cb, args=(opt,))
            elif action["type"] == "show_quick_menu":
                render_quick_menu(use_full_width=True)
            elif action["type"] == "show_schedule_table":
                # Execute native data drawing sequentially securely mirroring the main dashboard topology
                scheduler = Scheduler(owner=owner)
                today_date = ddate.today().isoformat()
                
                all_filtered = scheduler.filter_tasks(status=False, target_date=today_date)
                schedule = scheduler.generate_plan(tasks=all_filtered)
                
                if not all_filtered:
                    st.info("Your schedule is completely clear! Is there anything you'd like to add?")
                else:
                    task_pet = {t.id: pet.name for pet in owner.pets for t in pet.tasks}
                    def task_row(t):
                        return { "Pet": task_pet.get(t.id, "-"), "Task Title": t.title, "Time": t.scheduled_time, "Duration (min)": t.duration_minutes, "Priority": PRIORITY_EMOJI.get(t.priority, t.priority) }

                    if schedule.tasks:
                        st.markdown("**Scheduled:**")
                        sorted_scheduled = scheduler.sort_by_time(schedule.tasks)
                        st.table([task_row(t) for t in sorted_scheduled])
                    if schedule.unscheduled:
                        st.error(f"{len(schedule.unscheduled)} task(s) could not fit in your {owner.available_minutes}-minute active time budget.")
                        st.table([task_row(t) for t in schedule.unscheduled])


# Append the button at the document root
if st.button("💬 Ask AI", type="secondary"):
    ai_chat_dialog()

# Reverting to components.html: because st.html() blocked Javascript execution. 
# Resolving the terminal deprecation warning causes the floating UI layout to fail.
components.html(
    """
    <div style="display:none;">
    <script>
    // Search the parent React virtual DOM for our specific Ask AI button
    const buttons = window.parent.document.querySelectorAll('button');
    buttons.forEach(b => {
        if (b.innerText.includes('Ask AI')) {
            // Apply the floating styles directly to the native element, bypassing CSS limits
            b.style.position = 'fixed';
            b.style.bottom = '30px';
            b.style.right = '30px';
            b.style.zIndex = '9999';
            b.style.backgroundColor = '#2e2e2e';
            b.style.color = 'white';
            b.style.border = '2px solid white';
            b.style.borderRadius = '30px';
            b.style.height = '60px';
            b.style.width = '150px';
            b.style.fontWeight = 'bold';
            b.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
        }
    });
    </script>
    </div>
    """,
    height=0,
    width=0
)

