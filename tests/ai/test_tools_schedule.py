"""
test_tools_schedule.py
Verifies the tools related to checking the daily schedule context.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from ai.tools.schedule import schedule_tool
from core.models import Task, Pet, Owner

# ---------------------------------------------------------------------------
# Schedule Tool
# Test: schedule checking summarizes tasks correctly
# Test: clean or empty daily planner formats correctly
# Test: AI JSON is structured carefully out of text
# Test: native fallback behaves properly when network drops
# ---------------------------------------------------------------------------

def test_check_schedule_tool(mock_persistence, mock_ollama, mock_owner):
    """Ensure schedule checking summarizes tasks correctly."""
    mock_ollama.return_value = mock_ollama.response_class("Here is your plan for today with 1 task.")
    
    mock_owner.pets[0].tasks.append(Task(
        title="Morning Feed", 
        scheduled_time="08:00", 
        duration_minutes=15,
        priority="high",
        category="feeding",
        frequency="daily",
        due_date=datetime.now().strftime("%Y-%m-%d")
    ))
    
    with patch("ai.tools.schedule.load_data", return_value=mock_owner):
        result = schedule_tool("what is my schedule?")
    
    assert isinstance(result, dict)
    assert result["type"] == "show_schedule_table"
    assert result["message"] == "Here is your plan for today with 1 task."

def test_check_schedule_tool_empty(mock_persistence, mock_owner):
    """Lines 23-26: Test having an entirely clean or empty daily planner."""
    # mock_owner has pets, but no tasks are scheduled for today
    with patch("ai.tools.schedule.load_data", return_value=mock_owner):
        result = schedule_tool("what is my schedule?")
    
    assert isinstance(result, dict)
    assert result["type"] == "show_schedule_table"
    assert "completely clear for today" in result["message"]

def test_check_schedule_tool_valid_json(mock_persistence, mock_ollama, mock_owner):
    """Lines 58-60: Test extract_json properly parsing confidence and message."""
    json_output = '{"message": "Here is your structured plan JSON.", "confidence": 0.95}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    mock_owner.pets[0].tasks.append(Task(
        title="Morning Feed", 
        scheduled_time="08:00", 
        duration_minutes=15,
        priority="high",
        category="feeding",
        frequency="daily",
        due_date=datetime.now().strftime("%Y-%m-%d")
    ))
    
    with patch("ai.tools.schedule.load_data", return_value=mock_owner):
        result = schedule_tool("what is my schedule?")
    
    assert isinstance(result, dict)
    assert result["type"] == "show_schedule_table"
    assert result["message"] == "Here is your structured plan JSON."

def test_check_schedule_tool_connection_error(mock_persistence, mock_owner):
    """Lines 63-65: Test catching an underlying network exception where native fallback kicks in."""
    mock_owner.pets[0].tasks.append(Task(
        title="Morning Feed", 
        scheduled_time="08:00", 
        duration_minutes=15,
        priority="high",
        category="feeding",
        frequency="daily",
        due_date=datetime.now().strftime("%Y-%m-%d")
    ))
    
    with patch("ai.tools.schedule.load_data", return_value=mock_owner), \
         patch("ai.tools.schedule.ollama.chat", side_effect=Exception("API Error")):
        result = schedule_tool("what is my schedule?")
    
    assert isinstance(result, dict)
    assert result["type"] == "show_schedule_table"
    assert result["message"] == "Here is your completely optimized plan for today:"

