import logging
import streamlit as st
from core import load_data
from config import NAV_BAR_CSS
from views.ai_analytics import render_ai_metrics
from views.owner import render_owner_info
from views.pet import render_pet_form
from views.task import render_task_manager
from views.plan import render_plan_generator
from views.ai_chat import ai_chat_dialog, render_floating_button

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.markdown(NAV_BAR_CSS, unsafe_allow_html=True)

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

# --- UI Layout Rendering & Navigation ---

def dashboard_page():
    """Main dashboard combining owner and pet management."""
    render_owner_info(st.session_state.owner)
    render_pet_form(st.session_state.owner)

def task_page():
    """Dedicated task management interface."""
    render_task_manager(st.session_state.owner)

def planner_page():
    """AI-driven schedule and plan generation."""
    render_plan_generator(st.session_state.owner)

def ai_metrics_page():
    """System diagnostics and reliability monitoring."""
    render_ai_metrics()

# Define page structure (Flattened list for a cleaner, simpler sidebar)
pg = st.navigation([
    st.Page(dashboard_page, title="Dashboard", default=True),
    st.Page(task_page, title="Tasks"),
    st.Page(planner_page, title="Planner"),
    st.Page(ai_metrics_page, title="AI Metrics")
])


# Execute the router
pg.run()

# --- Global AI Assistant (Floating Action Button) ---
if st.button("💬 Ask AI", type="secondary"):
    ai_chat_dialog(st.session_state.owner)

# Position the floating button via high-performance JS injection (Warning-free st.html)
render_floating_button()

