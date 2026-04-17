import pytest
import json
from unittest.mock import patch, MagicMock
from ai.tools.get_insights import get_insights_tool

# ---------------------------------------------------------------------------
# Analytical Insights Tool
# Test: structured analytical summary extraction
# Test: empty history state handling
# Test: chat history context passing
# Test: Ollama service failure fallback
# Test: malformed JSON extraction failure resilience
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_persistence")
def test_get_insights_happy_path(mock_ollama, mock_owner):
    """Verifies analytical insights generation with valid historical data."""
    # Add history
    from core.models import CompletionRecord
    from datetime import datetime, timedelta
    mock_owner.history.append(CompletionRecord(
        task_id="123",
        pet_name="Mochi",
        task_title="Walk",
        category="exercise",
        timestamp=(datetime.now() - timedelta(hours=2)).isoformat()
    ))
    
    mock_response = {
        "message": "Mochi has been very active today! Good job.",
        "confidence": 0.95
    }
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(mock_response))
    
    with patch("ai.tools.get_insights.load_data", return_value=mock_owner):
        result = get_insights_tool("How is Mochi doing?")
    
    assert "Mochi has been very active" in result

@pytest.mark.usefixtures("mock_persistence")
def test_get_insights_empty_history(mock_owner):
    """Verifies friendly message when no history exists."""
    mock_owner.history = []
    
    with patch("ai.tools.get_insights.load_data", return_value=mock_owner):
        result = get_insights_tool("Show my insights")
    
    assert "haven't recorded any completed tasks" in result

@pytest.mark.usefixtures("mock_persistence")
def test_get_insights_context_passing(mock_ollama, mock_owner):
    """Verifies that chat history is passed to the LLM."""
    mock_ollama.return_value = mock_ollama.response_class(json.dumps({"message": "OK", "confidence": 1.0}))
    
    # Add history so it doesn't short-circuit to empty state
    from core.models import CompletionRecord
    mock_owner.history.append(CompletionRecord("1", "Mochi", "X", "Y", "2026-04-17T08:00:00"))
    
    chat_history = [{"role": "user", "content": "Previous question"}]
    
    with patch("ai.tools.get_insights.load_data", return_value=mock_owner):
        get_insights_tool("Current question", chat_history=chat_history)
    
    called_messages = mock_ollama.call_args[1]["messages"]
    assert len(called_messages) == 3
    assert called_messages[1]["content"] == "Previous question"
    assert called_messages[2]["content"] == "Current question"

def test_get_insights_ollama_failure(mock_ollama, mock_owner):
    """Ensure API failures return a stable fallback message."""
    mock_ollama.side_effect = Exception("Ollama disconnected")
    # Add history so it doesn't return early
    from core.models import CompletionRecord
    mock_owner.history.append(CompletionRecord("1", "Mochi", "X", "Y", "2026-04-17T08:00:00"))
    
    with patch("ai.tools.get_insights.load_data", return_value=mock_owner):
        result = get_insights_tool("Show insights")
    assert "having trouble summarizing" in result

def test_get_insights_extraction_failure(mock_ollama, mock_owner):
    """Ensure malformed JSON extraction returns a raw response."""
    mock_ollama.return_value = mock_ollama.response_class("Raw conversational response")
    from core.models import CompletionRecord
    mock_owner.history.append(CompletionRecord("1", "Mochi", "X", "Y", "2026-04-17T08:00:00"))
    
    with patch("ai.tools.get_insights.load_data", return_value=mock_owner):
        result = get_insights_tool("Show insights")
    assert result == "Raw conversational response"
