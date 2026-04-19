import pytest
import json
from unittest.mock import patch, MagicMock
from ai.tools.status import status_report_tool

# ---------------------------------------------------------------------------
# Predictive Alerts Tool
# Test: healthy history ("everything on track") grounding
# Test: anomaly humanization and scheduling follow-up
# Test: Ollama service failure fallback
# Test: malformed JSON extraction failure resilience
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_persistence")
def test_predictive_alerts_healthy_path(mock_ollama, mock_owner):
    """Verifies response when no anomalies are detected."""
    # Ensure no anomalies
    mock_owner.pets[0].tasks = []
    
    with patch("ai.tools.status.load_data", return_value=mock_owner):
        result = status_report_tool("Are my pets okay?")
    
    assert "Everything looks on track" in result

@pytest.mark.usefixtures("mock_persistence")
def test_predictive_alerts_anomaly_detected(mock_ollama, mock_owner, mock_session_state):
    """Verifies LLM-humanized alert when an anomaly is found."""
    # Create an anomaly (missed task)
    from core.models import Task
    mock_owner.pets[0].tasks.append(Task(
        title="Morning Walk",
        scheduled_time="08:00",
        duration_minutes=30,
        priority="high",
        category="exercise",
        frequency="daily",
        due_date="2000-01-01" # Obviously in the past
    ))
    
    mock_response = {
        "message": "I noticed Mochi missed their morning walk today. Should we schedule a catch-up?",
        "confidence": 0.9
    }
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(mock_response))
    
    with patch("ai.tools.status.load_data", return_value=mock_owner):
        result = status_report_tool("Any alerts?")
    
    assert "Mochi missed their morning walk" in result
    assert mock_session_state.active_intent == "SUGGEST_SCHEDULE"

@pytest.mark.usefixtures("mock_persistence")
def test_predictive_alerts_ollama_failure_fallback(mock_ollama, mock_owner):
    """Verifies fallback message when LLM fails."""
    from core.models import Task
    mock_owner.pets[0].tasks.append(Task(
        title="Food",
        scheduled_time="07:00",
        duration_minutes=10,
        priority="high",
        category="feeding",
        frequency="daily",
        due_date="2000-01-01"
    ))
    
    mock_ollama.side_effect = Exception("LLM Down")
    
    with patch("ai.tools.status.load_data", return_value=mock_owner):
        result = status_report_tool("Alerts?")
    
    assert "might need your attention" in result
    assert "Mochi" in result

@pytest.mark.usefixtures("mock_persistence")
def test_predictive_alerts_extraction_failure(mock_ollama, mock_owner):
    """Ensure malformed JSON extraction returns a raw response."""
    mock_ollama.return_value = mock_ollama.response_class("Raw alerts summary.")
    from core.models import Task
    mock_owner.pets[0].tasks.append(Task(
        title="Missed Task", 
        duration_minutes=10, 
        priority="high", 
        category="feeding", 
        frequency="daily", 
        due_date="2000-01-01"
    ))
    
    with patch("ai.tools.status.load_data", return_value=mock_owner):
        result = status_report_tool("Alerts?")
    assert result == "Raw alerts summary."
