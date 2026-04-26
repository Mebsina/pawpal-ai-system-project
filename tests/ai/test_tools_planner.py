import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime
from ai.tools.planner import planner_tool

# ---------------------------------------------------------------------------
# Smart Scheduler Agentic Tool
# Test: happy path timeline generation
# Test: multi-turn agentic feedback loop
# Test: baseline pet care enforcement (feed/walk)
# Test: Ollama service error handling
# Test: confidence threshold early exit
# Test: refinement turn limitation (max 5)
# Test: daily time budget enforcement
# Test: invalid HH:MM time string rejection
# Test: same-category task proximity checks
# Test: schema validation failure retries
# Test: existing task conflict detection
# Test: play/grooming classification logic
# Test: no-suggestion fallback behavior
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_happy_path(mock_ollama, mock_owner):
    """Verifies structured timeline generation from valid LLM response."""
    mock_response = {
        "summary": "Here is a great plan for Mochi!",
        "suggestions": [
            {
                "pet_name": "Mochi",
                "title": "Morning Walk",
                "scheduled_time": "08:00",
                "duration_minutes": 30,
                "priority": "high",
                "category": "exercise",
                "frequency": "daily"
            },
            {
                "pet_name": "Mochi",
                "title": "Breakfast",
                "scheduled_time": "08:30",
                "duration_minutes": 15,
                "priority": "high",
                "category": "feeding",
                "frequency": "daily"
            }
        ],
        "confidence": 0.95
    }
    
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(mock_response))
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Help me plan today")
    
    assert isinstance(result, dict)
    assert result["type"] == "plan_suggestion"
    assert len(result["suggestions"]) == 2
    assert result["suggestions"][0]["pet_name"] == "Mochi"
    assert result["suggestions"][0]["scheduled_time"] == "08:00"

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_agentic_feedback_loop(mock_ollama, mock_owner):
    """Tests multi-turn feedback where Turn 1 has a conflict and Turn 2 resolves it."""
    # Turn 1: Low confidence or issues
    response_1 = {
        "summary": "Draft 1",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Conflict Task", "scheduled_time": "08:00", "duration_minutes": 10, "category": "feeding"}
        ],
        "confidence": 0.5
    }
    
    # Turn 2: Resolved - satisfies all dog care requirements (feeding×2, walk×1, play×1)
    response_2 = {
        "summary": "Draft 2",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Resolved Task", "scheduled_time": "09:00", "duration_minutes": 10, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Morning Walk", "scheduled_time": "10:00", "duration_minutes": 30, "category": "walk"},
            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "14:00", "duration_minutes": 20, "category": "play"},
            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "18:00", "duration_minutes": 10, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    mock_ollama.side_effect = [
        mock_ollama.response_class(json.dumps(response_1)),
        mock_ollama.response_class(json.dumps(response_2))
    ]
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Plan something")
    
    assert mock_ollama.call_count == 2
    assert isinstance(result, dict)
    assert result["suggestions"][0]["scheduled_time"] == "09:00"

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_enforces_baseline_care(mock_ollama, mock_owner):
    """Verifies that the tool identifies gaps (e.g., missing feeding) and re-prompts with GAP feedback."""
    # LLM fails to provide feeding on first turn
    response_1 = {
        "summary": "No food here",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Just a walk", "scheduled_time": "08:00", "duration_minutes": 20, "category": "exercise"}
        ],
        "confidence": 0.95
    }
    
    # Second turn: LLM resolves all gaps - feeding×2, walk×1, play×1 with correct spacing
    response_2 = {
        "summary": "Added food",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Just a walk", "scheduled_time": "08:00", "duration_minutes": 20, "category": "walk"},
            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "09:30", "duration_minutes": 20, "category": "play"},
            {"pet_name": "Mochi", "title": "Breakfast", "scheduled_time": "11:00", "duration_minutes": 10, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "18:00", "duration_minutes": 10, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    mock_ollama.side_effect = [
        mock_ollama.response_class(json.dumps(response_1)),
        mock_ollama.response_class(json.dumps(response_2))
    ]
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("I need a plan")
    
    assert mock_ollama.call_count == 2
    
    # Inspect the second call's messages to verify the GAP feedback was sent
    second_call_messages = mock_ollama.call_args_list[1][1]["messages"]
    feedback_message = second_call_messages[-1]["content"]
    assert "GAP:" in feedback_message
    assert "feeding" in feedback_message.lower()
    
    assert any(s["category"] == "feeding" for s in result["suggestions"])


@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_ollama_error_handling(mock_ollama, mock_owner):
    """Graceful degradation if Ollama fails."""
    mock_ollama.side_effect = Exception("Ollama is down")

    # Patch at the planner's import binding so the early-exit budget check
    # does not fire against real persisted data before Ollama is ever called.
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Help")

    assert "error while refining" in result

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_confidence_threshold_exits_early(mock_ollama, mock_owner):
    """Assert single turn when confidence is high (>= 0.9) and no issues."""
    # Satisfies all dog requirements in one turn so the loop exits immediately
    mock_response = {
        "summary": "High confidence plan",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Breakfast", "scheduled_time": "08:00", "duration_minutes": 15, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Morning Walk", "scheduled_time": "09:00", "duration_minutes": 30, "category": "walk"},
            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "14:00", "duration_minutes": 20, "category": "play"},
            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "18:00", "duration_minutes": 15, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(mock_response))
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        planner_tool("Plan today")
    
    assert mock_ollama.call_count == 1

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_refines_up_to_five_turns(mock_ollama, mock_owner):
    """If issues persist, must loop up to 5 times then stop."""
    # Always return a response with an issue (missing feeding for Mochi)
    bad_response = {
        "summary": "No feeding here",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Walk", "scheduled_time": "08:00", "duration_minutes": 20, "category": "exercise"}
        ],
        "confidence": 0.95
    }
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(bad_response))
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Plan")
    
    assert mock_ollama.call_count == 6  # 5 loop turns + 1 dynamic fallback generator turn
    assert "Here is your smart plan" in result["message"]

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_respects_daily_time_budget(mock_ollama, mock_owner):
    """Verify that the tool detects and reports when total minutes exceed available_minutes."""
    mock_owner.available_minutes = 30 # Very tight budget
    
    too_long_response = {
        "summary": "Too much work",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Epic Journey", "scheduled_time": "08:00", "duration_minutes": 120, "category": "exercise"},
            {"pet_name": "Mochi", "title": "Big Breakfast", "scheduled_time": "10:00", "duration_minutes": 60, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    # Second turn: all 4 tasks fit within the tight 30-minute budget (total = 20 min)
    fixed_response = {
        "summary": "Fixed budget",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Short Walk", "scheduled_time": "08:00", "duration_minutes": 5, "category": "walk"},
            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "08:10", "duration_minutes": 5, "category": "play"},
            {"pet_name": "Mochi", "title": "Breakfast", "scheduled_time": "08:20", "duration_minutes": 5, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "20:00", "duration_minutes": 5, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    mock_ollama.side_effect = [
        mock_ollama.response_class(json.dumps(too_long_response)),
        mock_ollama.response_class(json.dumps(fixed_response))
    ]
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Plan")
    
    assert mock_ollama.call_count == 2
    # Check that turn 2 messages contained budget overflow warning
    feedback = mock_ollama.call_args_list[1][1]["messages"][-1]["content"]
    assert "OVER_BUDGET" in feedback

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_rejects_invalid_hhmm(mock_ollama, mock_owner):
    """Times like '25:99' must be flagged in feedback."""
    bad_time_response = {
        "summary": "Time travel",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Future Feed", "scheduled_time": "25:99", "duration_minutes": 10, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    fixed_response = {
        "summary": "Real time",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Breakfast", "scheduled_time": "08:00", "duration_minutes": 15, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Morning Walk", "scheduled_time": "09:00", "duration_minutes": 30, "category": "walk"},
            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "14:00", "duration_minutes": 20, "category": "play"},
            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "18:00", "duration_minutes": 15, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    mock_ollama.side_effect = [
        mock_ollama.response_class(json.dumps(bad_time_response)),
        mock_ollama.response_class(json.dumps(fixed_response))
    ]
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        planner_tool("Plan")
        
    feedback = mock_ollama.call_args_list[1][1]["messages"][-1]["content"]
    assert "INVALID_TIME" in feedback

@pytest.mark.usefixtures("mock_persistence")
def test_suggest_schedule_same_category_proximity_check(mock_ollama, mock_owner):
    """Two feedings 15 minutes apart should be flagged and spread."""
    too_close_response = {
        "summary": "Too frequent",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Breakfast 1", "scheduled_time": "08:00", "duration_minutes": 10, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Breakfast 2", "scheduled_time": "08:15", "duration_minutes": 10, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    fixed_response = {
        "summary": "Spread out",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Breakfast", "scheduled_time": "08:00", "duration_minutes": 10, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Morning Walk", "scheduled_time": "09:00", "duration_minutes": 30, "category": "walk"},
            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "14:00", "duration_minutes": 20, "category": "play"},
            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "18:00", "duration_minutes": 10, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    mock_ollama.side_effect = [
        mock_ollama.response_class(json.dumps(too_close_response)),
        mock_ollama.response_class(json.dumps(fixed_response))
    ]
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        planner_tool("Plan")
        
    feedback = mock_ollama.call_args_list[1][1]["messages"][-1]["content"]
    assert "TOO_CLOSE" in feedback

def test_suggest_schedule_schema_validation_failure(mock_ollama, mock_owner):
    """Ensure schema validation failures trigger a retry."""
    # Turn 1: Missing "summary"
    bad_schema = {"suggestions": [], "confidence": 0.5}
    # Turn 2: Valid - full dog requirements (feeding×2, walk×1, play×1)
    good_schema = {
        "summary": "Ok", 
        "suggestions": [
            {"pet_name": "Mochi", "title": "Breakfast", "scheduled_time": "08:00", "duration_minutes": 10, "category": "feeding"},
            {"pet_name": "Mochi", "title": "Walk", "scheduled_time": "09:00", "duration_minutes": 30, "category": "walk"},
            {"pet_name": "Mochi", "title": "Playtime", "scheduled_time": "14:00", "duration_minutes": 20, "category": "play"},
            {"pet_name": "Mochi", "title": "Dinner", "scheduled_time": "18:00", "duration_minutes": 10, "category": "feeding"}
        ], 
        "confidence": 0.95
    }
    
    mock_ollama.side_effect = [
        mock_ollama.response_class(json.dumps(bad_schema)),
        mock_ollama.response_class(json.dumps(good_schema))
    ]
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        planner_tool("Plan")
    
    assert mock_ollama.call_count == 2

def test_suggest_schedule_conflict_with_existing(mock_ollama, mock_owner):
    """Ensure conflicts with existing tasks are identified."""
    from core.models import Task
    # Add an existing task at 08:00
    mock_owner.pets[0].tasks.append(Task(
        title="Existing Walk", 
        scheduled_time="08:00", 
        duration_minutes=30,
        priority="high",
        frequency="daily",
        due_date=datetime.now().strftime("%Y-%m-%d"),
        category="exercise"
    ))
    
    # LLM suggests something at exactly 08:00
    conflict_response = {
        "summary": "Conflict plan",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Conflicting Feed", "scheduled_time": "08:00", "duration_minutes": 10, "category": "feeding"}
        ],
        "confidence": 0.95
    }
    
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(conflict_response))
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Plan")
    
    # When conflicts prevent all suggestions, it returns the fallback string
    assert "couldn't identify any new tasks" in result

def test_suggest_schedule_classify_play_and_grooming(mock_ollama, mock_owner):
    """Exercise Play and Grooming classification branches."""
    response = {
        "summary": "Full plan",
        "suggestions": [
            {"pet_name": "Mochi", "title": "Play with ball", "scheduled_time": "14:00", "duration_minutes": 15, "category": "fun"},
            {"pet_name": "Mochi", "title": "Bath time", "scheduled_time": "16:00", "duration_minutes": 30, "category": "cleaning"}
        ],
        "confidence": 0.95
    }
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(response))
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        # This will cover the _classify logic for play/grooming
        planner_tool("Plan")
    
    assert mock_ollama.called

def test_suggest_schedule_no_suggestions_fallback(mock_ollama, mock_owner):
    """Ensure fallback message when no suggestions can be made."""
    mock_ollama.return_value = mock_ollama.response_class(json.dumps({
        "summary": "Nothing to add",
        "suggestions": [],
        "confidence": 0.95
    }))
    
    # Force it to have zero suggestions and no issues (so it doesn't gap-loop)
    # Actually, it will gap-loop if there's no feeding. 
    # Let's mock the owner to already have feeding/activity today.
    from core.models import Task
    today = datetime.now().strftime("%Y-%m-%d")
    mock_owner.pets[0].tasks = [
        Task(title="Feed", category="feeding", scheduled_time="08:00", due_date=today, duration_minutes=10, priority="high", frequency="daily"),
        Task(title="Walk", category="exercise", scheduled_time="10:00", due_date=today, duration_minutes=30, priority="high", frequency="daily")
    ]
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Plan")
    
    assert "couldn't identify any new tasks" in result

def test_suggest_schedule_cross_pet_overlap_detection(mock_ollama, mock_owner):
    """Verify that tasks for different pets that overlap in time are flagged."""
    # Add a task for Mochi (pet[0]): 08:00 - 08:30 (30m)
    from core.models import Task
    today = datetime.now().strftime("%Y-%m-%d")
    mock_owner.pets[0].tasks.append(Task(
        title="Mochi Walk", 
        scheduled_time="08:00", 
        duration_minutes=30,
        category="exercise",
        priority="high",
        frequency="daily",
        due_date=today
    ))
    
    # LLM suggests a task for Luna (if we mock luna or just use pet names)
    # The tool maps pet_name to existing pets.
    overlap_response = {
        "summary": "Overlapping plan",
        "suggestions": [
            {"pet_name": "Luna", "title": "Luna Walk", "scheduled_time": "08:15", "duration_minutes": 30, "priority": "high", "category": "exercise", "frequency": "daily"},
            {"pet_name": "Luna", "title": "Luna Breakfast", "scheduled_time": "07:00", "duration_minutes": 15, "priority": "high", "category": "feeding", "frequency": "daily"},
            {"pet_name": "Mochi", "title": "Mochi Breakfast", "scheduled_time": "07:20", "duration_minutes": 15, "priority": "high", "category": "feeding", "frequency": "daily"}
        ],
        "confidence": 0.95
    }
    
    # Second turn: staggered, satisfying full dog requirements for both Mochi and Luna.
    # Mochi already has an existing Walk today, so only feeding×2 and play×1 are needed.
    fixed_response = {
        "summary": "Fixed plan",
        "suggestions": [
            {"pet_name": "Luna", "title": "Luna Walk", "scheduled_time": "08:35", "duration_minutes": 30, "priority": "high", "category": "walk", "frequency": "daily"},
            {"pet_name": "Luna", "title": "Luna Breakfast", "scheduled_time": "07:00", "duration_minutes": 15, "priority": "high", "category": "feeding", "frequency": "daily"},
            {"pet_name": "Luna", "title": "Luna Dinner", "scheduled_time": "18:00", "duration_minutes": 15, "priority": "high", "category": "feeding", "frequency": "daily"},
            {"pet_name": "Luna", "title": "Luna Playtime", "scheduled_time": "13:00", "duration_minutes": 20, "priority": "medium", "category": "play", "frequency": "daily"},
            {"pet_name": "Mochi", "title": "Mochi Breakfast", "scheduled_time": "07:20", "duration_minutes": 15, "priority": "high", "category": "feeding", "frequency": "daily"},
            {"pet_name": "Mochi", "title": "Mochi Dinner", "scheduled_time": "19:00", "duration_minutes": 15, "priority": "high", "category": "feeding", "frequency": "daily"},
            {"pet_name": "Mochi", "title": "Mochi Playtime", "scheduled_time": "14:00", "duration_minutes": 20, "priority": "medium", "category": "play", "frequency": "daily"}
        ],
        "confidence": 0.95
    }
    
    mock_ollama.side_effect = [
        mock_ollama.response_class(json.dumps(overlap_response)),
        mock_ollama.response_class(json.dumps(fixed_response))
    ]
    
    # Make sure 'Luna' exists in mock_owner
    from core.models import Pet
    mock_owner.pets.append(Pet(name="Luna", species="dog", age=10))
    
    with patch("ai.tools.planner.load_data", return_value=mock_owner):
        result = planner_tool("Plan for Luna")
        
    assert mock_ollama.call_count == 2
    feedback = mock_ollama.call_args_list[1][1]["messages"][-1]["content"]
    assert "CONFLICT" in feedback
    assert "Luna Walk" in feedback
    assert "Mochi Walk" in feedback
    # Assert Luna Walk is now at 08:35
    luna_walk = next(s for s in result["suggestions"] if s["title"] == "Luna Walk")
    assert luna_walk["scheduled_time"] == "08:35"
