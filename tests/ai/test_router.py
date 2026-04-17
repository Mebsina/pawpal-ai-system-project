"""
test_router.py
Verifies the intent classification and routing logic of the AI service layer.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from ai.router import classify_and_route

# ---------------------------------------------------------------------------
# AI Intent Routing
# Test: escape keywords (cancel, stop, etc.) release intent locks
# Test: active intent locks bypass classification
# Test: valid classification routes to specific tools
# Test: unknown inputs use conversational fallback
# Test: Ollama service unavailable graceful degradation
# Test: full intent routing matrix (ADD_PET, REMOVE_PET, etc.)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("keyword", ["cancel", "stop", "nevermind", "start over"])
def test_router_escape_keywords_parametrized(mock_session_state, keyword):
    """Ensure all escape keywords release intent locks immediately."""
    mock_session_state.active_intent = "ADD_TASK"
    classify_and_route(keyword)
    assert mock_session_state.active_intent is None

def test_router_ollama_unavailable_graceful_degradation(mock_session_state, mock_ollama):
    """Ensure system falls back to general chat if Ollama classification fails."""
    mock_session_state.active_intent = None
    mock_ollama.side_effect = Exception("Ollama connection failed")
    
    # It should not crash, but return a conversational fallback
    result = classify_and_route("help me")
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.parametrize("intent,tool_path,expected_lock", [
    ("ADD_PET", "ai.router.add_pet_tool", "ADD_PET"),
    ("REMOVE_PET", "ai.router.remove_pet_tool", "REMOVE_PET"),
    ("LIST_PETS", "ai.router.list_pets_tool", None),
    ("PET_INSIGHTS", "ai.router.get_insights_tool", None),
    ("SUGGEST_SCHEDULE", "ai.router.suggest_schedule_tool", None),
    ("CHECK_ALERTS", "ai.router.predictive_alerts_tool", None),
    ("CHECK_SCHEDULE", "ai.router.check_schedule_tool", None),
])
def test_router_full_intent_matrix(mock_session_state, mock_ollama, intent, tool_path, expected_lock):
    """Verify routing for all supported intents."""
    mock_session_state.active_intent = None
    mock_ollama.return_value = mock_ollama.response_class(json.dumps({"intent": intent, "confidence": 0.99}))
    
    with patch(tool_path, return_value="Routed") as mock_tool:
        result = classify_and_route("test input")
        assert mock_session_state.active_intent == expected_lock
        assert result == "Routed"

def test_router_locked_intent_bypass(mock_session_state, mock_ollama):
    """Prove that an active intent lock bypasses LLM classification entirely."""
    mock_session_state.active_intent = "ADD_TASK"
    
    with patch("ai.router.add_task_tool", return_value="Bypassed") as mock_tool:
        result = classify_and_route("any input")
        assert result == "Bypassed"
        assert mock_ollama.call_count == 0

def test_router_conversational_fallback(mock_session_state, mock_ollama):
    """Verify that unknown intents route to GENERAL_CHAT / conversational bypass."""
    mock_session_state.active_intent = None
    mock_ollama.return_value = mock_ollama.response_class(json.dumps({"intent": "WHOT_IS_THIS", "confidence": 0.1}))
    
    with patch("ai.router.conversational_bypass", return_value="Chatted") as mock_bypass:
        result = classify_and_route("hello")
        assert result == "Chatted"

def test_router_confidence_score_logged(mock_session_state, mock_ollama):
    """Ensure classification confidence is captured in the logger."""
    mock_session_state.active_intent = None
    mock_ollama.return_value = mock_ollama.response_class(json.dumps({"intent": "LIST_PETS", "confidence": 0.85}))
    
    with patch("ai.router.logger.info") as mock_log:
        classify_and_route("list my pets")
        # Find the log call that mentions confidence
        log_msgs = [call.args[0] for call in mock_log.call_args_list]
        assert any("Confidence: 0.85" in msg for msg in log_msgs)

def test_router_malformed_json_falls_back_to_chat(mock_session_state, mock_ollama):
    """Garbage LLM output must degrade to GENERAL_CHAT, not crash."""
    mock_session_state.active_intent = None
    mock_ollama.return_value = mock_ollama.response_class("This is not JSON")
    
    with patch("ai.router.conversational_bypass", return_value="Graceful Fallback") as mock_bypass:
        result = classify_and_route("what is this")
        assert result == "Graceful Fallback"

def test_router_with_chat_history(mock_session_state, mock_ollama):
    """Ensure chat history is correctly passed to the extraction module."""
    mock_session_state.active_intent = None
    chat_history = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    mock_ollama.return_value = mock_ollama.response_class(json.dumps({"intent": "GENERAL_CHAT", "confidence": 0.9}))
    
    classify_and_route("latest message", chat_history=chat_history)
    
    # Verify that ollama.chat was called with messages including chat_history
    called_messages = mock_ollama.call_args.kwargs["messages"]
    assert any(m["content"] == "hello" for m in called_messages)
    assert any(m["content"] == "hi" for m in called_messages)

def test_router_restricted_keywords_filter(mock_session_state, mock_ollama):
    """Verify that restricted keywords trigger a guardrail warning in logs."""
    mock_session_state.active_intent = None
    # Response contains 'veterinarian' which is restricted
    mock_ollama.return_value = mock_ollama.response_class(json.dumps({"intent": "GENERAL_CHAT", "confidence": 0.9, "extra": "Go to a veterinarian"}))
    
    with patch("ai.router.check_restricted_keywords") as mock_check:
        classify_and_route("give me advice")
        assert mock_check.called

def test_conversational_bypass_with_history(mock_ollama):
    """Ensure conversational fallback respects chat history."""
    from ai.router import conversational_bypass
    chat_history = [{"role": "user", "content": "I love dogs"}]
    mock_ollama.return_value = mock_ollama.response_class("Me too!")
    
    result = conversational_bypass("And cats?", chat_history=chat_history)
    
    assert result == "Me too!"
    called_messages = mock_ollama.call_args.kwargs["messages"]
    assert any(m["content"] == "I love dogs" for m in called_messages)

def test_conversational_bypass_failure(mock_ollama):
    """Ensure conversational fallback handles API failures gracefully."""
    from ai.router import conversational_bypass
    mock_ollama.side_effect = Exception("API Down")
    
    result = conversational_bypass("hello")
    assert "trouble maintaining conversation" in result
