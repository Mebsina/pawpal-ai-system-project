import logging
import streamlit as st
from core import load_data
from views.sidebar import render_sidebar
from views.owner import render_owner_info
from views.pet import render_pet_form
from views.task import render_task_manager
from views.plan import render_plan_generator
from views.ai_chat import ai_chat_dialog, render_floating_button

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")

# --- Session State Initialization ---
# Streamlit reruns the entire script on every user interaction.
# State initialization ensures objects and trackers are preserved across reruns.
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

# --- UI Layout Rendering ---
# The application logic is delegated to modular View components to maintain industrial standards.

# 1. Sidebar Metrics (contains ReliabilityAuditor monitoring)
render_sidebar()

# 2. Main Dashboard Sections (Owner management, Pet registration, Task Manager, and Plan Generation)
render_owner_info(owner)
render_pet_form(owner)
render_task_manager(owner)
render_plan_generator(owner)

# 3. AI Assistant Integration (Floating Dialog and Callback Hub)
if st.button("💬 Ask AI", type="secondary"):
    ai_chat_dialog(owner)

# 4. Floating Action Button Styling (Javascript Injection for UI positioning)
render_floating_button()

