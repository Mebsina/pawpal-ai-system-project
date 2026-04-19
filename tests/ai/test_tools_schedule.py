"""
test_tools_task.py
Verifies the task scheduling AI tools, extraction logic, and conflict detection.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from ai.tools.add_task import add_task_tool
from ai.tools.schedule import schedule_tool
from core.models import Task

# ---------------------------------------------------------------------------
# AI Task Tools
# Test: add task tool success extraction
# Test: add task tool missing pet selection
# Test: add task tool schedule conflict detection
# Test: check schedule tool summary table
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

def test_add_task_tool_missing_pet(mock_persistence, mock_ollama, mock_owner):
    """Ensure missing pet name triggers a selection menu."""
    # Mocking extraction WITH missing pet_name
    json_output = '{"title": "Feed", "pet_name": null, "scheduled_time": "08:00", "confidence": 0.85}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    # Add another pet to ensure it doesn't auto-pick
    from core.models import Pet
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
    
    # Pre-populate a conflicting task at EXACTLY the same time as the mock extraction
    mock_owner.pets[0].tasks.append(Task(
        title="Existing Walk", 
        scheduled_time="14:00", 
        duration_minutes=30,
        priority="medium",
        category="walk",
        frequency="once",
        due_date="2026-04-17"
    ))
    
    with patch("ai.tools.add_task.datetime") as mock_dt, \
         patch("ai.tools.add_task.load_data", return_value=mock_owner):
        mock_dt.now.return_value = datetime(2026, 4, 17, 12, 0)
        
        result = add_task_tool("Play with Mochi at 2pm")
        
        assert isinstance(result, str)
        assert "can't lock that in" in result
        assert "Existing Walk" in result

def test_check_schedule_tool(mock_persistence, mock_ollama, mock_owner):
    """Ensure schedule checking summarizes tasks correctly."""
    mock_ollama.return_value = mock_ollama.response_class("Here is your plan for today with 1 task.")
    
    # Ensure there is a task to summary
    mock_owner.pets[0].tasks.append(Task(
        title="Morning Feed", 
        scheduled_time="08:00", 
        duration_minutes=15,
        priority="high",
        category="feeding",
        frequency="daily",
        due_date=datetime.now().strftime("%Y-%m-%d")
    ))
    
    # Patch directly in the tool's namespace to be 100% sure the mock is used
    with patch("ai.tools.schedule.load_data", return_value=mock_owner):
        result = schedule_tool("what is my schedule?")
    
    assert isinstance(result, dict)
    assert result["type"] == "show_schedule_table"
    assert result["message"] == "Here is your plan for today with 1 task."
