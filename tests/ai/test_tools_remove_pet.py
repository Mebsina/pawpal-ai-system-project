import pytest
from unittest.mock import patch, MagicMock
from ai.tools.remove_pet import remove_pet_tool

# ---------------------------------------------------------------------------
# Remove Pet Tool
# Test: direct name matches bypass LLM extraction
# Test: natural language removal requests are extracted by LLM
# Test: requesting removal of a non-existent pet refusal
# Test: generic removal inquiries trigger a selection menu
# Test: Ollama service failure fallback to selection menu
# Test: malformed JSON extraction failure resilience
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_persistence")
def test_remove_pet_tool_direct_match(mock_owner):
    """Ensure direct name matches bypass LLM extraction."""
    # Mochi is already in mock_owner.pets
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        result = remove_pet_tool("Mochi")
    
    assert isinstance(result, dict)
    assert result["type"] == "pet_remove_confirmation"
    assert result["pet_name"] == "Mochi"

@pytest.mark.usefixtures("mock_persistence")
def test_remove_pet_tool_llm_fallback(mock_ollama, mock_owner):
    """Ensure natural language removal requests are extracted by LLM."""
    mock_ollama.return_value = mock_ollama.response_class('{"pet_name": "Mochi", "confidence": 0.99}')
    
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        result = remove_pet_tool("i need to rehome Mochi")
    
    assert isinstance(result, dict)
    assert result["type"] == "pet_remove_confirmation"
    assert result["pet_name"] == "Mochi"
    mock_ollama.assert_called_once()

@pytest.mark.usefixtures("mock_persistence")
def test_remove_pet_tool_nonexistent_pet(mock_ollama, mock_owner):
    """Requesting removal of 'Bella' when only 'Mochi' exists must refuse gracefully."""
    # LLM might correctly identify 'Bella' but it's not in our registry
    mock_ollama.return_value = mock_ollama.response_class('{"pet_name": "Bella", "confidence": 0.99}')
    
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        result = remove_pet_tool("remove Bella")
    
    assert result["type"] == "selection_menu"
    assert "not sure which pet" in result["message"]
    assert "Mochi" in result["options"]

@pytest.mark.usefixtures("mock_persistence")
def test_remove_pet_tool_no_hallucinated_auto_pick(mock_ollama, mock_owner):
    """Ensure generic removal inquiries trigger a menu, not an LLM guess."""
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        result = remove_pet_tool("remove a pet")
    
    assert result["type"] == "selection_menu"
    assert "Which pet" in result["message"]
    assert mock_ollama.call_count == 0

def test_remove_pet_tool_extraction_failure(mock_ollama, mock_owner):
    """Ensure malformed JSON extraction returns a generic response."""
    mock_ollama.return_value = mock_ollama.response_class("This is not JSON")
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        result = remove_pet_tool("get rid of it")
    assert result["type"] == "selection_menu"
    assert "not sure which pet" in result["message"]

def test_remove_pet_tool_ollama_failure(mock_ollama, mock_owner):
    """Ensure API failures are handled gracefully."""
    with patch("ai.tools.remove_pet.load_data", return_value=mock_owner):
        mock_ollama.side_effect = Exception("Ollama disconnected")
        # Note: direct match happens BEFORE ollama.chat, so we need a query that triggers LLM
        result = remove_pet_tool("I want to rehome it")
        assert result["type"] == "selection_menu"
        assert "not sure which pet" in result["message"]
