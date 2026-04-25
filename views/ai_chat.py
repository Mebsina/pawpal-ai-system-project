import streamlit as st
import streamlit.components.v1 as components
from datetime import date as ddate
from core import Task, Pet, Scheduler, save_data, remove_pet_for_owner
from ai.router import classify_and_route
from config import PRIORITY_EMOJI

def _complete_chat_action(message: str, role: str = "assistant"):
    """Internal helper to reset action state and update history."""
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.chat_history.append({"role": role, "content": message})

def _set_prompt_cb(opt: str):
    """Callback to inject a user prompt into the chat sequence."""
    st.session_state.pending_action = None
    st.session_state.active_intent = None
    st.session_state.user_prompt_override = opt

def _render_action_buttons(label_confirm: str, callback_confirm, args_confirm, label_cancel: str = "❌ Cancel"):
    """Standardizes the dual-column action button layout."""
    col1, col2 = st.columns(2)
    with col1:
        st.button(label_confirm, use_container_width=True, on_click=callback_confirm, args=args_confirm)
    with col2:
        st.button(label_cancel, use_container_width=True, on_click=cancel_task_cb)

def confirm_task_cb(owner_ref, pt):
    """Background callback locking in schedule data."""
    task_preview = pt["task_preview"]
    pet = owner_ref.get_pet_by_name(pt["pet_name"])
    if pet:
        pet.add_task(task_preview)
        save_data(owner_ref)
    
    msg = f"Task confirmed! I have scheduled **{task_preview.title}** for **{pet.name}** at {task_preview.scheduled_time} on {task_preview.due_date}. It will take {task_preview.duration_minutes} minutes, recurring '{task_preview.frequency}', with {task_preview.priority} priority.\n\nIs there anything else you would like to do?"
    _complete_chat_action(msg)

def confirm_plan_cb(owner_ref, suggestions):
    """Background callback to batch-add multiple suggested tasks."""
    count = 0
    for s in suggestions:
        pet = owner_ref.get_pet_by_name(s["pet_name"])
        if pet:
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
    _complete_chat_action(f"Confirmed! I've added {count} suggested tasks to your schedule. Anything else I can help with?")

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
    _complete_chat_action(f"Welcome to the family, **{new_pet.name}**! I've successfully registered their profile. What would you like to do next?")

def confirm_pet_remove_cb(owner_ref, pet_name):
    """Callback to delete a pet from the database."""
    if not remove_pet_for_owner(owner_ref, pet_name):
        _complete_chat_action(
            f"I couldn't find a pet named **{pet_name}** in your profile. Nothing was changed."
        )
        return
    save_data(owner_ref)
    n = len(owner_ref.pets)
    if n == 0:
        st.session_state.active_pet_index = 0
    else:
        st.session_state.active_pet_index = min(st.session_state.active_pet_index, n - 1)
    _complete_chat_action(
        f"Got it. **{pet_name}** has been removed from your profile along with all their records. "
        "Is there anything else I can help with?"
    )

def cancel_task_cb():
    """Callback to abort a pending action."""
    st.session_state.chat_history.append({"role": "user", "content": "Nevermind, cancel that."})
    _complete_chat_action("No problem! Action cancelled. What would you like to do instead?")

def render_pet_management_menu(use_full_width=True):
    """Specific menu for adding or removing pets."""
    st.button("Add a Pet", use_container_width=use_full_width, on_click=_set_prompt_cb, args=("I'd like to add a new pet",))
    st.button("Remove a Pet", use_container_width=use_full_width, on_click=_set_prompt_cb, args=("I need to remove a pet",))

def render_quick_menu(use_full_width=True):
    """Abstracts the core quick actions into a reusable container."""
    st.button("My Pets", use_container_width=use_full_width, on_click=_set_prompt_cb, args=("What pets do I have registered?",))
    st.button("Check Plan", use_container_width=use_full_width, on_click=_set_prompt_cb, args=("What's on my plan for today?",))

    st.button("Schedule Task", use_container_width=use_full_width, on_click=_set_prompt_cb, args=("Schedule a task for my pet",))
    st.button("What should I schedule?", use_container_width=use_full_width, on_click=_set_prompt_cb, args=("What should I schedule for my pets?",))
    st.button("Check Status", use_container_width=use_full_width, on_click=_set_prompt_cb, args=("How am I doing with my pets this week?",))

@st.dialog("🐾 PawPal AI Assistant", width="small")
def ai_chat_dialog(owner):
    """The main AI conversational interface dialog."""
    msg_container = st.container(height=550)
    user_prompt = st.session_state.pop("user_prompt_override", None)
    
    if prompt := st.chat_input("Ask PawPal to schedule a walk, check a plan, etc."):
        user_prompt = prompt
        st.session_state.pending_action = None

    with msg_container:
        # Step 1: Render existing conversation history sequentially to maintain context
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        # Step 2 & 3 & 4 logic handles interactive elements and new messages.
        # We process prompts first to update history, then render everything in order.
                
        # Step 3: Execute the AI Engine at the visual generation frame when a prompt is present
        if user_prompt:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Responding..."):
                    # The engine determines intent and may return a structured payload for confirmation
                    raw_response = classify_and_route(user_prompt, st.session_state.chat_history)
                    
                    if isinstance(raw_response, dict) and raw_response.get("type") in ["task_confirmation", "selection_menu", "show_quick_menu", "show_schedule_table", "plan_suggestion", "pet_add_confirmation", "pet_remove_confirmation", "pet_management_menu"]:
                        st.session_state.pending_action = raw_response
                        response_text = raw_response["message"]
                    else:
                        st.session_state.pending_action = None
                        response_text = raw_response
                        
                st.markdown(response_text)
                
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # --- Interactive Section (Bottom of Container) ---
        # Define placeholder here so it always appears below the chat history.
        action_area = st.empty()

        # Step 2: Display the Quick Menu inline only when the history is at its initial state
        if len(st.session_state.chat_history) == 1 and not user_prompt:
            with action_area.container():
                render_quick_menu(use_full_width=True)

        # Step 4: Structurally attach conditional widgets beneath the dynamic messages
        if st.session_state.pending_action:
            action = st.session_state.pending_action
            with action_area.container():
                if action["type"] == "task_confirmation":
                    _render_action_buttons("✅ Confirm", confirm_task_cb, (owner, action))

                elif action["type"] == "plan_suggestion":
                    suggestions = action["suggestions"]
                    # Group by pet, then sort by time within each group for readability
                    from itertools import groupby
                    sorted_suggestions = sorted(suggestions, key=lambda s: (s["pet_name"], s.get("scheduled_time", "00:00")))
                    for pet_name, group in groupby(sorted_suggestions, key=lambda s: s["pet_name"]):
                        st.markdown(f"### {pet_name}")
                        for s in group:
                            dur = s.get('duration_minutes', 0)
                            st.markdown(f"`{s['scheduled_time']}` - {s['title']}  {dur}m")
                    
                    if suggestions:
                        _render_action_buttons("✅ Confirm Plan", confirm_plan_cb, (owner, suggestions), label_cancel="❌ Nevermind")
                
                elif action["type"] == "pet_add_confirmation":
                    _render_action_buttons("✅ Confirm", confirm_pet_add_cb, (owner, action))

                elif action["type"] == "pet_remove_confirmation":
                    _render_action_buttons("🗑 Confirm Removal", confirm_pet_remove_cb, (owner, action["pet_name"]))
                    
                elif action["type"] == "selection_menu":
                    for opt in action["options"]:
                        st.button(opt, use_container_width=True, on_click=_set_prompt_cb, args=(opt,))
                elif action["type"] == "pet_management_menu":
                    render_pet_management_menu(use_full_width=True)
                elif action["type"] == "show_quick_menu":
                    render_quick_menu(use_full_width=True)
                elif action["type"] == "show_schedule_table":
                    # Mirror the main dashboard topology for data consistency
                    scheduler = Scheduler(owner=owner)
                    today_date = ddate.today().isoformat()
                    all_filtered = scheduler.filter_tasks(status=False, target_date=today_date)
                    schedule = scheduler.generate_plan(tasks=all_filtered)
                    
                    if not all_filtered:
                        st.info("Your schedule is completely clear! Is there anything you'd like to add?")
                    else:
                        task_pet = {t.id: pet.name for pet in owner.pets for t in pet.tasks}
                        def task_row(t):
                            return { "Pet": task_pet.get(t.id, "-"), "Task Title": t.title, "Time": t.scheduled_time, "Duration (min)": t.duration_minutes, "Priority": PRIORITY_EMOJI.get(t.priority.lower(), t.priority) }

                        if schedule.tasks:
                            st.markdown("**Scheduled:**")
                            sorted_scheduled = scheduler.sort_by_time(schedule.tasks)
                            st.table([task_row(t) for t in sorted_scheduled])
                        if schedule.unscheduled:
                            st.error(f"{len(schedule.unscheduled)} task(s) could not fit in your {owner.available_minutes}-minute active time budget.")
                            st.table([task_row(t) for t in schedule.unscheduled])

def render_floating_button():
    """Injects Javascript to style the 'Ask AI' button as a floating action button."""
    components.html(
        """
        <script>
        function styleFloatingButton() {
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(b => {
                if (b.innerText.indexOf('Ask AI') !== -1) {
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
        }
        
        // Initial run
        styleFloatingButton();
        
        // Continuous check to handle Streamlit re-renders
        setInterval(styleFloatingButton, 500);
        </script>
        """,
        height=0,
        width=0
    )
