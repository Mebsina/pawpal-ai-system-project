import pytest
from unittest.mock import patch, MagicMock
from ai.tools.remove_pet import remove_pet_tool

# ---------------------------------------------------------------------------
# Remove Pet Tool
# Test: direct name matches bypass LLM extraction
# Test: natural language removal requests are extracted by LLM
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
