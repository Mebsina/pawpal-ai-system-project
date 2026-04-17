"""
test_real_ai.py
Direct integration test for the local Ollama instance and llama3.2:3b model.
Run this to verify your local environment is ready for AI features.
"""

import ollama
import json
import sys
import os

# Add project root to path so we can import ai.utils if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from ai.utils import extract_json
    from config import MODEL_NAME, OLLAMA_HOST
except ImportError:
    print("Error: Could not import project modules. Run this from the project root.")
    sys.exit(1)

def test_ollama_connection():
    print(f"--- Checking Ollama Connection ({OLLAMA_HOST}) ---")
    try:
        # Simple tags check to see if service is up
        models = ollama.list()
        print("✅ Ollama is reachable.")
        
        found = any(m['name'].startswith(MODEL_NAME) for m in models.get('models', []))
        if found:
            print(f"✅ Model '{MODEL_NAME}' is pulled and ready.")
        else:
            print(f"❌ Model '{MODEL_NAME}' not found. Run 'ollama pull {MODEL_NAME}'.")
            return False
        return True
    except Exception as e:
        print(f"❌ Ollama is unreachable: {e}")
        print("Ensure 'ollama serve' is running.")
        return False

def test_extraction_logic():
    print(f"\n--- Testing Real Extraction with {MODEL_NAME} ---")
    prompt = "Add a task for Mochi: a 30 minute walk at 2pm tomorrow."
    system_prompt = "Exract task details as JSON: title, pet_name, duration_minutes, scheduled_time, due_date. ONLY JSON."
    
    try:
        print(f"Sending prompt: '{prompt}'...")
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.0}
        )
        content = response.message.content
        print(f"Raw Output:\n{content}")
        
        data = extract_json(content)
        if data:
            print("✅ Successfully extracted JSON:")
            print(json.dumps(data, indent=2))
        else:
            print("❌ Failed to extract JSON from model output.")
            
    except Exception as e:
        print(f"❌ Extraction test failed: {e}")

if __name__ == "__main__":
    if test_ollama_connection():
        test_extraction_logic()
