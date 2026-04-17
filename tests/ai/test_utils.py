"""
test_utils.py
Validates the JSON sanitization capacities against varied LLM responses.
"""

from ai.utils import extract_json

# ---------------------------------------------------------------------------
# AI Utilities: JSON Sanitization
# Test: extract json from clean markdown
# Test: extract json from raw bracketed input
# Test: extract json fails gracefully on garbage
# ---------------------------------------------------------------------------

def test_extract_json_with_clean_markdown():
    """Ensure standard markdown blocks correctly resolve to python structures."""
    payload = "Here is the output:\n```json\n{\"time\": \"14:00\", \"pet\": \"Mochi\"}\n```\nHope this helps!"
    result = extract_json(payload)
    assert result == {"time": "14:00", "pet": "Mochi"}

def test_extract_json_with_missing_markdown():
    """Ensure raw brackets fallback functions appropriately."""
    payload = "I forgot markdown but here: {\"time\": null, \"pet\": \"Luna\"} let me know."
    result = extract_json(payload)
    assert result == {"time": None, "pet": "Luna"}

def test_extract_json_fails_gracefully():
    """Ensure random conversational garbage resolves safely to None."""
    payload = "I am not exactly sure what time you mean. Can you clarify?"
    result = extract_json(payload)
    assert result is None
