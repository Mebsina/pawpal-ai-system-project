import pytest
from unittest.mock import patch, MagicMock
from ai.tools.add_pet import add_pet_tool

# ---------------------------------------------------------------------------
# Add Pet Tool
# Test: valid AI extraction results in a pet add confirmation
# Test: missing pet age triggers a follow-up question
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("mock_persistence")
def test_add_pet_tool_success(mock_ollama, mock_owner):
    """Ensure valid AI extraction results in a pet add confirmation."""
    json_output = '{"name": "Bella", "species": "dog", "age": 2, "special_needs": ["none"], "confidence": 0.98}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a 2 year old dog named Bella")
    
    assert isinstance(result, dict)
    assert result["type"] == "pet_add_confirmation"
    assert result["pet_data"]["name"] == "Bella"
    assert result["pet_data"]["age"] == 2

@pytest.mark.usefixtures("mock_persistence")
def test_add_pet_tool_missing_age(mock_ollama, mock_owner):
    """Ensure missing age triggers a follow-up question."""
    json_output = '{"name": "Bella", "species": "dog", "age": null, "confidence": 0.8}'
    mock_ollama.return_value = mock_ollama.response_class(json_output)
    
    with patch("ai.tools.add_pet.load_data", return_value=mock_owner):
        result = add_pet_tool("add a dog named Bella")
    
    assert isinstance(result, str)
    assert "how old is **Bella**" in result
