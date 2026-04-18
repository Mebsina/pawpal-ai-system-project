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
STANDARD_CARE_GUIDELINES = {
    "dog": [
        "Feed twice a day (morning and evening).",
        "At least one 30-minute walk per day.",
        "Daily playtime or enrichment session."
    ],
    "cat": [
        "Feed 2-3 times a day or ensure fresh food is available.",
        "Daily play session to stimulate hunting instincts.",
        "Grooming session every 1-2 days for long-haired cats or seniors."
    ],
    "general": [
        "Check and clean water bowls daily.",
        "Complete any medication tasks strictly on schedule."
    ]
}
