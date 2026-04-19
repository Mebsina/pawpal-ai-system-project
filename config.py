"""
config.py
Centralized configuration settings for the PawPal+ AI system.
"""

import os

# --- LLM Configuration ---
# The exact local model name used for Ollama requests.
MODEL_NAME = "llama3.2:3b"

# Base URL for the local Ollama instance.
# Defaults to localhost standard port for offline deployment.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# --- Model Hyperparameters ---
# STRICT_TEMPERATURE forces the model to act deterministically.
# Used exclusively for intent routing (router.py) and data extraction (tools.py)
# to minimize hallucinations and enforce valid JSON structure.
STRICT_TEMPERATURE = 0.0

# CHAT_TEMPERATURE permits conversational creativity.
# Used for generating natural language follow-up prompts and RAG assistant feedback.
CHAT_TEMPERATURE = 0.7

# --- Application Constants ---
# Path pointing to the persistent JSON datastore.
DATA_FILE = "data/pawpal_data.json"

# Numeric weight assigned to task priorities for sorting algorithms.
PRIORITY_ORDER: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}

# --- UI Constants ---
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

# --- Pet Care Guidelines ---
# Standard industry baselines used by the AI when suggesting plans.
# Structured for both AI prompting and automated validation.
STANDARD_CARE_GUIDELINES: dict[str, list[dict]] = {
    "dog": [
        {"type": "feeding", "min_count": 2, "label": "Feed twice a day (morning and evening)."},
        {"type": "walk", "min_count": 1, "label": "At least one 30-minute walk per day."},
        {"type": "play", "min_count": 1, "label": "Daily playtime or enrichment session."}
    ],
    "cat": [
        {"type": "feeding", "min_count": 2, "label": "Feed 2-3 times a day or ensure fresh food is available."},
        {"type": "play", "min_count": 1, "label": "Daily play session to stimulate hunting instincts."},
        {"type": "grooming", "min_count": 0.5, "label": "Grooming session every 1-2 days for long-haired cats or seniors."}
    ],
    "general": [
        {"type": "utility", "min_count": 1, "label": "Check and clean water bowls daily."},
        {"type": "meds", "min_count": 0, "label": "Complete any medication tasks strictly on schedule."}
    ]
}

# --- UI Styling ---
# Custom CSS for Streamlit navigation items
# targets [data-testid="stSidebarNav"] to increase font size in the sidebar
NAV_BAR_CSS = """
<style>
    [data-testid="stSidebarNav"] div[role="button"] p {
        font-size: 1.15rem !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebarNav"] span {
        font-size: 1.1rem !important;
    }
</style>
"""
