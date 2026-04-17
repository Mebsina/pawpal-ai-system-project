import pytest
import json
from unittest.mock import patch, MagicMock
from ai.tools.list_pets import list_pets_tool

# ---------------------------------------------------------------------------
# List Pets Tool
# Test: listing pets generates a summary string with emojis
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_persistence")
def test_list_pets_tool(mock_ollama, mock_owner):
    """Ensure listing pets generates a summary string with emojis."""
    mock_response = {
        "message": "Here are your pets: 🐶 Mochi",
        "confidence": 0.99
    }
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(mock_response))
    
    with patch("ai.tools.list_pets.load_data", return_value=mock_owner):
        result = list_pets_tool("show my pets")
    
    assert isinstance(result, str)
    assert "Mochi" in result
    assert "🐶" in result

@pytest.mark.usefixtures("mock_persistence")
def test_list_pets_tool_empty_registry(mock_ollama, mock_owner):
    """Owner with zero pets — message should invite adding one."""
    mock_owner.pets = []
    
    with patch("ai.tools.list_pets.load_data", return_value=mock_owner):
        result = list_pets_tool("what pets do I have?")
    
    assert "haven't registered any pets yet" in result
    assert mock_ollama.call_count == 0

@pytest.mark.usefixtures("mock_persistence")
def test_list_pets_tool_species_emojis(mock_ollama, mock_owner):
    """Verify species-specific emoji branching (🐶 for dogs, 🐱 for cats)."""
    # Force species to cat for one pet
    mock_owner.pets[0].species = "cat"
    
    # We need to capture the system prompt sent to Ollama
    mock_response = {"message": "Summary with cats", "confidence": 0.9}
    mock_ollama.return_value = mock_ollama.response_class(json.dumps(mock_response))
    
    with patch("ai.tools.list_pets.load_data", return_value=mock_owner):
        list_pets_tool("list pets")
        
    system_prompt = mock_ollama.call_args_list[0][1]["messages"][0]["content"]
    assert "🐱" in system_prompt
    assert "🐶" not in system_prompt # Since we have only 1 pet and it's a cat
