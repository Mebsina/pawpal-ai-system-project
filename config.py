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
