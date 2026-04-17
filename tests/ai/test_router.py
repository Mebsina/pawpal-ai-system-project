"""
test_router.py
Verifies the intent classification and routing logic of the AI service layer.
"""

import pytest
from unittest.mock import patch, MagicMock
from ai.router import classify_and_route

# ---------------------------------------------------------------------------
# AI Intent Routing
# Test: escape keywords release intent locks
# Test: active intent locks bypass classification
# Test: valid classification routes to specific tools
# Test: unknown inputs use conversational fallback
# ---------------------------------------------------------------------------

def test_router_escape_keywords(mock_session_state):
    """Ensure escape keywords release intent locks immediately."""
    # Use the session_state mock to set active_intent
    mock_session_state.active_intent = "ADD_TASK"
    
    # Trigger escape via keywords defined in router.py
    # Note: 'cancel' clears the intent but then proceeds to conversational fallback
    result = classify_and_route("cancel")
    
    assert mock_session_state.active_intent is None
    assert isinstance(result, str)
    assert "cancel" in result.lower() or "sorry" in result.lower()

def test_router_locked_intent_bypass(mock_session_state, mock_ollama):
    """Ensure active intent locks bypass classification logic."""
    mock_session_state.active_intent = "ADD_TASK"
    
    # We patch the tool to avoid real execution
    with patch("ai.router.add_task_tool", return_value="Tool Called") as mock_tool:
        result = classify_and_route("just some input")
        
        # Verify Ollama was NOT called because logic was locked
        mock_ollama.assert_not_called()
        mock_tool.assert_called_once()
        assert result == "Tool Called"

def test_router_classification_routing(mock_session_state, mock_ollama):
    """Ensure Ollama classification correctly routes to specific tools."""
    mock_session_state.active_intent = None
    mock_ollama.return_value = mock_ollama.response_class("ADD_TASK")
    
    with patch("ai.router.add_task_tool", return_value="Routed") as mock_tool:
        result = classify_and_route("i want to walk my dog")
        
        assert mock_session_state.active_intent == "ADD_TASK"
        assert result == "Routed"

def test_router_conversational_fallback(mock_session_state, mock_ollama):
    """Ensure unrecognized intents fall back to conversational bypass."""
    mock_session_state.active_intent = None
    mock_ollama.side_effect = [
        mock_ollama.response_class("GENERAL_CHAT"),
        mock_ollama.response_class("Hello there!")
    ]
    
    result = classify_and_route("hi")
    assert result == "Hello there!"
