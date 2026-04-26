import streamlit as st
from core import save_data

def render_owner_info(owner):
    """Renders the owner information management section."""
    st.subheader("Owner Info")
    
    # Automatically enter editing mode if no name is set
    if not owner.name:
        st.session_state.owner_editing = True
        
    is_editing = st.session_state.owner_editing
    col1, col2, col3 = st.columns([3, 3, 1])
    
    with col1:
        # Use st.text_input with the current owner name. 
        # Modification only happens when in editing mode.
        temp_name = st.text_input("Owner name", value=owner.name, disabled=not is_editing)
        if is_editing:
            owner.name = temp_name
    
    with col2:
        temp_minutes = st.number_input(
            "Available minutes per day", min_value=1, max_value=480, value=owner.available_minutes,
            disabled=not is_editing
        )
        if is_editing:
            owner.available_minutes = temp_minutes
    
    with col3:
        st.write("")  # vertical alignment spacer
        if not is_editing:
            if st.button("Edit"):
                st.session_state.owner_editing = True
                st.rerun()
        else:
            # Only allow saving if a name has been entered
            if st.button("Save", disabled=not owner.name.strip()):
                st.session_state.owner_editing = False
                save_data(owner)
                st.rerun()

    st.divider()
