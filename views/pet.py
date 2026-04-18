import streamlit as st
from core import Pet, save_data

def render_pet_form(owner):
    """Renders the 'Add a Pet' form and handles pet registration."""
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
