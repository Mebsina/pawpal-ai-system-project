import streamlit as st
from core import Pet, save_data, remove_pet_for_owner

def render_pet_form(owner):
    """Renders the 'Add a Pet' form and handles pet registration."""
    if "pending_dashboard_pet_removal" not in st.session_state:
        st.session_state.pending_dashboard_pet_removal = None

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
    st.subheader("Remove a Pet")
    if not owner.pets:
        st.caption("No pets registered yet.")
    else:
        pending = st.session_state.pending_dashboard_pet_removal
        if pending and not any(p.name == pending for p in owner.pets):
            st.session_state.pending_dashboard_pet_removal = None
            pending = None

        if pending:
            st.error(
                f"You are about to **permanently remove {pending}**. "
                "All of their scheduled tasks and completion history for this pet will be deleted. "
                "**This cannot be undone.**"
            )
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, remove permanently", type="primary", key="dashboard_remove_yes"):
                    if remove_pet_for_owner(owner, pending):
                        save_data(owner)
                        n = len(owner.pets)
                        if n == 0:
                            st.session_state.active_pet_index = 0
                        else:
                            st.session_state.active_pet_index = min(
                                st.session_state.active_pet_index, n - 1
                            )
                        st.session_state.pending_dashboard_pet_removal = None
                        st.success(f"{pending} has been removed.")
                        st.rerun()
                    else:
                        st.session_state.pending_dashboard_pet_removal = None
                        st.warning("Could not remove that pet.")
            with col_no:
                if st.button("Cancel", key="dashboard_remove_cancel"):
                    st.session_state.pending_dashboard_pet_removal = None
                    st.rerun()
        else:
            st.caption(
                "Choose a pet, then click Remove. Nothing is deleted until you confirm on the next step."
            )
            remove_name = st.selectbox(
                "Pet to remove",
                options=[p.name for p in owner.pets],
                key="dashboard_remove_pet_select",
            )
            if st.button("Remove", type="primary", key="dashboard_remove_review"):
                st.session_state.pending_dashboard_pet_removal = remove_name
                st.rerun()
