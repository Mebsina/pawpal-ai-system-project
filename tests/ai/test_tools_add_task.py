"""
test_tools_add_task.py
Verifies the add_task_tool, covering extraction logic, fallback prompts, and exception paths.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from ai.tools.add_task import add_task_tool
from core.models import Task, Pet, Owner

# ---------------------------------------------------------------------------
# Add Task Tool
# Test: valid AI extraction results in a task confirmation
# Test: missing pet name triggers a selection menu when multiple pets exist
# Test: detected schedule overlaps trigger a warning instead of confirmation
# Test: zero registered pets halts workflow natively
# Test: preserving deep history for accumulated context state
# Test: local AI extraction connection failure fallback
# Test: JSON structural validation failure handles error
# Test: missing task title defaults gracefully to extracted category
# Test: single pet profiles automatically assign pet
# Test: missing general activity title naturally asks user for details
# Test: missing exact time dynamically prompts user
# Test: mismatched pet names report as unregistered
# Test: poorly formatted times are sliced correctly
# Test: explicit failure catching for core dataclass Task creation
# ---------------------------------------------------------------------------

def test_add_task_tool_success(mock_persistence, mock_ollama, mock_owner):
    """Ensure valid AI extraction results in a task confirmation."""
    json_output = '```json\n{"title": "Walk", "pet_name": "Mochi", "duration_minutes": 30, "scheduled_time": "14:00", "due_date": "2026-04-17", "confidence": 0.95}\n```'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.datetime") as mock_dt, \
         patch("ai.tools.add_task.load_data", return_value=mock_owner):
        mock_dt.now.return_value = datetime(2026, 4, 17, 12, 0)
        
        result = add_task_tool("walk Mochi at 2pm")
        
        assert isinstance(result, dict)
        assert result["type"] == "task_confirmation"
        assert result["pet_name"] == "Mochi"
        assert result["task_preview"].title == "Walk"
        assert result["task_preview"].scheduled_time == "14:00"

def test_add_task_tool_missing_pet_multiple_pets(mock_persistence, mock_ollama, mock_owner):
    """Ensure missing pet name triggers a selection menu when multiple pets exist."""
    json_output = '{"title": "Feed", "pet_name": null, "scheduled_time": "08:00", "confidence": 0.85}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    mock_owner.pets.append(Pet(name="Luna", species="Cat", age=2))
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Feed the pet at 8am")
    
    assert isinstance(result, dict)
    assert result["type"] == "selection_menu"
    assert "Which pet" in result["message"]

def test_add_task_tool_conflict(mock_persistence, mock_ollama, mock_owner):
    """Ensure detected schedule overlaps trigger a warning instead of confirmation."""
    json_output = '{"title": "Play", "pet_name": "Mochi", "duration_minutes": 60, "scheduled_time": "14:00", "confidence": 0.9}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    mock_owner.pets[0].tasks.append(Task(
        title="Existing Walk", 
        scheduled_time="14:00", 
        duration_minutes=30,
        due_date="2026-04-17",
        priority="medium",
        category="walk",
        frequency="once"
    ))
    
    with patch("ai.tools.add_task.datetime") as mock_dt, \
         patch("ai.tools.add_task.load_data", return_value=mock_owner):
        mock_dt.now.return_value = datetime(2026, 4, 17, 12, 0)
        result = add_task_tool("Play with Mochi at 2pm")
        
        assert isinstance(result, str)
        assert "can't lock that in" in result
        assert "Existing Walk" in result

# --- New specific coverage tests ---

def test_add_task_tool_zero_registered_pets(mock_persistence):
    """Line 20: Test behavior when an owner has zero registered pets."""
    owner_no_pets = Owner(name="Test", pets=[], available_minutes=120)
    with patch("ai.tools.add_task.load_data", return_value=owner_no_pets):
        result = add_task_tool("Feed Mochi at 2pm")
        assert "no pets are registered" in result

def test_add_task_tool_chat_history(mock_persistence, mock_ollama, mock_owner):
    """Line 58: Test providing conversational context via chat_history."""
    json_output = '{"title": "Run", "pet_name": "Mochi", "scheduled_time": "15:00", "confidence": 0.9}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    chat_history = [{"role": "user", "content": "I want to add a task"}] * 10
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Run at 3pm", chat_history=chat_history)
        assert isinstance(result, dict)
        assert result["type"] == "task_confirmation"

def test_add_task_tool_model_exception(mock_persistence, mock_owner):
    """Lines 68-70: Test catching a generic Exception thrown by ollama.chat."""
    with patch("ai.tools.add_task.load_data", return_value=mock_owner), \
         patch("ai.tools.add_task.ollama.chat", side_effect=Exception("API Error")):
        result = add_task_tool("Feed Mochi")
        assert "having trouble connecting" in result

def test_add_task_tool_invalid_schema(mock_persistence, mock_ollama, mock_owner):
    """Lines 77-78: Test validate_schema failing with an extraction output missing required fields."""
    json_output = '{"pet_name": "Mochi"}' # Missing confidence, title, scheduled_time
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Feed Mochi")
        assert "natural language extractor failed" in result

def test_add_task_tool_fallback_title(mock_persistence, mock_ollama, mock_owner):
    """Line 90: Test missing title but having a valid category extracted."""
    json_output = '{"title": "", "category": "Grooming", "pet_name": "Mochi", "scheduled_time": "10:00", "confidence": 0.8}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Brush Mochi at 10am")
        assert isinstance(result, dict)
        assert result["task_preview"].title == "Grooming"

def test_add_task_tool_auto_select_pet(mock_persistence, mock_ollama, mock_owner):
    """Line 94: Test missing pet_name when exactly one pet exists."""
    json_output = '{"title": "Walk", "pet_name": null, "scheduled_time": "10:00", "confidence": 0.9}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    # mock_owner already has exactly 1 pet named Mochi
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Walk at 10am")
        assert isinstance(result, dict)
        assert result["pet_name"] == "Mochi"

def test_add_task_tool_missing_title(mock_persistence, mock_ollama, mock_owner):
    """Line 104: Test missing title asks user for activity."""
    json_output = '{"title": "null", "pet_name": "Mochi", "scheduled_time": "10:00", "confidence": 0.8}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Schedule something for Mochi at 10am")
        assert isinstance(result, str)
        assert "What specific activity or task" in result

def test_add_task_tool_missing_time(mock_persistence, mock_ollama, mock_owner):
    """Lines 107-109: Test missing scheduled_time to trigger a user follow-up prompt."""
    json_output = '{"title": "Walk", "pet_name": "Mochi", "scheduled_time": "", "confidence": 0.9}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Walk Mochi")
        assert isinstance(result, str)
        assert "What specific time should the schedule reflect?" in result

def test_add_task_tool_unregistered_pet(mock_persistence, mock_ollama, mock_owner):
    """Line 115: Test matching a pet_name not in the system."""
    json_output = '{"title": "Walk", "pet_name": "Bruno", "scheduled_time": "10:00", "confidence": 0.9}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Walk Bruno at 10am")
        assert isinstance(result, dict)
        assert result["type"] == "selection_menu"

def test_add_task_tool_time_format_slice(mock_persistence, mock_ollama, mock_owner):
    """Line 119: Test scheduled_time parsed improperly and sliced to 5 characters."""
    json_output = '{"title": "Walk", "pet_name": "Mochi", "scheduled_time": "0014:00", "confidence": 0.9}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner):
        result = add_task_tool("Walk Mochi at 2pm")
        assert isinstance(result, dict)
        assert result["task_preview"].scheduled_time == "14:00"

def test_add_task_tool_task_error(mock_persistence, mock_ollama, mock_owner):
    """Lines 153-155: Test a deliberate fault during Task generation."""
    json_output = '{"title": "Walk", "pet_name": "Mochi", "scheduled_time": "14:00", "confidence": 0.9}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_task.load_data", return_value=mock_owner), \
         patch("ai.tools.add_task.Task", side_effect=Exception("Task Error")):
        result = add_task_tool("Walk Mochi at 2pm")
        assert isinstance(result, str)
        assert "error processing the task details" in result

