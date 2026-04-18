import streamlit as st
from core import save_data

def render_owner_info(owner):
    """Renders the owner information management section."""
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
